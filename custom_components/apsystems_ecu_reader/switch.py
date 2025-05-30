"""Switch platform for APsystems ECU Reader."""

import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, POWER_ICON, ECU_MODEL_MAP, INVERTER_MODEL_MAP

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, _, async_add_entities):
    """Set up the switch platform."""
    ecu = hass.data[DOMAIN]["ecu"]
    coordinator = hass.data[DOMAIN].get("coordinator")
    switches = []
    inverters = coordinator.data.get("inverters", {})

    # Add inverter switches only if ECU-R-Pro or ECU-C
    if ecu.ecu.ecu_id.startswith(("215", "2162")):
        for uid, inv_data in inverters.items():
            switches.append(APsystemsECUInverterSwitch(coordinator, ecu, uid, inv_data))

    # Add Zero Export switch only if ECU-C
    if ecu.ecu.ecu_id.startswith("215"):
        switches.append(APsystemsZeroExportSwitch(coordinator, ecu))

    async_add_entities(switches)


class APsystemsBaseSwitch(CoordinatorEntity, SwitchEntity, RestoreEntity):
    """Base class for APsystems switches."""

    def __init__(self, coordinator, ecu, name, unique_id, icon, entity_category=None):
        """Initialize the base switch."""
        super().__init__(coordinator)
        self.coordinator = coordinator
        self._ecu = ecu
        self._name = name
        self._unique_id = unique_id
        self._icon = icon
        self._entity_category = entity_category
        self._state = False  # Default state is off

    @property
    def unique_id(self):
        """Return the unique ID of the switch."""
        return self._unique_id

    @property
    def name(self):
        """Return the name of the switch."""
        return self._name

    @property
    def icon(self):
        """Return the icon to use in the UI."""
        return self._icon

    @property
    def device_info(self):
        """Return the device info."""
        return {
            "identifiers": {
                (DOMAIN, f"ecu_{self._ecu.ecu.ecu_id}"),
            },
            "name": f"ECU {self._ecu.ecu.ecu_id}",
            "manufacturer": "APsystems",
            "model": ECU_MODEL_MAP.get(self._ecu.ecu.ecu_id[:4], "Unknown Model"),
            "sw_version": self._ecu.ecu.firmware,
        }

    @property
    def entity_category(self):
        """Return the category of the entity."""
        return self._entity_category

    @property
    def is_on(self):
        """Return the state of the switch."""
        return self._state

    async def async_added_to_hass(self):
        """Restore the state of the switch when added to Home Assistant."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state:
            self._state = last_state.state == "on"

    async def async_turn_on(self, **kwargs):
        """Turn on the switch."""
        raise NotImplementedError("This method should be implemented by subclasses.")

    async def async_turn_off(self, **kwargs):
        """Turn off the switch."""
        raise NotImplementedError("This method should be implemented by subclasses.")


class APsystemsECUInverterSwitch(APsystemsBaseSwitch):
    """Representation of a switch for an individual inverter."""

    def __init__(self, coordinator, ecu, uid, inv_data):
        super().__init__(
            coordinator,
            ecu,
            name=f"Inverter {uid} On/Off",
            unique_id=f"{ecu.ecu.ecu_id}_inverter_{uid}",
            icon=POWER_ICON,
            entity_category=EntityCategory.CONFIG,
        )
        self._ecu = ecu
        self._uid = uid
        self._inv_data = inv_data

    def turn_on(self, **kwargs):
        """Turn on the inverter switch."""
        return self.async_turn_on(**kwargs)

    def turn_off(self, **kwargs):
        """Turn off the inverter switch."""
        return self.async_turn_off(**kwargs)

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
            "model": INVERTER_MODEL_MAP.get(self._uid[:2], "Unknown Model"),
            "via_device": (DOMAIN, f"ecu_{self._ecu.ecu.ecu_id}"),
        }

    async def async_turn_off(self, **kwargs):
        """Turn off the inverter switch."""
        if await self._ecu.set_inverter_state(self._uid, False):
            self._state = False
            self.async_write_ha_state()

    async def async_turn_on(self, **kwargs):
        """Turn on the inverter switch."""
        if await self._ecu.set_inverter_state(self._uid, True):
            self._state = True
            self.async_write_ha_state()


class APsystemsZeroExportSwitch(APsystemsBaseSwitch):
    """Switch for zero export control."""

    def __init__(self, coordinator, ecu):
        super().__init__(
            coordinator,
            ecu,
            name=f"ECU {ecu.ecu.ecu_id} Zero Export",
            unique_id=f"ECU_{ecu.ecu.ecu_id}_zero_export_switch",
            icon=POWER_ICON,
            entity_category=EntityCategory.CONFIG,
        )

    async def async_turn_on(self, **kwargs):
        """Turn on zero export."""
        try:
            await self._ecu.set_zero_export(1)
            self._state = True
            self.async_write_ha_state()
        except (ConnectionError, TimeoutError) as e:
            _LOGGER.warning(
                "Failed to turn on zero export for ECU %s: %s", self._ecu.ecu.ecu_id, e
            )

    async def async_turn_off(self, **kwargs):
        """Turn off zero export."""
        try:
            await self._ecu.set_zero_export(0)
            self._state = False
            self.async_write_ha_state()
        except (ConnectionError, TimeoutError) as e:
            _LOGGER.warning(
                "Failed to turn off zero export for ECU %s: %s", self._ecu.ecu.ecu_id, e
            )

    def turn_on(self, **kwargs):
        """Turn on zero export."""
        return self.async_turn_on(**kwargs)

    def turn_off(self, **kwargs):
        """Turn off zero export."""
        return self.async_turn_off(**kwargs)
