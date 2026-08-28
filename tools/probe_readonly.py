#!/usr/bin/env python3
"""Read a sanitized CasaTunes capability summary without changing state."""

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


async def _async_probe(host: str, port: int) -> dict[str, object]:
    async with aiohttp.ClientSession() as session:
        snapshot = await CasaTunesClient(host, session, port=port).async_get_snapshot()

    visible_zones = tuple(zone for zone in snapshot.zones if not zone.hidden)
    visible_sources = tuple(source for source in snapshot.sources if not source.hidden)
    return {
        "casatunes_version": snapshot.system.casatunes_version,
        "rest_services_version": snapshot.system.rest_services_version,
        "license_valid": snapshot.system.is_license_valid,
        "matrix_count": snapshot.system.matrix_count,
        "zone_count": len(snapshot.zones),
        "visible_zone_count": len(visible_zones),
        "powered_zone_count": sum(zone.power for zone in snapshot.zones),
        "source_count": len(snapshot.sources),
        "visible_source_count": len(visible_sources),
        "now_playing_count": len(snapshot.now_playing),
        "volume_range": {
            "minimum": snapshot.system.volume_settings.minimum,
            "maximum": snapshot.system.volume_settings.maximum,
            "increment": snapshot.system.volume_settings.increment,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("host", help="CasaTunes host name or IP address")
    parser.add_argument("--port", type=int, default=8735)
    args = parser.parse_args()
    print(json.dumps(asyncio.run(_async_probe(args.host, args.port)), indent=2))


if __name__ == "__main__":
    main()
