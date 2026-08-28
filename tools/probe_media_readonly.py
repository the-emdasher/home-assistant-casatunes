#!/usr/bin/env python3
"""Probe CasaTunes media browsing and queue shapes without changing state."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

import aiohttp

sys.path.insert(
    0,
    str(Path(__file__).parents[1] / "custom_components" / "casatunes"),
)

from casatunes_api import CasaTunesClient  # noqa: E402


async def _async_probe(host: str, port: int, zone_name: str) -> dict[str, object]:
    async with aiohttp.ClientSession() as session:
        client = CasaTunesClient(host, session, port=port)
        zones = await client.async_get_zones()
        matches = [
            zone
            for zone in zones
            if not zone.hidden and zone.name.casefold() == zone_name.casefold()
        ]
        if len(matches) != 1:
            raise RuntimeError(
                f"Expected one visible zone named {zone_name!r}; found {len(matches)}"
            )
        zone = matches[0]
        root = await client.async_browse_zone(zone.persistent_zone_id)
        queue = await client.async_get_zone_queue(zone.persistent_zone_id)
        expandable = next((item for item in root.media_items if item.can_expand), None)
        child = (
            await client.async_browse_media(expandable.id)
            if expandable is not None
            else None
        )
        search = await client.async_search_zone(
            zone.persistent_zone_id,
            "__casatunes_ha_no_match_probe__",
        )

    return {
        "zone": zone_name,
        "root_item_count": len(root.media_items),
        "root_total_available": root.total_available,
        "root_searchable": root.can_search,
        "root_playable_count": sum(item.can_play for item in root.media_items),
        "root_expandable_count": sum(item.can_expand for item in root.media_items),
        "child_item_count": len(child.media_items) if child else 0,
        "child_total_available": child.total_available if child else 0,
        "child_playable_count": (
            sum(item.can_play for item in child.media_items) if child else 0
        ),
        "child_expandable_count": (
            sum(item.can_expand for item in child.media_items) if child else 0
        ),
        "queue_item_count": len(queue.media_items),
        "queue_total_available": queue.total_available,
        "empty_search_item_count": len(search.media_items),
        "empty_search_total_available": search.total_available,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("host", help="CasaTunes host name or IP address")
    parser.add_argument("zone", help="Exact visible zone name")
    parser.add_argument("--port", type=int, default=8735)
    args = parser.parse_args()
    result = asyncio.run(_async_probe(args.host, args.port, args.zone))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
