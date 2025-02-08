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

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor", "binary_sensor", "switch"]


class ECUREADER:
    """ECU Reader"""
    def __init__(self, ipaddr, show_graphs, config_entry):
        self.ipaddr = ipaddr
        self.show_graphs = show_graphs
        self._cache_reboot_limit = config_entry.data.get("cache_reboot", 4)
        self.ecu = APsystemsSocket(ipaddr, self.show_graphs)
        self.data_from_cache = False
        self.data_from_cache_count = 0
        self.cached_data = {}

        # Register callback for options update
        config_entry.add_update_listener(self.async_options_updated)


    async def async_options_updated(self, _, config_entry):
        """Handle options update."""
        _LOGGER.warning("Options updated: %s", config_entry.data)
        self._cache_reboot_limit = config_entry.data.get("cache_reboot", 4)

    # called from switch.py
    def set_inverter_state(self, inverter_id, state):
        """Set the on/off state of an inverter. 1=on, 2=off"""
        action = {"ids[]": f'{inverter_id}1' if state else f'{inverter_id}2'}
        headers = {'X-Requested-With': 'XMLHttpRequest', "Connection": "keep-alive"}
        url = f'http://{self.ipaddr}/index.php/configuration/set_switch_state'

        try:
            response = requests.post(url, headers=headers, data=action, timeout=15)
            _LOGGER.warning(
                "Response from ECU on switching the inverter %s to state %s: %s",
                inverter_id, 'on' if state else 'off',
                re.search(r'"message":"([^"]+)"', response.text).group(1)
            )

        except (requests.ConnectionError, requests.Timeout, requests.HTTPError) as err:
            _LOGGER.warning(
                "Attempt to switch inverter %s failed with error: %s\n\t"
                "This switch is only compatible with ECU-ID 2162... series and ECU-C models",
                state, err
            )

    async def reboot_ecu(self):
        """ Reboot the ECU (compatible with ECU-ID 2162... series and ECU-C models) """
        action = {"command" : "reboot"}
        headers = {'X-Requested-With': 'XMLHttpRequest', "Connection": "keep-alive"}
        url = f'http://{self.ipaddr}/index.php/hidden/exec_command'

        try:
            async with (
                aiohttp.ClientSession() as session,
                async_timeout.timeout(15),
                session.post(url, headers=headers, data=action) as response
            ):
                response_text = await response.text()
                if (match := re.search(r'"value":(\d+)', response_text)):
                    return "Ok" if match.group(1) == "0" else "Error"
                return "Error regex don't match"
        except (
            aiohttp.ClientError,
            aiohttp.ClientConnectionError,
            asyncio.TimeoutError,
        ) as err:
            return f"Attempt to reboot the ECU failed with error: {err}"


    async def update(self, port_retries, show_graphs):
        """ Fetch ECU data or use cached data if querying failed. """

        self.data_from_cache = True
        self.data_from_cache_count += 1

        # Reboot the ECU when the cache counter reaches the cache limit
        # This is a workaround for the ECU not responding to queries after a while
        if self.data_from_cache_count > self._cache_reboot_limit:
            self.data_from_cache_count = 0
            response = await self.reboot_ecu()
            _LOGGER.warning("Response from ECU on reboot: %s", response)
        else:
            try:
                # Fetch the latest port_retries value dynamically.
                data = await self.ecu.query_ecu(port_retries, show_graphs)
                if data.get("ecu_id"):
                    self.cached_data = data
                    self.data_from_cache = False
                    self.data_from_cache_count = 0
            except APsystemsInvalidData as err:
                _LOGGER.warning("Update failure caused by %s", err)

        # Set cache sensors
        self.cached_data["data_from_cache"] = self.data_from_cache
        self.cached_data["data_from_cache_count"] = self.data_from_cache_count

        _LOGGER.debug("Returning data: %s", self.cached_data)
        return self.cached_data


async def update_listener(_, config):
    """ Handle options update being triggered by config entry options updates """
    _LOGGER.debug("Configuration updated: %s",config.as_dict())


async def async_setup_entry(hass, config):
    """ Setup APsystems platform """
    hass.data.setdefault(DOMAIN, {})
    interval = timedelta(seconds=config.data["scan_interval"])
    ecu = ECUREADER(
        config.data["ecu_host"],
        config.data["show_graphs"],
        config  # Pass the config_entry to ECUREADER
    )

    async def do_ecu_update():
        """ Pass current port_retries value dynamically. """
        return await ecu.update(
            config.data["port_retries"],
            config.data["show_graphs"]
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
            "Not able to establish a connection with the ECU @ %s. "
            "Check the ECU status and/or IP-Address.",
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
