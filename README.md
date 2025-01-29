# APsystems ECU Reader
This custom integration for Home Assistant sends commands to the ECU to retreive data and is an extension/further development of ksheumaker's "homeassistant-apsystems_ecur" integration.

# FAQ
- Why is my inverter going offline sometimes during the day?

This is due to a lost Zigbee connection between the ECU and inverter and will not effect the power returned to the grid. There may be poor reception of the Zigbee signal, causing the inverter to appear to be offline. Move the ECU to a better position or point the Zigbee antenna towards the inverter. Sometimes reception is temporarily poor due to weather conditions.


