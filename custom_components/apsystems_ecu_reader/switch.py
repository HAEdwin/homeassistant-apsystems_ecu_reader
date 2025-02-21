"""Support for APsystems ECU switches."""

import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity
)

from .const import (
    DOMAIN,
    POWER_ICON,
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, _, add_entities):
    """Set up the APsystems Inverter switches."""

    ecu = hass.data[DOMAIN].get("ecu")
    coordinator = hass.data[DOMAIN].get("coordinator")
    switches = []
    inverters = coordinator.data.get("inverters", {})
    for uid, inv_data in inverters.items():
        switches.append(APsystemsECUInverterSwitch(coordinator, ecu, uid, inv_data))
    add_entities(switches)

class APsystemsECUInverterSwitch(CoordinatorEntity, SwitchEntity):
    """Representation of a switch for an individual inverter."""
    def __init__(self, coordinator, ecu, uid, inv_data):
        super().__init__(coordinator)
        self.coordinator = coordinator
        self._ecu = ecu
        self._uid = uid
        self._inv_data = inv_data
        self._name = f"Inverter {uid} On/Off"
        self._state = True

    @property
    def unique_id(self):
        """Return the unique id of the switch."""
        return f"{self._ecu.ecu.ecu_id}_inverter_{self._uid}"

    @property
    def name(self):
        """Return the name of the switch."""
        return self._name

    @property
    def icon(self):
        """Return the icon to use in the UI."""
        return POWER_ICON

    @property
    def device_info(self):
        """Return the device info."""
        parent = f"inverter_{self._uid}"
        return {
            "identifiers": {
                (DOMAIN, parent),
            },
            "name": f"Inverter {self._uid}",
            "manufacturer": "APsystems",
            "model": self._inv_data.get("model", "Unknown"),
            "via_device": (DOMAIN, f"ecu_{self._ecu.ecu.ecu_id}"),
        }

    @property
    def entity_category(self):
        """Return the category of the entity."""
        return EntityCategory.DIAGNOSTIC

    @property
    def is_on(self):
        """Return the state of the inverter switch."""
        return self._state

    def turn_off(self, *args, **kwargs):
        """Turn off the inverter switch."""
        self._ecu.set_inverter_state(self._uid, False)
        self._state = False
        self.schedule_update_ha_state()

    def turn_on(self, *args, **kwargs):
        """Turn on the inverter switch."""
        self._ecu.set_inverter_state(self._uid, True)
        self._state = True
        self.schedule_update_ha_state()
