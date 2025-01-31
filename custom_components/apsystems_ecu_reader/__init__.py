""" __init__.py """


# Standard library imports
import traceback
import logging
import re
from datetime import timedelta
import asyncio

# Third-party imports
import requests
from homeassistant.helpers import device_registry as dr
from homeassistant.components.persistent_notification import (
    create as create_persistent_notification
)
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from .ecu_api import APsystemsSocket, APsystemsInvalidData
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor", "binary_sensor", "switch"]


class ECUREADER:
    """ Class to handle the ECU data and actions. """
    def __init__(self, ipaddr, show_graphs):
        self.ipaddr = ipaddr
        self.show_graphs = show_graphs
        self.ecu = APsystemsSocket(ipaddr, self.show_graphs)
        self.data_from_cache = False
        self.cached_data = {}


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


    async def update(self, port_retries, show_graphs):
        """ Fetch ECU data or use cached data if querying failed. """
        self.data_from_cache = True
        try:
            # Fetch the latest port_retries value dynamically.
            data = await self.ecu.query_ecu(port_retries, show_graphs)
            if data.get("ecu_id"):
                self.cached_data = data
                self.data_from_cache = False # Set cache sensor
        except APsystemsInvalidData as err:
            _LOGGER.warning("Update failure caused by %s", err)

        self.cached_data["data_from_cache"] = self.data_from_cache # Set cache sensor
        _LOGGER.debug("Returning data: %s", self.cached_data)
        return self.cached_data


async def update_listener(_, config):
    """ Handle options update being triggered by config entry options updates """
    _LOGGER.warning("Configuration updated: %s",config.as_dict())


async def async_setup_entry(hass, config):
    """ Setup APsystems platform """
    hass.data.setdefault(DOMAIN, {})
    interval = timedelta(seconds=config.data["scan_interval"])

    ecu = ECUREADER(config.data["ecu_host"], config.data["show_graphs"])

    async def do_ecu_update():
        """ Pass current port_retries value dynamically. """
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
