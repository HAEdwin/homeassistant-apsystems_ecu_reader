"""Config flow for APsystems ECU Reader."""
import logging
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from .const import DOMAIN, KEYS
from .ecu_api import APsystemsSocket, APsystemsInvalidData

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema({
    vol.Required(KEYS[0], default=''): str,                # ECU Host
    vol.Required(KEYS[1], default=300): int,               # Scan interval
    vol.Optional(KEYS[2], default=5): int,                 # Port retries
    vol.Optional(KEYS[3], default=3): int,                 # Cache reboot
    vol.Optional(KEYS[4], default=True): bool,             # Show graphs
})

@config_entries.HANDLERS.register(DOMAIN)
class FlowHandler(config_entries.ConfigFlow):
    """Handle a config flow."""
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is None:
            # Show form because user input is empty.
            return self.async_show_form(
                step_id="user",
                data_schema=STEP_USER_DATA_SCHEMA,
                errors=errors
            )

        # User input is not empty, processing input.
        retries = user_input.get(KEYS[2], 5)  # port_retries, default = 5
        cache_reboot = user_input.get(KEYS[3], 3)  # cache_reboot, default = 3
        show_graphs = user_input.get(KEYS[4], False)  # show_graphs, default = False

        ecu_id = await test_ecu_connection(
            user_input[KEYS[0]],
            retries,
            cache_reboot,
            show_graphs
        )

        if ecu_id:
            return self.async_create_entry(title=f"ECU: {ecu_id}", data=user_input)

        errors["ecu_host"] = "no_ecu_found"
        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
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
        current_options = {**self.entry.data}

        schema = vol.Schema({
            vol.Required(KEYS[0], default=current_options.get(KEYS[0])): str,  # ECU Host
            vol.Required(KEYS[1], default=current_options.get(KEYS[1])): int,  # Scan interval
            vol.Optional(KEYS[2], default=current_options.get(KEYS[2], 5)): int,  # Port retries
            vol.Optional(KEYS[3], default=current_options.get(KEYS[3], 3)): int,  # Cache reboot
            vol.Optional(KEYS[4], default=current_options.get(KEYS[4], True)): bool,  # Show graphs
        })

        if user_input is not None:
            retries = user_input.get(KEYS[2], 5)
            cache_reboot = user_input.get(KEYS[3], 3)
            show_graphs = user_input.get(KEYS[4], False)

            ecu_id = await test_ecu_connection(
                user_input[KEYS[0]],
                retries,
                cache_reboot,
                show_graphs
            )

            if ecu_id:
                self.hass.config_entries.async_update_entry(
                    self.entry, data=user_input
                )
                return self.async_create_entry(title=f"ECU: {ecu_id}", data={})

            errors["ecu_host"] = "no_ecu_found"
        return self.async_show_form(
            step_id="init",
            data_schema=schema,
            errors=errors
        )


async def test_ecu_connection(ecu_host, retries, cache_reboot, show_graphs):
    """Test the connection to the ECU and return the ECU ID if successful."""
    try:
        ap_ecu = APsystemsSocket(ecu_host, cache_reboot, show_graphs)
        # Pass the retries parameter dynamically
        test_query = await ap_ecu.query_ecu(retries, show_graphs)
        ecu_id = test_query.get("ecu_id", None)
        return ecu_id
    except APsystemsInvalidData as err:
        _LOGGER.debug("APsystemsInvalidData exception: %s", err)
        return None
