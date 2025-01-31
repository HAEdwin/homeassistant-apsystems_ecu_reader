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

# Installation
APsystems ECU reader is an Integration not an Add-on. To install the integration if you use HACS select it from the left pane and then select the Overflow Menu at the top right in HACS. From the pull-down select Custom repositories.

Repository: https://github.com/HAEdwin/homeassistant-apsystems_ecu_reader 

Type: Integration and press [+Add]-button. Then wait a while, it will pop-up in the list, Available for download. Select Download from the Overflow menu on the right of the available integration. You then will be asked to restart HA. After restart go to Settings in the left pane then choose Integrations > Devices & Services and on the down right select Add integration > Type "aps" and the apsystems integration named APsystems ECU Reader should pop-up. Select it and you will be asked to enter parameters.

Steps taken:
- Pointed and downloaded the integration from the https://github.com/HAEdwin/homeassistant-apsystems_ecu_reader git
- By restarting HA it was detected by HA and became available for selection in the Integrations section
- Configured and started the integration

# To Do
- Add logos to the integration
- Expand readme
- Still some code cleanup/checks to do
- Debugging

# FAQ
- Why is my inverter going offline sometimes during the day?

This is due to a lost Zigbee connection between the ECU and inverter and will not effect the power returned to the grid. There may be poor reception of the Zigbee signal (< -70dBm), causing the inverter to appear to be offline. Move the ECU to a better position or point the Zigbee antenna towards the inverter and keep a close eye on the Signal Strength sensors. Strength should be between -10dBm (best) and -70dBm (worst). Sometimes reception is temporarily poor due to weather conditions.

- Why do the ECU values ​​differ from the EMA values?

EMA does it's own calculations based on data received from the ECU. Sometimes data cannot be posted at EMA and data will be corrected in the evening (ECU maintenance period). If you want to help solve this issue and do some data analyses, feel free to contact me.
