#!/usr/bin/env python3
"""Probe typed CasaTunes zone capabilities without changing state."""

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
        capabilities = await client.async_get_zone_capabilities(
            matches[0].persistent_zone_id
        )

    return {
        "zone": zone_name,
        "balance": capabilities.balance,
        "equalizer": capabilities.eq,
        "equalizer_presets": capabilities.eq_presets,
        "loudness": capabilities.loudness,
        "absolute_volume": capabilities.absolute_volume,
        "maximum_volume": capabilities.max_volume,
        "power_on_volume": capabilities.power_on_volume != 0,
        "page_volume": capabilities.mute_page_volume != 0,
        "fixed_volume": capabilities.fixed_volume != 0,
        "balance_range": {
            "minimum": capabilities.balance_settings.minimum,
            "maximum": capabilities.balance_settings.maximum,
            "increment": capabilities.balance_settings.increment,
        },
        "equalizer_range": {
            "minimum": capabilities.eq_settings.minimum,
            "maximum": capabilities.eq_settings.maximum,
            "increment": capabilities.eq_settings.increment,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("host")
    parser.add_argument("zone")
    parser.add_argument("--port", type=int, default=8735)
    args = parser.parse_args()
    result = asyncio.run(_async_probe(args.host, args.port, args.zone))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
