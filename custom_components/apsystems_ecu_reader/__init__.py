"""__init__.py"""

import asyncio
import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntryState
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr

from .const import DOMAIN, ECU_MODEL_MAP, SETUP_DELAY_SECONDS
from .coordinator import APsystemsData, ECUREADER, build_coordinator, get_entry_value
from .gui_helpers import pers_gui_notification

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor", "binary_sensor", "switch", "number", "button"]


async def update_listener(hass, config):
    """Handle options update, triggered by config entry options updates"""
    _LOGGER.debug("Configuration updated: %s", config.as_dict())
    # Update the scan interval
    new_interval = timedelta(seconds=get_entry_value(config, "scan_interval"))
    coordinator = config.runtime_data.coordinator
    coordinator.update_interval = new_interval
    await coordinator.async_refresh()


async def async_setup_entry(hass, config):
    """Setup APsystems platform"""
    # delay the setup after the first and every following ECU hub
    other_entries = [
        entry
        for entry in hass.config_entries.async_entries(DOMAIN)
        if entry.entry_id != config.entry_id and entry.state is ConfigEntryState.LOADED
    ]
    if len(other_entries) > 1:
        await asyncio.sleep(SETUP_DELAY_SECONDS)

    ecu = ECUREADER(
        get_entry_value(config, "ecu_host"),
        get_entry_value(config, "wifi_ssid", "ECU-local"),
        get_entry_value(config, "wifi_password", "default"),
        get_entry_value(config, "show_graphs", True),
    )

    coordinator = build_coordinator(hass, config, ecu)

    config.runtime_data = APsystemsData(ecu=ecu, coordinator=coordinator)

    # First refresh the coordinator to make sure data is fetched.
    await coordinator.async_config_entry_first_refresh()

    # Ensure data is updated before getting it
    await coordinator.async_refresh()

    # When first install was ok, an ECU ID should be present when HA restarts.
    # If not, raise ConfigEntryNotReady so Home Assistant retries the setup
    # automatically instead of leaving the entry in a failed state.
    if not ecu.ecu.ecu_id:
        raise ConfigEntryNotReady(
            f"Unable to connect with ECU @ {ecu.ipaddr}. Check "
            "IP-Address or wait 10 minutes because the ECU might be "
            "recovering from reboot."
        )

    # Register the ECU device.
    device_registry = dr.async_get(hass)
    ecu_device = device_registry.async_get_or_create(
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
            via_device_id=ecu_device.id,
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
    if not unload_state:
        _LOGGER.error(
            "Failed to unload platforms for config entry %s", config_entry.entry_id
        )
    return unload_state


async def async_reload_entry(hass, config_entry):
    """Handle reload of a config entry."""
    await async_unload_entry(hass, config_entry)
    await async_setup_entry(hass, config_entry)
