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

from custom_components.casatunes import (
    async_setup,
    async_setup_entry,
    async_unload_entry,
)
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


def _dynamic_coordinator(
    client: object,
    snapshot: CasaTunesSnapshot | None = None,
) -> tuple[CasaTunesCoordinator, unittest.mock.Mock]:
    coordinator = object.__new__(CasaTunesCoordinator)
    coordinator.client = client  # type: ignore[assignment]
    coordinator.data = snapshot or _snapshot()
    coordinator._pending_mutes = {}
    coordinator._pending_positions = {}
    coordinator._casatunes_refresh_lock = asyncio.Lock()
    coordinator._dynamic_refresh_task = None
    coordinator._last_full_refresh_started = asyncio.get_running_loop().time()

    published = unittest.mock.Mock()

    def set_updated_data(data: CasaTunesSnapshot) -> None:
        coordinator.data = data
        published(data)

    coordinator.async_set_updated_data = set_updated_data  # type: ignore[method-assign]
    return coordinator, published


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

    @patch("custom_components.casatunes.dr.async_get")
    @patch("custom_components.casatunes.async_get_clientsession")
    @patch("custom_components.casatunes.CasaTunesCoordinator")
    @patch("custom_components.casatunes.CasaTunesClient")
    async def test_entry_setup_starts_dynamic_refresh(
        self,
        client_class: unittest.mock.Mock,
        coordinator_class: unittest.mock.Mock,
        get_session: unittest.mock.Mock,
        get_device_registry: unittest.mock.Mock,
    ) -> None:
        coordinator = coordinator_class.return_value
        coordinator.async_config_entry_first_refresh = AsyncMock()
        coordinator.async_load_zone_capabilities = AsyncMock()
        coordinator.async_start_dynamic_refresh = unittest.mock.Mock()
        coordinator.data = _snapshot()
        get_session.return_value = object()
        get_device_registry.return_value.async_get_or_create = unittest.mock.Mock()
        forward = AsyncMock()
        hass = SimpleNamespace(
            config_entries=SimpleNamespace(async_forward_entry_setups=forward)
        )
        entry = SimpleNamespace(
            data={"host": "casaserver.local", "port": 8735},
            entry_id="entry-id",
            options={},
            runtime_data=None,
            unique_id="server-id",
        )

        self.assertTrue(
            await async_setup_entry(hass, entry)  # type: ignore[arg-type]
        )

        coordinator.async_start_dynamic_refresh.assert_called_once_with()
        forward.assert_awaited_once()
        self.assertIs(entry.runtime_data.coordinator, coordinator)

    async def test_entry_unload_stops_dynamic_refresh(self) -> None:
        stop = AsyncMock()
        unload = AsyncMock(return_value=True)
        hass = SimpleNamespace(
            config_entries=SimpleNamespace(async_unload_platforms=unload)
        )
        entry = SimpleNamespace(
            runtime_data=SimpleNamespace(
                coordinator=SimpleNamespace(async_stop_dynamic_refresh=stop)
            )
        )

        self.assertTrue(
            await async_unload_entry(hass, entry)  # type: ignore[arg-type]
        )

        stop.assert_awaited_once_with()


