"""Advanced numeric controls for CasaTunes zones."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.const import PERCENTAGE, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .casatunes_api import SettingsRange, ZoneCapabilities
from .coordinator import CasaTunesCoordinator
from .data import CasaTunesConfigEntry
from .entity import CasaTunesZoneFeatureEntity

PARALLEL_UPDATES = 0


@dataclass(frozen=True, slots=True)
class ZoneNumberSpec:
    key: str
    name: str
    icon: str
    property_name: str
    zone_attribute: str
    supported: Callable[[ZoneCapabilities], bool]
    range_attribute: str
    unit: str | None = None


ZONE_NUMBER_SPECS = (
    ZoneNumberSpec(
        key="balance",
        name="Balance",
        icon="mdi:swap-horizontal",
        property_name="Balance",
        zone_attribute="balance",
        supported=lambda capabilities: capabilities.balance,
        range_attribute="balance_settings",
    ),
    ZoneNumberSpec(
        key="bass",
        name="Bass",
        icon="mdi:tune-vertical",
        property_name="Bass",
        zone_attribute="bass",
        supported=lambda capabilities: capabilities.eq,
        range_attribute="eq_settings",
    ),
    ZoneNumberSpec(
        key="treble",
        name="Treble",
        icon="mdi:tune-vertical",
        property_name="Treble",
        zone_attribute="treble",
        supported=lambda capabilities: capabilities.eq,
        range_attribute="eq_settings",
    ),
    ZoneNumberSpec(
        key="maximum_volume",
        name="Maximum volume",
        icon="mdi:volume-high",
        property_name="MaxVolume",
        zone_attribute="max_volume",
        supported=lambda capabilities: capabilities.max_volume,
        range_attribute="volume_settings",
        unit=PERCENTAGE,
    ),
    ZoneNumberSpec(
        key="page_volume",
        name="Page volume",
        icon="mdi:bullhorn",
        property_name="PageVolume",
        zone_attribute="page_volume",
        supported=lambda capabilities: capabilities.mute_page_volume != 0,
        range_attribute="volume_settings",
        unit=PERCENTAGE,
    ),
    ZoneNumberSpec(
        key="power_on_volume",
        name="Power-on volume",
        icon="mdi:volume-plus",
        property_name="PowerOnVolume",
        zone_attribute="power_on_volume",
        supported=lambda capabilities: capabilities.power_on_volume != 0,
        range_attribute="volume_settings",
        unit=PERCENTAGE,
    ),
    ZoneNumberSpec(
        key="fixed_volume",
        name="Fixed volume",
        icon="mdi:volume-lock",
        property_name="FixedVolume",
        zone_attribute="fixed_volume",
        supported=lambda capabilities: capabilities.fixed_volume != 0,
        range_attribute="volume_settings",
        unit=PERCENTAGE,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: CasaTunesConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up capability-driven advanced zone numbers."""
    del hass
    coordinator = entry.runtime_data.coordinator
    entities: list[CasaTunesZoneNumber] = []
    for zone in coordinator.data.zones:
        capabilities = coordinator.zone_capabilities.get(zone.persistent_zone_id)
        if capabilities is None:
            continue
        for spec in ZONE_NUMBER_SPECS:
            if not spec.supported(capabilities):
                continue
            value_range = (
                coordinator.data.system.volume_settings
                if spec.range_attribute == "volume_settings"
                else getattr(capabilities, spec.range_attribute)
            )
            entities.append(
                CasaTunesZoneNumber(
                    coordinator,
                    zone.persistent_zone_id,
                    spec,
                    value_range,
                )
            )
    async_add_entities(entities)


class CasaTunesZoneNumber(CasaTunesZoneFeatureEntity, NumberEntity):
    """One advanced numeric property of a CasaTunes zone."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_mode = NumberMode.BOX

    def __init__(
        self,
        coordinator: CasaTunesCoordinator,
        zone_id: str,
        spec: ZoneNumberSpec,
        value_range: SettingsRange,
    ) -> None:
        super().__init__(coordinator, zone_id, spec.key)
        self._spec = spec
        self._attr_name = spec.name
        self._attr_icon = spec.icon
        self._attr_native_min_value = value_range.minimum
        self._attr_native_max_value = value_range.maximum
        self._attr_native_step = value_range.increment
        self._attr_native_unit_of_measurement = spec.unit

    @property
    def native_value(self) -> float | None:
        zone = self.zone
        return float(getattr(zone, self._spec.zone_attribute)) if zone else None

    async def async_set_native_value(self, value: float) -> None:
        await self._async_set_zone_property(**{self._spec.property_name: round(value)})
