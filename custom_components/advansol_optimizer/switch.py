"""Switch platform for AdvanSol Optimizer."""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import AdvansolCoordinator
from .const import DOMAIN
from .entity import AdvansolModuleEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up AdvanSol switches."""
    coordinator: AdvansolCoordinator = hass.data[DOMAIN][entry.entry_id]
    added_module_indexes: set[int] = set()

    def async_add_new_modules() -> None:
        """Add switches for modules discovered after platform setup."""
        new_modules = [
            module
            for module in coordinator.modules
            if module.index not in added_module_indexes
        ]
        if not new_modules:
            return

        added_module_indexes.update(module.index for module in new_modules)
        async_add_entities(
            AdvansolModuleSwitch(coordinator, module.index) for module in new_modules
        )

    async_add_new_modules()
    entry.async_on_unload(coordinator.async_add_listener(async_add_new_modules))


class AdvansolModuleSwitch(AdvansolModuleEntity, SwitchEntity):
    """MOS switch for an optimizer module."""

    _attr_translation_key = "optimizer_switch"

    def __init__(self, coordinator: AdvansolCoordinator, module_index: int) -> None:
        super().__init__(coordinator, module_index)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_module_{module_index}_switch"

    @property
    def is_on(self) -> bool | None:
        """Return switch state."""
        if self.module_data is None:
            return None
        return self.module_data.switch_on

    async def async_turn_on(self, **kwargs) -> None:
        """Turn MOS on."""
        await self.coordinator.async_switch_module(self.module_index, True)

    async def async_turn_off(self, **kwargs) -> None:
        """Turn MOS off."""
        await self.coordinator.async_switch_module(self.module_index, False)
