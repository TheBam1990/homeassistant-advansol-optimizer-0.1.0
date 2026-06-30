"""Binary sensor platform for AdvanSol Optimizer."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import AdvansolCoordinator
from .const import DOMAIN
from .entity import AdvansolEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up AdvanSol binary sensors."""
    coordinator: AdvansolCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            AdvansolConnectionBinarySensor(coordinator),
            AdvansolNightModeBinarySensor(coordinator),
        ]
    )


class AdvansolConnectionBinarySensor(AdvansolEntity, BinarySensorEntity):
    """Connection status."""

    _attr_translation_key = "connection"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    def __init__(self, coordinator: AdvansolCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_connection"

    @property
    def is_on(self) -> bool:
        """Return true if connected."""
        data = self.coordinator.data or {}
        return bool(data.get("connected"))


class AdvansolNightModeBinarySensor(AdvansolEntity, BinarySensorEntity):
    """Night mode status."""

    _attr_translation_key = "night_mode"

    def __init__(self, coordinator: AdvansolCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_night_mode"

    @property
    def is_on(self) -> bool:
        """Return true if night mode is active."""
        data = self.coordinator.data or {}
        return bool(data.get("night_mode"))
