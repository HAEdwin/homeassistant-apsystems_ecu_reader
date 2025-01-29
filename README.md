# APsystems ECU Reader
This custom integration for Home Assistant sends commands to the ECU to retreive data and is an extension/further development of ksheumaker's "homeassistant-apsystems_ecur" integration.

# Update version v2.1.0 (work in progress)
- Moved the Inverter On/Off switch to the inverter instead of being a part of the ECU for better overview
- Same goes for the Inverter Online sensor
- Removed the ECU Query Switch, because it was being forgotten to turn on when the cache was used intensively, triggering the Switch Off.
You can build an automation and put an action on it if the ECU Using Cache sensor is On for a certain amount of time
- Cleaned up some code

# FAQ
- Why is my inverter going offline sometimes during the day?

This is due to a lost Zigbee connection between the ECU and inverter and will not effect the power returned to the grid. There may be poor reception of the Zigbee signal, causing the inverter to appear to be offline. Move the ECU to a better position or point the Zigbee antenna towards the inverter. Sometimes reception is temporarily poor due to weather conditions.


