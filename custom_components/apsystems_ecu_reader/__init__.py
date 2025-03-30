""" __init__.py """

import asyncio
import logging
import re
import traceback
from datetime import timedelta

import aiohttp
import async_timeout
import requests

from homeassistant.components.persistent_notification import (
    create as create_persistent_notification
)
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import DOMAIN
from .ecu_api import APsystemsSocket, APsystemsInvalidData
from .gui_helpers import (
    set_inverter_state,
    set_all_inverters_state,
    set_zero_export,
    reboot_ecu,
    set_inverter_max_power,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor", "binary_sensor", "switch", "number", "button"]

class ECUREADER:
    """ECU Reader"""
    def __init__(self, ipaddr, wifi_ssid, wifi_password, show_graphs):
        self.ipaddr = ipaddr
        self.wifi_ssid = wifi_ssid
        self.wifi_password = wifi_password
        self.show_graphs = show_graphs
        self.ecu = APsystemsSocket(ipaddr, self.show_graphs)
        self.data_from_cache = False
        self.data_from_cache_count = 0
        self.cached_data = {}

    # called from number.py
    async def set_inverter_max_power(self, inverter_uid, max_panel_power):
        """Set the max power for an inverter."""
        return await set_inverter_max_power(self.ipaddr, inverter_uid, max_panel_power)

    # called from switch.py
    async def set_inverter_state(self, inverter_id, state):
        """Set the on/off state of an inverter. 1=on, 2=off"""
        await set_inverter_state(self.ipaddr, inverter_id, state)
    
    async def set_all_inverters_state(self, state):
        """Set the on/off state of an inverter. 1=on, 2=off"""
        await set_all_inverters_state(self.ipaddr, state)

    async def set_zero_export(self, state):
        """Set the bridge state for zero export. 0=closed, 1=open"""
        await set_zero_export(self.ipaddr, state)

    async def reboot_ecu(self):
        """ Reboot the ECU (compatible with ECU-ID 2162... series and ECU-C models) """
        return await reboot_ecu(self.ipaddr, self.wifi_ssid, self.wifi_password, self.cached_data)

    async def update(self, port_retries, cache_reboot, show_graphs):
        """ Fetch ECU data or use cached data if querying failed. """
        self.data_from_cache = True
        self.data_from_cache_count += 1

        # Reboot the ECU when the cache counter reaches the cache limit
        # This is a workaround for the ECU not responding to queries after a while
        if self.data_from_cache_count >= cache_reboot:
            _LOGGER.warning(
                "Restarting ECU after %s failed attempts to fetch data",
                self.data_from_cache_count
            )
            self.data_from_cache_count = 0
            response = await self.reboot_ecu()
            _LOGGER.debug("Response from ECU on reboot: %s", response)
        else:
            try:
                data = await self.ecu.query_ecu(port_retries, show_graphs)
                if data.get("ecu_id"):
                    self.cached_data = data
                    self.data_from_cache = False
                    self.data_from_cache_count = 0
            except APsystemsInvalidData as err:
                _LOGGER.warning("Update failure during %s", err)

        # Set cache sensors
        self.cached_data["data_from_cache"] = self.data_from_cache
        self.cached_data["data_from_cache_count"] = self.data_from_cache_count

        _LOGGER.debug("Returning data: %s", self.cached_data)
        return self.cached_data

async def update_listener(hass, config):
    """ Handle options update being triggered by config entry options updates """
    _LOGGER.debug("Configuration updated: %s", config.as_dict())
    config_dict = config.as_dict()
    # Update the scan interval
    new_interval = timedelta(seconds=config_dict["data"]["scan_interval"])
    coordinator = hass.data[DOMAIN]["coordinator"]
    coordinator.update_interval = new_interval
    await coordinator.async_refresh()


async def async_setup_entry(hass, config):
    """ Setup APsystems platform """
    hass.data.setdefault(DOMAIN, {})
    interval = timedelta(seconds=config.data.get("scan_interval", 300))
    ecu = ECUREADER(
        config.data["ecu_host"],
        config.data.get("wifi_ssid", "ECU-local"),
        config.data.get("wifi_password", "default"),
        config.data.get("show_graphs", True)
    )

    async def do_ecu_update():
        """ Pass current port_retries value dynamically. """
        return await ecu.update(
            config.data.get("port_retries", 2),
            config.data.get("cache_reboot", 3),
            config.data.get("show_graphs", True)
        )


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

    # When first install was successful, an ECU ID should be available when HA restarts.
    # If not, the user should be notified and devices should not be created.
    if not ecu.ecu.ecu_id:
        _LOGGER.error(
           "Unable to connect with ECU @ %s. Check IP-Address or wait "
            "10 minutes because the ECU might be recovering from reboot.",
            config.data["ecu_host"]
        )
        return False

    # Register the ECU device.
    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=config.entry_id,
        identifiers={(DOMAIN, f"ecu_{ecu.ecu.ecu_id}")},
        manufacturer="APsystems",
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
            manufacturer="APsystems",
            suggested_area="Roof",
            name=f"Inverter {uid}",
            model=inv_data.get("model")
        )

    # Forward platform setup requests.
    await hass.config_entries.async_forward_entry_setups(config, PLATFORMS)
    config.async_on_unload(config.add_update_listener(update_listener))
    return True


async def async_remove_config_entry_device(hass, _, device_entry) -> bool:
    """ Handle device removal """	
    if device_entry:
        # Notify the user that the device has been removed
        create_persistent_notification(
            hass,
            title="Device Removed",
            message=f"The following device was removed: {device_entry.name}"
        )
        return True
    return False

async def async_unload_config_entry(hass, config):
    """ Unload APsystems platform """
    ecu = hass.data[DOMAIN].get("ecu")
    unload_ok, _ = await asyncio.gather(
        hass.config_entries.async_unload_platforms(config, PLATFORMS),
        ecu.set_querying_state(False)
    )
    if unload_ok:
        hass.data[DOMAIN].pop(config.entry_id)
    return unload_ok
