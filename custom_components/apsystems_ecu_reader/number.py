"""Number platform for APsystems ECU Reader."""

from homeassistant.components.number import RestoreNumber
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

async def async_setup_entry(hass, _, async_add_entities):
    """Set up the number platform."""
    coordinator = hass.data[DOMAIN]["coordinator"]
    ecu = hass.data[DOMAIN]["ecu"]

    entities = []
    for inverter_id, inverter_data in coordinator.data.get("inverters", {}).items():
        entities.append(InverterMaxPwrNumber(coordinator, ecu, inverter_id, inverter_data))

    async_add_entities(entities, True)

class InverterMaxPwrNumber(CoordinatorEntity, RestoreNumber):
    """Representation of an Inverter_MaxPwr Number entity."""

    #def set_native_value(self, value: float) -> None:
    #    """Set new value."""
    #    self._attr_native_value = value
    #    self.async_write_ha_state()

    def __init__(self, coordinator, ecu, inverter_id, inverter_data):
        """Initialize the number entity."""
        super().__init__(coordinator)
        self.ecu = ecu
        self.inverter_id = inverter_id
        self.inverter_data = inverter_data
        self._attr_name = f"Inverter {inverter_id} Maxpwr"
        self._attr_unique_id = f"{DOMAIN}_inverter_{inverter_id}_maxpwr"
        self._attr_native_min_value = 20
        self._attr_native_max_value = 500
        self._attr_native_step = 1
        self._attr_native_value = inverter_data.get("number_value", 0)
        self._attr_device_class = "power"  # Set device class
        self._attr_mode = "slider"  # Set mode to slider

    async def async_set_native_value(self, value: float):
        """Update the current value."""
        await self.ecu.set_inverter_max_power(self.inverter_id, value)
        self._attr_native_value = value
        self.async_write_ha_state()

    async def async_added_to_hass(self):
        """Handle entity which value will be restored."""
        await super().async_added_to_hass()
        if (last_state := await self.async_get_last_state()) is not None:
            self._attr_native_value = last_state.state
