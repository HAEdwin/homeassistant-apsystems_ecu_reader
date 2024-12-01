import aiohttp
import logging
import requests
import traceback
from datetime import timedelta
from .ecu_api import APsystemsSocket, APsystemsInvalidData
from homeassistant.helpers import device_registry as dr
from homeassistant.components.persistent_notification import create as create_persistent_notification
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)
PLATFORMS = ["sensor", "binary_sensor", "switch"]


class ECUR:
    def __init__(self, ipaddr, ssid, wpa, cache, graphs):
        self.ecu = APsystemsSocket(ipaddr)
        self.cache_count = 0
        self.data_from_cache = False
        self.querying = True
        self.inverters_online = True
        self.ecu_restarting = False
        self.cached_data = {}


    def set_querying_state(self, state: bool):
        """Set the querying state to either True or False."""
        self.querying = state


    async def set_inverters(self, state: bool):
        headers = {'X-Requested-With': 'XMLHttpRequest'}
        state_str = 'on' if state else 'off'
        url = f'http://{self.ecu.ipaddr}/index.php/configuration/set_switch_all_{state_str}'

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url, headers=headers) as response:
                    self.inverters_online = state
                    _LOGGER.debug(f"Response from ECU on switching the inverters {state_str}: {response.status}")
            except Exception as err:
                _LOGGER.warning(f"Attempt to switch inverters {state_str} failed with error: {err}")



    async def update(self):
        """Fetch data from ECU or use cached data."""
        data = {}

        # If querying is stopped, return cached data
        if not self.querying:
            _LOGGER.debug("Not querying ECU due to query=False")
            data = self.cached_data
            self.data_from_cache = True
            data["data_from_cache"] = self.data_from_cache
            data["querying"] = self.querying
            return self.cached_data

        _LOGGER.debug("Querying ECU...")
        try:
            data = await self.ecu.query_ecu(3)

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
            data = self.cached_data(msg)

        except Exception:
            msg = "General exception error. Using cached data."
            _LOGGER.warning(f"Exception error: {traceback.format_exc()}. Using cached data.")
            data = self.cached_data(msg)

        data["data_from_cache"] = self.data_from_cache
        data["querying"] = self.querying
        data["restart_ecu"] = self.ecu_restarting
        _LOGGER.debug(f"Returning data: {data}")
        
        if not data.get("ecu_id"):
            raise UpdateFailed("Data doesn't contain a valid ecu_id")
        return data

async def update_listener(hass, config):
    # Handle options update being triggered by config entry options updates
    _LOGGER.warning(f"Configuration updated: {config.as_dict()}")
    ecu = ECUR(config.data["ecu_host"],
               config.data["wifi_ssid"],
               config.data["wifi_password"],
               config.data["port_retries"],
               config.data["show_graphs"]
              )


async def async_setup_entry(hass, config):
    # Setup the APsystems platform
    hass.data.setdefault(DOMAIN, {})
    host = config.data["ecu_host"]
    interval = timedelta(seconds=config.data["scan_interval"])

    ecu = ECUR(config.data["ecu_host"],
               config.data["wifi_ssid"],
               config.data["wifi_password"],
               config.data["port_retries"],
               config.data["show_graphs"]
              )

    async def do_ecu_update():
        # Directly await ecu.update() since it's asynchronous
        return await ecu.update()

    coordinator = DataUpdateCoordinator(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_method=do_ecu_update,
            update_interval=interval,
    )

    hass.data[DOMAIN] = {
        "ecu" : ecu,
        "coordinator" : coordinator
    }

    # First refresh the coordinator to make sure data is fetched
    await coordinator.async_config_entry_first_refresh()

    # Ensure that data is updated before getting it
    await coordinator.async_refresh()

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

    await hass.config_entries.async_forward_entry_setups(config, PLATFORMS)
    config.async_on_unload(config.add_update_listener(update_listener))
    return True


async def async_remove_config_entry_device(hass, config, device_entry) -> bool:
    if device_entry is not None:
        # Notify the user that the device has been removed
        create_persistent_notification(
            hass,
            title="Important notification",
            message=f"The following device was removed from the system: {device_entry.name}"
        )
        return True
    else:
        return False

async def async_unload_entry(hass, config):
    unload_ok = await hass.config_entries.async_unload_platforms(config, PLATFORMS)
    ecu = hass.data[DOMAIN].get("ecu")
    ecu.stop_query()
    if unload_ok:
        hass.data[DOMAIN].pop(config.entry_id)
    return unload_ok
