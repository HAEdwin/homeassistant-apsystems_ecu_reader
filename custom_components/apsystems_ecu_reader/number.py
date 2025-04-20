"""Number platform for APsystems ECU Reader."""

from homeassistant.components.number import RestoreNumber
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import EntityCategory

from .const import DOMAIN, INVERTER_MODEL_MAP


async def async_setup_entry(hass, _, async_add_entities):
    """Set up the number platform."""
    coordinator = hass.data[DOMAIN]["coordinator"]
    ecu = hass.data[DOMAIN]["ecu"]

    entities = []
    for inverter_id, inverter_data in coordinator.data.get("inverters", {}).items():
        entities.append(
            InverterMaxPwrNumber(coordinator, ecu, inverter_id, inverter_data)
        )

    async_add_entities(entities, True)


class InverterMaxPwrNumber(CoordinatorEntity, RestoreNumber):
    """Representation of an Inverter_MaxPwr Number entity."""

    def __init__(self, coordinator, ecu, inverter_id, inverter_data):
        """Initialize the number entity."""
        super().__init__(coordinator)
        self._ecu = ecu
        self._uid = inverter_id
        self._inv_data = inverter_data
        self._attr_name = f"Inverter {inverter_id} Maxpwr"
        self._attr_unique_id = f"{DOMAIN}_inverter_{inverter_id}_maxpwr"
        self._attr_native_min_value = 20
        self._attr_native_max_value = 500
        self._attr_native_step = 1
        self._attr_native_value = self._inv_data.get("number_value", 0)
        self._attr_device_class = "power"  # Set device class
        self._attr_mode = "slider"  # Set mode to slider

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

    @property
    def entity_category(self):
        """Return the category of the entity."""
        return EntityCategory.CONFIG

    async def async_set_native_value(self, value: float):
        """Update the current value."""
        await self._ecu.set_inverter_max_power(self._uid, value)
        self._attr_native_value = value
        self.async_write_ha_state()

    async def async_added_to_hass(self):
        """Handle entity which value will be restored."""
        await super().async_added_to_hass()
        if (last_state := await self.async_get_last_state()) is not None:
            self._attr_native_value = last_state.state
