"""Coordinated CasaTunes state updates."""

from __future__ import annotations

import asyncio
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .casatunes_api import (
    CasaTunesClient,
    CasaTunesError,
    CasaTunesSnapshot,
    ZoneCapabilities,
)
from .const import CONF_INCLUDE_HIDDEN, DEFAULT_SCAN_INTERVAL, DOMAIN
from .data import CasaTunesConfigEntry

_LOGGER = logging.getLogger(__name__)


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
        try:
            return await self.client.async_get_snapshot()
        except CasaTunesError as err:
            raise UpdateFailed(f"Unable to update CasaTunes state: {err}") from err
