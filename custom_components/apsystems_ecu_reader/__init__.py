"""__init__.py"""

import asyncio
import logging
from datetime import timedelta

from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    DOMAIN,
    ECU_MODEL_MAP,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_PORT_RETRIES,
    SETUP_DELAY_SECONDS,
    DEFAULT_CACHE_REBOOT,
)
from .ecu_api import APsystemsSocket, APsystemsInvalidData
from .gui_helpers import (
    set_inverter_state,
    set_zero_export,
    reboot_ecu,
    set_inverter_max_power,
    pers_gui_notification,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor", "binary_sensor", "switch", "number", "button"]


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


async def update_listener(hass, config):
    """Handle options update, triggered by config entry options updates"""
    _LOGGER.debug("Configuration updated: %s", config.as_dict())
    config_dict = config.as_dict()
    # Update the scan interval
    new_interval = timedelta(seconds=config_dict["data"]["scan_interval"])
    coordinator = hass.data[DOMAIN][config.entry_id]["coordinator"]
    coordinator.update_interval = new_interval
    await coordinator.async_refresh()


async def async_setup_entry(hass, config):
    """Setup APsystems platform"""
    hass.data.setdefault(DOMAIN, {})

    # delay the setup after the first and every following ECU hub
    if len(hass.data[DOMAIN]) > 1:
        await asyncio.sleep(SETUP_DELAY_SECONDS)

    interval = timedelta(
        seconds=config.data.get("scan_interval", DEFAULT_SCAN_INTERVAL)
    )
    ecu = ECUREADER(
        config.data["ecu_host"],
        config.data.get("wifi_ssid", "ECU-local"),
        config.data.get("wifi_password", "default"),
        config.data.get("show_graphs", True),
    )

    async def do_ecu_update():
        """Pass current port_retries value dynamically."""
        return await ecu.update(
            config.data.get("port_retries", DEFAULT_PORT_RETRIES),
            config.data.get("cache_reboot", DEFAULT_CACHE_REBOOT),
            config.data.get("show_graphs", True),
        )

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=DOMAIN,
        update_method=do_ecu_update,
        update_interval=interval,
    )

    hass.data[DOMAIN][config.entry_id] = {"ecu": ecu, "coordinator": coordinator}

    # First refresh the coordinator to make sure data is fetched.
    await coordinator.async_config_entry_first_refresh()

    # Ensure data is updated before getting it
    await coordinator.async_refresh()

    # When first install was ok, an ECU ID should be present when HA restarts.
    # If not, the user should be notified and devices should not be created.
    if not ecu.ecu.ecu_id:
        _LOGGER.error(
            "Unable to connect with ECU @ %s. Check IP-Address or wait "
            "10 minutes because the ECU might be recovering from reboot.",
            config.data["ecu_host"],
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
        model=ECU_MODEL_MAP.get(ecu.ecu.ecu_id[:4], "Unknown Model"),
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
            model=inv_data.get("model"),
        )

    # Forward all platforms at once
    await hass.config_entries.async_forward_entry_setups(config, PLATFORMS)

    config.async_on_unload(config.add_update_listener(update_listener))
    return True


async def async_remove_config_entry_device(hass, _, device_entry) -> bool:
    """Handle device removal"""
    if not device_entry:
        return False
    # Notify user that the device will be removed - HA core handles the rest
    pers_gui_notification(hass, f"Device {device_entry.name} removed")
    return True


async def async_unload_entry(hass, config_entry) -> bool:
    """Unload APsystems platforms"""
    unload_state = await hass.config_entries.async_unload_platforms(
        config_entry, PLATFORMS
    )
    if unload_state:
        hass.data[DOMAIN].pop(config_entry.entry_id)
    else:
        _LOGGER.error(
            "Failed to unload platforms for config entry %s", config_entry.entry_id
        )
    return unload_state


async def async_reload_entry(hass, config_entry):
    """Handle reload of a config entry."""
    await async_unload_entry(hass, config_entry)
    await async_setup_entry(hass, config_entry)
