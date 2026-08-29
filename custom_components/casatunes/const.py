"""Constants for the CasaTunes integration."""

from datetime import timedelta

from homeassistant.const import Platform

DOMAIN = "casatunes"
DEFAULT_PORT = 8735
DEFAULT_SCAN_INTERVAL = timedelta(seconds=10)
CONF_INCLUDE_HIDDEN = "include_hidden"
FRONTEND_RESOURCE_URL = "/casatunes_frontend/casatunes-group-volume.js"
PLATFORMS = [Platform.MEDIA_PLAYER, Platform.NUMBER, Platform.SWITCH]
