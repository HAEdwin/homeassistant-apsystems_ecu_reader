"""GUI helper functions for the ECU UI (ECU-R-Pro and ECU-C)."""

import logging
import re
from datetime import datetime

import asyncio
import json
import aiohttp

from homeassistant.components.persistent_notification import (
    create as persistent_notification_create,
)

_LOGGER = logging.getLogger(__name__)


async def set_inverter_state(ipaddr, inverter_id, state) -> bool:
    """Set the on/off state of an inverter. 1=on, 2=off"""
    action = {"ids[]": f"{inverter_id}1" if state else f"{inverter_id}2"}
    headers = {"X-Requested-With": "XMLHttpRequest", "Connection": "keep-alive"}
    url = f"http://{ipaddr}/index.php/configuration/set_switch_state"

    max_retries = 3
    for attempt in range(max_retries):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url, headers=headers, data=action, timeout=15
                ) as response:
                    response_text = await response.text()
                    message_match = re.search(r'"message":"([^"]+)"', response_text)
                    message = message_match.group(1) if message_match else ""
                    _LOGGER.debug(
                        "Response from ECU on switching the inverter %s to state %s: %s",
                        inverter_id,
                        "on" if state else "off",
                        message,
                    )
                    if message == "See the results 5 minutes later !":
                        return True

                    _LOGGER.debug(
                        "Retrying inverter state change for %s (attempt %d/%d)",
                        inverter_id,
                        attempt + 1,
                        max_retries,
                    )
                    await asyncio.sleep(2)
        except (
            aiohttp.ClientError,
            aiohttp.ClientConnectionError,
            asyncio.TimeoutError,
        ) as err:
            _LOGGER.debug(
                "Attempt to switch inverter %s failed with error: %s\n\t"
                "This switch is only compatible with ECU-ID 2162... series and ECU-C models",
                inverter_id,
                err,
            )
    return False


async def set_zero_export(ipaddr, state):
    """Set the bridge state for zero export. 0=closed, 1=open"""
    action = {"meter_func": "1" if state else "0", "this_func": "1", "power_limit": "0"}
    headers = {"X-Requested-With": "XMLHttpRequest", "Connection": "keep-alive"}
    url = f"http://{ipaddr}/index.php/meter/set_meter_display_funcs"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url, headers=headers, data=action, timeout=15
            ) as response:
                response_text = await response.text()
                _LOGGER.debug(
                    "Response from ECU on bridging zero export to state %s: %s",
                    "open" if state else "close",
                    re.search(r'"message":"([^"]+)"', response_text).group(1),
                )

    except (
        aiohttp.ClientError,
        aiohttp.ClientConnectionError,
        asyncio.TimeoutError,
    ) as err:
        _LOGGER.debug(
            "Attempt to bridge zero export failed with error: %s\n\t"
            "This switch is only compatible with ECU-C models",
            err,
        )


async def set_inverter_max_power(ipaddr, inverter_uid, max_panel_power):
    """Set the max power for an inverter."""
    action = {"id": inverter_uid, "maxpower": max_panel_power}
    headers = {"X-Requested-With": "XMLHttpRequest"}
    url = f"http://{ipaddr}/index.php/configuration/set_maxpower"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url, headers=headers, data=action, timeout=15
            ) as response:
                response_text = await response.text()
                _LOGGER.debug(
                    "Response from ECU on setting panel max power to %s for inverter %s: %s",
                    max_panel_power,
                    inverter_uid,
                    re.search(r'"message":"([^"]+)"', response_text).group(1),
                )
    except (
        aiohttp.ClientError,
        aiohttp.ClientConnectionError,
        asyncio.TimeoutError,
    ) as err:
        _LOGGER.error("Error setting max power for inverter %s: %s", inverter_uid, err)
        return err


async def reboot_ecu(ipaddr, wifi_ssid, wifi_password, cached_data):
    """Reboot the ECU (compatible with ECU-ID 2162... series and ECU-C models)"""
    ecu_id = cached_data.get("ecu_id", None)
    action = {
        "SSID": wifi_ssid,
        "channel": 0,
        "method": 2,
        "psk_wep": "",
        "psk_wpa": wifi_password,
    }
    headers = {"X-Requested-With": "XMLHttpRequest"}
    url = "http://" + str(ipaddr) + "/index.php/management/set_wlan_ap"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, data=action) as response:
                return await response.text()
    except (
        aiohttp.ClientError,
        aiohttp.ClientConnectionError,
        asyncio.TimeoutError,
    ) as err:
        _LOGGER.error("Error rebooting ECU %s: %s", ecu_id, err)
        return err


async def get_power_meter_graph_data(ipaddr):
    """Fetch data from the meter power graph endpoint."""
    url = f"http://{ipaddr}/index.php/meter/old_meter_power_graph"
    headers = {"X-Requested-With": "XMLHttpRequest"}

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

                    _LOGGER.debug("Parsed data: %s", data)

                    # Map the data to sensor properties and add calculated fields
                    mapped_data = {
                        f"{prefix}_ct_{phase.lower()}": (
                            data[f"power{index}"][-1][f"power{phase}"]
                            if data[f"power{index}"]
                            else None
                        )
                        for index, prefix in enumerate(["production", "grid"], start=1)
                        for phase in ["A", "B", "C"]
                    }

                    mapped_data.update(
                        {
                            f"consumed_{phase}": (
                                (mapped_data[f"production_ct_{phase}"] or 0)
                                + (mapped_data[f"grid_ct_{phase}"] or 0)
                            )
                            for phase in ["a", "b", "c"]
                        }
                    )
                    return mapped_data
                else:
                    _LOGGER.error(
                        "Failed fetching graph data. HTTP status: %s", response.status
                    )
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
        hass, f"Message @ {timestamp}: {message}", title="APsystems ECU Reader"
    )
