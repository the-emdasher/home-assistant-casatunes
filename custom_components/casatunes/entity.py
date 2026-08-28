"""Shared CasaTunes zone entity behavior."""

from __future__ import annotations

from typing import Any

from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .casatunes_api import CasaTunesError, Zone
from .const import DOMAIN
from .coordinator import CasaTunesCoordinator


class CasaTunesZoneFeatureEntity(CoordinatorEntity[CasaTunesCoordinator]):
    """Base class for disabled-by-default advanced zone controls."""

    _attr_entity_registry_enabled_default = False
    _attr_has_entity_name = True

    def __init__(
        self, coordinator: CasaTunesCoordinator, zone_id: str, key: str
    ) -> None:
        super().__init__(coordinator)
        self._zone_id = zone_id
        self._attr_unique_id = f"{zone_id}_{key}"

    @property
    def zone(self) -> Zone | None:
        """Return the current coordinator model for this entity's zone."""
        return self.coordinator.data.zones_by_persistent_id.get(self._zone_id)

    @property
    def available(self) -> bool:
        return super().available and self.zone is not None

    @property
    def device_info(self) -> DeviceInfo:
        zone = self.zone
        assert zone is not None
        system = self.coordinator.data.system
        return DeviceInfo(
            identifiers={(DOMAIN, zone.persistent_zone_id)},
            manufacturer="CasaTunes",
            model="Audio zone",
            name=zone.name,
            via_device=(DOMAIN, system.mac_address.lower()),
        )

    async def _async_set_zone_property(self, **changes: Any) -> None:
        try:
            await self.coordinator.client.async_update_zone(self._zone_id, **changes)
        except CasaTunesError as err:
            raise HomeAssistantError(f"CasaTunes command failed: {err}") from err
        await self.coordinator.async_request_refresh()
