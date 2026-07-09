"""Config flow for AdvanSol Optimizer."""

from __future__ import annotations

import asyncio
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST
from homeassistant.core import callback

from .const import (
    CONF_NIGHT_END,
    CONF_NIGHT_START,
    CONF_POLL_INTERVAL,
    CONF_REQUEST_TIMEOUT,
    CONF_SKIP_VALIDATION,
    CONF_SWITCH_RETRIES,
    CONF_SWITCH_RETRY_DELAY,
    CONF_TCP_PORT,
    DEFAULT_HOST,
    DEFAULT_NIGHT_END,
    DEFAULT_NIGHT_START,
    DEFAULT_POLL_INTERVAL,
    DEFAULT_REQUEST_TIMEOUT,
    DEFAULT_SKIP_VALIDATION,
    DEFAULT_SWITCH_RETRIES,
    DEFAULT_SWITCH_RETRY_DELAY,
    DEFAULT_TCP_PORT,
    DOMAIN,
)
from .protocol import AdvansolClient, AdvansolError


class AdvansolConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle an AdvanSol Optimizer config flow."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle the initial setup step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            await self.async_set_unique_id(f"{user_input[CONF_HOST]}:{user_input[CONF_TCP_PORT]}")
            self._abort_if_unique_id_configured()

            controller_serial = user_input[CONF_HOST]
            if not user_input.get(CONF_SKIP_VALIDATION, DEFAULT_SKIP_VALIDATION):
                client = AdvansolClient(
                    user_input[CONF_HOST],
                    user_input[CONF_TCP_PORT],
                    user_input[CONF_REQUEST_TIMEOUT],
                    user_input[CONF_SWITCH_RETRIES],
                    user_input[CONF_SWITCH_RETRY_DELAY],
                )
                try:
                    controller_serial = await client.read_controller_serial()
                except (AdvansolError, OSError, asyncio.TimeoutError):
                    errors["base"] = "cannot_connect"
                finally:
                    await client.close()

            if not errors:
                return self.async_create_entry(
                    title=f"AdvanSol {controller_serial}",
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST, default=DEFAULT_HOST): str,
                    vol.Required(CONF_TCP_PORT, default=DEFAULT_TCP_PORT): vol.All(
                        vol.Coerce(int), vol.Range(min=1, max=65535)
                    ),
                    vol.Required(CONF_POLL_INTERVAL, default=DEFAULT_POLL_INTERVAL): vol.All(
                        vol.Coerce(int), vol.Range(min=2)
                    ),
                    vol.Required(CONF_REQUEST_TIMEOUT, default=DEFAULT_REQUEST_TIMEOUT): vol.All(
                        vol.Coerce(float), vol.Range(min=0.5)
                    ),
                    vol.Required(CONF_SWITCH_RETRIES, default=DEFAULT_SWITCH_RETRIES): vol.All(
                        vol.Coerce(int), vol.Range(min=1, max=20)
                    ),
                    vol.Required(
                        CONF_SWITCH_RETRY_DELAY, default=DEFAULT_SWITCH_RETRY_DELAY
                    ): vol.All(vol.Coerce(float), vol.Range(min=0)),
                    vol.Required(CONF_NIGHT_START, default=DEFAULT_NIGHT_START): vol.All(
                        vol.Coerce(int), vol.Range(min=0, max=23)
                    ),
                    vol.Required(CONF_NIGHT_END, default=DEFAULT_NIGHT_END): vol.All(
                        vol.Coerce(int), vol.Range(min=0, max=23)
                    ),
                    vol.Optional(
                        CONF_SKIP_VALIDATION,
                        default=DEFAULT_SKIP_VALIDATION,
                    ): bool,
                }
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return AdvansolOptionsFlow(config_entry)


class AdvansolOptionsFlow(config_entries.OptionsFlow):
    """Handle options updates."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Manage integration options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options = self.config_entry.options
        data = self.config_entry.data
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_POLL_INTERVAL,
                        default=options.get(CONF_POLL_INTERVAL, data.get(CONF_POLL_INTERVAL)),
                    ): vol.All(vol.Coerce(int), vol.Range(min=2)),
                    vol.Required(
                        CONF_REQUEST_TIMEOUT,
                        default=options.get(CONF_REQUEST_TIMEOUT, data.get(CONF_REQUEST_TIMEOUT)),
                    ): vol.All(vol.Coerce(float), vol.Range(min=0.5)),
                    vol.Required(
                        CONF_SWITCH_RETRIES,
                        default=options.get(CONF_SWITCH_RETRIES, data.get(CONF_SWITCH_RETRIES)),
                    ): vol.All(vol.Coerce(int), vol.Range(min=1, max=20)),
                    vol.Required(
                        CONF_SWITCH_RETRY_DELAY,
                        default=options.get(
                            CONF_SWITCH_RETRY_DELAY, data.get(CONF_SWITCH_RETRY_DELAY)
                        ),
                    ): vol.All(vol.Coerce(float), vol.Range(min=0)),
                    vol.Required(
                        CONF_NIGHT_START,
                        default=options.get(CONF_NIGHT_START, data.get(CONF_NIGHT_START)),
                    ): vol.All(vol.Coerce(int), vol.Range(min=0, max=23)),
                    vol.Required(
                        CONF_NIGHT_END,
                        default=options.get(CONF_NIGHT_END, data.get(CONF_NIGHT_END)),
                    ): vol.All(vol.Coerce(int), vol.Range(min=0, max=23)),
                }
            ),
        )
