"""Support for APsystems ECU switches."""

import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, POWER_ICON

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, _, add_entities):
    """Set up the APsystems Inverter switches."""

    ecu = hass.data[DOMAIN].get("ecu")
    coordinator = hass.data[DOMAIN].get("coordinator")
    switches = []
    inverters = coordinator.data.get("inverters", {})
    for uid, inv_data in inverters.items():
        switches.append(APsystemsECUInverterSwitch(coordinator, ecu, uid, inv_data))
    switches.append(APsystemsZeroExportSwitch(coordinator, ecu))  # Add zero export switch
    add_entities(switches)

class APsystemsECUInverterSwitch(CoordinatorEntity, SwitchEntity, RestoreEntity):
    """Representation of a switch for an individual inverter."""

    def turn_off(self, **kwargs):
        """Turn off the inverter switch."""
        self.hass.async_create_task(self.async_turn_off(**kwargs))

    def turn_on(self, **kwargs):
        """Turn on the inverter switch."""
        self.hass.async_create_task(self.async_turn_on(**kwargs))

    def __init__(self, coordinator, ecu, uid, inv_data):
        super().__init__(coordinator)
        self.coordinator = coordinator
        self._ecu = ecu
        self._uid = uid
        self._inv_data = inv_data
        self._name = f"Inverter {uid} On/Off"
        self._state = False  # Set initial state to False (disabled by default)

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
        return EntityCategory.CONFIG

    @property
    def is_on(self):
        """Return the state of the inverter switch."""
        return self._state

    async def async_added_to_hass(self):
        """Handle entity which will be added."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state:
            self._state = last_state.state == "on"

    async def async_turn_off(self, **kwargs):
        """Turn off the inverter switch."""
        await self._ecu.set_inverter_state(self._uid, False)
        self._state = False
        self.async_write_ha_state()

    async def async_turn_on(self, **kwargs):
        """Turn on the inverter switch."""
        await self._ecu.set_inverter_state(self._uid, True)
        self._state = True
        self.async_write_ha_state()

class APsystemsZeroExportSwitch(CoordinatorEntity, SwitchEntity, RestoreEntity):
    """Representation of a switch for zero export control."""
    def turn_off(self, **kwargs):
        """Turn off zero export."""
        self.hass.async_create_task(self.async_turn_off(**kwargs))

    def turn_on(self, **kwargs):
        """Turn on zero export."""
        self.hass.async_create_task(self.async_turn_on(**kwargs))

    def __init__(self, coordinator, ecu):
        super().__init__(coordinator)
        self.coordinator = coordinator
        self._ecu = ecu
        self._name = "Zero Export Control"
        self._state = False  # Set initial state to False (disabled by default)

    @property
    def unique_id(self):
        """Return the unique id of the switch."""
        return f"{self._ecu.ecu.ecu_id}_zero_export"

    @property
    def name(self):
        """Return the name of the switch."""
        return self._name

    @property
    def icon(self):
        """Return the icon to use in the UI."""
        return "mdi:power"

    @property
    def device_info(self):
        """Return the device info."""
        return {
            "identifiers": {
                (DOMAIN, f"ecu_{self._ecu.ecu.ecu_id}"),
            },
            "name": f"ECU {self._ecu.ecu.ecu_id}",
            "manufacturer": "APsystems",
            "model": self._ecu.ecu.firmware,
            "sw_version": self._ecu.ecu.firmware,
        }

    @property
    def entity_category(self):
        """Return the category of the entity."""
        return EntityCategory.CONFIG

    @property
    def is_on(self):
        """Return the state of the zero export switch."""
        return self._state

    async def async_added_to_hass(self):
        """Handle entity which will be added."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state:
            self._state = last_state.state == "on"

    async def async_turn_off(self, **kwargs):
        """Turn off zero export."""
        await self._ecu.set_zero_export(0)
        self._state = False
        self.async_write_ha_state()

    async def async_turn_on(self, **kwargs):
        """Turn on zero export."""
        await self._ecu.set_zero_export(1)
        self._state = True
        self.async_write_ha_state()
