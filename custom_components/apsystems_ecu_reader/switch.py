"""Switch platform for APsystems ECU Reader."""

import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, POWER_ICON, ECU_MODEL_MAP, INVERTER_MODEL_MAP

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the switch platform."""
    ecu = hass.data[DOMAIN][config_entry.entry_id]["ecu"]
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    switches = []
    inverters = coordinator.data.get("inverters", {})

    # Add ECU Query switch for all ECU types
    switches.append(APsystemsECUQuerySwitch(coordinator, ecu))

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
        else:
            # If no previous state, try to get actual inverter state
            if hasattr(self, "_inv_data"):
                self._state = self._inv_data.get("online", True)
            else:
                self._state = False

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
            # Get the current power limit from the number entity
            power_limit_entity_id = f"number.ecu_{self._ecu.ecu.ecu_id}_power_limit"
            power_limit_state = self.hass.states.get(power_limit_entity_id)
            power_limit = 0
            if power_limit_state and power_limit_state.state not in (
                "unknown",
                "unavailable",
            ):
                # Convert from kW display value to watts
                power_limit = int(float(power_limit_state.state) * 1000)

            await self._ecu.set_zero_export(1, power_limit)
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


class APsystemsECUQuerySwitch(APsystemsBaseSwitch):
    """Switch to control ECU querying on/off."""

    def __init__(self, coordinator, ecu):
        super().__init__(
            coordinator,
            ecu,
            name=f"ECU {ecu.ecu.ecu_id} Query ECU",
            unique_id=f"ECU_{ecu.ecu.ecu_id}_query_switch",
            icon="mdi:access-point-network",
            entity_category=EntityCategory.CONFIG,
        )
        self._state = True  # Default to on

    async def async_added_to_hass(self):
        """Restore the state of the switch when added to Home Assistant."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state:
            self._state = last_state.state == "on"
        else:
            self._state = True  # Default to on if no previous state
        self._ecu.query_enabled = self._state

    async def async_turn_on(self, **kwargs):
        """Turn on ECU querying."""
        self._ecu.query_enabled = True
        self._state = True
        self.async_write_ha_state()
        # Trigger an immediate coordinator refresh to resume data collection
        await self.coordinator.async_refresh()

    async def async_turn_off(self, **kwargs):
        """Turn off ECU querying."""
        self._ecu.query_enabled = False
        self._state = False
        self.async_write_ha_state()

    def turn_on(self, **kwargs):
        """Turn on ECU querying."""
        return self.async_turn_on(**kwargs)

    def turn_off(self, **kwargs):
        """Turn off ECU querying."""
        return self.async_turn_off(**kwargs)
