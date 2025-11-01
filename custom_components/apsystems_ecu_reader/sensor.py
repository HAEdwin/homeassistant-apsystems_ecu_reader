"""sensor.py"""

import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
)
from homeassistant.helpers.restore_state import RestoreEntity

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorStateClass,
)

from homeassistant.const import (
    UnitOfPower,
    UnitOfEnergy,
    UnitOfTemperature,
    UnitOfElectricPotential,
    UnitOfFrequency,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT as dBm,
)


from homeassistant.core import callback

from .const import (
    DOMAIN,
    SOLAR_ICON,
    FREQ_ICON,
    SIGNAL_ICON,
    SOLAR_PANEL_ICON,
    CACHE_COUNTER_ICON,
    FROM_GRID_ICON,
    CONSUMED_ICON,
    DOWNLOAD_ICON,
    INVERTER_MODEL_MAP,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, add_entities):
    """sensor.py async_setup_entry"""

    ecu = hass.data[DOMAIN][config_entry.entry_id]["ecu"]
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]

    # Add ECU sensors
    sensors = [
        APsystemsECUSensor(
            coordinator,
            ecu,
            "current_power",
            label=f"{ecu.ecu.ecu_id} Current Power",
            unit=UnitOfPower.WATT,
            devclass=SensorDeviceClass.POWER,
            icon=SOLAR_ICON,
            stateclass=SensorStateClass.MEASUREMENT,
        ),
        APsystemsECUSensor(
            coordinator,
            ecu,
            "today_energy",
            label=f"{ecu.ecu.ecu_id} Today Energy",
            unit=UnitOfEnergy.KILO_WATT_HOUR,
            devclass=SensorDeviceClass.ENERGY,
            icon=SOLAR_ICON,
            stateclass=SensorStateClass.TOTAL_INCREASING,
        ),
        APsystemsECUSensor(
            coordinator,
            ecu,
            "lifetime_energy",
            label=f"{ecu.ecu.ecu_id} Lifetime Energy",
            unit=UnitOfEnergy.KILO_WATT_HOUR,
            devclass=SensorDeviceClass.ENERGY,
            icon=SOLAR_ICON,
            stateclass=SensorStateClass.TOTAL_INCREASING,
        ),
        APsystemsECUSensor(
            coordinator,
            ecu,
            "lifetime_maximum_power",
            label=f"{ecu.ecu.ecu_id} Lifetime Maximum Power",
            unit=UnitOfPower.WATT,
            devclass=SensorDeviceClass.POWER,
            icon=SOLAR_ICON,
            stateclass=SensorStateClass.MEASUREMENT,
        ),
        APsystemsECUSensor(
            coordinator,
            ecu,
            "qty_of_inverters",
            label=f"{ecu.ecu.ecu_id} Inverters",
            icon=SOLAR_ICON,
            entity_category=EntityCategory.DIAGNOSTIC,
        ),
        APsystemsECUSensor(
            coordinator,
            ecu,
            "qty_of_online_inverters",
            label=f"{ecu.ecu.ecu_id} Inverters Online",
            icon=SOLAR_ICON,
            entity_category=EntityCategory.DIAGNOSTIC,
        ),
        APsystemsECUSensor(
            coordinator,
            ecu,
            "data_from_cache_count",
            label=f"{ecu.ecu.ecu_id} Using Cache Counter",
            icon=CACHE_COUNTER_ICON,
            entity_category=EntityCategory.DIAGNOSTIC,
        ),
        APsystemsECUFirmwareSensor(
            coordinator,
            ecu,
            "firmware_version",
            label="Firmware Version",
            icon=DOWNLOAD_ICON,
            entity_category=EntityCategory.DIAGNOSTIC,
        ),
    ]

    # Add CT sensors for ECU-C only
    if ecu.ecu.ecu_id.startswith("215"):
        # Add production CT sensors
        sensors.extend(
            [
                APsystemsECUSensor(
                    coordinator,
                    ecu,
                    "production_ct_a",
                    label=f"{ecu.ecu.ecu_id} Production CT A",
                    unit=UnitOfPower.WATT,
                    devclass=SensorDeviceClass.POWER,
                    icon=SOLAR_ICON,
                    stateclass=SensorStateClass.MEASUREMENT,
                ),
                APsystemsECUSensor(
                    coordinator,
                    ecu,
                    "production_ct_b",
                    label=f"{ecu.ecu.ecu_id} Production CT B",
                    unit=UnitOfPower.WATT,
                    devclass=SensorDeviceClass.POWER,
                    icon=SOLAR_ICON,
                    stateclass=SensorStateClass.MEASUREMENT,
                ),
                APsystemsECUSensor(
                    coordinator,
                    ecu,
                    "production_ct_c",
                    label=f"{ecu.ecu.ecu_id} Production CT C",
                    unit=UnitOfPower.WATT,
                    devclass=SensorDeviceClass.POWER,
                    icon=SOLAR_ICON,
                    stateclass=SensorStateClass.MEASUREMENT,
                ),
            ]
        )

        # Add grid CT sensors
        sensors.extend(
            [
                APsystemsECUSensor(
                    coordinator,
                    ecu,
                    "grid_ct_a",
                    label=f"{ecu.ecu.ecu_id} Grid CT A",
                    unit=UnitOfPower.WATT,
                    devclass=SensorDeviceClass.POWER,
                    icon=FROM_GRID_ICON,
                    stateclass=SensorStateClass.MEASUREMENT,
                ),
                APsystemsECUSensor(
                    coordinator,
                    ecu,
                    "grid_ct_b",
                    label=f"{ecu.ecu.ecu_id} Grid CT B",
                    unit=UnitOfPower.WATT,
                    devclass=SensorDeviceClass.POWER,
                    icon=FROM_GRID_ICON,
                    stateclass=SensorStateClass.MEASUREMENT,
                ),
                APsystemsECUSensor(
                    coordinator,
                    ecu,
                    "grid_ct_c",
                    label=f"{ecu.ecu.ecu_id} Grid CT C",
                    unit=UnitOfPower.WATT,
                    devclass=SensorDeviceClass.POWER,
                    icon=FROM_GRID_ICON,
                    stateclass=SensorStateClass.MEASUREMENT,
                ),
            ]
        )

        # Add consumed CT sensors
        sensors.extend(
            [
                APsystemsECUSensor(
                    coordinator,
                    ecu,
                    "consumed_a",
                    label=f"{ecu.ecu.ecu_id} Consumed A",
                    unit=UnitOfPower.WATT,
                    devclass=SensorDeviceClass.POWER,
                    icon=CONSUMED_ICON,
                    stateclass=SensorStateClass.MEASUREMENT,
                ),
                APsystemsECUSensor(
                    coordinator,
                    ecu,
                    "consumed_b",
                    label=f"{ecu.ecu.ecu_id} Consumed B",
                    unit=UnitOfPower.WATT,
                    devclass=SensorDeviceClass.POWER,
                    icon=CONSUMED_ICON,
                    stateclass=SensorStateClass.MEASUREMENT,
                ),
                APsystemsECUSensor(
                    coordinator,
                    ecu,
                    "consumed_c",
                    label=f"{ecu.ecu.ecu_id} Consumed C",
                    unit=UnitOfPower.WATT,
                    devclass=SensorDeviceClass.POWER,
                    icon=CONSUMED_ICON,
                    stateclass=SensorStateClass.MEASUREMENT,
                ),
            ]
        )

    # Add inverter binary sensors
    inverters = coordinator.data.get("inverters", {})
    for uid, inv_data in inverters.items():
        sensors.append(
            APsystemsECUInverterBinarySensor(coordinator, ecu, uid, inv_data)
        )

    # Add Inverter sensors
    inverters = coordinator.data.get("inverters", {})
    for uid, inv_data in inverters.items():

        # if statement for configured but not yet connected inverters
        if inv_data.get("channel_qty"):
            sensors.extend(
                [
                    APsystemsECUInverterSensor(
                        coordinator,
                        ecu,
                        uid,
                        "temperature",
                        label="Temperature",
                        unit=UnitOfTemperature.CELSIUS,
                        devclass=SensorDeviceClass.TEMPERATURE,
                        stateclass=SensorStateClass.MEASUREMENT,
                        entity_category=EntityCategory.DIAGNOSTIC,
                    ),
                    APsystemsECUInverterSensor(
                        coordinator,
                        ecu,
                        uid,
                        "frequency",
                        label="Frequency",
                        unit=UnitOfFrequency.HERTZ,
                        stateclass=SensorStateClass.MEASUREMENT,
                        devclass=SensorDeviceClass.FREQUENCY,
                        icon=FREQ_ICON,
                        entity_category=EntityCategory.DIAGNOSTIC,
                    ),
                    APsystemsECUInverterSensor(
                        coordinator,
                        ecu,
                        uid,
                        "signal",
                        unit=dBm,
                        stateclass=SensorStateClass.MEASUREMENT,
                        devclass=SensorDeviceClass.SIGNAL_STRENGTH,
                        icon=SIGNAL_ICON,
                        entity_category=EntityCategory.DIAGNOSTIC,
                    ),
                ]
            )

            # 3-phase inverters
            if inv_data.get("uid")[:2] in ["50", "90"]:
                for i, label in enumerate(["Voltage L1", "Voltage L2", "Voltage L3"]):
                    sensors.append(
                        APsystemsECUInverterSensor(
                            coordinator,
                            ecu,
                            uid,
                            "voltage",
                            index=i,
                            label=label,
                            unit=UnitOfElectricPotential.VOLT,
                            stateclass=SensorStateClass.MEASUREMENT,
                            devclass=SensorDeviceClass.VOLTAGE,
                            entity_category=EntityCategory.DIAGNOSTIC,
                        )
                    )
            else:  # single-phase inverters
                sensors.append(
                    APsystemsECUInverterSensor(
                        coordinator,
                        ecu,
                        uid,
                        "voltage",
                        index=0,
                        label="Voltage",
                        unit=UnitOfElectricPotential.VOLT,
                        stateclass=SensorStateClass.MEASUREMENT,
                        devclass=SensorDeviceClass.VOLTAGE,
                        entity_category=EntityCategory.DIAGNOSTIC,
                    )
                )

            for i in range(0, inv_data.get("channel_qty", 0)):
                sensors.append(
                    APsystemsECUInverterSensor(
                        coordinator,
                        ecu,
                        uid,
                        "power",
                        index=i,
                        label=f"Power Ch {i+1}",
                        unit=UnitOfPower.WATT,
                        devclass=SensorDeviceClass.POWER,
                        icon=SOLAR_ICON,
                        stateclass=SensorStateClass.MEASUREMENT,
                    )
                )
    add_entities(sensors)


class APsystemsECUInverterBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Representation of a binary sensor for an individual inverter being Online/Offline."""

    def __init__(self, coordinator, ecu, uid, inv_data):

        super().__init__(coordinator)
        self.coordinator = coordinator
        self._ecu = ecu
        self._uid = uid
        self._inv_data = inv_data
        self._name = f"Inverter {uid} Online"
        self._state = inv_data.get("online", False)
        self._attr_name = f"Inverter {uid} Online"

        # Set custom state attributes for activity log
        self._attr_device_class = None
        self._attr_should_poll = False

        # Override default state values to show true/false in activity log
        self._attr_extra_state_attributes = {}

    @property
    def state(self):
        """Return custom state for activity log."""
        return "true" if self.is_on else "false"

    async def async_added_to_hass(self):
        """Handle entity which will be added."""
        await super().async_added_to_hass()
        self.async_on_remove(
            self.coordinator.async_add_listener(self._handle_coordinator_update)
        )

    @property
    def unique_id(self):
        """Return the unique id of the binary sensor."""
        return f"{self._ecu.ecu.ecu_id}_inverter_{self._uid}_online"

    @property
    def name(self):
        """Return the name of the binary sensor."""
        return self._name

    @property
    def icon(self):
        """Return the icon to use in the frontend, if any."""
        return SOLAR_PANEL_ICON

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
        return EntityCategory.DIAGNOSTIC

    @property
    def is_on(self):
        """Return the state of the binary sensor."""
        return self._inv_data.get("online", False)

    @property
    def device_class(self):
        """Return the device class of the binary sensor."""
        return None  # No device class to avoid default "turned on/off" messages

    @property
    def extra_state_attributes(self):
        """Return the extra state attributes."""
        return {
            "timezone": self._ecu.ecu.timezone,
            "last_data_update": self._ecu.ecu.last_update,
            "state_display": "true" if self.is_on else "false",
        }

    @callback
    def _handle_coordinator_update(self):
        """Handle updated data from the coordinator."""
        self._inv_data = self.coordinator.data["inverters"].get(
            self._uid, self._inv_data
        )
        self.async_write_ha_state()


class APsystemsECUInverterSensor(CoordinatorEntity, SensorEntity):
    """sensor.py APsystemsECUInverterSensor"""

    def __init__(
        self,
        coordinator,
        ecu,
        uid,
        field,
        index=0,
        label=None,
        icon=None,
        unit=None,
        devclass=None,
        stateclass=None,
        entity_category=None,
    ):

        super().__init__(coordinator)
        self.coordinator = coordinator
        self._index = index
        self._uid = uid
        self._ecu = ecu
        self._field = field
        self._devclass = devclass
        self._label = label
        self._label = label or field
        self._icon = icon
        self._unit = unit
        self._stateclass = stateclass
        self._entity_category = entity_category
        self._name = f"Inverter {self._uid} {self._label}"
        self._state = None

    @property
    def unique_id(self):
        field = self._field
        if self._index:
            field = f"{field}_{self._index}"
        return f"{self._ecu.ecu.ecu_id}_{self._uid}_{field}"

    @property
    def device_class(self):
        return self._devclass

    @property
    def name(self):
        return self._name

    @property
    def native_value(self):
        """Return the state of the sensor."""
        # _LOGGER.debug("State called for %s", self._field)
        if self._field == "voltage":
            # _LOGGER.debug("VOLTAGE  %s %s", self._uid, self._index)
            return (
                self.coordinator.data.get("inverters", {})
                .get(self._uid, {})
                .get("voltage", [])[self._index]
            )
        elif self._field == "power":
            # _LOGGER.debug("POWER  %s %s", self._uid, self._index)
            return (
                self.coordinator.data.get("inverters", {})
                .get(self._uid, {})
                .get("power", [])[self._index]
            )
        else:
            return (
                self.coordinator.data.get("inverters", {})
                .get(self._uid, {})
                .get(self._field)
            )

    @property
    def icon(self):
        return self._icon

    @property
    def native_unit_of_measurement(self):
        return self._unit

    @property
    def extra_state_attributes(self):
        return {
            "timezone": self._ecu.ecu.timezone,
            "last_data_update": self._ecu.ecu.last_update,
        }

    @property
    def state_class(self):
        # _LOGGER.debug("State class %s - %s", self._stateclass, self._field)
        return self._stateclass

    @property
    def device_info(self):
        parent = f"inverter_{self._uid}"
        return {
            "identifiers": {
                (DOMAIN, parent),
            }
        }

    @property
    def entity_category(self):
        return self._entity_category


class APsystemsECUSensor(CoordinatorEntity, SensorEntity, RestoreEntity):
    """sensor.py APsystemsECUSensor"""

    def __init__(
        self,
        coordinator,
        ecu,
        field,
        label=None,
        icon=None,
        unit=None,
        devclass=None,
        stateclass=None,
        entity_category=None,
        #    disabled_by=None,
    ):
        super().__init__(coordinator)
        self.coordinator = coordinator
        self._ecu = ecu
        self._field = field
        self._label = label or field
        self._icon = icon
        self._unit = unit
        self._devclass = devclass
        self._stateclass = stateclass
        self._entity_category = entity_category
        #    self._disabled_by = disabled_by
        self._name = f"ECU {self._label}"
        self._state = None

    async def async_added_to_hass(self):
        """Handle entity that needs to be restored."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state and self._field == "lifetime_maximum_power":
            try:
                self._state = (
                    0
                    if last_state.state in ["unknown", "unavailable"]
                    else float(last_state.state)
                )
            except ValueError:
                self._state = 0

    @property
    def unique_id(self):
        return f"{self._ecu.ecu.ecu_id}_{self._field}"

    @property
    def name(self):
        return self._name

    @property
    def device_class(self):
        return self._devclass

    @property
    def native_value(self):
        """Return the state of the sensor."""
        # Get the current value from the coordinator data
        if self._field == "lifetime_maximum_power":
            current_power = self.coordinator.data.get("current_power", 0) or 0
            self._state = max(self._state or 0, current_power)
            return round(self._state)
        else:
            return self.coordinator.data.get(self._field, 0)

    @property
    def icon(self):
        return self._icon

    @property
    def native_unit_of_measurement(self):
        return self._unit

    @property
    def extra_state_attributes(self):
        return {
            "timezone": self._ecu.ecu.timezone,
            "last_data_update": self._ecu.ecu.last_update,
        }

    @property
    def state_class(self):
        # _LOGGER.debug("State class %s - %s", self._stateclass, self._field)
        return self._stateclass

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
        return self._entity_category


