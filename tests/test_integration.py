"""Tests for CasaTunes integration orchestration."""

from __future__ import annotations

import asyncio
import json
import unittest
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, PropertyMock, patch

from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.casatunes import async_setup
from custom_components.casatunes.casatunes_api import (
    CasaTunesConnectionError,
    CasaTunesSnapshot,
    NowPlaying,
    Source,
    SystemInfo,
    Zone,
    ZoneCapabilities,
)
from custom_components.casatunes.config_flow import (
    CasaTunesConfigFlow,
    CasaTunesOptionsFlow,
    _async_validate_input,
)
from custom_components.casatunes.const import (
    CONF_INCLUDE_HIDDEN,
    FRONTEND_RESOURCE_URL,
)
from custom_components.casatunes.coordinator import CasaTunesCoordinator
from custom_components.casatunes.diagnostics import async_get_config_entry_diagnostics
from tests.test_models import NOW_PLAYING, SOURCE, SYSTEM, ZONE, ZONE_CAPABILITIES


def _snapshot() -> CasaTunesSnapshot:
    from datetime import UTC, datetime

    return CasaTunesSnapshot(
        system=SystemInfo.from_dict(SYSTEM),
        zones=(Zone.from_dict(ZONE),),
        sources=(Source.from_dict(SOURCE),),
        now_playing=(NowPlaying.from_dict(NOW_PLAYING),),
        captured_at=datetime.now(UTC),
    )


class SetupTests(unittest.IsolatedAsyncioTestCase):
    async def test_setup_registers_bundled_frontend_resource(self) -> None:
        register = AsyncMock()
        hass = SimpleNamespace(
            http=SimpleNamespace(async_register_static_paths=register)
        )

        self.assertTrue(await async_setup(hass, {}))  # type: ignore[arg-type]

        paths = register.await_args.args[0]
        self.assertEqual(len(paths), 1)
        self.assertEqual(paths[0].url_path, FRONTEND_RESOURCE_URL)
        self.assertTrue(paths[0].path.endswith("casatunes-group-volume.js"))
        self.assertFalse(paths[0].cache_headers)


class CoordinatorTests(unittest.IsolatedAsyncioTestCase):
    async def test_coordinator_returns_client_snapshot(self) -> None:
        expected = _snapshot()
        client = unittest.mock.Mock()
        client.async_get_snapshot = AsyncMock(return_value=expected)
        coordinator = object.__new__(CasaTunesCoordinator)
        coordinator.client = client

        actual = await coordinator._async_update_data()

        self.assertIs(actual, expected)

    async def test_coordinator_wraps_client_errors(self) -> None:
        client = unittest.mock.Mock()
        client.async_get_snapshot = AsyncMock(
            side_effect=CasaTunesConnectionError("not reachable")
        )
        coordinator = object.__new__(CasaTunesCoordinator)
        coordinator.client = client

        with self.assertRaisesRegex(UpdateFailed, "Unable to update CasaTunes state"):
            await coordinator._async_update_data()

    async def test_pending_mute_masks_stale_snapshot_until_confirmed(self) -> None:
        coordinator = object.__new__(CasaTunesCoordinator)
        coordinator._pending_mutes = {
            "zone-persistent-id": (True, asyncio.get_running_loop().time() + 5)
        }
        coordinator._pending_positions = {}

        stale = _snapshot()
        masked = coordinator._apply_pending_state(stale)
        self.assertTrue(masked.zones[0].mute)
        self.assertIn("zone-persistent-id", coordinator._pending_mutes)

        confirmed = replace(
            stale,
            zones=(replace(stale.zones[0], mute=True),),
        )
        actual = coordinator._apply_pending_state(confirmed)
        self.assertTrue(actual.zones[0].mute)
        self.assertNotIn("zone-persistent-id", coordinator._pending_mutes)

    async def test_pending_seek_masks_stale_position_until_confirmed(self) -> None:
        coordinator = object.__new__(CasaTunesCoordinator)
        issued_at = datetime.now(UTC)
        coordinator._pending_mutes = {}
        coordinator._pending_positions = {
            2: (12, issued_at, asyncio.get_running_loop().time() + 5)
        }

        stale = replace(_snapshot(), captured_at=issued_at + timedelta(seconds=1))
        masked = coordinator._apply_pending_state(stale)
        self.assertEqual(masked.now_playing[0].progress, 13)
        self.assertIn(2, coordinator._pending_positions)

        confirmed = replace(
            stale,
            now_playing=(replace(stale.now_playing[0], progress=13),),
        )
        actual = coordinator._apply_pending_state(confirmed)
        self.assertEqual(actual.now_playing[0].progress, 13)
        self.assertNotIn(2, coordinator._pending_positions)

    async def test_coordinator_loads_static_zone_capabilities(self) -> None:
        capabilities = ZoneCapabilities.from_dict(ZONE_CAPABILITIES)
        client = SimpleNamespace(
            async_get_zone_capabilities=AsyncMock(return_value=capabilities)
        )
        coordinator = SimpleNamespace(
            config_entry=SimpleNamespace(data={}, options={}),
            data=_snapshot(),
            client=client,
            zone_capabilities={},
        )

        await CasaTunesCoordinator.async_load_zone_capabilities(  # type: ignore[arg-type]
            coordinator
        )

        self.assertIs(coordinator.zone_capabilities["zone-persistent-id"], capabilities)


