"""const.py"""

DOMAIN = "apsystems_ecu_reader"

SOLAR_ICON = "mdi:solar-power"
FREQ_ICON = "mdi:sine-wave"
SIGNAL_ICON = "mdi:signal"
CACHE_ICON = "mdi:cached"
POWER_ICON = "mdi:power"
SOLAR_PANEL_ICON = "mdi:solar-panel"
CACHE_COUNTER_ICON = "mdi:counter"
ECU_REBOOT_ICON = "mdi:restart"
FROM_GRID_ICON = "mdi:transmission-tower-export"
CONSUMED_ICON = "mdi:transmission-tower"


# Config flow schema. These are also translated through json translations
KEYS = [
    "ecu_host",
    "scan_interval",
    "port_retries",
    "cache_reboot",
    "show_graphs",
    "wifi_ssid",
    "wifi_password",
]

# Model maps for ECU and inverter types
ECU_MODEL_MAP = {
    "2160": "ECU-R",
    "2162": "ECU-R-Pro",
    "2163": "ECU-B",
    "2150": "ECU-C",
    "2030": "ECU-3",
}

INVERTER_MODEL_MAP = {
    "10": "YC500 series",
    "40": "YC600 series",
    "50": "YC1000 series",
    "70": "DS3 series",
    "80": "QS1 series",
    "90": "QT2 series",
}
