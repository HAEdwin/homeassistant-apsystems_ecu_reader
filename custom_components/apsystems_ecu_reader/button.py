"""Button platform for APsystems ECU Reader."""

import logging
from homeassistant.components.button import ButtonEntity, ButtonDeviceClass
from homeassistant.helpers.entity import EntityCategory


from .const import DOMAIN, ECU_REBOOT_ICON, ECU_MODEL_MAP
from .gui_helpers import pers_gui_notification


_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the button platform."""
    ecu = hass.data[DOMAIN][config_entry.entry_id]["ecu"]

    # Add the button only if ecu_id starts with "2162" (ECU-R-Pro) or "215" (ECU-C)
    if ecu.ecu.ecu_id.startswith(("215", "2162")):
        async_add_entities([RebootECUButton(ecu)])


class RebootECUButton(ButtonEntity):
    """Representation of a button to reboot the ECU."""

    def press(self):
        """Handle the synchronous button press."""
        self.hass.async_create_task(self.async_press())

    def __init__(self, ecu):
        """Initialize the button."""
        self._ecu = ecu
        self._attr_icon = ECU_REBOOT_ICON
        self._attr_name = f"ECU {ecu.ecu.ecu_id} Reboot"
        self._attr_unique_id = f"ECU_{ecu.ecu.ecu_id}_reboot_button"
        self._attr_device_class = ButtonDeviceClass.RESTART

    @property
    def device_info(self):
        """Return the device info for the ECU."""
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
        return EntityCategory.DIAGNOSTIC

    async def async_press(self):
        """Handle the button press."""
        try:
            response = await self._ecu.reboot_ecu()

            # Interpret the response
            if response == '{"value":0}':
                message = f"Rebooted ECU {self._ecu.ecu.ecu_id} successfully."
            else:
                message = f"Reboot ECU {self._ecu.ecu.ecu_id} failed."

            # Send notification
            pers_gui_notification(self.hass, message)

        except (ConnectionError, TimeoutError, ValueError) as e:
            _LOGGER.error("Failed to reboot ECU %s: %s", self._ecu.ecu.ecu_id, e)
            pers_gui_notification(self.hass, f"Failed to reboot ECU: {e}")
