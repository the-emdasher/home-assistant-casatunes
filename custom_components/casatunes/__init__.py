"""CasaTunes integration setup."""

from __future__ import annotations

from pathlib import Path

from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.typing import ConfigType

from .casatunes_api import CasaTunesClient
from .const import DEFAULT_PORT, DOMAIN, FRONTEND_RESOURCE_URL, PLATFORMS
from .coordinator import CasaTunesCoordinator
from .data import CasaTunesConfigEntry, CasaTunesRuntimeData


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register frontend assets shared by all CasaTunes entries."""
    del config
    frontend_path = Path(__file__).parent / "frontend" / "casatunes-group-volume.js"
    await hass.http.async_register_static_paths(
        [StaticPathConfig(FRONTEND_RESOURCE_URL, str(frontend_path), False)]
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: CasaTunesConfigEntry) -> bool:
    """Set up CasaTunes from a config entry."""
    client = CasaTunesClient(
        entry.data["host"],
        async_get_clientsession(hass),
        port=entry.data.get("port", DEFAULT_PORT),
    )
    coordinator = CasaTunesCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()
    await coordinator.async_load_zone_capabilities()
    entry.runtime_data = CasaTunesRuntimeData(client=client, coordinator=coordinator)

    system = coordinator.data.system
    server_identifier = entry.unique_id or system.mac_address.lower()
    dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, server_identifier)},
        manufacturer="CasaTunes",
        name=system.host_name,
        model=system.app_name,
        sw_version=system.casatunes_version,
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: CasaTunesConfigEntry) -> bool:
    """Unload a CasaTunes config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
