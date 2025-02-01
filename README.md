[![hacs_badge](https://img.shields.io/maintenance/yes/2025)](https://github.com/haedwin/homeassistant-apsystems_ecu_reader)
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![hacs_badge](https://img.shields.io/github/v/release/haedwin/homeassistant-apsystems_ecu_reader)](https://github.com/haedwin/homeassistant-apsystems_ecu_reader)
[![Validate with Hassfest](https://github.com/haedwin/homeassistant-apsystems_ecu_reader/actions/workflows/validate%20with%20Hassfest.yml/badge.svg)](https://github.com/haedwin/homeassistant-apsystems_ecu_reader/actions/workflows/validate%20with%20Hassfest.yml)


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
APsystems ECU reader is an Integration not an Add-on.

The installation of custom integrations is done in three steps (assuming HACS is already installed):

1. Downloading the custom integration

Navigate to HACS and choose the overflow menu in the top right corner of the Home Assistant Community Store.
Choose Custom repositories and paste the url: https://github.com/HAEdwin/homeassistant-apsystems_ecu_reader in the Repository field.
Choose Type > Integration and select the [Add]-button. From this point it might allready have been added to the personal store repository.
In HACS search for APsystems and the APsystems ECU Reader will be listed in de Available for download section.
From the overflow menu on the right select [Download] and automatically the latest version will be listed for download so choose [Download].
HA Settings will now show the repair action that a Restart is required, submit the action and HA will restart.
After HA's restart the downloaded custom integration will be detected by HA. The integration will need to be configured in order to fully integrate it in HA and make it work.

2. Integrating the custom integration into Home Assistant

Navigate to [Settings] > [Devices & services] and choose the button [+ ADD INTEGRATION].
In Search for a brand name, choose APsystems and the APsystems ECY Reader will be listed.
Select it and the Configuration diaglog will show, enter the IP-Address of your ECU other settings are fine right now so choose [SUBMIT].

# To Do
- Add logos to the integration
- Expand readme
- Still some code cleanup/checks to do
- Debugging

# Happy with this software?
<a href="https://buymeacoffee.com/haedwin" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/default-orange.png" alt="Buy Me A Coffee" height="41" width="174"></a>


# FAQ
- Why is my inverter going offline sometimes during the day?

This is due to a lost Zigbee connection between the ECU and inverter and will not effect the power returned to the grid. There may be poor reception of the Zigbee signal (< -70dBm), causing the inverter to appear to be offline. Move the ECU to a better position or point the Zigbee antenna towards the inverter and keep a close eye on the Signal Strength sensors. Strength should be between -10dBm (best) and -70dBm (worst). Sometimes reception is temporarily poor due to weather conditions.

- Why do the ECU values ​​differ from the EMA values?

EMA performs its own calculations based on data received from the ECU. Sometimes data cannot be posted to the EMA and the data is corrected in the evening (ECU maintenance period). If you would like to help solve this problem and do data analysis, please feel free to contact me.
