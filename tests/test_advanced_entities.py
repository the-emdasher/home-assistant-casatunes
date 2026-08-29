"""Tests for capability-driven CasaTunes number and switch entities."""

from __future__ import annotations

import unittest
from types import SimpleNamespace

from custom_components.casatunes.casatunes_api import ZoneCapabilities
from custom_components.casatunes.number import (
    ZONE_NUMBER_SPECS,
    CasaTunesZoneNumber,
)
from custom_components.casatunes.number import (
    async_setup_entry as async_setup_numbers,
)
from custom_components.casatunes.switch import (
    ZONE_SWITCH_SPECS,
    CasaTunesZoneSwitch,
)
from custom_components.casatunes.switch import (
    async_setup_entry as async_setup_switches,
)
from tests.test_media_player import FakeCoordinator, _snapshot
from tests.test_models import ZONE_CAPABILITIES


class AdvancedEntityTests(unittest.IsolatedAsyncioTestCase):
    def _coordinator(self) -> FakeCoordinator:
        coordinator = FakeCoordinator(_snapshot())
        coordinator.zone_capabilities = {  # type: ignore[attr-defined]
            "zone-persistent-id": ZoneCapabilities.from_dict(ZONE_CAPABILITIES)
        }
        return coordinator

    async def test_platforms_discover_only_supported_controls(self) -> None:
        coordinator = self._coordinator()
        entry = SimpleNamespace(runtime_data=SimpleNamespace(coordinator=coordinator))
        numbers: list[CasaTunesZoneNumber] = []
        switches: list[CasaTunesZoneSwitch] = []

        await async_setup_numbers(
            object(),  # type: ignore[arg-type]
            entry,  # type: ignore[arg-type]
            numbers.extend,  # type: ignore[arg-type]
        )
        await async_setup_switches(
            object(),  # type: ignore[arg-type]
            entry,  # type: ignore[arg-type]
            switches.extend,  # type: ignore[arg-type]
        )

        self.assertEqual(len(numbers), 7)
        self.assertEqual(len(switches), 4)
        self.assertTrue(
            all(not item.entity_registry_enabled_default for item in numbers)
        )
        self.assertTrue(
            all(not item.entity_registry_enabled_default for item in switches)
        )

    async def test_number_uses_capability_range_and_writes_property(self) -> None:
        coordinator = self._coordinator()
        capabilities = coordinator.zone_capabilities[  # type: ignore[attr-defined]
            "zone-persistent-id"
        ]
        bass_spec = next(spec for spec in ZONE_NUMBER_SPECS if spec.key == "bass")
        entity = CasaTunesZoneNumber(  # type: ignore[arg-type]
            coordinator,
            "zone-persistent-id",
            bass_spec,
            capabilities.eq_settings,
        )

        self.assertEqual(entity.native_value, 0)
        self.assertEqual(entity.native_min_value, -18)
        self.assertEqual(entity.native_max_value, 18)
        self.assertEqual(entity.native_step, 2)
        self.assertEqual(
            entity.device_info["via_device"],
            ("casatunes", "established-server-id"),
        )
        await entity.async_set_native_value(4.2)

        self.assertEqual(
            coordinator.client.zone_commands,
            [("zone-persistent-id", {"Bass": 4})],
        )
        self.assertEqual(coordinator.refresh_count, 1)

    async def test_switch_reads_and_writes_property(self) -> None:
        coordinator = self._coordinator()
        loudness_spec = next(
            spec for spec in ZONE_SWITCH_SPECS if spec.key == "loudness"
        )
        entity = CasaTunesZoneSwitch(  # type: ignore[arg-type]
            coordinator,
            "zone-persistent-id",
            loudness_spec,
        )

        self.assertFalse(entity.is_on)
        await entity.async_turn_on()
        await entity.async_turn_off()

        self.assertEqual(
            coordinator.client.zone_commands,
            [
                ("zone-persistent-id", {"Loudness": True}),
                ("zone-persistent-id", {"Loudness": False}),
            ],
        )
        self.assertEqual(coordinator.refresh_count, 2)
