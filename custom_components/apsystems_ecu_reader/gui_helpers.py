"""GUI helper functions for the ECU UI (ECU-R-Pro and ECU-C)."""

import logging
import re
import asyncio
import aiohttp
import json  # Add this import at the top of the file
from homeassistant.components.persistent_notification import create as persistent_notification_create
from datetime import datetime

_LOGGER = logging.getLogger(__name__)

async def set_all_inverters_state(ipaddr, state):
    """Set the on/off state of all inverters. 1=on, 2=off"""
    headers = {'X-Requested-With': 'XMLHttpRequest'}
    url = f"http://{ipaddr}/index.php/configuration/set_switch_all_{'on' if state else 'off'}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, timeout=15) as response:
                status_code = response.status
                _LOGGER.debug(
                    "Response from ECU on switching the inverters %s: %s",
                    'on' if state else 'off',
                    status_code
                )
                return status_code
    except Exception as err:
        _LOGGER.warning(
            "Attempt to switch inverters %s failed with error: %s (This switch is only compatible with ECU-R pro and ECU-C type ECU's)",
            'on' if state else 'off',
            err
        )
        return None

async def set_inverter_state(ipaddr, inverter_id, state):
    """Set the on/off state of an inverter. 1=on, 2=off"""
    action = {"ids[]": f'{inverter_id}1' if state else f'{inverter_id}2'}
    headers = {'X-Requested-With': 'XMLHttpRequest', "Connection": "keep-alive"}
    url = f'http://{ipaddr}/index.php/configuration/set_switch_state'

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, data=action, timeout=15) as response:
                response_text = await response.text()
                _LOGGER.debug(
                    "Response from ECU on switching the inverter %s to state %s: %s",
                    inverter_id, 'on' if state else 'off',
                    re.search(r'"message":"([^"]+)"', response_text).group(1)
                )

    except (aiohttp.ClientError, aiohttp.ClientConnectionError, asyncio.TimeoutError) as err:
        _LOGGER.debug(
            "Attempt to switch inverter %s failed with error: %s\n\t"
            "This switch is only compatible with ECU-ID 2162... series and ECU-C models",
            inverter_id, err
        )

async def set_zero_export(ipaddr, state):
    """Set the bridge state for zero export. 0=closed, 1=open"""
    action = {
        "meter_func": "1" if state else "0",
        "this_func": "1",
        "power_limit": "0"
    }
    headers = {'X-Requested-With': 'XMLHttpRequest', "Connection": "keep-alive"}
    url = f'http://{ipaddr}/index.php/meter/set_meter_display_funcs'

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, data=action, timeout=15) as response:
                response_text = await response.text()
                _LOGGER.debug(
                    "Response from ECU on bridging zero export to state %s: %s",
                    'open' if state else 'close',
                    re.search(r'"message":"([^"]+)"', response_text).group(1)
                )

    except (aiohttp.ClientError, aiohttp.ClientConnectionError, asyncio.TimeoutError) as err:
        _LOGGER.debug(
            "Attempt to bridge zero export failed with error: %s\n\t"
            "This switch is only compatible with ECU-C models", err
        )

async def set_inverter_max_power(ipaddr, inverter_uid, max_panel_power):
    """Set the max power for an inverter."""
    action = {
        "id": inverter_uid,
        "maxpower": max_panel_power
    }
    headers = {'X-Requested-With': 'XMLHttpRequest'}
    url = f'http://{ipaddr}/index.php/configuration/set_maxpower'

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, data=action, timeout=15) as response:
                response_text = await response.text()
                _LOGGER.debug(
                    "Response from ECU on setting panel max power to %s for inverter %s: %s",
                    max_panel_power,
                    inverter_uid,
                    re.search(r'"message":"([^"]+)"', response_text).group(1)
                )
    except (
        aiohttp.ClientError,
        aiohttp.ClientConnectionError,
        asyncio.TimeoutError,
    ) as err:
        _LOGGER.error("Error setting max power for inverter %s: %s", inverter_uid, err)
        return err

async def reboot_ecu(ipaddr, wifi_ssid, wifi_password, cached_data):
    """ Reboot the ECU (compatible with ECU-ID 2162... series and ECU-C models) """
    ecu_id = cached_data.get("ecu_id", None)
    if ecu_id.startswith(("215", "2162")):
        action = {
            'SSID': wifi_ssid,
            'channel': 0,
            'method': 2,
            'psk_wep': '',
            'psk_wpa': wifi_password
        }
        headers = {'X-Requested-With': 'XMLHttpRequest'}
        url = 'http://' + str(ipaddr) + '/index.php/management/set_wlan_ap'

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, data=action) as response:
                    return await response.text()
        except (
            aiohttp.ClientError,
            aiohttp.ClientConnectionError,
            asyncio.TimeoutError,
        ) as err:
            _LOGGER.error("Error rebooting ECU: %s", err)
            return err

async def get_power_meter_graph_data(ipaddr):
    """Fetch data from the meter power graph endpoint."""
    url = f"http://{ipaddr}/index.php/meter/old_meter_power_graph"
    headers = {'X-Requested-With': 'XMLHttpRequest'}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=15) as response:
                if response.status == 200:
                    data = await response.text()
                    try:
                        data = json.loads(data)  # Convert the string to a JSON object
                    except json.JSONDecodeError as err:
                        _LOGGER.warning("Failed to decode JSON response: %s", err)
                        return None

                    _LOGGER.warning("Parsed data: %s", data)

                    # Map the data to sensor properties and add calculated fields
                    mapped_data = {
                        f"{prefix}_ct_{phase.lower()}": data[f"power{index}"][-1][f"power{phase}"]
                        if data[f"power{index}"] else None
                        for index, prefix in enumerate(["grid", "production"], start=1)
                        for phase in ["A", "B", "C"]
                    }

                    mapped_data.update({
                        f"consumed_{phase}": (mapped_data[f"production_ct_{phase}"] or 0) + (mapped_data[f"grid_ct_{phase}"] or 0)
                        for phase in ["a", "b", "c"]
                    })
                    return mapped_data
                else:
                    _LOGGER.error("Failed to fetch meter power graph data. HTTP status: %s", response.status)
                    return None
    except (
        aiohttp.ClientError,
        aiohttp.ClientConnectionError,
        asyncio.TimeoutError,
    ) as err:
        _LOGGER.error("Error fetching meter power graph data: %s", err)
        return None

def pers_gui_notification(hass, message):
    """Create a persistent notification for things that really needs user attention."""
    timestamp = datetime.now().strftime("%b %d %H:%M")
    persistent_notification_create(
        hass,
        f"Message @ {timestamp}: {message}",
        title="APsystems ECU Reader"
    )