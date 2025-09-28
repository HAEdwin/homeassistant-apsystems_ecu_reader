"""Config flow for APsystems ECU Reader."""

import logging
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from .const import DOMAIN, KEYS
from .ecu_api import APsystemsSocket, APsystemsInvalidData


_LOGGER = logging.getLogger(__name__)

"""Set defaults for the configuration."""
ECU_HOST = ""
SCAN_INTERVAL = 300
PORT_RETRIES = 5
CACHE_REBOOT = 3
SHOW_GRAPHS = True
WIFI_SSID = "ECU-WIFI_local"
WIFI_PASSWORD = "default"


@config_entries.HANDLERS.register(DOMAIN)
class FlowHandler(config_entries.ConfigFlow):
    """Handle a config flow."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        init_schema = vol.Schema(
            {
                vol.Required(KEYS[0], default=ECU_HOST): str,
                vol.Required(KEYS[1], default=SCAN_INTERVAL): int,
                vol.Required(KEYS[2], default=PORT_RETRIES): vol.All(
                    int, vol.Range(min=1, max=10)
                ),
                vol.Required(KEYS[3], default=CACHE_REBOOT): vol.All(
                    int, vol.Range(min=3, max=5)
                ),
                vol.Optional(KEYS[4], default=SHOW_GRAPHS): bool,
                vol.Optional(KEYS[5], default=WIFI_SSID): str,
                vol.Optional(KEYS[6], default=WIFI_PASSWORD): str,
            }
        )

        if user_input:
            ecu_id = await test_ecu_connection(user_input)
            if ecu_id:
                await self.async_set_unique_id(ecu_id)
                self._abort_if_unique_id_configured()
                # Use the ECU-ID in the title to ensure uniqueness
                return self.async_create_entry(
                    title=f"APsystems ECU {ecu_id}", data=user_input
                )
            errors["ecu_host"] = "no_ecu_found"

        # Show form because user input is empty.
        return self.async_show_form(
            step_id="user", data_schema=init_schema, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow changes."""

    def __init__(self, entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        super().__init__()
        self.entry = entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        errors = {}
        # Get current options
        _config = {**self.entry.data}
        alter_schema = vol.Schema(
            {
                vol.Required(KEYS[0], default=_config.get(KEYS[0], ECU_HOST)): str,
                vol.Required(KEYS[1], default=_config.get(KEYS[1], SCAN_INTERVAL)): int,
                vol.Required(
                    KEYS[2], default=_config.get(KEYS[2], PORT_RETRIES)
                ): vol.All(int, vol.Range(min=1, max=10)),
                vol.Required(
                    KEYS[3], default=_config.get(KEYS[3], CACHE_REBOOT)
                ): vol.All(int, vol.Range(min=3, max=5)),
                vol.Optional(KEYS[4], default=_config.get(KEYS[4], SHOW_GRAPHS)): bool,
                vol.Optional(KEYS[5], default=_config.get(KEYS[5], WIFI_SSID)): str,
                vol.Optional(KEYS[6], default=_config.get(KEYS[6], WIFI_PASSWORD)): str,
            }
        )

        if user_input:
            ecu_id = await test_ecu_connection(user_input)
            if ecu_id:
                self.hass.config_entries.async_update_entry(
                    self.entry, data={**self.entry.data, **user_input}
                )
                return self.async_create_entry(title="APsystems", data={})
            errors["ecu_host"] = "no_ecu_found"
        return self.async_show_form(
            step_id="init", data_schema=alter_schema, errors=errors
        )


async def test_ecu_connection(input_data):
    """Test the connection to the ECU and return the ECU ID if successful."""
    try:
        ecu = APsystemsSocket(input_data.get(KEYS[0]))
        retries = input_data.get(KEYS[2], 2)
        test_query = await ecu.get_update(retries, True)
        return test_query.get("ecu_id", None)
    # collector of APsystemsInvalidData exceptions
    except APsystemsInvalidData as err:
        _LOGGER.warning(
            "APsystems invalid data exception for ECU %s: %s", ecu.ecu_id, err
        )
        return None
