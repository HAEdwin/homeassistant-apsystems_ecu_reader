"""Coordinator and ECU data wrapper for the APsystems ECU Reader integration."""

import logging
from dataclasses import dataclass
from datetime import timedelta

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    DOMAIN,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_PORT_RETRIES,
    DEFAULT_CACHE_REBOOT,
)
from .ecu_client import APsystemsSocket, APsystemsInvalidData
from .gui_helpers import (
    set_inverter_state,
    set_zero_export,
    reboot_ecu,
    set_inverter_max_power,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class APsystemsData:
    """Runtime data stored on the config entry (ConfigEntry.runtime_data)."""

    ecu: "ECUREADER"
    coordinator: DataUpdateCoordinator


def get_entry_value(config_entry, key, default=None):
    """Return a config entry value, preferring options over data.

    Options are written by the options flow after setup. Data holds the
    values from the initial setup. Falling back to data keeps existing
    config entries (which only have data) working unchanged.
    """
    return config_entry.options.get(key, config_entry.data.get(key, default))


class ECUREADER:
    """ECU Reader"""

    def __init__(
        self, ipaddr: str, wifi_ssid: str, wifi_password: str, show_graphs: bool
    ) -> None:

        self.ipaddr = ipaddr
        self.wifi_ssid = wifi_ssid
        self.wifi_password = wifi_password
        self.show_graphs = show_graphs
        self.ecu = APsystemsSocket(ipaddr)
        self.data_from_cache = False
        self.data_from_cache_count = 0
        self.cached_data = {}
        self.query_enabled = True

    # called from number.py
    async def set_inverter_max_power(self, inverter_uid, max_panel_power):
        """Set the max power for an inverter."""
        return await set_inverter_max_power(self.ipaddr, inverter_uid, max_panel_power)

    # called from switch.py
    async def set_inverter_state(self, inverter_id, state) -> bool:
        """Set the on/off state of an inverter. 1=on, 2=off"""
        return await set_inverter_state(self.ipaddr, inverter_id, state)

    async def set_zero_export(self, state, power_limit):
        """Set the bridge state for zero export. 0=closed, 1=open"""
        return await set_zero_export(self.ipaddr, state, power_limit)

    # called from number.py
    async def set_power_limit(self, power_limit):
        """Set the power limit for zero export"""
        return await set_zero_export(self.ipaddr, 1, power_limit)

    # called from button.py
    async def reboot_ecu(self):
        """Reboot the ECU (ECU-ID 2162... and ECU-C compatible)"""
        return await reboot_ecu(
            self.ipaddr, self.wifi_ssid, self.wifi_password, self.cached_data
        )

    async def update(self, port_retries, cache_reboot, show_graphs):
        """Fetch ECU data or use cached data if querying failed."""
        # If querying is disabled, return cached data
        if not self.query_enabled:
            self.data_from_cache = True
            self.cached_data["data_from_cache"] = self.data_from_cache
            self.cached_data["data_from_cache_count"] = self.data_from_cache_count
            _LOGGER.debug("ECU querying disabled, returning cached data")
            return self.cached_data

        self.data_from_cache = True
        self.data_from_cache_count += 1

        # Reboot the ECU when the cache counter reaches the cache limit
        # This is a workaround for the ECU not responding to queries
        if self.data_from_cache_count >= cache_reboot and self.ecu.ecu_id.startswith(
            ("215", "2162")
        ):
            _LOGGER.warning(
                "Restarting ECU %s after %s failed attempts to fetch data",
                self.ecu.ecu_id,
                self.data_from_cache_count,
            )
            self.data_from_cache_count = 0
            response = await self.reboot_ecu()
            _LOGGER.debug(
                "Response from ECU %s on reboot: %s", self.ecu.ecu_id, response
            )
        else:
            try:
                data = await self.ecu.get_update(port_retries, show_graphs)
                if data.get("ecu_id"):
                    self.cached_data = data
                    self.data_from_cache = False
                    self.data_from_cache_count = 0
            # collector of APsystemsInvalidData exceptions
            except APsystemsInvalidData as err:
                _LOGGER.warning(
                    "Using cached data for ECU %s: %s", self.ecu.ecu_id, err
                )

        # Set cache sensors
        self.cached_data["data_from_cache"] = self.data_from_cache
        self.cached_data["data_from_cache_count"] = self.data_from_cache_count

        _LOGGER.debug("ECU %s returned data: %s", self.ipaddr, self.cached_data)
        return self.cached_data


def build_coordinator(hass, config_entry, ecu: ECUREADER) -> DataUpdateCoordinator:
    """Create the DataUpdateCoordinator that polls the given ECU."""
    interval = timedelta(
        seconds=get_entry_value(config_entry, "scan_interval", DEFAULT_SCAN_INTERVAL)
    )

    async def do_ecu_update():
        """Pass current port_retries value dynamically."""
        return await ecu.update(
            get_entry_value(config_entry, "port_retries", DEFAULT_PORT_RETRIES),
            get_entry_value(config_entry, "cache_reboot", DEFAULT_CACHE_REBOOT),
            get_entry_value(config_entry, "show_graphs", True),
        )

    return DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=DOMAIN,
        update_method=do_ecu_update,
        update_interval=interval,
    )
