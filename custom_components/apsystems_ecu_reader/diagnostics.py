"""Diagnostics platform for the APsystems ECU Reader integration."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN

# Fields in config.data that are secrets and must never be exported
_PRIVATE_KEYS = {"wifi_ssid", "wifi_password"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, config_entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    data = hass.data[DOMAIN][config_entry.entry_id]
    ecu = data["ecu"]
    coordinator = data["coordinator"]

    config_data = {
        key: value for key, value in config_entry.data.items() if key not in _PRIVATE_KEYS
    }
    options = {
        key: value for key, value in config_entry.options.items() if key not in _PRIVATE_KEYS
    }

    return {
        "config": {
            "data": config_data,
            "options": options,
            "entry_id": config_entry.entry_id,
            "title": config_entry.title,
        },
        "ecu": {
            "ip_address": ecu.ipaddr,
            "ecu_id": ecu.ecu.ecu_id,
            "firmware": ecu.ecu.firmware,
            "model": ecu.ecu.ecu_id[:4] if ecu.ecu.ecu_id else None,
            "timezone": ecu.ecu.timezone,
            "last_update": ecu.ecu.last_update,
            "query_enabled": ecu.query_enabled,
            "data_from_cache": ecu.data_from_cache,
            "data_from_cache_count": ecu.data_from_cache_count,
        },
        "coordinator": {
            "last_update_success": coordinator.last_update_success,
            "last_update": coordinator.last_update.isoformat()
            if coordinator.last_update
            else None,
            "data": _redact_data(coordinator.data),
        },
    }


def _redact_data(data: dict[str, Any] | None) -> dict[str, Any] | None:
    """Return coordinator data without secrets or large graph payloads."""
    if not isinstance(data, dict):
        return data
    keys_to_keep = {
        "ecu_id",
        "last_update",
        "current_power",
        "today_energy",
        "lifetime_energy",
        "qty_of_inverters",
        "qty_of_online_inverters",
        "data_from_cache",
        "data_from_cache_count",
    }
    return {
        key: value
        for key, value in data.items()
        if key in keys_to_keep or key.startswith("inverters")
    }
