""" __init__.py """


# Standard library imports
import logging
from datetime import timedelta

# Third-party imports
import requests
from homeassistant.helpers import device_registry as dr
from homeassistant.components.persistent_notification import create as create_persistent_notification
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from .ecu_api import APsystemsSocket, APsystemsInvalidData
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor", "binary_sensor", "switch"]


class ECUR:
    def __init__(self, ipaddr, ssid, wpa, show_graphs):
        self.ipaddr = ipaddr
        self.show_graphs = show_graphs
        self.cache_count = 0
        self.data_from_cache = False
        self.is_querying = True
        self.inverters_online = True
        self.ecu_restarting = False
        self.cached_data = {}
        self.ecu = APsystemsSocket(ipaddr, self.show_graphs)


    # called from switch.py
    def set_querying_state(self, state: bool):
        """Set the querying state to either True or False."""
        self.is_querying = state

    # called from switch.py
    def toggle_all_inverters(self, turn_on: bool):
        action = 'on' if turn_on else 'off'
        headers = {'X-Requested-With': 'XMLHttpRequest'}
        url = f'http://{self.ipaddr}/index.php/configuration/set_switch_all_{action}'
        _LOGGER.debug("URL = %s", url)
        try:
            get_url = requests.post(url, headers=headers)
            self.inverters_online = turn_on
            _LOGGER.debug(
                "Response from ECU on switching the inverters \n\t%s: %s",
                action, str(get_url.status_code)
            )
        except Exception as err:
            _LOGGER.warning(
                "Attempt to switch inverters %s failed with error: \n\t%s\n\t"
                "This switch is only compatible with ECU-R pro and ECU-C models",
                action, err
            )

    async def update(self, port_retries, show_graphs):
        # Fetch ECU data or use cached data.
        data = {}
        
        # If querying is stopped, use cached data.
        if not self.is_querying:
            _LOGGER.debug("Not querying ECU, using cached data.")
            data = self.cached_data
            self.data_from_cache = True
            data["data_from_cache"] = self.data_from_cache
            data["querying"] = self.is_querying
            return self.cached_data
        try:
            # Fetch the latest port_retries value dynamically.
            data = await self.ecu.query_ecu(port_retries, show_graphs)

            if data.get("ecu_id"):
                self.cached_data = data
                self.cache_count = 0
                self.data_from_cache = False
                self.ecu_restarting = False
                self.error_message = ""
            else:
                msg = "Using cached data. No ecu_id returned."
                _LOGGER.warning(msg)
                self.cached_data["error_message"] = msg
                data = self.cached_data

        except APsystemsInvalidData as err:
            msg = f"Invalid data error: {err}. Using cached data."
            if str(err) != 'timed out':
                _LOGGER.warning(msg)
            self.cached_data["error_message"] = msg
            data = self.cached_data

        except Exception as err:
            msg = "General exception error. Using cached data."
            _LOGGER.warning("Exception error: %s. Using cached data.", err)
            self.cached_data["error_message"] = msg
            data = self.cached_data

        data["data_from_cache"] = self.data_from_cache
        data["querying"] = self.is_querying
        data["restart_ecu"] = self.ecu_restarting
        _LOGGER.debug(f"Returning data: {data}")
        
        if not data.get("ecu_id"):
            raise UpdateFailed("Data doesn't contain a valid ecu_id")
        return data


async def update_listener(hass, config):
    # Handle options update being triggered by config entry options updates.
    _LOGGER.warning(f"Configuration updated: {config.as_dict()}")


async def async_setup_entry(hass, config):
    # Setup APsystems platform
    hass.data.setdefault(DOMAIN, {})
    interval = timedelta(seconds=config.data["scan_interval"])

    ecu = ECUR(config.data["ecu_host"],
               config.data["wifi_ssid"],
               config.data["wifi_password"],
               config.data["show_graphs"]
              )


    async def do_ecu_update():
        # Pass current port_retries value dynamically.
        return await ecu.update(config.data["port_retries"], config.data["show_graphs"])

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=DOMAIN,
        update_method=do_ecu_update,
        update_interval=interval,
    )

    hass.data[DOMAIN] = {
        "ecu": ecu,
        "coordinator": coordinator
    }

    # First refresh the coordinator to make sure data is fetched.
    await coordinator.async_config_entry_first_refresh()

    # Ensure data is updated before getting it
    await coordinator.async_refresh()

    # Register the ECU device.
    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=config.entry_id,
        identifiers={(DOMAIN, f"ecu_{ecu.ecu.ecu_id}")},
        manufacturer="APSystems",
        suggested_area="Roof",
        name=f"ECU {ecu.ecu.ecu_id}",
        model=ecu.ecu.firmware,
        sw_version=ecu.ecu.firmware,
    )

    # Register the inverter devices.
    inverters = coordinator.data.get("inverters", {})
    for uid, inv_data in inverters.items():
        device_registry.async_get_or_create(
            config_entry_id=config.entry_id,
            identifiers={(DOMAIN, f"inverter_{uid}")},
            manufacturer="APSystems",
            suggested_area="Roof",
            name=f"Inverter {uid}",
            model=inv_data.get("model")
        )

    # Forward platform setup requests.
    await hass.config_entries.async_forward_entry_setups(config, PLATFORMS)
    config.async_on_unload(config.add_update_listener(update_listener))
    return True


async def async_remove_config_entry_device(hass, config, device_entry) -> bool:
    # Handle device removal.
    if device_entry:
        # Notify the user that the device has been removed
        create_persistent_notification(
            hass,
            title="Device Removed",
            message=f"The following device was removed: {device_entry.name}"
        )
        return True
    return False

async def async_unload_entry(hass, config):
    unload_ok = await hass.config_entries.async_unload_platforms(config, PLATFORMS)
    ecu = hass.data[DOMAIN].get("ecu")
    ecu.stop_query()
    if unload_ok:
        hass.data[DOMAIN].pop(config.entry_id)
    return unload_ok
