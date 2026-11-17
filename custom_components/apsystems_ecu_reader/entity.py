"""Shared base entities for the APsystems ECU Reader integration.

All platform modules (sensor, binary_sensor, switch, number, button) build
their entities on top of the base classes defined here, so that device
information (manufacturer, model, name, sw_version) is defined exactly once
per device type instead of being duplicated in every platform file.
"""

from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, ECU_MODEL_MAP, INVERTER_MODEL_MAP


def ecu_device_info(ecu):
    """Return the device info dict for the ECU device."""
    return {
        "identifiers": {(DOMAIN, f"ecu_{ecu.ecu.ecu_id}")},
        "manufacturer": "APsystems",
        "name": f"ECU {ecu.ecu.ecu_id}",
        "model": ECU_MODEL_MAP.get(ecu.ecu.ecu_id[:4], "Unknown Model"),
        "sw_version": ecu.ecu.firmware,
    }


def inverter_device_info(uid):
    """Return the device info dict for an individual inverter device."""
    return {
        "identifiers": {(DOMAIN, f"inverter_{uid}")},
        "manufacturer": "APsystems",
        "name": f"Inverter {uid}",
        "model": INVERTER_MODEL_MAP.get(uid[:2], "Unknown Model"),
    }


class APsystemsEcuEntity(CoordinatorEntity):
    """Base class for entities that belong to the ECU device itself."""

    _attr_has_entity_name = True

    def __init__(self, coordinator, ecu):
        super().__init__(coordinator)
        self._ecu = ecu

    @property
    def device_info(self):
        """Return device info for the ECU device."""
        return ecu_device_info(self._ecu)


class APsystemsInverterEntity(CoordinatorEntity):
    """Base class for entities that belong to an individual inverter device."""

    _attr_has_entity_name = True

    def __init__(self, coordinator, ecu, uid):
        super().__init__(coordinator)
        self._ecu = ecu
        self._uid = uid

    @property
    def device_info(self):
        """Return device info for the inverter device."""
        return inverter_device_info(self._uid)
