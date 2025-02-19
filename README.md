[![hacs_badge](https://img.shields.io/maintenance/yes/2025)](https://github.com/haedwin/homeassistant-apsystems_ecu_reader)
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![hacs_badge](https://img.shields.io/github/v/release/haedwin/homeassistant-apsystems_ecu_reader)](https://github.com/haedwin/homeassistant-apsystems_ecu_reader)
[![Validate with Hassfest](https://github.com/haedwin/homeassistant-apsystems_ecu_reader/actions/workflows/validate%20with%20Hassfest.yml/badge.svg)](https://github.com/haedwin/homeassistant-apsystems_ecu_reader/actions/workflows/validate%20with%20Hassfest.yml)
[![Validate with HACS](https://github.com/haedwin/homeassistant-apsystems_ecu_reader/actions/workflows/validate%20with%20HACS.yml/badge.svg)](https://github.com/haedwin/homeassistant-apsystems_ecu_reader/actions/workflows/validate%20with%20HACS.yml)
![Home Assistant Dashboard](https://github.com/haedwin/homeassistant-apsystems_ecu_reader/blob/main/dashboard.PNG)


# APsystems ECU Reader
This custom integration for Home Assistant sends commands to the ECU to retreive data and is an extension/further development of ksheumaker's "homeassistant-apsystems_ecur" integration. It supports the following features:
- Extensive data integrity checking
- Extensive control on communication with the ECU
- Ability to switch individual inverters on/off (ECU-R-Pro 2162 and ECU-C only)
- Better handling of communication errors
- More efficient handling of queries that fail
- Caching based on individual queries
- Added L2 and L3 voltages for three-phased inverters
- Added support for multiple ECU hubs
- Added individual Inverter Online sensors for automations
- dBm expression for Zigbee Signal Strength, ideally between -10dBm (best signal) and -70dBm (worst signal)
> [!CAUTION]
> ECU entities are not migrated from the predecessor of this integration (https://github.com/ksheumaker) because the ECU-ID is now part of the ECU specific entities to enable the use of multiple ECU's. The inverter entities have remained the same, except for the Zigbee signal (this unit is converted from % to dBm). To avoid duplication of inverter entities ("inverter_408000123456_power_ch_1" becomes two entities: "inverter_408000123456_power_ch_1" and "inverter_408000123456_power_ch_1-1") you have to completely remove the old integration and reboot before activating the new one. The old entities are then first removed and later added again without losing historical data. Always use the UI to remove an integration.

## Install the integration
The installation of custom integrations is done in three steps (assuming HACS is already installed):

**1. Downloading the custom integration**
- Navigate to HACS and choose the overflow menu in the top right corner of the Home Assistant Community Store.
- Choose Custom repositories and paste the url: https://github.com/HAEdwin/homeassistant-apsystems_ecu_reader in the Repository field.
- Choose Type > Integration and select the [Add]-button.
From this point it might allready have been added to the personal store repository. If not, wait for it to appear.
- In HACS search for APsystems and the APsystems ECU Reader will be listed in de Available for download section.
- From the overflow menu on the right select [Download] and automatically the latest version will be listed for download so choose [Download].
- HA Settings will now show the repair action that a Restart is required, submit the action and HA will restart.

After HA's restart the downloaded custom integration will be detected by HA.
The integration will need to be configured in order to fully integrate it in HA and make it work.

**2. Integrating the custom integration into Home Assistant**
- Navigate to [Settings] > [Devices & services] and choose the button [+ ADD INTEGRATION].
- In "Search for a brand name", choose APsystems and the APsystems ECU Reader will be listed.
- Select it and the Configuration dialog will show, enter IP-Address of the ECU, rest of the defaults are fine so choose [SUBMIT].
> [!IMPORTANT]
> If you recieve the message "ECU not found..." make sure the ECU is running for at least 10 minutes after a restart of the ECU before (re-)configuring the integration. The ECU might still be in recovery state (contains incomplete data which is currently not accepted by the integration). I'm working on a fix for that to help understand the message.

### Test your connection and find your ECU on the LAN
Final step to the prerequisites is testing the connection between HomeAssistant and the ECU. Sometimes it is difficult to find the ECU among all the other nodes, especially if you have many IOT devices. In any case, look for **Espressif Inc. or ESP** because the ECU's WiFi interface is from this brand. Testing the connection can be done from the terminal using the Netcat command, follow the example below but use the correct (fixed) IP address of your ECU. If connected you'll see line 2, then type in the command APS1100160001END if you get a response (line 4) you are ready to install the integration. If not, power cycle your ECU wait for it to get started and try again. **It is highly recommended to assign a fixed IP-Address to the ECU**.
```
[core-ssh .storage]$ nc -v 172.16.0.4 8899 <┘
172.16.0.4 (172.16.0.4:8899) open
APS1100160001END <┘
APS11009400012160000xxxxxxxz%10012ECU_R_1.2.22009Etc/GMT-8
```
Sometimes you might see the "Unknown error occurred" message. Installation can best be done in the daytime when inverters are running.

### APsystems ECU Configuration
- ECU-IP address: The address you have assigned to the ECU must be entered here
- ECU query interval in seconds: I strongly recommend keeping this value set to 300 since data in the ECU is only refreshed every 5 minutes. 
- Using Cache Counter (UCC) sensor: When the ECU fails to respond to connection requests for the number of retries you specified, the UCC value will increase until the number you specified at "Cache count before ECU reboot". 
- Cache countbefore ECU reboot: If you own an ECU-R-Pro (2162xxxxx) or an ECU-C the integration will reboot the ECU and set the UCC to zero.
If you own a ECU-R (2160xxxxx) or ECU-B a reboot will not take place, the ECU firmware does not provide this option on these models. Instead you can use an automation where you use the UCC sensor to trigger a smartplug to turn Off and On again after a 10 seconds wait. If you don't restart the ECU, the UCC will increase until there was a succesfull connection with the ECU again.
- Update graphs when inverters are offline: You can turn this on or off. In the On state most entities will be set to zero when the inverters are offline. The temperature and zigbee sensors will never be plotted when the inverters are offline.

## To Do
- Expand readme
- Still some code cleanup/checks to do
- Debugging

## Support my work
<a href="https://buymeacoffee.com/haedwin" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/default-orange.png" alt="Buy Me A Coffee" height="41" width="174"></a>


## FAQ
- Why is my inverter going offline sometimes during the day?

This is due to a lost Zigbee connection between the ECU and inverter and will not effect the power returned to the grid. There may be poor reception of the Zigbee signal (< -70dBm), causing the inverter to appear to be offline. Move the ECU to a better position or point the Zigbee antenna towards the inverter and keep a close eye on the Signal Strength sensors. Strength should be between -10dBm (best) and -70dBm (worst). Sometimes reception is temporarily poor due to weather conditions.

- Why do the ECU values ​​differ from the EMA values?

APsystems replied: "The ECU-C is not a continuous energy meter like the one from the electricity company, the sampling frequency can indeed cause a difference, as can the location of the CTs and possible interferences can affect this data.
It gives an indication of the energy but it is not a calibrated value."
EMA performs its own calculations based on data received from the ECU. Sometimes data cannot be posted to the EMA and the data is corrected in the evening (ECU maintenance period). If you would like to help solve this problem and do data analysis, please feel free to contact me.
