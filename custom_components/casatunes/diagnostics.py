"""Privacy-safe diagnostics for CasaTunes."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant

from .const import CONF_INCLUDE_HIDDEN
from .data import CasaTunesConfigEntry


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: CasaTunesConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics without host, room, source, account, or media identity."""
    del hass
    snapshot = entry.runtime_data.coordinator.data
    return {
        "options": {
            CONF_INCLUDE_HIDDEN: entry.options.get(
                CONF_INCLUDE_HIDDEN,
                entry.data.get(CONF_INCLUDE_HIDDEN, False),
            )
        },
        "system": {
            "app_name": snapshot.system.app_name,
            "casatunes_version": snapshot.system.casatunes_version,
            "rest_services_version": snapshot.system.rest_services_version,
            "license_valid": snapshot.system.is_license_valid,
            "system_sleep_enabled": snapshot.system.is_system_sleep_enabled,
            "password_required": snapshot.system.is_password_required,
            "settings_password_required": (
                snapshot.system.is_settings_password_required
            ),
            "matrix_count": snapshot.system.matrix_count,
            "volume_range": {
                "minimum": snapshot.system.volume_settings.minimum,
                "maximum": snapshot.system.volume_settings.maximum,
                "increment": snapshot.system.volume_settings.increment,
            },
        },
        "snapshot": {
            "captured_at": snapshot.captured_at.isoformat(),
            "zone_count": len(snapshot.zones),
            "visible_zone_count": sum(not zone.hidden for zone in snapshot.zones),
            "powered_zone_count": sum(zone.power for zone in snapshot.zones),
            "source_count": len(snapshot.sources),
            "visible_source_count": sum(
                not source.hidden for source in snapshot.sources
            ),
            "now_playing_count": len(snapshot.now_playing),
        },
        "zones": [
            {
                "hidden": zone.hidden,
                "power": zone.power,
                "mute": zone.mute,
                "fixed_volume_enabled": zone.fixed_volume_enabled,
                "volume_control_type": zone.volume_control_type,
                "shared": zone.shared,
                "group_member_count": (
                    sum(
                        other.shared and other.shared_room_id == zone.shared_room_id
                        for other in snapshot.zones
                    )
                    if zone.shared_room_id
                    else len(zone.group_info)
                ),
                "sleep_enabled": zone.sleep_enabled,
                "low_pass_filter_supported": zone.low_pass_filter_supported,
            }
            for zone in snapshot.zones
        ],
        "sources": [
            {
                "hidden": source.hidden,
                "shared": source.is_shared,
                "source_kind": int(source.source_kind),
                "control_type": int(source.control_type),
                "media_types_supported": source.media_types_supported,
            }
            for source in snapshot.sources
        ],
    }
