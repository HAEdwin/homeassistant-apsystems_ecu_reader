import logging
import requests

import voluptuous as vol
import traceback
import datetime as dt
from datetime import timedelta

from .APSystemsSocket import APSystemsSocket, APSystemsInvalidData
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.discovery import load_platform
from homeassistant.helpers.entity import Entity
from homeassistant import config_entries, exceptions
from homeassistant.helpers import device_registry as dr
from homeassistant.components.persistent_notification import (
    create as create_persistent_notification
    )
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
    )
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)
PLATFORMS = [ "sensor", "binary_sensor", "switch" ]

class WiFiSet():
    ipaddr = ""
    ssid = ""
    wpa = ""
    cache = 3
WiFiSet = WiFiSet()

# handle all the communications with the ECUR class and deal with our need for caching, etc
class ECUR():
    def __init__(self, ipaddr, ssid, wpa, cache, graphs):
        self.ecu = APSystemsSocket(ipaddr, graphs)
        self.cache_count = 0
        self.data_from_cache = False
        self.querying = True
        self.inverters_online = True
        self.ecu_restarting = False
        self.cached_data = {}
        WiFiSet.ipaddr = ipaddr
        WiFiSet.ssid = ssid
        WiFiSet.wpa = wpa
        WiFiSet.cache = cache

    def stop_query(self):
        self.querying = False

    def start_query(self):
        self.querying = True
        
    def inverters_off(self):
        headers = {'X-Requested-With': 'XMLHttpRequest'}
        url = 'http://'+ str(WiFiSet.ipaddr) + '/index.php/configuration/set_switch_all_off'
        try:
            get_url = requests.post(url, headers=headers)
            self.inverters_online = False
            _LOGGER.debug(f"Response from ECU on switching the inverters off: {str(get_url.status_code)}")
        except Exception as err:
            _LOGGER.warning(f"Attempt to switch inverters off failed with error: {err} (This switch is only compatible with ECU-R pro and ECU-C type ECU's)")

    def inverters_on(self):
        headers = {'X-Requested-With': 'XMLHttpRequest'}
        url = 'http://'+ str(WiFiSet.ipaddr) + '/index.php/configuration/set_switch_all_on'
        try:
            get_url = requests.post(url, headers=headers)
            self.inverters_online = True
            _LOGGER.debug(f"Response from ECU on switching the inverters on: {str(get_url.status_code)}")
        except Exception as err:
            _LOGGER.warning(f"Attempt to switch inverters on failed with error: {err} (This switch is only compatible with ECU-R pro and ECU-C type ECU's)")

    def use_cached_data(self, msg):
        # we got invalid data, so we need to pull from cache
        self.error_msg = msg
        self.cache_count += 1
        self.data_from_cache = True

        if self.cache_count == WiFiSet.cache:
            _LOGGER.warning(f"Communication with the ECU failed after {WiFiSet.cache} repeated attempts.")
            data = {'SSID': WiFiSet.ssid, 'channel': 0, 'method': 2, 'psk_wep': '', 'psk_wpa': WiFiSet.wpa}
            _LOGGER.debug(f"Data sent with URL: {data}")
            # Determine ECU type to decide ECU restart (for ECU-C and ECU-R with sunspec only)
            if (self.cached_data.get("ecu_id", None)[0:3] == "215") or (self.cached_data.get("ecu_id", None)[0:4] == "2162"):
                url = 'http://' + str(WiFiSet.ipaddr) + '/index.php/management/set_wlan_ap'
                headers = {'X-Requested-With': 'XMLHttpRequest'}
                try:
                    get_url = requests.post(url, headers=headers, data=data)
                    _LOGGER.debug(f"Response from ECU on restart: {str(get_url.status_code)}")
                    self.ecu_restarting = True
                except Exception as err:
                    _LOGGER.warning(f"Attempt to restart ECU failed with error: {err}. Querying is stopped automatically.")
                    self.querying = False
            else:
                # Older ECU-R models starting with 2160
                _LOGGER.warning("Try manually power cycling the ECU. Querying is stopped automatically, turn switch back on after restart of ECU.")
                self.querying = False
            
        if self.cached_data.get("ecu_id", None) == None:
            _LOGGER.debug(f"Cached data {self.cached_data}")
            raise UpdateFailed(f"Unable to get correct data from ECU, and no cached data. See log for details, and try power cycling the ECU.")
        return self.cached_data

    def update(self):
        data = {}
        # if we aren't actively quering data, pull data form the cache
        # this is so we can stop querying after sunset
        if not self.querying:
            _LOGGER.debug("Not querying ECU due to query=False")
            data = self.cached_data
            self.data_from_cache = True
            data["data_from_cache"] = self.data_from_cache
            data["querying"] = self.querying
            return self.cached_data

        _LOGGER.debug("Querying ECU...")
        try:
            data = self.ecu.query_ecu()
            _LOGGER.debug("Got data from ECU")

            # we got good results, so we store it and set flags about our cache state
            if data["ecu_id"] != None:
                self.cached_data = data
                self.cache_count = 0
                self.data_from_cache = False
                self.ecu_restarting = False
                self.error_message = ""
            else:
                msg = f"Using cached data from last successful communication from ECU. Error: no ecu_id returned"
                _LOGGER.warning(msg)
                data = self.use_cached_data(msg)

        except APSystemsInvalidData as err:
            msg = f"Using cached data from last successful communication from ECU. Invalid data error: {err}"
            if str(err) != 'timed out':
                _LOGGER.warning(msg)
            data = self.use_cached_data(msg)

        except Exception:
            msg = ""
            _LOGGER.warning("Using cached data from last successful communication from ECU. Exception error: %s", traceback.format_exc())
            data = self.use_cached_data(msg)

        data["data_from_cache"] = self.data_from_cache
        data["querying"] = self.querying
        data["restart_ecu"] = self.ecu_restarting
        _LOGGER.debug(f"Returning {data}")
        if data.get("ecu_id", None) == None:
            raise UpdateFailed(f"Somehow data doesn't contain a valid ecu_id")
        return data

