#!/usr/bin/env python3
"""Run guarded CasaTunes zone controls and restore the original state."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

import aiohttp

sys.path.insert(
    0,
    str(Path(__file__).parents[1] / "custom_components" / "casatunes"),
)

from casatunes_api import (  # noqa: E402
    CasaTunesClient,
    PlayerStatus,
    SourceControlType,
    Zone,
)


@dataclass(slots=True)
class ZoneState:
    power: bool
    mute: bool
    volume: int
    source_id: int

    @classmethod
    def from_zone(cls, zone: Zone) -> ZoneState:
        return cls(
            power=zone.power,
            mute=zone.mute,
            volume=zone.volume,
            source_id=zone.source_id,
        )


def _find_visible_zone(zones: tuple[Zone, ...], name: str) -> Zone:
    matches = [zone for zone in zones if zone.name.casefold() == name.casefold()]
    visible = [zone for zone in matches if not zone.hidden]
    if len(visible) != 1:
        raise RuntimeError(
            f"Expected exactly one visible zone named {name!r}; found {len(visible)}"
        )
    return visible[0]


def _find_zone_by_id(zones: tuple[Zone, ...], zone_id: str) -> Zone:
    matches = [zone for zone in zones if zone.persistent_zone_id == zone_id]
    if len(matches) != 1:
        raise RuntimeError(f"Expected exactly one zone with ID {zone_id!r}")
    return matches[0]


async def _get_settled_zone(
    client: CasaTunesClient, zone_id: str, *, delay: float = 1.0
) -> Zone:
    """Wait for matrix transitions, then fetch rather than trust the command reply."""
    await asyncio.sleep(delay)
    return _find_zone_by_id(await client.async_get_zones(), zone_id)


async def _restore_transport(
    client: CasaTunesClient, zone_id: str, original_status: int | None
) -> None:
    if original_status == PlayerStatus.PLAYING:
        await client.async_player_action(zone_id, "play")
    elif original_status == PlayerStatus.PAUSED:
        await client.async_player_action(zone_id, "pause")
    elif original_status is not None:
        await client.async_player_action(zone_id, "stop")


async def _restore_zone(
    client: CasaTunesClient, zone_id: str, original: ZoneState
) -> None:
    # This controller reports volume 0 while muted and ignores volume while off.
    current = _find_zone_by_id(await client.async_get_zones(), zone_id)
    if not current.power:
        await client.async_update_zone(zone_id, Power=True)
        await _get_settled_zone(client, zone_id)
    await client.async_update_zone(
        zone_id,
        SourceID=original.source_id,
        Volume=original.volume,
    )
    restored_volume = await _get_settled_zone(client, zone_id)
    if restored_volume.volume != original.volume:
        raise RuntimeError("Could not restore the zone's original volume")
    await client.async_update_zone(
        zone_id,
        Power=original.power,
        Mute=original.mute,
    )
    await _get_settled_zone(client, zone_id, delay=3.0)


async def _async_run(host: str, port: int, zone_name: str) -> dict[str, object]:
    steps: list[dict[str, object]] = []
    async with aiohttp.ClientSession() as session:
        client = CasaTunesClient(host, session, port=port)
        snapshot = await client.async_get_snapshot()
        zone = _find_visible_zone(snapshot.zones, zone_name)
        original = ZoneState.from_zone(zone)

        other_powered_zones = [
            item for item in snapshot.zones if item.power and item != zone
        ]
        if other_powered_zones:
            raise RuntimeError(
                "Aborting because another powered zone could share a source"
            )

        original_now_playing = snapshot.now_playing_by_source_id.get(zone.source_id)
        original_status = (
            original_now_playing.status if original_now_playing is not None else None
        )
        alternate_source = next(
            (
                source
                for source in snapshot.sources
                if not source.hidden
                and source.source_id != zone.source_id
                and zone.supports_source(source.source_id)
                and not source.is_shared
            ),
            None,
        )
        current_source = snapshot.sources_by_id.get(zone.source_id)
        if original.power or original.mute:
            raise RuntimeError(
                "Guarded test requires the target zone to be off and unmuted"
            )
        if (
            current_source is None
            or not current_source.control_type & SourceControlType.MEDIA_PLAYER
            or original_now_playing is None
            or original_now_playing.status != PlayerStatus.STOPPED
            or original_now_playing.queue_count != 0
        ):
            raise RuntimeError(
                "Guarded test requires a stopped media-player source "
                "with an empty queue"
            )

        increment = snapshot.system.volume_settings.increment
        stepped_volume = min(
            original.volume + increment,
            snapshot.system.volume_settings.maximum,
        )
        if stepped_volume == original.volume:
            raise RuntimeError("Original volume leaves no room for a safe upward step")

        try:
            await client.async_update_zone(zone.persistent_zone_id, Mute=True)
            await client.async_update_zone(
                zone.persistent_zone_id, Power=True, Mute=True
            )
            await _get_settled_zone(client, zone.persistent_zone_id)
            await client.async_update_zone(
                zone.persistent_zone_id, Volume=original.volume
            )
            updated = await _get_settled_zone(client, zone.persistent_zone_id)
            steps.append(
                {
                    "control": "power_on_and_restore_valid_volume",
                    "power": updated.power,
                    "mute": updated.mute,
                    "volume": updated.volume,
                }
            )
            if updated.mute or updated.volume != original.volume:
                raise RuntimeError("Zone did not settle at its original valid volume")

            await client.async_update_zone(
                zone.persistent_zone_id,
                AdjustVolume=increment,
            )
            stepped = await _get_settled_zone(client, zone.persistent_zone_id)
            steps.append(
                {
                    "control": "volume_up",
                    "volume": stepped.volume,
                }
            )
            if stepped.volume != stepped_volume:
                raise RuntimeError("Zone volume-up did not produce the expected value")

            await client.async_update_zone(
                zone.persistent_zone_id,
                AdjustVolume=-increment,
            )
            stepped_back = await _get_settled_zone(client, zone.persistent_zone_id)
            steps.append(
                {
                    "control": "volume_down",
                    "volume": stepped_back.volume,
                }
            )
            if stepped_back.volume != original.volume:
                raise RuntimeError(
                    "Zone volume-down did not restore the original value"
                )

            muted = await client.async_update_zone(zone.persistent_zone_id, Mute=True)
            steps.append(
                {
                    "control": "mute",
                    "mute": muted.mute,
                    "reported_volume": muted.volume,
                }
            )
            if not muted.mute:
                raise RuntimeError("Zone did not mute")

            if alternate_source is not None:
                selected = await client.async_update_zone(
                    zone.persistent_zone_id, SourceID=alternate_source.source_id
                )
                steps.append(
                    {
                        "control": "select_source",
                        "source_changed": selected.source_id
                        == alternate_source.source_id,
                    }
                )
                await client.async_update_zone(
                    zone.persistent_zone_id, SourceID=original.source_id
                )

            if (
                current_source is not None
                and current_source.control_type & SourceControlType.MEDIA_PLAYER
            ):
                await client.async_player_action(zone.persistent_zone_id, "play")
                await asyncio.sleep(0.5)
                played = await client.async_get_now_playing()
                played_state = next(
                    (
                        item.status
                        for item in played
                        if item.source_id == original.source_id
                    ),
                    None,
                )
                await client.async_player_action(zone.persistent_zone_id, "stop")
                steps.append(
                    {
                        "control": "transport_play_stop",
                        "status_after_play": played_state,
                    }
                )
        finally:
            await _restore_transport(client, zone.persistent_zone_id, original_status)
            await _restore_zone(client, zone.persistent_zone_id, original)

        final_zone = _find_visible_zone(await client.async_get_zones(), zone_name)
        final = ZoneState.from_zone(final_zone)
        if final != original:
            raise RuntimeError(
                f"Zone restoration failed: expected {original}, received {final}"
            )

    return {
        "zone": zone_name,
        "original_state": asdict(original),
        "steps": steps,
        "restored": True,
        "final_state": asdict(final),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("host")
    parser.add_argument("zone")
    parser.add_argument("--port", type=int, default=8735)
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Required acknowledgement that this script changes live zone state",
    )
    args = parser.parse_args()
    if not args.execute:
        parser.error("--execute is required")
    result = asyncio.run(_async_run(args.host, args.port, args.zone))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
