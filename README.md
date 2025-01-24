# homeassistant-apsystems_ecu_reader
##Reader for APsystems ECU's##
This custom integration for Home Assistant sends commands to the ECU to read data


# Improved version
- Extensive data integrity checking
- Extensive control on communication with the ECU
- Hardened error handling
- Ability to switch individual inverters on/off
- Better handling of communication errors
- More efficient handling of queries that fail
- Caching based on individual queries
- Removed the need for retries
- Added L2 and L3 voltages for three-phased inverters
- Added support for multiple ECU hubs
- Added individual inverter online sensors for automations

#Difference in totals EMA and integration
Data produced by the ECU represents the data over the past five minutes. That's why the statistics on the EMA site are five minutes behind. For example: at 09:05 new data arrives, but this represents data from 09:00
