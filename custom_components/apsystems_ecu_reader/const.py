""" const.py """

DOMAIN = 'apsystems_ecu_reader'

SOLAR_ICON = "mdi:solar-power"
FREQ_ICON = "mdi:sine-wave"
SIGNAL_ICON = "mdi:signal"
CACHE_ICON = "mdi:cached"
POWER_ICON = "mdi:power"
SOLAR_PANEL_ICON = "mdi:solar-panel"


# Config flow schema. These are also translated through associated json translations
KEYS = [
    "ecu_host",
    "scan_interval",
    "port_retries",
    "show_graphs",
]
