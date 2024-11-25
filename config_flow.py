# config_flow.py module

import logging
import voluptuous as vol

from homeassistant.core import callback
from homeassistant import config_entries

from .const import DOMAIN, KEYS
from .APSystemsSocket import APSystemsSocket, APSystemsInvalidData

_LOGGER = logging.getLogger(__name__)


STEP_USER_DATA_SCHEMA = vol.Schema({
    vol.Required(KEYS[0], default= ''): str,
    vol.Required(KEYS[1], default= 300): int,
    vol.Optional(KEYS[2], default= 5): int,
    vol.Optional(KEYS[3], default= "ECU-WIFI_local"): str,
    vol.Optional(KEYS[4], default= "default"): str,
    vol.Optional(KEYS[5], default= False): bool,
})

@config_entries.HANDLERS.register(DOMAIN)
class FlowHandler(config_entries.ConfigFlow):

    VERSION = 1


    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is None:
            # Show form because user input is empty.
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
            )
        
        # User input is not empty, processing input.
        ecu_id = await test_ecu_connection(self.hass, user_input["ecu_host"])
        
        if ecu_id:
            return self.async_create_entry(title=f"ECU: {ecu_id}", data=user_input)
        else:
            errors["ecu_host"] = "no_ecu_found"
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
            )

    # Enable the integration to be reconfigured in the UI
    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return OptionsFlowHandler(config_entry)

class OptionsFlowHandler(config_entries.OptionsFlow):
    """Regular change of integration configuration."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Init options handler."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Altering the integration configuration."""
        errors = {}
        current_options = (
            self.config_entry.data
            if not self.config_entry.options
            else self.config_entry.options
        )
        
        _LOGGER.debug("async_step_init with configuration: %s", current_options)

        schema = vol.Schema(
            {
                vol.Required(KEYS[0], default=current_options.get(KEYS[0])): str,
                vol.Required(KEYS[1], default=current_options.get(KEYS[1])): int,
                vol.Optional(KEYS[2], default=current_options.get(KEYS[2])): int,
                vol.Optional(KEYS[3], default=current_options.get(KEYS[3])): str,
                vol.Optional(KEYS[4], default=current_options.get(KEYS[4])): str,
                vol.Optional(KEYS[5], default=current_options.get(KEYS[5])): bool,
            }
        )

        if user_input:

            ecu_id = await test_ecu_connection(self.hass, user_input["ecu_host"])
            if ecu_id:
                self.hass.config_entries.async_update_entry(
                    self.config_entry, data=user_input
                )
                return self.async_create_entry(title="", data={})
            else:
                errors["ecu_host"] = "no_ecu_found"
                return self.async_show_form(
                    step_id="init", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
                )
        else:
            errors = {}
            return self.async_show_form(
                step_id="init", data_schema=schema, errors=errors
            )


async def test_ecu_connection(hass, ecu_host):
    """Test the connection to the ECU and return the ECU ID if successful."""
    try:
        ap_ecu = APSystemsSocket(ecu_host)
        test_query = await hass.async_add_executor_job(ap_ecu.query_ecu)
        ecu_id = test_query.get("ecu_id", None)
        return ecu_id

    except APSystemsInvalidData as err:
        _LOGGER.debug(f"APSystemsInvalidData exception: {err}")
        return None
    except Exception as err:
        _LOGGER.debug(f"Unknown error occurred during ECU query: {err}")
        return None