class ConfigValidationTests(unittest.IsolatedAsyncioTestCase):
    async def test_config_flow_form_has_documented_defaults(self) -> None:
        flow = CasaTunesConfigFlow()

        result = await flow.async_step_user()
        validated = result["data_schema"]({CONF_HOST: "casaserver.local"})

        self.assertEqual(result["type"], FlowResultType.FORM)
        self.assertEqual(validated[CONF_PORT], 8735)
        self.assertFalse(validated[CONF_INCLUDE_HIDDEN])

    @patch("custom_components.casatunes.config_flow._async_validate_input")
    async def test_config_flow_reports_connection_error(
        self, validate: unittest.mock.Mock
    ) -> None:
        validate.side_effect = CasaTunesConnectionError("not reachable")
        flow = CasaTunesConfigFlow()
        flow.hass = object()  # type: ignore[assignment]

        result = await flow.async_step_user(
            {CONF_HOST: "casaserver.local", CONF_PORT: 8735}
        )

        self.assertEqual(result["type"], FlowResultType.FORM)
        self.assertEqual(result["errors"], {"base": "cannot_connect"})

    async def test_reconfigure_form_uses_current_address(self) -> None:
        entry = SimpleNamespace(data={CONF_HOST: "casaserver.local", CONF_PORT: 8735})
        flow = CasaTunesConfigFlow()
        flow._get_reconfigure_entry = unittest.mock.Mock(  # type: ignore[method-assign]
            return_value=entry
        )

        result = await flow.async_step_reconfigure()
        validated = result["data_schema"]({})

        self.assertEqual(result["type"], FlowResultType.FORM)
        self.assertEqual(validated[CONF_HOST], "casaserver.local")
        self.assertEqual(validated[CONF_PORT], 8735)

    async def test_options_flow_defaults_to_existing_hidden_setting(self) -> None:
        entry = SimpleNamespace(
            data={CONF_INCLUDE_HIDDEN: True},
            options={},
        )
        flow = CasaTunesOptionsFlow()
        with patch.object(
            CasaTunesOptionsFlow,
            "config_entry",
            new_callable=PropertyMock,
            return_value=entry,
        ):
            result = await flow.async_step_init()
        validated = result["data_schema"]({})

        self.assertEqual(result["type"], FlowResultType.FORM)
        self.assertTrue(validated[CONF_INCLUDE_HIDDEN])

    @patch("custom_components.casatunes.config_flow.CasaTunesClient")
    @patch("custom_components.casatunes.config_flow.async_get_clientsession")
    async def test_validation_uses_server_identity(
        self,
        get_session: unittest.mock.Mock,
        client_class: unittest.mock.Mock,
    ) -> None:
        session = object()
        get_session.return_value = session
        client = client_class.return_value
        client.async_get_system_info = AsyncMock(
            return_value=SystemInfo.from_dict(SYSTEM)
        )

        unique_id, title = await _async_validate_input(
            object(),  # type: ignore[arg-type]
            {CONF_HOST: "casaserver.local", CONF_PORT: 8735},
        )

        self.assertEqual(unique_id, "001122334455")
        self.assertEqual(title, "CASASERVER")
        client_class.assert_called_once_with(
            "casaserver.local",
            session,
            port=8735,
        )


class DiagnosticsTests(unittest.IsolatedAsyncioTestCase):
    async def test_diagnostics_omit_private_identifiers_and_media(self) -> None:
        entry = SimpleNamespace(
            data={
                CONF_HOST: "casaserver.local",
                CONF_PORT: 8735,
                CONF_INCLUDE_HIDDEN: False,
            },
            options={},
            runtime_data=SimpleNamespace(coordinator=SimpleNamespace(data=_snapshot())),
        )

        result = await async_get_config_entry_diagnostics(
            object(),  # type: ignore[arg-type]
            entry,  # type: ignore[arg-type]
        )
        serialized = json.dumps(result)

        for private_value in (
            "casaserver.local",
            "CASASERVER",
            "001122334455",
            "Patio",
            "zone-persistent-id",
            "Player A",
            "Test Song",
            "Test Artist",
        ):
            self.assertNotIn(private_value, serialized)
        self.assertEqual(result["snapshot"]["zone_count"], 1)
        self.assertEqual(result["system"]["rest_services_version"], "1.107")
