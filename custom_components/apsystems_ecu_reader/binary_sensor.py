"""binary_sensor.py"""

import logging

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, CACHE_ICON

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, _, add_entities):
    """Set up the binary sensor for the APsystems ECU data cache."""
    ecu = hass.data[DOMAIN].get("ecu")
    coordinator = hass.data[DOMAIN].get("coordinator")

    add_entities(
        [
            APsystemsECUBinarySensor(
                coordinator,
                ecu,
                "data_from_cache",
                label=f"{ecu.ecu.ecu_id} Using Cached Data",
                icon=CACHE_ICON,
            )
        ]
    )


class APsystemsECUBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Representation of a binary sensor for APsystems ECU."""

    def __init__(self, coordinator, ecu, field, label=None, icon=None):
        super().__init__(coordinator)
        self.coordinator = coordinator
        self._ecu = ecu
        self._field = field
        self._label = label or field
        self._icon = icon
        self._name = f"ECU {self._label}"
        self._state = None

    @property
    def unique_id(self):
        return f"{self._ecu.ecu.ecu_id}_{self._field}"

    @property
    def name(self):
        return self._name

    @property
    def is_on(self):
        return self.coordinator.data.get(self._field)

    @property
    def icon(self):
        return self._icon

    @property
    def extra_state_attributes(self):
        """Return the state attributes of the sensor."""
        return {
            "ecu_id": self._ecu.ecu.ecu_id,
            "firmware": self._ecu.ecu.firmware,
            "timezone": self._ecu.ecu.timezone,
            "last_update": self._ecu.ecu.last_update,
        }

    @property
    def entity_category(self):
        return EntityCategory.DIAGNOSTIC

    @property
    def device_info(self):
        parent = f"ecu_{self._ecu.ecu.ecu_id}"
        return {
            "identifiers": {
                (DOMAIN, parent),
            }
        }
