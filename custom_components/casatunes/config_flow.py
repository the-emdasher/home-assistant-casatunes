"""Config flow for CasaTunes."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlowWithReload,
)
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .casatunes_api import CasaTunesClient, CasaTunesConnectionError, CasaTunesError
from .const import CONF_INCLUDE_HIDDEN, DEFAULT_PORT, DOMAIN

_LOGGER = logging.getLogger(__name__)


async def _async_validate_input(
    hass: HomeAssistant, data: dict[str, Any]
) -> tuple[str, str]:
    client = CasaTunesClient(
        data[CONF_HOST],
        async_get_clientsession(hass),
        port=data[CONF_PORT],
    )
    system = await client.async_get_system_info()
    return system.mac_address.lower(), system.host_name


class CasaTunesConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle CasaTunes configuration."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> CasaTunesOptionsFlow:
        """Return the CasaTunes options flow."""
        return CasaTunesOptionsFlow()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                unique_id, title = await _async_validate_input(self.hass, user_input)
            except (CasaTunesConnectionError, TimeoutError):
                errors["base"] = "cannot_connect"
            except (CasaTunesError, ValueError):
                errors["base"] = "invalid_response"
            except Exception:  # noqa: BLE001 - config flows must report unknown errors
                _LOGGER.exception("Unexpected exception while connecting to CasaTunes")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured(
                    updates={
                        CONF_HOST: user_input[CONF_HOST],
                        CONF_PORT: user_input[CONF_PORT],
                    }
                )
                return self.async_create_entry(title=title, data=user_input)

        schema = vol.Schema(
            {
                vol.Required(CONF_HOST): str,
                vol.Required(CONF_PORT, default=DEFAULT_PORT): vol.All(
                    vol.Coerce(int), vol.Range(min=1, max=65535)
                ),
                vol.Optional(CONF_INCLUDE_HIDDEN, default=False): bool,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Update the CasaTunes network address."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                unique_id, _title = await _async_validate_input(self.hass, user_input)
            except (CasaTunesConnectionError, TimeoutError):
                errors["base"] = "cannot_connect"
            except (CasaTunesError, ValueError):
                errors["base"] = "invalid_response"
            except Exception:  # noqa: BLE001
                _LOGGER.exception(
                    "Unexpected exception while reconnecting to CasaTunes"
                )
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(unique_id)
                # A CasaTunes server can report a different MAC address after a
                # network-interface or IP change. Reconfigure is an explicit user
                # action, so preserve this entry's established identity while
                # still preventing it from being pointed at a server that already
                # has its own config entry.
                if unique_id != entry.unique_id:
                    self._abort_if_unique_id_configured()
                return self.async_update_reload_and_abort(
                    entry,
                    data_updates={
                        CONF_HOST: user_input[CONF_HOST],
                        CONF_PORT: user_input[CONF_PORT],
                    },
                )

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_HOST,
                    default=entry.data[CONF_HOST],
                ): str,
                vol.Required(
                    CONF_PORT,
                    default=entry.data.get(CONF_PORT, DEFAULT_PORT),
                ): vol.All(vol.Coerce(int), vol.Range(min=1, max=65535)),
            }
        )
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(schema, user_input),
            errors=errors,
        )


class CasaTunesOptionsFlow(OptionsFlowWithReload):
    """Configure CasaTunes runtime options and reload on changes."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage CasaTunes options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_INCLUDE_HIDDEN,
                    default=self.config_entry.options.get(
                        CONF_INCLUDE_HIDDEN,
                        self.config_entry.data.get(CONF_INCLUDE_HIDDEN, False),
                    ),
                ): bool,
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
