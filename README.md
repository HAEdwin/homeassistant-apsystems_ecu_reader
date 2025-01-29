# APsystems ECU Reader
This custom integration for Home Assistant sends commands to the ECU to retreive data and is an extension/further development of ksheumaker's "homeassistant-apsystems_ecur" integration. It supports the following features:
- Extensive data integrity checking
- Extensive control on communication with the ECU
- Hardened error handling
- Ability to switch individual inverters on/off (ECU-R-Pro 2162 and ECU-C only)
- Better handling of communication errors
- More efficient handling of queries that fail
- Caching based on individual queries
- Removed the need for retries
- Added L2 and L3 voltages for three-phased inverters
- Added support for multiple ECU hubs
- Added individual inverter online sensors for automations
- dBm expression for Zigbee Signal Strength, ideally between -10dBm (best signal) and -70dBm (worst signal)

# FAQ
- Why is my inverter going offline sometimes during the day?

This is due to a lost Zigbee connection between the ECU and inverter and will not effect the power returned to the grid. There may be poor reception of the Zigbee signal (< -70dBm), causing the inverter to appear to be offline. Move the ECU to a better position or point the Zigbee antenna towards the inverter and keep a close eye on the Signal Strength sensors. Strength should be between -10dBm (best) and -70dBm (worst). Sometimes reception is temporarily poor due to weather conditions.
