import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    RELOAD_ICON,
    POWER_ICON
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config, add_entities, discovery_info=None):
    ecu = hass.data[DOMAIN].get("ecu")
    coordinator = hass.data[DOMAIN].get("coordinator")

    if not ecu or not coordinator:
        _LOGGER.error("ECU or coordinator not found in hass.data[DOMAIN].")
        return

    switches = [
        APsystemsECUQuerySwitch(coordinator, ecu, "query_device", 
            label="Query Device", icon=RELOAD_ICON),
        APsystemsECUInvertersSwitch(coordinator, ecu, "inverters_online", 
            label="Inverters Online", icon=POWER_ICON),
    ]
    add_entities(switches)

class APsystemsECUQuerySwitch(CoordinatorEntity, SwitchEntity):
    def __init__(self, coordinator, ecu, field, label=None, icon=None):
        super().__init__(coordinator)
        self.coordinator = coordinator
        self._ecu = ecu
        self._field = field
        self._label = label or field
        self._icon = icon
        self._name = f"ECU {self._label}"
        self._state = True  # Default state

    @property
    def unique_id(self):
        return f"{self._ecu.ecu.ecu_id}_{self._field}"

    @property
    def name(self):
        return self._name

    @property
    def icon(self):
        return self._icon

    @property
    def device_info(self):
        parent = f"ecu_{self._ecu.ecu.ecu_id}"
        return {
            "identifiers": {
                (DOMAIN, parent),
            }
        }

    @property
    def entity_category(self):
        return EntityCategory.CONFIG
    
    @property
    def is_on(self):
        return self._ecu.querying

    def turn_off(self, **kwargs):
        _LOGGER.debug("Turning off %s", self._name)
        self._ecu.set_querying_state(False)
        self._state = False
        self.schedule_update_ha_state()
    
    def turn_on(self, **kwargs):
        _LOGGER.debug("Turning on %s", self._name)
        self._ecu.set_querying_state(True)
        self._state = True
        self.schedule_update_ha_state()


class APsystemsECUInvertersSwitch(CoordinatorEntity, SwitchEntity):
    def __init__(self, coordinator, ecu, field, label=None, icon=None):
        super().__init__(coordinator)
        self.coordinator = coordinator
        self._ecu = ecu
        self._field = field
        self._label = label or field
        self._icon = icon
        self._name = f"ECU {self._label}"
        self._state = True  # Default state

    @property
    def unique_id(self):
        return f"{self._ecu.ecu.ecu_id}_{self._field}"

    @property
    def name(self):
        return self._name

    @property
    def icon(self):
        return self._icon

    @property
    def device_info(self):
        parent = f"ecu_{self._ecu.ecu.ecu_id}"
        return {
            "identifiers": {
                (DOMAIN, parent),
            }
        }

    @property
    def entity_category(self):
        return EntityCategory.CONFIG
    
    @property
    def is_on(self):
        return self._ecu.inverters_online

    def turn_off(self, **kwargs):
        _LOGGER.debug("Turning off %s", self._name)
        self._ecu.toggle_all_inverters(turn_on=False)
        self._state = False
        self.schedule_update_ha_state()

    def turn_on(self, **kwargs):
        _LOGGER.debug("Turning on %s", self._name)
        self._ecu.toggle_all_inverters(turn_on=True)
        self._state = True
        self.schedule_update_ha_state()
