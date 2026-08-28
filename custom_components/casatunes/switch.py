"""Advanced switches for CasaTunes zones."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .casatunes_api import ControllerFeature, Zone, ZoneCapabilities
from .coordinator import CasaTunesCoordinator
from .data import CasaTunesConfigEntry
from .entity import CasaTunesZoneFeatureEntity

PARALLEL_UPDATES = 0


@dataclass(frozen=True, slots=True)
class ZoneSwitchSpec:
    key: str
    name: str
    icon: str
    property_name: str
    zone_attribute: str
    supported: Callable[[Zone, ZoneCapabilities, ControllerFeature], bool]


ZONE_SWITCH_SPECS = (
    ZoneSwitchSpec(
        key="do_not_disturb",
        name="Do not disturb",
        icon="mdi:minus-circle",
        property_name="DND",
        zone_attribute="dnd",
        supported=lambda zone, _capabilities, features: (
            not zone.hide_dnd_control
            and bool(features & ControllerFeature.HARDWARE_DND)
        ),
    ),
    ZoneSwitchSpec(
        key="keypad_lock",
        name="Keypad lock",
        icon="mdi:lock",
        property_name="KeypadLock",
        zone_attribute="keypad_lock",
        supported=lambda _zone, _capabilities, features: bool(
            features & ControllerFeature.HARDWARE_KEYPAD_LOCK
        ),
    ),
    ZoneSwitchSpec(
        key="loudness",
        name="Loudness",
        icon="mdi:volume-equal",
        property_name="Loudness",
        zone_attribute="loudness",
        supported=lambda _zone, capabilities, features: (
            capabilities.loudness
            and bool(features & ControllerFeature.LOUDNESS_COMPENSATION)
        ),
    ),
    ZoneSwitchSpec(
        key="reset_power_on_volume",
        name="Reset volume on power-on",
        icon="mdi:restart",
        property_name="ResetPowerOnVolume",
        zone_attribute="reset_power_on_volume",
        supported=lambda _zone, capabilities, features: (
            capabilities.power_on_volume != 0
            and bool(features & ControllerFeature.RESET_VOLUME_ON_POWER)
        ),
    ),
    ZoneSwitchSpec(
        key="low_pass_filter",
        name="Low-pass filter",
        icon="mdi:sine-wave",
        property_name="LowPassFilterEnabled",
        zone_attribute="low_pass_filter_enabled",
        supported=lambda zone, _capabilities, _features: zone.low_pass_filter_supported,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: CasaTunesConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up capability-driven advanced zone switches."""
    del hass
    coordinator = entry.runtime_data.coordinator
    features = coordinator.data.system.controller_features
    entities: list[CasaTunesZoneSwitch] = []
    for zone in coordinator.data.zones:
        capabilities = coordinator.zone_capabilities.get(zone.persistent_zone_id)
        if capabilities is None:
            continue
        entities.extend(
            CasaTunesZoneSwitch(
                coordinator,
                zone.persistent_zone_id,
                spec,
            )
            for spec in ZONE_SWITCH_SPECS
            if spec.supported(zone, capabilities, features)
        )
    async_add_entities(entities)


class CasaTunesZoneSwitch(CasaTunesZoneFeatureEntity, SwitchEntity):
    """One advanced boolean property of a CasaTunes zone."""

    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self,
        coordinator: CasaTunesCoordinator,
        zone_id: str,
        spec: ZoneSwitchSpec,
    ) -> None:
        super().__init__(coordinator, zone_id, spec.key)
        self._spec = spec
        self._attr_name = spec.name
        self._attr_icon = spec.icon

    @property
    def is_on(self) -> bool | None:
        zone = self.zone
        return bool(getattr(zone, self._spec.zone_attribute)) if zone else None

    async def async_turn_on(self, **kwargs: object) -> None:
        del kwargs
        await self._async_set_zone_property(**{self._spec.property_name: True})

    async def async_turn_off(self, **kwargs: object) -> None:
        del kwargs
        await self._async_set_zone_property(**{self._spec.property_name: False})
