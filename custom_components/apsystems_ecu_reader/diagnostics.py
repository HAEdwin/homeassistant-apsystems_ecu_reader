"""Diagnostics platform for the APsystems ECU Reader integration.

The output is designed to be safe to attach to a public GitHub issue: the
ECU-ID, inverter UIDs, IP address and Wi-Fi credentials are all redacted or
removed. What *is* kept (model codes, firmware version, cache/fallback
state, per-inverter online/signal/power data and the ECU-C CT/meter values)
mirrors the information most often requested when triaging reports such as
"no data" / "CT returns 0 or None after firmware update", "connection keeps
breaking", and "maxpwr / on-off not working" on
https://github.com/HAEdwin/homeassistant-apsystems_ecu_reader/issues.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import ECU_MODEL_MAP, INVERTER_MODEL_MAP

# Fields in config.data / config.options that must never be exported.
# ecu_host is the ECU's IP address on the local network; wifi_ssid/
# wifi_password are the inverter Wi-Fi access point credentials.
TO_REDACT = {"ecu_host", "wifi_ssid", "wifi_password"}

_REDACTED = "**REDACTED**"


def _redact_ecu_id(ecu_id: str | None) -> str | None:
    """Keep the model code (first 4 chars), redact the unique serial."""
    if not ecu_id:
        return ecu_id
    return f"{ecu_id[:4]}-{_REDACTED}"


def _redact_inverter_uid(uid: str | None) -> str | None:
    """Keep the model code (first 2 chars), redact the unique serial."""
    if not uid:
        return uid
    return f"{uid[:2]}-{_REDACTED}"


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, config_entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    runtime_data = config_entry.runtime_data
    ecu = runtime_data.ecu
    coordinator = runtime_data.coordinator

    ecu_id = ecu.ecu.ecu_id
    is_ecu_c = bool(ecu_id and ecu_id.startswith("215"))

    return {
        "config": {
            "data": async_redact_data(dict(config_entry.data), TO_REDACT),
            "options": async_redact_data(dict(config_entry.options), TO_REDACT),
        },
        "ecu": {
            "ecu_id": _redact_ecu_id(ecu_id),
            "model": ECU_MODEL_MAP.get(ecu_id[:4], "Unknown Model") if ecu_id else None,
            "firmware": ecu.ecu.firmware,
            "timezone": ecu.ecu.timezone,
            "has_ct_meter": is_ecu_c,
            "query_enabled": ecu.query_enabled,
            "data_from_cache": ecu.data_from_cache,
            "data_from_cache_count": ecu.data_from_cache_count,
        },
        "coordinator": {
            "last_update_success": coordinator.last_update_success,
            "last_exception": type(coordinator.last_exception).__name__
            if coordinator.last_exception
            else None,
            "update_interval": coordinator.update_interval.total_seconds()
            if coordinator.update_interval
            else None,
            "last_update": ecu.ecu.last_update,
            "data": _redact_coordinator_data(coordinator.data),
        },
    }


def _redact_coordinator_data(data: dict[str, Any] | None) -> dict[str, Any] | None:
    """Return coordinator data with ECU/inverter identifiers redacted.

    Keeps the fields most relevant to the known categories of reported
    issues: overall connectivity/cache fallback, the ECU-C CT/meter
    readings (frequently reported as stuck at "No Data"/0/None after a
    firmware update), and per-inverter online/signal/power/voltage/model
    data (reported as missing or incorrect for specific inverter models).
    """
    if not isinstance(data, dict):
        return data

    summary = {
        key: data[key]
        for key in (
            "timestamp",
            "last_update",
            "current_power",
            "today_energy",
            "lifetime_energy",
            "qty_of_inverters",
            "qty_of_online_inverters",
            "data_from_cache",
            "data_from_cache_count",
        )
        if key in data
    }

    meter = {
        key: value
        for key, value in data.items()
        if key.startswith(("production_ct_", "grid_ct_", "consumed_"))
    }
    if meter:
        summary["meter"] = meter

    inverters = data.get("inverters")
    if isinstance(inverters, dict):
        summary["inverters"] = [
            {
                "inverter": f"inverter_{index}",
                "uid": _redact_inverter_uid(uid),
                "model": INVERTER_MODEL_MAP.get(uid[:2], "Unknown Model")
                if uid
                else None,
                "online": inv_data.get("online"),
                "signal": inv_data.get("signal"),
                "temperature": inv_data.get("temperature"),
                "frequency": inv_data.get("frequency"),
                "power": inv_data.get("power"),
                "voltage": inv_data.get("voltage"),
                "channel_qty": inv_data.get("channel_qty"),
            }
            for index, (uid, inv_data) in enumerate(inverters.items(), start=1)
        ]

    return summary
