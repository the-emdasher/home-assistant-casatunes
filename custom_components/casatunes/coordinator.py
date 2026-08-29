"""Coordinated CasaTunes state updates."""

from __future__ import annotations

import asyncio
import logging
from contextlib import suppress
from dataclasses import replace
from datetime import UTC, datetime

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .casatunes_api import (
    CasaTunesClient,
    CasaTunesError,
    CasaTunesSnapshot,
    NowPlaying,
    PlayerStatus,
    Zone,
    ZoneCapabilities,
)
from .const import CONF_INCLUDE_HIDDEN, DEFAULT_SCAN_INTERVAL, DOMAIN
from .data import CasaTunesConfigEntry

_LOGGER = logging.getLogger(__name__)

OPTIMISTIC_STATE_SECONDS = 5.0
POSITION_TOLERANCE_SECONDS = 3
DYNAMIC_REFRESH_INTERVAL_SECONDS = 1.0


class CasaTunesCoordinator(DataUpdateCoordinator[CasaTunesSnapshot]):
    """Fetch one coherent CasaTunes snapshot for all entities."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: CasaTunesConfigEntry,
        client: CasaTunesClient,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=DEFAULT_SCAN_INTERVAL,
        )
        self.client = client
        self.zone_capabilities: dict[str, ZoneCapabilities] = {}
        self._pending_mutes: dict[str, tuple[bool, float]] = {}
        self._pending_positions: dict[int, tuple[int, datetime, float]] = {}
        self._casatunes_refresh_lock = asyncio.Lock()
        self._dynamic_refresh_task: asyncio.Task[None] | None = None
        self._last_full_refresh_started = 0.0

    @callback
    def async_start_dynamic_refresh(self) -> None:
        """Start the config-entry-managed dynamic state refresh."""
        if (
            self._dynamic_refresh_task is not None
            and not self._dynamic_refresh_task.done()
        ):
            return
        self._dynamic_refresh_task = self.config_entry.async_create_background_task(
            self.hass,
            self._async_dynamic_refresh_loop(),
            f"{DOMAIN} dynamic refresh",
        )

    async def async_stop_dynamic_refresh(self) -> None:
        """Stop the dynamic state refresh and wait for it to finish."""
        task = self._dynamic_refresh_task
        self._dynamic_refresh_task = None
        if task is None:
            return
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task

    async def _async_dynamic_refresh_loop(self) -> None:
        """Refresh dynamic data every second and retain full refresh cadence."""
        loop = asyncio.get_running_loop()
        full_interval = DEFAULT_SCAN_INTERVAL.total_seconds()
        while True:
            tick_started = loop.time()
            try:
                if tick_started - self._last_full_refresh_started >= full_interval:
                    await self.async_refresh()
                else:
                    await self.async_refresh_dynamic_data()
            except asyncio.CancelledError:
                raise
            except Exception:  # noqa: BLE001 - background tasks must remain supervised
                _LOGGER.exception("Unexpected error refreshing dynamic CasaTunes state")
            elapsed = loop.time() - tick_started
            await asyncio.sleep(max(0, DYNAMIC_REFRESH_INTERVAL_SECONDS - elapsed))

    async def async_refresh_dynamic_data(self) -> bool:
        """Fetch and publish only rapidly changing CasaTunes state."""
        try:
            async with self._casatunes_refresh_lock:
                zones, now_playing = await asyncio.gather(
                    self.client.async_get_zones(),
                    self.client.async_get_now_playing(),
                )
                if self.data is None:
                    return False
                snapshot = self._apply_pending_state(
                    replace(
                        self.data,
                        zones=zones,
                        now_playing=now_playing,
                        captured_at=datetime.now(UTC),
                    )
                )
                self.async_set_updated_data(snapshot)
        except CasaTunesError as err:
            _LOGGER.debug("Unable to refresh dynamic CasaTunes state: %s", err)
            return False
        except Exception:  # noqa: BLE001 - keep the fast path isolated
            _LOGGER.exception("Unexpected error refreshing dynamic CasaTunes state")
            return False
        return True

    @callback
    def async_set_optimistic_mute(self, zone: Zone, mute: bool) -> None:
        """Publish a mute command while CasaTunes state catches up."""
        deadline = asyncio.get_running_loop().time() + OPTIMISTIC_STATE_SECONDS
        self._pending_mutes[zone.persistent_zone_id] = (mute, deadline)
        optimistic_zone = replace(zone, mute=mute)
        self.async_set_updated_data(
            replace(
                self.data,
                zones=tuple(
                    optimistic_zone
                    if item.persistent_zone_id == zone.persistent_zone_id
                    else item
                    for item in self.data.zones
                ),
            )
        )

    @callback
    def async_set_optimistic_position(self, source_id: int, position: int) -> None:
        """Publish a seek command while CasaTunes state catches up."""
        now = datetime.now(UTC)
        deadline = asyncio.get_running_loop().time() + OPTIMISTIC_STATE_SECONDS
        self._pending_positions[source_id] = (position, now, deadline)
        self.async_set_updated_data(
            replace(
                self.data,
                now_playing=tuple(
                    replace(item, progress=position)
                    if item.source_id == source_id
                    else item
                    for item in self.data.now_playing
                ),
                captured_at=now,
            )
        )

    def _apply_pending_state(self, snapshot: CasaTunesSnapshot) -> CasaTunesSnapshot:
        """Keep recent commands from being overwritten by stale API reads."""
        pending_mutes = getattr(self, "_pending_mutes", {})
        pending_positions = getattr(self, "_pending_positions", {})
        if not pending_mutes and not pending_positions:
            return snapshot

        loop_time = asyncio.get_running_loop().time()
        zones: list[Zone] = []
        for zone in snapshot.zones:
            pending = pending_mutes.get(zone.persistent_zone_id)
            if pending is None:
                zones.append(zone)
                continue
            expected, deadline = pending
            if zone.mute == expected or loop_time >= deadline:
                pending_mutes.pop(zone.persistent_zone_id, None)
                zones.append(zone)
            else:
                zones.append(replace(zone, mute=expected))

        now_playing: list[NowPlaying] = []
        for item in snapshot.now_playing:
            pending = pending_positions.get(item.source_id)
            if pending is None:
                now_playing.append(item)
                continue
            expected, issued_at, deadline = pending
            elapsed = max(0, round((snapshot.captured_at - issued_at).total_seconds()))
            projected = expected + (
                elapsed if item.status == PlayerStatus.PLAYING else 0
            )
            if (
                abs(item.progress - projected) <= POSITION_TOLERANCE_SECONDS
                or loop_time >= deadline
            ):
                pending_positions.pop(item.source_id, None)
                now_playing.append(item)
            else:
                now_playing.append(replace(item, progress=projected))

        return replace(
            snapshot,
            zones=tuple(zones),
            now_playing=tuple(now_playing),
        )

    async def async_load_zone_capabilities(self) -> None:
        """Load relatively static advanced zone capabilities once at setup."""
        include_hidden = self.config_entry.options.get(
            CONF_INCLUDE_HIDDEN,
            self.config_entry.data.get(CONF_INCLUDE_HIDDEN, False),
        )
        zones = [zone for zone in self.data.zones if include_hidden or not zone.hidden]
        results = await asyncio.gather(
            *(
                self.client.async_get_zone_capabilities(zone.persistent_zone_id)
                for zone in zones
            ),
            return_exceptions=True,
        )
        for zone, result in zip(zones, results, strict=True):
            if isinstance(result, BaseException):
                _LOGGER.warning(
                    "Unable to load advanced capabilities for CasaTunes zone %s: %s",
                    zone.zone_id,
                    result,
                )
                continue
            self.zone_capabilities[zone.persistent_zone_id] = result

    async def _async_update_data(self) -> CasaTunesSnapshot:
        async with self._casatunes_refresh_lock:
            self._last_full_refresh_started = asyncio.get_running_loop().time()
            try:
                snapshot = await self.client.async_get_snapshot()
            except CasaTunesError as err:
                raise UpdateFailed(f"Unable to update CasaTunes state: {err}") from err
            return self._apply_pending_state(snapshot)
