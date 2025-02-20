"""Config flow for APsystems ECU Reader."""
import logging
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from .const import DOMAIN, KEYS
from .ecu_api import APsystemsSocket, APsystemsInvalidData


_LOGGER = logging.getLogger(__name__)


@config_entries.HANDLERS.register(DOMAIN)
class FlowHandler(config_entries.ConfigFlow):
    """Handle a config flow."""
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        init_schema = vol.Schema({
            vol.Required(KEYS[0], default=''): str, # ECU Host
            vol.Required(KEYS[1], default=300): int, # scan interval
            vol.Required(KEYS[2], default=5): vol.All(int, vol.Range(min=1, max=10)), # Port retries
            vol.Required(KEYS[3], default=3): vol.All(int, vol.Range(min=3, max=5)), # Cache reboot
            vol.Optional(KEYS[4], default=True): bool, # Show graphs
            vol.Optional(KEYS[5], default="ECU-WIFI_local"): str, # SSID
            vol.Optional(KEYS[6], default="default"): str, # Password
        })

        if user_input:
            ecu_id = await test_ecu_connection(user_input)
            if ecu_id:
                await self.async_set_unique_id(ecu_id)
                return self.async_create_entry(title="APsystems", data=user_input)
            errors["ecu_host"] = "no_ecu_found"

        # Show form because user input is empty.
        return self.async_show_form(
            step_id="user",
            data_schema=init_schema,
            errors=errors
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
        current_config = {**self.entry.data}
        alter_schema = vol.Schema({
            vol.Required(KEYS[0], default=current_config.get(KEYS[0])): str,  # ECU Host
            vol.Required(KEYS[1], default=current_config.get(KEYS[1], 300)): int, # Scan interval
            vol.Required(
                KEYS[2],
                default=current_config.get(KEYS[2], 5)
            ): vol.All(
                int,
                vol.Range(min=1, max=10)
            ), # Port retries
            vol.Required(
                KEYS[3],
                default=current_config.get(KEYS[3], 3)
            ): vol.All(
                int,
                vol.Range(min=3, max=5)
            ), # Cache reboot
            vol.Optional(KEYS[4], default=current_config.get(KEYS[4], True)): bool,  # Show graphs
            vol.Optional(KEYS[5], default=current_config.get(KEYS[5], "ECU-local")): str,  # SSID
            vol.Optional(KEYS[6], default=current_config.get(KEYS[6], "default")): str, # Password
        })

        if user_input:
            ecu_id = await test_ecu_connection(user_input)
            if ecu_id:
                self.hass.config_entries.async_update_entry(
                    self.entry,
                    data={**self.entry.data, **user_input}
                )
                return self.async_create_entry(title="APsystems", data={})
            errors["ecu_host"] = "no_ecu_found"
        return self.async_show_form(
            step_id="init",
            data_schema=alter_schema,
            errors=errors
        )

async def test_ecu_connection(input_data):
    """Test the connection to the ECU and return the ECU ID if successful."""
    try:
        ecu = APsystemsSocket(input_data.get(KEYS[0]))
        retries = input_data.get(KEYS[2], 2)
        test_query = await ecu.query_ecu(retries, True)
        return test_query.get("ecu_id", None)
    except APsystemsInvalidData as err:
        _LOGGER.debug("APsystemsInvalidData exception: %s", err)
        return None
