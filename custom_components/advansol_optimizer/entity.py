"""Base entity classes for AdvanSol Optimizer."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from . import AdvansolCoordinator


class AdvansolEntity(CoordinatorEntity[AdvansolCoordinator]):
    """Base entity for controller-level AdvanSol data."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: AdvansolCoordinator) -> None:
        super().__init__(coordinator)

    @property
    def device_info(self) -> DeviceInfo:
        """Return controller device info."""
        serial = self.coordinator.controller_serial or self.coordinator.host
        return DeviceInfo(
            identifiers={(DOMAIN, f"controller-{serial}")},
            name="AdvanSol Optimizer Controller",
            manufacturer="AdvanSol",
            model="DCON-WIFI / RS485 bridge",
            serial_number=self.coordinator.controller_serial,
        )


class AdvansolModuleEntity(CoordinatorEntity[AdvansolCoordinator]):
    """Base entity for optimizer-module data."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: AdvansolCoordinator, module_index: int) -> None:
        super().__init__(coordinator)
        self.module_index = module_index

    @property
    def module_data(self):
        """Return current decoded module data."""
        data = self.coordinator.data or {}
        return data.get("module_data", {}).get(self.module_index)

    @property
    def module(self):
        """Return discovered module metadata."""
        data = self.coordinator.data or {}
        return data.get("modules", {}).get(self.module_index)

    @property
    def device_info(self) -> DeviceInfo:
        """Return optimizer device info."""
        module = self.module
        serial = module.serial_number if module else f"module-{self.module_index}"
        return DeviceInfo(
            identifiers={(DOMAIN, f"module-{serial}")},
            name=f"AdvanSol Optimizer {self.module_index}",
            manufacturer="AdvanSol",
            model="MRO/MR Optimizer",
            serial_number=serial,
            via_device=(DOMAIN, f"controller-{self.coordinator.controller_serial or self.coordinator.host}"),
        )