class CoordinatorTests(unittest.IsolatedAsyncioTestCase):
    async def test_coordinator_returns_client_snapshot(self) -> None:
        expected = _snapshot()
        client = unittest.mock.Mock()
        client.async_get_snapshot = AsyncMock(return_value=expected)
        coordinator = object.__new__(CasaTunesCoordinator)
        coordinator.client = client
        coordinator._casatunes_refresh_lock = asyncio.Lock()
        coordinator._last_full_refresh_started = 0.0

        actual = await coordinator._async_update_data()

        self.assertIs(actual, expected)

    async def test_coordinator_wraps_client_errors(self) -> None:
        client = unittest.mock.Mock()
        client.async_get_snapshot = AsyncMock(
            side_effect=CasaTunesConnectionError("not reachable")
        )
        coordinator = object.__new__(CasaTunesCoordinator)
        coordinator.client = client
        coordinator._casatunes_refresh_lock = asyncio.Lock()
        coordinator._last_full_refresh_started = 0.0

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

    async def test_dynamic_refresh_publishes_external_playback_change(self) -> None:
        original = _snapshot()
        changed_zone = replace(original.zones[0], power=False, volume=47)
        changed_song = replace(
            original.now_playing[0].current_song,
            title="Externally Selected Track",
            artists="External Artist",
        )
        changed_now_playing = replace(
            original.now_playing[0],
            progress=3,
            current_song=changed_song,
        )
        client = SimpleNamespace(
            async_get_zones=AsyncMock(return_value=(changed_zone,)),
            async_get_now_playing=AsyncMock(return_value=(changed_now_playing,)),
        )
        coordinator, published = _dynamic_coordinator(client, original)

        self.assertTrue(await coordinator.async_refresh_dynamic_data())

        updated = coordinator.data
        self.assertEqual(updated.zones, (changed_zone,))
        self.assertEqual(updated.now_playing, (changed_now_playing,))
        self.assertEqual(
            updated.now_playing[0].current_song.title,
            "Externally Selected Track",
        )
        self.assertIs(updated.system, original.system)
        self.assertIs(updated.sources, original.sources)
        self.assertGreater(updated.captured_at, original.captured_at)
        published.assert_called_once_with(updated)
        client.async_get_zones.assert_awaited_once_with()
        client.async_get_now_playing.assert_awaited_once_with()

    async def test_dynamic_refresh_waits_for_full_refresh_and_wins_race(self) -> None:
        original = _snapshot()
        full_started = asyncio.Event()
        release_full = asyncio.Event()
        dynamic_started = asyncio.Event()
        full_snapshot = replace(
            original,
            zones=(replace(original.zones[0], volume=20),),
        )
        dynamic_zone = replace(original.zones[0], volume=55)

        async def get_full_snapshot() -> CasaTunesSnapshot:
            full_started.set()
            await release_full.wait()
            return full_snapshot

        async def get_zones() -> tuple[Zone, ...]:
            dynamic_started.set()
            return (dynamic_zone,)

        client = SimpleNamespace(
            async_get_snapshot=get_full_snapshot,
            async_get_zones=get_zones,
            async_get_now_playing=AsyncMock(return_value=original.now_playing),
        )
        coordinator, _published = _dynamic_coordinator(client, original)

        full_task = asyncio.create_task(coordinator._async_update_data())
        await full_started.wait()
        dynamic_task = asyncio.create_task(coordinator.async_refresh_dynamic_data())
        await asyncio.sleep(0)
        self.assertFalse(dynamic_started.is_set())

        release_full.set()
        coordinator.async_set_updated_data(await full_task)
        self.assertTrue(await dynamic_task)

        self.assertTrue(dynamic_started.is_set())
        self.assertEqual(coordinator.data.zones, (dynamic_zone,))
        self.assertIs(coordinator.data.system, full_snapshot.system)
        self.assertIs(coordinator.data.sources, full_snapshot.sources)

    async def test_dynamic_zone_and_now_playing_requests_are_concurrent(self) -> None:
        original = _snapshot()
        started: set[str] = set()
        both_started = asyncio.Event()
        release = asyncio.Event()

        async def wait_for_peer(name: str, result: object) -> object:
            started.add(name)
            if len(started) == 2:
                both_started.set()
            await release.wait()
            return result

        client = SimpleNamespace(
            async_get_zones=lambda: wait_for_peer("zones", original.zones),
            async_get_now_playing=lambda: wait_for_peer(
                "now_playing", original.now_playing
            ),
        )
        coordinator, _published = _dynamic_coordinator(client, original)

        refresh = asyncio.create_task(coordinator.async_refresh_dynamic_data())
        await asyncio.wait_for(both_started.wait(), timeout=1)
        release.set()

        self.assertTrue(await refresh)
        self.assertEqual(started, {"zones", "now_playing"})

    async def test_dynamic_refresh_failure_preserves_availability_and_data(
        self,
    ) -> None:
        original = _snapshot()
        client = SimpleNamespace(
            async_get_zones=AsyncMock(
                side_effect=CasaTunesConnectionError("temporary failure")
            ),
            async_get_now_playing=AsyncMock(return_value=original.now_playing),
        )
        coordinator, published = _dynamic_coordinator(client, original)
        coordinator.last_update_success = True

        self.assertFalse(await coordinator.async_refresh_dynamic_data())

        self.assertIs(coordinator.data, original)
        self.assertTrue(coordinator.last_update_success)
        published.assert_not_called()

    async def test_dynamic_refresh_task_starts_once_and_stops_cleanly(self) -> None:
        refreshed = asyncio.Event()

        async def refresh_dynamic() -> bool:
            refreshed.set()
            return True

        class FakeEntry:
            def __init__(self) -> None:
                self.task: asyncio.Task[None] | None = None

            def async_create_background_task(
                self,
                hass: object,
                target: object,
                name: str,
            ) -> asyncio.Task[None]:
                del hass
                self.task = asyncio.create_task(target, name=name)  # type: ignore[arg-type]
                return self.task

        entry = FakeEntry()
        coordinator = object.__new__(CasaTunesCoordinator)
        coordinator.config_entry = entry  # type: ignore[assignment]
        coordinator.hass = object()  # type: ignore[assignment]
        coordinator._dynamic_refresh_task = None
        coordinator._last_full_refresh_started = asyncio.get_running_loop().time()
        coordinator.async_refresh_dynamic_data = refresh_dynamic  # type: ignore[method-assign]

        coordinator.async_start_dynamic_refresh()
        task = coordinator._dynamic_refresh_task
        coordinator.async_start_dynamic_refresh()
        await asyncio.wait_for(refreshed.wait(), timeout=1)
        await coordinator.async_stop_dynamic_refresh()

        self.assertIsNotNone(task)
        self.assertIs(task, entry.task)
        self.assertTrue(task.cancelled())
        self.assertIsNone(coordinator._dynamic_refresh_task)

    async def test_dynamic_loop_keeps_ten_second_full_refresh_due(self) -> None:
        full_refreshed = asyncio.Event()

        async def full_refresh() -> None:
            full_refreshed.set()

        coordinator = object.__new__(CasaTunesCoordinator)
        coordinator._last_full_refresh_started = 0.0
        coordinator.async_refresh = full_refresh  # type: ignore[method-assign]
        coordinator.async_refresh_dynamic_data = AsyncMock()  # type: ignore[method-assign]

        task = asyncio.create_task(coordinator._async_dynamic_refresh_loop())
        await asyncio.wait_for(full_refreshed.wait(), timeout=1)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task

        coordinator.async_refresh_dynamic_data.assert_not_awaited()  # type: ignore[attr-defined]


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

    @patch("custom_components.casatunes.config_flow._async_validate_input")
    async def test_reconfigure_accepts_changed_server_identifier(
        self,
        validate: unittest.mock.Mock,
    ) -> None:
        validate.return_value = ("new-interface-mac", "CASASERVER")
        entry = SimpleNamespace(
            unique_id="original-interface-mac",
            data={CONF_HOST: "192.0.2.10", CONF_PORT: 8735},
        )
        flow = CasaTunesConfigFlow()
        flow.hass = object()  # type: ignore[assignment]
        flow._get_reconfigure_entry = unittest.mock.Mock(  # type: ignore[method-assign]
            return_value=entry
        )
        expected = {"type": FlowResultType.ABORT, "reason": "reconfigure_successful"}

        with (
            patch.object(flow, "async_set_unique_id", new_callable=AsyncMock) as set_id,
            patch.object(flow, "_abort_if_unique_id_configured") as check_duplicate,
            patch.object(
                flow,
                "async_update_reload_and_abort",
                return_value=expected,
            ) as update,
        ):
            result = await flow.async_step_reconfigure(
                {CONF_HOST: "192.0.2.20", CONF_PORT: 8735}
            )

        self.assertEqual(result, expected)
        set_id.assert_awaited_once_with("new-interface-mac")
        check_duplicate.assert_called_once_with()
        update.assert_called_once_with(
            entry,
            data_updates={CONF_HOST: "192.0.2.20", CONF_PORT: 8735},
        )

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