async def update_listener(hass, config):
    # Handle options update being triggered by config entry options updates
    _LOGGER.debug(f"Configuration updated: {config.as_dict()}")
    ecu = ECUR(config.data["host"],
               config.data["SSID"],
               config.data["WPA-PSK"],
               config.data["CACHE"],
               config.data["stop_graphs"]
              )

async def async_setup_entry(hass, config):
    # Setup the APsystems platform """
    hass.data.setdefault(DOMAIN, {})
    host = config.data["host"]
    interval = timedelta(seconds=config.data["scan_interval"])
    # Defaults for new parameters that might not have been set yet from previous integration versions
    cache = config.data.get("CACHE", 5)
    ssid = config.data.get("SSID", "ECU-WiFi_SSID")
    wpa = config.data.get("WPA-PSK", "myWiFipassword")
    graphs = config.options.get("stop_graphs", False)
    ecu = ECUR(host, ssid, wpa, cache, graphs)
    

    async def do_ecu_update():
        return await hass.async_add_executor_job(ecu.update)

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
    await coordinator.async_config_entry_first_refresh()

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
    for uid,inv_data in inverters.items():
        model = inv_data.get("model", "Inverter")
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
            message=f"The following device was removed from the system: {device_entry}"
        )
        return True
    else:
        return False

async def async_unload_entry(hass, config):
    unload_ok = await hass.config_entries.async_unload_platforms(config, PLATFORMS)
    coordinator = hass.data[DOMAIN].get("coordinator")
    ecu = hass.data[DOMAIN].get("ecu")
    ecu.stop_query()
    if unload_ok:
        hass.data[DOMAIN].pop(config.entry_id)
    return unload_ok
