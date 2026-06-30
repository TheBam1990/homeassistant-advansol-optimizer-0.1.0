"""Home Assistant integration for AdvanSol optimizers."""

from __future__ import annotations

import asyncio
from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.util import dt as dt_util
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_NIGHT_END,
    CONF_NIGHT_START,
    CONF_POLL_INTERVAL,
    CONF_REQUEST_TIMEOUT,
    CONF_SWITCH_RETRIES,
    CONF_SWITCH_RETRY_DELAY,
    CONF_TCP_PORT,
    DEFAULT_NIGHT_END,
    DEFAULT_NIGHT_START,
    DEFAULT_POLL_INTERVAL,
    DEFAULT_REQUEST_TIMEOUT,
    DEFAULT_SWITCH_RETRIES,
    DEFAULT_SWITCH_RETRY_DELAY,
    DEFAULT_TCP_PORT,
    DOMAIN,
)
from .protocol import AdvansolClient, AdvansolError, ModuleData, OptimizerModule

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR, Platform.SWITCH]


AdvansolData = dict[str, object]


class AdvansolCoordinator(DataUpdateCoordinator[AdvansolData]):
    """Coordinator that polls all optimizer modules."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.entry = entry
        self.host = entry.data[CONF_HOST]
        self.tcp_port = entry.data.get(CONF_TCP_PORT, DEFAULT_TCP_PORT)
        self.night_start = entry.options.get(
            CONF_NIGHT_START, entry.data.get(CONF_NIGHT_START, DEFAULT_NIGHT_START)
        )
        self.night_end = entry.options.get(
            CONF_NIGHT_END, entry.data.get(CONF_NIGHT_END, DEFAULT_NIGHT_END)
        )
        self.client = AdvansolClient(
            self.host,
            self.tcp_port,
            entry.options.get(
                CONF_REQUEST_TIMEOUT,
                entry.data.get(CONF_REQUEST_TIMEOUT, DEFAULT_REQUEST_TIMEOUT),
            ),
            entry.options.get(
                CONF_SWITCH_RETRIES,
                entry.data.get(CONF_SWITCH_RETRIES, DEFAULT_SWITCH_RETRIES),
            ),
            entry.options.get(
                CONF_SWITCH_RETRY_DELAY,
                entry.data.get(CONF_SWITCH_RETRY_DELAY, DEFAULT_SWITCH_RETRY_DELAY),
            ),
        )
        self.controller_serial: str | None = None
        self.modules: list[OptimizerModule] = []
        self.night_mode = False
        self.module_failures: dict[int, int] = {}
        self._rediscover_next = False

        interval = entry.options.get(
            CONF_POLL_INTERVAL, entry.data.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL)
        )
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=interval),
        )

    def is_night_hour(self) -> bool:
        """Return true when polling should be skipped."""
        current_hour = dt_util.now().hour
        if self.night_start <= self.night_end:
            return self.night_start <= current_hour < self.night_end
        return current_hour >= self.night_start or current_hour < self.night_end

    async def async_discover(self) -> None:
        """Discover controller and modules."""
        self.controller_serial = await self.client.read_controller_serial()
        self.modules = await self.client.read_device_list(self.controller_serial)
        self.module_failures = {module.index: 0 for module in self.modules}
        self._rediscover_next = False
        _LOGGER.info(
            "Found AdvanSol controller %s with modules %s",
            self.controller_serial,
            ", ".join(f"{module.index}:{module.serial_number}" for module in self.modules),
        )

    async def _async_update_data(self) -> AdvansolData:
        if self.is_night_hour():
            self.night_mode = True
            return {
                "connected": self.client.connected,
                "controller_serial": self.controller_serial,
                "modules": {module.index: module for module in self.modules},
                "module_data": self.data.get("module_data", {}) if self.data else {},
                "night_mode": True,
            }

        try:
            if not self.modules or self._rediscover_next:
                await self.async_discover()

            previous_values = self.data.get("module_data", {}) if self.data else {}
            module_values: dict[int, ModuleData] = dict(previous_values)
            success_count = 0
            fail_count = 0

            for module in self.modules:
                try:
                    module_values[module.index] = await self.client.read_module(module.index)
                    self.module_failures[module.index] = 0
                    success_count += 1
                except AdvansolError as err:
                    self.module_failures[module.index] = self.module_failures.get(module.index, 0) + 1
                    fail_count += 1
                    _LOGGER.debug("Module %s read failed: %s", module.index, err)

            self.night_mode = fail_count >= 5 and success_count == 0

            return {
                "connected": self.client.connected,
                "controller_serial": self.controller_serial,
                "modules": {module.index: module for module in self.modules},
                "module_data": module_values,
                "night_mode": self.night_mode,
            }
        except (AdvansolError, OSError, asyncio.TimeoutError) as err:
            await self.client.close()
            raise UpdateFailed(str(err)) from err

    async def async_switch_module(self, module_index: int, target_on: bool) -> None:
        """Switch one optimizer module."""
        module = next((item for item in self.modules if item.index == module_index), None)
        if module is None:
            raise AdvansolError(f"Module {module_index} is not known")
        await self.client.switch_module(module.serial_number, target_on)
        await self.async_request_refresh()

    async def async_close(self) -> None:
        """Close TCP resources."""
        await self.client.close()


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up AdvanSol Optimizer from a config entry."""
    coordinator = AdvansolCoordinator(hass, entry)

    try:
        await coordinator.async_config_entry_first_refresh()
    except UpdateFailed as err:
        raise ConfigEntryNotReady(str(err)) from err

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    coordinator: AdvansolCoordinator | None = hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    if coordinator is not None:
        await coordinator.async_close()
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload after options changed."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
