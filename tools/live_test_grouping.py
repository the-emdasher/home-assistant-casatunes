#!/usr/bin/env python3
"""Guardedly join two CasaTunes zones, ungroup them, and restore both."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import aiohttp

sys.path.insert(
    0,
    str(Path(__file__).parents[1] / "custom_components" / "casatunes"),
)

from casatunes_api import (  # noqa: E402
    CasaTunesClient,
    MediaQueue,
    NowPlaying,
    PlayerStatus,
    Zone,
)


@dataclass(frozen=True, slots=True)
class ZoneState:
    """Zone fields that grouping is allowed to disturb temporarily."""

    power: bool
    mute: bool
    volume: int
    source_id: int
    shared: bool
    shared_room_id: str | None
    group_name: str
    group_info: tuple[dict[str, Any], ...]

    @classmethod
    def from_zone(cls, zone: Zone) -> ZoneState:
        return cls(
            power=zone.power,
            mute=zone.mute,
            volume=zone.volume,
            source_id=zone.source_id,
            shared=zone.shared,
            shared_room_id=zone.shared_room_id,
            group_name=zone.group_name,
            group_info=zone.group_info,
        )


def _find_visible_zone(zones: tuple[Zone, ...], name: str) -> Zone:
    matches = [
        zone
        for zone in zones
        if not zone.hidden and zone.name.casefold() == name.casefold()
    ]
    if len(matches) != 1:
        raise RuntimeError(
            f"Expected exactly one visible zone named {name!r}; found {len(matches)}"
        )
    return matches[0]


def _find_zone_by_id(zones: tuple[Zone, ...], zone_id: str) -> Zone:
    matches = [zone for zone in zones if zone.persistent_zone_id == zone_id]
    if len(matches) != 1:
        raise RuntimeError(f"Expected exactly one zone with ID {zone_id!r}")
    return matches[0]


def _group_member_ids(zone: Zone) -> set[int]:
    member_ids: set[int] = set()
    for item in zone.group_info:
        raw_id = item.get("zoneId", item.get("ZoneID", item.get("zoneID")))
        if isinstance(raw_id, int) and not isinstance(raw_id, bool):
            member_ids.add(raw_id)
    return member_ids


def _pair_is_grouped(zones: tuple[Zone, ...], master: Zone, member: Zone) -> bool:
    pair = {master.zone_id, member.zone_id}
    if any(pair <= _group_member_ids(zone) for zone in zones):
        return True
    current = {
        zone.persistent_zone_id: zone
        for zone in zones
        if zone.persistent_zone_id
        in {master.persistent_zone_id, member.persistent_zone_id}
    }
    return len(current) == 2 and (
        any(zone.shared_room_id for zone in current.values())
        or all(zone.shared or bool(zone.group_info) for zone in current.values())
    )


def _group_summary(zones: tuple[Zone, ...], master: Zone, member: Zone) -> list[dict]:
    pair = {master.zone_id, member.zone_id}
    related = []
    for zone in zones:
        group_ids = _group_member_ids(zone)
        if (
            zone.zone_id in pair
            or pair <= group_ids
            or (zone.zone_id >= 1000 and group_ids & pair)
        ):
            related.append(
                {
                    "zone_id": zone.zone_id,
                    "name": zone.name,
                    "power": zone.power,
                    "mute": zone.mute,
                    "volume": zone.volume,
                    "source_id": zone.source_id,
                    "shared": zone.shared,
                    "shared_room_id": zone.shared_room_id,
                    "group_name": zone.group_name,
                    "group_info": list(zone.group_info),
                }
            )
    return related


async def _settled_zones(
    client: CasaTunesClient, *, delay: float = 1.5
) -> tuple[Zone, ...]:
    await asyncio.sleep(delay)
    return await client.async_get_zones()


async def _wait_for_group(
    client: CasaTunesClient,
    master: Zone,
    member: Zone,
    *,
    wait_seconds: float = 12.0,
) -> tuple[tuple[Zone, ...], float]:
    """Poll because CasaTunes creates its virtual group asynchronously."""
    loop = asyncio.get_running_loop()
    started = loop.time()
    zones: tuple[Zone, ...] = ()
    while loop.time() - started < wait_seconds:
        await asyncio.sleep(1.0)
        zones = await client.async_get_zones()
        elapsed = loop.time() - started
        if _pair_is_grouped(zones, master, member):
            return zones, elapsed
    return zones, loop.time() - started


async def _restore_zone(
    client: CasaTunesClient, zone_id: str, original: ZoneState
) -> None:
    # This controller ignores volume changes while a zone is off, so briefly power
    # it before restoring source and volume. Both guarded source players are stopped.
    current = _find_zone_by_id(await client.async_get_zones(), zone_id)
    if not current.power:
        await client.async_update_zone(zone_id, Power=True)
        await _settled_zones(client, delay=1.0)
    await client.async_update_zone(
        zone_id,
        SourceID=original.source_id,
        Volume=original.volume,
    )
    zones = await _settled_zones(client, delay=1.0)
    restored = _find_zone_by_id(zones, zone_id)
    if restored.volume != original.volume or restored.source_id != original.source_id:
        raise RuntimeError("Could not restore a zone's original source and volume")
    # Selecting a network-player source can resume its queued session after a
    # delay. The guarded precondition says the original transport was stopped.
    await client.async_player_action(zone_id, "stop")
    await asyncio.sleep(1.0)
    await client.async_update_zone(
        zone_id,
        Power=original.power,
        Mute=original.mute,
    )
    zones = await _settled_zones(client, delay=3.0)
    final = _find_zone_by_id(zones, zone_id)
    if ZoneState.from_zone(final) != original:
        raise RuntimeError(
            f"Zone did not settle at its original state: {ZoneState.from_zone(final)}"
        )


async def _ungroup_pair(
    client: CasaTunesClient, master: Zone, member: Zone
) -> tuple[tuple[Zone, ...], str]:
    """Try member self-removal first, then leader and numeric-ID fallbacks."""
    attempts = (
        (
            member.persistent_zone_id,
            member.persistent_zone_id,
            "member removes itself",
        ),
        (
            master.persistent_zone_id,
            member.persistent_zone_id,
            "leader removes member",
        ),
        (master.persistent_zone_id, str(member.zone_id), "numeric member fallback"),
        (str(master.zone_id), str(member.zone_id), "numeric IDs fallback"),
    )
    errors: list[str] = []
    for group_id, grouped_zone_id, label in attempts:
        try:
            await client.async_ungroup_zone(group_id, grouped_zone_id)
        except Exception as err:  # Continue only to the narrow recovery variants.
            errors.append(f"{type(err).__name__}: {err}")
        zones = await _settled_zones(client)
        if not _pair_is_grouped(zones, master, member):
            return zones, label
    raise RuntimeError(
        "CasaTunes still reports the zones as grouped after recovery attempts: "
        + "; ".join(errors)
    )


def _require_protected_queue(queue: MediaQueue, zone_name: str) -> None:
    if queue.start_index != 0 or queue.total_available != len(queue.media_items):
        raise RuntimeError(
            f"Guarded grouping requires the entire {zone_name} queue to fit in one page"
        )


def _require_stopped_source(now_playing: NowPlaying | None, zone_name: str) -> None:
    if now_playing is None or now_playing.status != PlayerStatus.STOPPED:
        raise RuntimeError(
            f"Guarded grouping requires {zone_name}'s source to be stopped"
        )


async def _async_run(
    host: str,
    port: int,
    master_name: str,
    member_name: str,
) -> dict[str, object]:
    async with aiohttp.ClientSession() as session:
        client = CasaTunesClient(host, session, port=port)
        snapshot = await client.async_get_snapshot()
        master = _find_visible_zone(snapshot.zones, master_name)
        member = _find_visible_zone(snapshot.zones, member_name)
        if master.persistent_zone_id == member.persistent_zone_id:
            raise RuntimeError("Grouping test requires two different zones")
        if any(zone.power for zone in snapshot.zones):
            raise RuntimeError(
                "Guarded grouping requires every CasaTunes zone to be off"
            )
        if any(
            zone.shared or zone.shared_room_id or zone.group_info
            for zone in snapshot.zones
        ):
            raise RuntimeError("Guarded grouping requires no pre-existing active group")

        groupable = await client.async_get_groupable_zones(master.persistent_zone_id)
        if not any(
            zone.persistent_zone_id == member.persistent_zone_id for zone in groupable
        ):
            raise RuntimeError(
                f"CasaTunes does not report {member_name} as groupable with "
                f"{master_name}"
            )

        original_states = {
            master.persistent_zone_id: ZoneState.from_zone(master),
            member.persistent_zone_id: ZoneState.from_zone(member),
        }
        original_queues = {
            master.persistent_zone_id: await client.async_get_zone_queue(
                master.persistent_zone_id
            ),
            member.persistent_zone_id: await client.async_get_zone_queue(
                member.persistent_zone_id
            ),
        }
        for zone in (master, member):
            _require_protected_queue(
                original_queues[zone.persistent_zone_id], zone.name
            )
            _require_stopped_source(
                snapshot.now_playing_by_source_id.get(zone.source_id), zone.name
            )
        original_players = {
            source_id: snapshot.now_playing_by_source_id[source_id]
            for source_id in {master.source_id, member.source_id}
        }

        after_join: tuple[Zone, ...] = ()
        ungrouped: tuple[Zone, ...] = ()
        ungroup_method: str | None = None
        virtual_group: Zone | None = None
        requested_group_id: str | None = None
        virtual_group_error: str | None = None
        group_detected_after: float | None = None
        join_attempted = False
        try:
            # CasaTunes joins the second room to the leader's current audio
            # session. An off leader accepts the command but does not create a
            # group, so make the stopped, empty leader source active first.
            await client.async_update_zone(
                master.persistent_zone_id,
                Power=True,
                Mute=False,
                SourceID=master.source_id,
                Volume=master.volume,
            )
            await _settled_zones(client, delay=2.0)
            await client.async_player_action(master.persistent_zone_id, "stop")
            join_attempted = True
            await client.async_join_zone(
                member.persistent_zone_id,
                master.persistent_zone_id,
            )
            after_join, group_detected_after = await _wait_for_group(
                client, master, member
            )
            if not _pair_is_grouped(after_join, master, member):
                print(
                    json.dumps(
                        {
                            "diagnostic": "join returned success without a group",
                            "observed_zones": _group_summary(
                                after_join, master, member
                            ),
                        },
                        indent=2,
                    ),
                    flush=True,
                )
                raise RuntimeError(
                    "CasaTunes accepted the join but did not expose a two-zone "
                    "group within 12 seconds"
                )
            shared_room_ids = {
                zone.shared_room_id
                for zone in after_join
                if zone.zone_id in {master.zone_id, member.zone_id}
                and zone.shared_room_id
            }
            if len(shared_room_ids) == 1:
                try:
                    requested_group_id = shared_room_ids.pop()
                    virtual_group = await client.async_get_zone(requested_group_id)
                except Exception as err:
                    virtual_group_error = f"{type(err).__name__}: {err}"
        finally:
            cleanup_errors: list[str] = []
            if join_attempted:
                try:
                    ungrouped, ungroup_method = await _ungroup_pair(
                        client, master, member
                    )
                except Exception as err:
                    cleanup_errors.append(f"ungroup: {err}")
            for zone in (master, member):
                try:
                    await _restore_zone(
                        client,
                        zone.persistent_zone_id,
                        original_states[zone.persistent_zone_id],
                    )
                except Exception as err:
                    cleanup_errors.append(f"restore {zone.name}: {err}")
            try:
                cleanup_snapshot = await client.async_get_snapshot()
                if any(
                    zone.shared or zone.shared_room_id or zone.group_info
                    for zone in cleanup_snapshot.zones
                ):
                    cleanup_errors.append("CasaTunes still reports an active group")
                for zone in (master, member):
                    cleaned_zone = _find_zone_by_id(
                        cleanup_snapshot.zones, zone.persistent_zone_id
                    )
                    if (
                        ZoneState.from_zone(cleaned_zone)
                        != original_states[zone.persistent_zone_id]
                    ):
                        cleanup_errors.append(
                            f"{zone.name} does not match its original state"
                        )
                    cleaned_queue = await client.async_get_zone_queue(
                        zone.persistent_zone_id
                    )
                    if cleaned_queue != original_queues[zone.persistent_zone_id]:
                        cleanup_errors.append(f"{zone.name} queue changed")
                for source_id, original_player in original_players.items():
                    cleaned_player = cleanup_snapshot.now_playing_by_source_id.get(
                        source_id
                    )
                    if cleaned_player is None or (
                        cleaned_player.status,
                        cleaned_player.queue_count,
                        cleaned_player.repeat_mode,
                        cleaned_player.shuffle_mode,
                    ) != (
                        original_player.status,
                        original_player.queue_count,
                        original_player.repeat_mode,
                        original_player.shuffle_mode,
                    ):
                        cleanup_errors.append(
                            f"source {source_id} transport state changed"
                        )
            except Exception as err:
                cleanup_errors.append(f"cleanup audit: {err}")
            if cleanup_errors:
                raise RuntimeError(
                    "Grouping cleanup failed: " + "; ".join(cleanup_errors)
                )

        final_snapshot = await client.async_get_snapshot()
        final_queues = {
            master.persistent_zone_id: await client.async_get_zone_queue(
                master.persistent_zone_id
            ),
            member.persistent_zone_id: await client.async_get_zone_queue(
                member.persistent_zone_id
            ),
        }
        for zone in (master, member):
            final_zone = _find_zone_by_id(final_snapshot.zones, zone.persistent_zone_id)
            expected = original_states[zone.persistent_zone_id]
            if ZoneState.from_zone(final_zone) != expected:
                raise RuntimeError(
                    f"{zone.name} restoration failed: expected {expected}, "
                    f"received {ZoneState.from_zone(final_zone)}"
                )
            if (
                final_queues[zone.persistent_zone_id]
                != original_queues[zone.persistent_zone_id]
            ):
                raise RuntimeError(f"{zone.name} queue changed during grouping test")
        if _pair_is_grouped(final_snapshot.zones, master, member):
            raise RuntimeError("The two zones remain grouped after restoration")

        return {
            "master": master.name,
            "joined_zone": member.name,
            "original_states": {
                master.name: asdict(original_states[master.persistent_zone_id]),
                member.name: asdict(original_states[member.persistent_zone_id]),
            },
            "original_queue_counts": {
                master.name: original_queues[master.persistent_zone_id].total_available,
                member.name: original_queues[member.persistent_zone_id].total_available,
            },
            "group_topology": _group_summary(after_join, master, member),
            "group_detected_after_seconds": group_detected_after,
            "virtual_group": (
                {
                    "zone_id": virtual_group.zone_id,
                    "name": virtual_group.name,
                    "persistent_id_matches_shared_room": virtual_group.shared_room_id
                    == requested_group_id
                    or virtual_group.persistent_zone_id == requested_group_id,
                    "shared": virtual_group.shared,
                    "shared_room_id": virtual_group.shared_room_id,
                    "group_name": virtual_group.group_name,
                    "group_info": list(virtual_group.group_info),
                }
                if virtual_group is not None
                else None
            ),
            "virtual_group_error": virtual_group_error,
            "ungroup_method": ungroup_method,
            "ungrouped_topology": _group_summary(ungrouped, master, member),
            "restored": True,
            "queues_unchanged": True,
        }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("host")
    parser.add_argument("master_zone")
    parser.add_argument("joining_zone")
    parser.add_argument("--port", type=int, default=8735)
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Required acknowledgement that this script changes two live zones",
    )
    args = parser.parse_args()
    if not args.execute:
        parser.error("--execute is required")
    result = asyncio.run(
        _async_run(
            args.host,
            args.port,
            args.master_zone,
            args.joining_zone,
        )
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
