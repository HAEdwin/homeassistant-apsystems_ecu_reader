"""Config flow for APsystems ECU Reader."""
import logging
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from .const import DOMAIN, KEYS
from .ecu_api import APsystemsSocket, APsystemsInvalidData

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = 300
PORT_RETRIES = 5
CACHE_REBOOT = 3
SHOW_GRAPHS = True
WIFI_SSID = "ECU-WIFI_local"
WIFI_PASSWORD = "default"

@config_entries.HANDLERS.register(DOMAIN)
class FlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow."""
    VERSION = 1

    def __init__(self):
        """Initialize the flow handler."""
        self.ecu_id = None
        self.user_input = {}

    async def async_step_user(self, user_input=None):
        errors = {}
        init_schema = vol.Schema({
            vol.Required(KEYS[0], default=''): str,
            vol.Required(KEYS[1], default=SCAN_INTERVAL): int,
            vol.Required(KEYS[2], default=PORT_RETRIES): vol.All(int, vol.Range(1, 10)),
            vol.Optional(KEYS[4], default=SHOW_GRAPHS): bool,
        })

        if user_input:
            ecu_id = await test_ecu_connection(user_input)
            if ecu_id:
                _LOGGER.debug("ECU connection successful, ECU ID: %s", ecu_id)
                self.ecu_id = ecu_id
                self.user_input = user_input
                if ecu_id.startswith(("215", "2162")):
                    return await self.async_step_additional_options()
                return self.async_create_entry(title="APsystems", data=user_input)
            errors["ecu_host"] = "no_ecu_found"

        return self.async_show_form(
            step_id="user",
            data_schema=init_schema,
            errors=errors
        )

    async def async_step_additional_options(self, user_input=None):
        """Handle additional options for ECU-R-Pro and ECU-C devices."""
        errors = {}
        additional_schema = vol.Schema({
            vol.Required(KEYS[3], default=CACHE_REBOOT): vol.All(int, vol.Range(3, 5)),
            vol.Optional(KEYS[5], default=WIFI_SSID): str,
            vol.Optional(KEYS[6], default=WIFI_PASSWORD): str,
        })

        if user_input:
            _LOGGER.debug("Received additional options: %s", user_input)
            user_input.update(self.user_input)
            await self.async_set_unique_id(self.ecu_id)
            return self.async_create_entry(title="APsystems", data=user_input)

        return self.async_show_form(
            step_id="additional_options",
            data_schema=additional_schema,
            errors=errors,
            description_placeholders={"title": "Additional Configuration"}
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
        self.entry = entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        errors = {}
        _cfg = {**self.entry.data}
        alter_schema = vol.Schema({
            vol.Required(KEYS[0], default=_cfg.get(KEYS[0])): str,
            vol.Required(KEYS[1], default=_cfg.get(KEYS[1], SCAN_INTERVAL)): int,
            vol.Required(KEYS[2], default=_cfg.get(KEYS[2], PORT_RETRIES)): vol.All(int, vol.Range(1, 10)),
            vol.Optional(KEYS[4], default=_cfg.get(KEYS[4], SHOW_GRAPHS)): bool,
        })

        if user_input:
            ecu_id = await test_ecu_connection(user_input)
            if ecu_id:
                self.hass.config_entries.async_update_entry(
                    self.entry,
                    data={**self.entry.data, **user_input}
                )
                if ecu_id.startswith(("215", "2162")):
                    return await self.async_step_additional_options()
                return self.async_create_entry(title="APsystems", data={})
            errors["ecu_host"] = "no_ecu_found"

        return self.async_show_form(
            step_id="init",
            data_schema=alter_schema,
            errors=errors
        )

    async def async_step_additional_options(self, user_input=None):
        """Handle additional options."""
        errors = {}
        _cfg = {**self.entry.data}
        additional_schema = vol.Schema({
            vol.Required(KEYS[3], default=_cfg.get(KEYS[3], CACHE_REBOOT)): vol.All(int, vol.Range(3, 5)),
            vol.Optional(KEYS[5], default=_cfg.get(KEYS[5], WIFI_SSID)): str,
            vol.Optional(KEYS[6], default=_cfg.get(KEYS[6], WIFI_PASSWORD)): str,
        })

        if user_input:
            _LOGGER.debug("Received additional options: %s", user_input)
            self.hass.config_entries.async_update_entry(
                self.entry,
                data={**self.entry.data, **user_input}
            )
            return self.async_create_entry(title="APsystems", data={})

        return self.async_show_form(
            step_id="additional_options",
            data_schema=additional_schema,
            errors=errors,
            description_placeholders={"title": "Additional Configuration"}
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
