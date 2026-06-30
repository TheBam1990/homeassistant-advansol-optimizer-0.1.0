"""Sensor platform for AdvanSol Optimizer."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import AdvansolCoordinator
from .const import DOMAIN
from .entity import AdvansolEntity, AdvansolModuleEntity
from .protocol import ModuleData


@dataclass(frozen=True, kw_only=True)
class AdvansolModuleSensorDescription(SensorEntityDescription):
    """Description of an optimizer module sensor."""

    value_fn: Callable[[ModuleData], str | int | float]


MODULE_SENSOR_DESCRIPTIONS: tuple[AdvansolModuleSensorDescription, ...] = (
    AdvansolModuleSensorDescription(
        key="output_voltage",
        translation_key="output_voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.output_voltage,
    ),
    AdvansolModuleSensorDescription(
        key="output_current",
        translation_key="output_current",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.output_current,
    ),
    AdvansolModuleSensorDescription(
        key="power",
        translation_key="power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.power,
    ),
    AdvansolModuleSensorDescription(
        key="energy",
        translation_key="energy",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda data: data.energy,
    ),
    AdvansolModuleSensorDescription(
        key="input_voltage",
        translation_key="input_voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.input_voltage,
    ),
    AdvansolModuleSensorDescription(
        key="input_current",
        translation_key="input_current",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.input_current,
    ),
    AdvansolModuleSensorDescription(
        key="temperature",
        translation_key="temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.temperature,
    ),
    AdvansolModuleSensorDescription(
        key="mos",
        translation_key="mos",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.mos,
    ),
    AdvansolModuleSensorDescription(
        key="software",
        translation_key="software",
        value_fn=lambda data: data.software,
    ),
    AdvansolModuleSensorDescription(
        key="hardware",
        translation_key="hardware",
        value_fn=lambda data: data.hardware,
    ),
    AdvansolModuleSensorDescription(
        key="serial_number",
        translation_key="serial_number",
        value_fn=lambda data: data.serial_number,
    ),
    AdvansolModuleSensorDescription(
        key="raw",
        translation_key="raw",
        value_fn=lambda data: data.raw,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up AdvanSol sensors."""
    coordinator: AdvansolCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[SensorEntity] = [
        AdvansolControllerSerialSensor(coordinator),
        AdvansolModuleCountSensor(coordinator),
    ]
    entities.extend(
        AdvansolModuleSensor(coordinator, module.index, description)
        for module in coordinator.modules
        for description in MODULE_SENSOR_DESCRIPTIONS
    )
    async_add_entities(entities)


class AdvansolControllerSerialSensor(AdvansolEntity, SensorEntity):
    """Controller serial number sensor."""

    _attr_translation_key = "controller_serial"

    def __init__(self, coordinator: AdvansolCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_controller_serial"

    @property
    def native_value(self) -> str | None:
        """Return controller serial number."""
        return self.coordinator.controller_serial


class AdvansolModuleCountSensor(AdvansolEntity, SensorEntity):
    """Module count sensor."""

    _attr_translation_key = "module_count"

    def __init__(self, coordinator: AdvansolCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_module_count"

    @property
    def native_value(self) -> int:
        """Return discovered module count."""
        return len(self.coordinator.modules)


class AdvansolModuleSensor(AdvansolModuleEntity, SensorEntity):
    """Sensor for a single module value."""

    entity_description: AdvansolModuleSensorDescription

    def __init__(
        self,
        coordinator: AdvansolCoordinator,
        module_index: int,
        description: AdvansolModuleSensorDescription,
    ) -> None:
        super().__init__(coordinator, module_index)
        self.entity_description = description
        self._attr_unique_id = (
            f"{coordinator.entry.entry_id}_module_{module_index}_{description.key}"
        )

    @property
    def native_value(self) -> str | int | float | None:
        """Return the current sensor value."""
        if self.module_data is None:
            return None
        return self.entity_description.value_fn(self.module_data)
