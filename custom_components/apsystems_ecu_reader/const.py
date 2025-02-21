""" const.py """

DOMAIN = 'apsystems_ecu_reader'

SOLAR_ICON = "mdi:solar-power"
FREQ_ICON = "mdi:sine-wave"
SIGNAL_ICON = "mdi:signal"
CACHE_ICON = "mdi:cached"
POWER_ICON = "mdi:power"
SOLAR_PANEL_ICON = "mdi:solar-panel"
CACHE_COUNTER_ICON = "mdi:restart"


# Config flow schema. These are also translated through json translations
KEYS = [
    "ecu_host",
    "scan_interval",
    "port_retries",
    "cache_reboot",
    "show_graphs",
    "wifi_ssid",
    "wifi_password"
]
