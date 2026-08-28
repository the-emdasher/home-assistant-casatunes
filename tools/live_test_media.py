#!/usr/bin/env python3
"""Guardedly validate CasaTunes enqueue and clear without starting playback."""

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

from casatunes_api import CasaTunesClient, PlayerStatus, Zone  # noqa: E402


@dataclass(frozen=True, slots=True)
class ZoneState:
    power: bool
    mute: bool
    volume: int
    source_id: int

    @classmethod
    def from_zone(cls, zone: Zone) -> ZoneState:
        return cls(zone.power, zone.mute, zone.volume, zone.source_id)


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


async def _restore_zone(
    client: CasaTunesClient,
    zone_id: str,
    original: ZoneState,
) -> None:
    current = next(
        zone
        for zone in await client.async_get_zones()
        if zone.persistent_zone_id == zone_id
    )
    if not current.power:
        await client.async_update_zone(zone_id, Power=True)
        await asyncio.sleep(1)
    await client.async_update_zone(
        zone_id,
        SourceID=original.source_id,
        Volume=original.volume,
    )
    await asyncio.sleep(1)
    await client.async_update_zone(
        zone_id,
        Power=original.power,
        Mute=original.mute,
    )
    await asyncio.sleep(3)


async def _async_run(host: str, port: int, zone_name: str) -> dict[str, object]:
    async with aiohttp.ClientSession() as session:
        client = CasaTunesClient(host, session, port=port)
        snapshot = await client.async_get_snapshot()
        zone = _find_visible_zone(snapshot.zones, zone_name)
        original = ZoneState.from_zone(zone)
        if any(item.power for item in snapshot.zones):
            raise RuntimeError("Guarded media test requires every zone to be off")

        original_queue = await client.async_get_zone_queue(zone.persistent_zone_id)
        if original_queue.total_available or original_queue.media_items:
            raise RuntimeError("Guarded media test requires an empty target queue")
        original_now_playing = snapshot.now_playing_by_source_id.get(zone.source_id)
        if (
            original_now_playing is None
            or original_now_playing.status != PlayerStatus.STOPPED
        ):
            raise RuntimeError("Guarded media test requires a stopped source")

        root = await client.async_browse_zone(zone.persistent_zone_id)
        expandable = next((item for item in root.media_items if item.can_expand), None)
        if expandable is None:
            raise RuntimeError("No expandable media root is available")
        child = await client.async_browse_media(expandable.id)
        playable = next((item for item in child.media_items if item.can_play), None)
        if playable is None:
            raise RuntimeError("No queueable media item is available")

        added_result: int | None = None
        queued_count = 0
        zone_after_enqueue: ZoneState | None = None
        status_after_enqueue: int | None = None
        try:
            await client.async_update_zone(zone.persistent_zone_id, Mute=True)
            await client.async_update_zone(
                zone.persistent_zone_id,
                Power=True,
                Mute=True,
            )
            await asyncio.sleep(1)
            added_result = await client.async_play_media(
                zone.persistent_zone_id,
                playable.id,
                add_to_queue=True,
                auto_start=False,
            )
            queued = await client.async_get_zone_queue(zone.persistent_zone_id)
            queued_count = queued.total_available
            if queued_count < 1 or not queued.media_items:
                raise RuntimeError("CasaTunes did not add the media item to the queue")
            zone_after_enqueue = ZoneState.from_zone(
                _find_visible_zone(await client.async_get_zones(), zone_name)
            )
            now_playing = await client.async_get_now_playing()
            status_after_enqueue = next(
                (
                    item.status
                    for item in now_playing
                    if item.source_id == original.source_id
                ),
                None,
            )
        finally:
            try:
                await client.async_clear_queue(zone.persistent_zone_id)
            finally:
                try:
                    await client.async_player_action(zone.persistent_zone_id, "stop")
                finally:
                    await _restore_zone(client, zone.persistent_zone_id, original)

        final_queue = await client.async_get_zone_queue(zone.persistent_zone_id)
        final_zone = _find_visible_zone(await client.async_get_zones(), zone_name)
        final = ZoneState.from_zone(final_zone)
        if final_queue.total_available or final_queue.media_items:
            raise RuntimeError("Queue restoration failed")
        if final != original:
            raise RuntimeError(
                f"Zone changed during queue test: expected {original}, received {final}"
            )

    return {
        "zone": zone_name,
        "original_state": asdict(original),
        "play_result": added_result,
        "queued_count": queued_count,
        "status_after_enqueue": status_after_enqueue,
        "zone_after_enqueue": (
            asdict(zone_after_enqueue) if zone_after_enqueue is not None else None
        ),
        "queue_restored": True,
        "zone_restored": True,
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
        help="Required acknowledgement that this script changes the live queue",
    )
    args = parser.parse_args()
    if not args.execute:
        parser.error("--execute is required")
    result = asyncio.run(_async_run(args.host, args.port, args.zone))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
