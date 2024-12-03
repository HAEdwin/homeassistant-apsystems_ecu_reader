""" const.py """

DOMAIN = 'apsystems_ecur'

SOLAR_ICON = "mdi:solar-power"
FREQ_ICON = "mdi:sine-wave"
SIGNAL_ICON = "mdi:signal"
RELOAD_ICON = "mdi:reload"
CACHE_ICON = "mdi:cached"
RESTART_ICON = "mdi:restart"
POWER_ICON = "mdi:power"


# Config flow schema. These are also translated through associated json translations
KEYS = [
    "ecu_host",
    "scan_interval",
    "port_retries",
    "wifi_ssid",
    "wifi_password",
    "show_graphs",
]