class APsystemsECUFirmwareSensor(CoordinatorEntity, SensorEntity, RestoreEntity):
    """Representation of the ECU firmware version sensor."""

    def __init__(
        self,
        coordinator,
        ecu,
        field,
        label=None,
        icon=None,
        entity_category=None,
    ):
        super().__init__(coordinator)
        self.coordinator = coordinator
        self._ecu = ecu
        self._field = field
        self._label = label or field
        self._icon = icon
        self._entity_category = entity_category
        self._name = "Firmware Version"
        self._attr_has_entity_name = True
        self._state = None

    async def async_added_to_hass(self):
        """Handle entity that needs to be restored."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state:
            self._state = (
                last_state.state
                if last_state.state not in ["unknown", "unavailable"]
                else None
            )

    @property
    def unique_id(self):
        """Return the unique ID for this sensor."""
        return f"{self._ecu.ecu.ecu_id}_{self._field}"

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def native_value(self):
        """Return the firmware version."""
        return self._ecu.ecu.firmware

    @property
    def icon(self):
        """Return the icon of the sensor."""
        return self._icon

    @property
    def extra_state_attributes(self):
        """Return the state attributes of the entity."""
        return {
            "ip_address": self._ecu.ipaddr,
            "timezone": self._ecu.ecu.timezone,
            "last_data_update": self._ecu.ecu.last_update,
        }

    @property
    def device_info(self):
        """Return device info."""
        parent = f"ecu_{self._ecu.ecu.ecu_id}"
        return {
            "identifiers": {
                (DOMAIN, parent),
            }
        }

    @property
    def entity_category(self):
        """Return the category of the entity."""
        return self._entity_category
