"""GUI helper functions for the ECU UI (ECU-R-Pro and ECU-C)."""

import logging
import re
import asyncio
import aiohttp

_LOGGER = logging.getLogger(__name__)

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
