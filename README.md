# Reader for APsystems ECU's ##
This custom integration for Home Assistant sends commands to the ECU to retreive data and is an extension/further development of the ksheumaker integration.




# Improved version v2.0.0
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

# Update version v2.1.0 (work in progress)
- Moved the Inverter On/Off switch to the inverter instead of being a part of the ECU for better overview
- Same goes for the Inverter Online sensor
- Removed the ECU Query Switch, because it was being forgotten to turn on when the cache was used intensively, triggering the Switch Off.
You can build an automation and put an action on it if the ECU Using Cache sensor is On for a certain amount of time

# Difference in totals EMA and integration
Data produced by the ECU represents the data over the past five minutes. That's why the statistics on the EMA site are five minutes behind.


