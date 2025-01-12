import logging

#from homeassistant.util import dt as dt_util
from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity
)

from .const import (
    DOMAIN,
    RELOAD_ICON,
    POWER_ICON
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config, add_entities, discovery_info=None):
    """Set up the APSystems ECU switches."""	

    ecu = hass.data[DOMAIN].get("ecu")
    coordinator = hass.data[DOMAIN].get("coordinator")
    switches = [
        APSystemsECUQuerySwitch(coordinator, ecu, "query_device",
            label="Query Device", icon=RELOAD_ICON),
        APSystemsECUInvertersSwitch(coordinator, ecu, "inverters_online",
            label="Inverters Online", icon=POWER_ICON),
    ]
    add_entities(switches)

class APSystemsECUQuerySwitch(CoordinatorEntity, SwitchEntity):
    """Representation of a switch."""	
    def __init__(self, coordinator, ecu, field, label=None, icon=None):
        super().__init__(coordinator)
        self.coordinator = coordinator
        self._ecu = ecu
        self._field = field
        self._label = label
        if not label:
            self._label = field
        self._icon = icon
        self._name = f"ECU {self._label}"
        self._state = True

    @property
    def unique_id(self):
        """Return the unique id of the switch."""	
        return f"{self._ecu.ecu.ecu_id}_{self._field}"

    @property
    def name(self):
        """Return the name of the switch."""
        return self._name

    @property
    def icon(self):
        """Return the icon to use in the frontend, if any."""	
        return self._icon

    @property
    def device_info(self):
        """Return the device info."""	
        parent = f"ecu_{self._ecu.ecu.ecu_id}"
        return {
            "identifiers": {
                (DOMAIN, parent),
            }
        }

    @property
    def entity_category(self):
        """Return the category of the entity."""	
        return EntityCategory.CONFIG

    @property
    def is_on(self):
        """Return the state of the switch."""	
        return self._ecu.is_querying

    def turn_off(self, *args, **kwargs):
        """Turn off the switch."""
        self._ecu.set_querying_state(False)
        self._state = False
        self.schedule_update_ha_state()

    def turn_on(self, *args, **kwargs):
        """Turn on the switch."""
        self._ecu.set_querying_state(True)
        self._state = True
        self.schedule_update_ha_state()

class APSystemsECUInvertersSwitch(CoordinatorEntity, SwitchEntity):
    """Representation of a switch."""
    def __init__(self, coordinator, ecu, field, label=None, icon=None):
        super().__init__(coordinator)
        self.coordinator = coordinator
        self._ecu = ecu
        self._field = field
        self._label = label
        if not label:
            self._label = field
        self._icon = icon
        self._name = f"ECU {self._label}"
        self._state = True

    @property
    def unique_id(self):
        """Return the unique id of the switch."""	
        return f"{self._ecu.ecu.ecu_id}_{self._field}"

    @property
    def name(self):
        """Return the name of the switch."""	
        return self._name

    @property
    def icon(self):
        """Return the icon to use in the frontend, if any."""	
        return self._icon

    @property
    def device_info(self):
        """Return the device info."""	
        parent = f"ecu_{self._ecu.ecu.ecu_id}"
        return {
            "identifiers": {
                (DOMAIN, parent),
            }
        }

    @property
    def entity_category(self):
        """Return the category of the entity."""	
        return EntityCategory.CONFIG

    @property
    def is_on(self):
        """Return the state of the switch."""	
        return self._ecu.inverters_online

    def turn_off(self, *args, **kwargs):
        """Turn off the switch."""
        self._ecu.toggle_all_inverters(False)
        self._state = False
        self.schedule_update_ha_state()

    def turn_on(self, *args, **kwargs):
        """Turn on the switch."""
        self._ecu.toggle_all_inverters(True)
        self._state = True
        self.schedule_update_ha_state()
