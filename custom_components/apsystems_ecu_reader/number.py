"""Number platform for APsystems ECU Reader."""

from homeassistant.components.number import RestoreNumber
from homeassistant.const import UnitOfPower
from homeassistant.helpers.entity import EntityCategory


from .const import DOMAIN
from .entity import APsystemsEcuEntity, APsystemsInverterEntity


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the number platform."""
    coordinator = config_entry.runtime_data.coordinator
    ecu = config_entry.runtime_data.ecu

    entities = []

    # ECU Power Limit Number - only compatible with ECU-C
    if ecu.ecu.ecu_id.startswith("215"):
        entities.append(ECUPowerLimitNumber(coordinator, ecu))

    # Inverter Max Power Numbers - only compatible with ECU-C and ECU-R-Pro
    if ecu.ecu.ecu_id.startswith(("215", "2162")):
        for inverter_id, inverter_data in coordinator.data.get("inverters", {}).items():
            entities.append(
                InverterMaxPwrNumber(coordinator, ecu, inverter_id, inverter_data)
            )

    if entities:
        async_add_entities(entities, True)


class InverterMaxPwrNumber(APsystemsInverterEntity, RestoreNumber):
    """Representation of an Inverter_MaxPwr Number entity."""

    def __init__(self, coordinator, ecu, inverter_id, inverter_data):
        """Initialize the number entity."""
        super().__init__(coordinator, ecu, inverter_id)
        self._inv_data = inverter_data
        self._attr_name = "Max Power"
        self._attr_unique_id = f"{DOMAIN}_inverter_{inverter_id}_maxpwr"
        self._attr_native_min_value = 20
        self._attr_native_max_value = 500
        self._attr_native_step = 1
        default_value = self._inv_data.get("number_value") or 500
        self._attr_native_value = max(default_value, 20)
        self._attr_device_class = "power"
        self._attr_native_unit_of_measurement = UnitOfPower.WATT
        self._attr_mode = "slider"

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
            self._attr_native_value = float(last_state.state)


class ECUPowerLimitNumber(APsystemsEcuEntity, RestoreNumber):
    """Representation of an ECU Power Limit Number entity."""

    def __init__(self, coordinator, ecu):
        """Initialize the number entity."""
        super().__init__(coordinator, ecu)
        self._attr_name = "Power Limit"
        self._attr_unique_id = f"{ecu.ecu.ecu_id}_power_limit"
        self._attr_native_min_value = 0
        self._attr_native_max_value = 3
        self._attr_native_step = 0.1
        self._attr_native_value = 0
        self._attr_device_class = "power"
        self._attr_native_unit_of_measurement = "kW"
        self._attr_mode = "slider"

    @property
    def entity_category(self):
        """Return the category of the entity."""
        return EntityCategory.CONFIG

    @property
    def suggested_display_precision(self):
        """Return the suggested number of decimal places for display."""
        return 1

    async def async_set_native_value(self, value: float):
        """Update the current value."""
        # Convert from kW to watts for the ECU API
        power_limit_watts = int(value * 1000)
        await self._ecu.set_power_limit(power_limit_watts)
        self._attr_native_value = value
        self.async_write_ha_state()

    async def async_added_to_hass(self):
        """Handle entity which value will be restored."""
        await super().async_added_to_hass()
        if (last_state := await self.async_get_last_state()) is not None:
            self._attr_native_value = float(last_state.state)
