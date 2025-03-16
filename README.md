[![hacs_badge](https://img.shields.io/github/v/release/haedwin/homeassistant-apsystems_ecu_reader)](https://github.com/haedwin/homeassistant-apsystems_ecu_reader)
[![Validate with Hassfest](https://github.com/HAEdwin/homeassistant-apsystems_ecu_reader/actions/workflows/validate%20with%20Hassfest.yaml/badge.svg)](https://github.com/HAEdwin/homeassistant-apsystems_ecu_reader/actions/workflows/validate%20with%20Hassfest.yaml)
[![Validate with HACS](https://github.com/HAEdwin/homeassistant-apsystems_ecu_reader/actions/workflows/validate%20with%20HACS.yaml/badge.svg)](https://github.com/HAEdwin/homeassistant-apsystems_ecu_reader/actions/workflows/validate%20with%20HACS.yaml)
[![hacs_badge](https://img.shields.io/maintenance/yes/2025)](https://github.com/haedwin/homeassistant-apsystems_ecu_reader)
<!--
![Home Assistant Dashboard](https://github.com/haedwin/homeassistant-apsystems_ecu_reader/blob/main/dashboard.PNG)
-->

# APsystems ECU Reader
📢 We have over 740 active installations! 🎉

This custom integration for Home Assistant sends commands to the ECU to retreive data and is an extension/further development of ksheumaker's "homeassistant-apsystems_ecur" integration. It supports the following features:
- Extensive data integrity checking
- Extensive control on communication with the ECU
- Ability to switch individual inverters on/off (ECU-R-Pro 2162 and ECU-C only)
- Better handling of communication errors
- More efficient handling of queries that fail
- Added L2 and L3 voltages for three-phased inverters
- Added support for multiple ECU hubs
- Added individual Inverter Online sensors for automations
- Ability to enable Zero Export (ECU-C and ECU-3)
- Limit maximum Power of each panel (ECU-R-Pro, ECU-C, ECU-3)
- dBm expression for Zigbee Signal Strength, ideally between -10dBm (best signal) and -70dBm (worst signal)
> [!CAUTION]
> - ECU entities are not migrated from the predecessor of this integration (https://github.com/ksheumaker) because the ECU-ID is now part of the ECU specific entities to enable the use of multiple ECU's.
> - Inverter entities have remained the same, except for the Zigbee signal (this unit is converted from % to dBm). To avoid duplication of inverter entities ("inverter_408000123456_power_ch_1" becomes two entities: "inverter_408000123456_power_ch_1" and "inverter_408000123456_power_ch_1-1") you have to completely remove the old integration and reboot before activating the new one. The old entities are then first removed and later added again without losing historical data. Always use the UI to remove an integration.

## Prerequisites
You own an APSystems ECU model ECU-B, ECU-R or ECU-C and any combination of YC600, YC1000/QT2, DS3/DS3D, DS3-H or QS1/QS1A inverter. If your inverter is not supported, please raise an issue. Your ECU is connected to your LAN, correctly configured (assigned a fixed IP address) and Home Assistant has free access to it. You also have HACS installed in Home Assistant. You allready have an APsystemsema (Energy Monitoring & Analysis System) account and are succesfully uploading data to the EMA site.
Connection method (ethernet or WiFi) depends on your ECU model, follow the table below.
Connection required | ECU Model | Automated Restart* | Turn on/off Inverters
--- | --- | --- | ---
Wireless | ECU-R (2160xxxxxxxx series) and ECU-B | No | No
Wireless | ECU-R (SunSpec logo/ECU-ID starting with 2162xxxxxxxx) | Yes | Yes
Wired | ECU-C | Yes | Yes

ECU-3 owners might want to take a look at: https://github.com/jeeshofone/ha-apc-ecu-3

### Configure your wireless ECU connection
1. **Install EMA Manager**: 
Download and install the EMA Manager app on your mobile device from the appropriate app store.
1. **Put ECU-R in Access Point Mode**: 
Locate the physical button on your ECU-R router. Press and hold the button for a few seconds until the router's Wi-Fi starts. You should see it in your accessible WIFI networks of your device (phone). This indicates that the router is in Access Point mode.
1. **Connect to ECU-R Wi-Fi**:
Use your mobile device to connect to the newly created Wi-Fi network from your ECU-R router.
The default Wi-Fi password is 88888888.
1. **Launch EMA Manager**:
Open the EMA Manager app on your device.
Choose the "Local" connection option. The app should automatically detect and connect to your ECU-R router.
1. **Configure ECU-R Network Settings**:
Once connected, use the EMA Manager app to configure the ECU-R's network settings.
Connect the ECU-R to the same Wi-Fi network as your Home Assistant.

### Test the ECU connection and finding your ECU on the Local Network
Final step to the prerequisites is testing the connection between HomeAssistant and the ECU. Sometimes it is difficult to find the ECU among all the other nodes, especially if you have many IOT devices. In any case, look for **Espressif Inc. or ESP** because the ECU's WiFi interface is from this brand. Testing the connection can be done from the terminal using the Netcat command, follow the example below but use the correct (fixed) IP address of your ECU. If connected you'll see line 2, then type in the command APS1100160001END if you get a response (line 4) you are ready to install the integration. If not, power cycle your ECU wait for it to get started and try again. **It is highly recommended to assign a fixed IP-Address to the ECU**.
```
[core-ssh .storage]$ nc -v 172.16.0.4 8899 <┘
172.16.0.4 (172.16.0.4:8899) open
APS1100160001END <┘
APS11009400012160000xxxxxxxz%10012ECU_R_1.2.22009Etc/GMT-8
```

## Install the integration
The installation of custom integrations is done in three steps (assuming HACS is already installed):

**1. Downloading the custom integration**
- Navigate to HACS and choose the overflow menu in the top right corner of the Home Assistant Community Store.
- Choose Custom repositories and paste the url: https://github.com/HAEdwin/homeassistant-apsystems_ecu_reader in the Repository field.
- Choose Type > Integration and select the [Add]-button.
From this point it might allready have been added to the personal store repository. If not, wait for it to appear then close the Custom repositories dialog window.
- In HACS search for APsystems and the APsystems ECU Reader will be listed in de Available for download section.
- From the overflow menu on the right select [Download] and automatically the latest version will be listed for download so choose [Download].
- HA Settings will now show the repair action that a Restart is required, submit the action and HA will restart.

After HA's restart the downloaded custom integration will be detected by HA.
The integration will need to be configured in order to fully integrate it in HA and make it work.

**2. Integrating the custom integration into Home Assistant**
- Navigate to [Settings] > [Devices & services] and choose the button [+ ADD INTEGRATION] in the lower right corner.
- In "Search for a brand name", choose APsystems and the APsystems ECU Reader will be listed.
- Select it and the Configuration dialog will show, enter IP-Address of the ECU, rest of the defaults are fine so choose [SUBMIT].
> [!IMPORTANT]
> When you recieve the message "No ECU found at this IP-address or ECU is recovering from restart" make sure the ECU is running for at least 10 minutes after a restart of the ECU before (re-)configuring the integration. The ECU might still contain incomplete data which cannot be accepted. Other option is still a wrong IP-address being entered, below more details on how to test and find the ECU on your network.

### APsystems ECU Configuration
- ECU-IP address: The address you have assigned to the ECU must be entered here
- ECU query interval in seconds: I strongly recommend keeping this value set to 300 since data in the ECU is only refreshed every 5 minutes. 
- Using Cache Counter (UCC) sensor: When the ECU fails to respond to connection requests for the number of retries you specified, the UCC value will increase until the number you specified at "Cache count before ECU reboot". 
- Cache countbefore ECU reboot: If you own an ECU-R-Pro (2162xxxxx) or an ECU-C the integration will reboot the ECU and set the UCC to zero.
If you own a ECU-R (2160xxxxx) or ECU-B a reboot will not take place, the ECU firmware does not provide this option on these models. Instead you can use an automation where you use the UCC sensor to trigger a smartplug to turn Off and On again after a 10 seconds wait. If you don't restart the ECU, the UCC will increase until there was a succesfull connection with the ECU again.
- Update graphs when inverters are offline: You can turn this on or off. In the On state most entities will be set to zero when the inverters are offline. The temperature and zigbee sensors will never be plotted when the inverters are offline.

## In case of ECU firmware issues
In some cases the ECU firmware is not handling the Daily Energy or Lifetime Energy well. I recommend the utility meter integration to accommodate this. Below is an example of a Lifetime Energy Meter.
Edit in configuration.yaml:
```
# integration
utility_meter:
  lifetime_energy:
    source: sensor.ecu_xxxxxxxxxxxx_current_power
		       

# Custom sensors
sensor:
  - platform: template
    sensors:
      lifetime_energy_kwh:
        friendly_name: "Lifetime Energy (kWh)"
        unit_of_measurement: "kWh"
        value_template: "{{ states('sensor.lifetime_energy') | float / 1000 }}"
```
## Compatibility of extra features
|Type	|function		|ECU-R |ECU-R-Pro |ECU-C |ECU-3|
|-------|-----------------------|------|----------|------|-----|
|switch	|Zero Export Control	|No    |No	  |Yes   |Yes  |
|switch	|Inverter On/Off	|No    |Yes	  |Yes	 |Yes  |
|action	|Maximum Power		|No    |Yes	  |Yes	 |Yes  |
|action	|Software Reboot	|No    |Yes	  |Yes	 |Yes  |


## To Do
- Expand readme
- Still some code cleanup/checks to do
- Debugging

## FAQ
- Why is my inverter going offline sometimes during the day?

This is due to a lost Zigbee connection between the ECU and inverter and will not effect the power returned to the grid. There may be poor reception of the Zigbee signal (< -70dBm), causing the inverter to appear to be offline. Move the ECU to a better position or point the Zigbee antenna towards the inverter and keep a close eye on the Signal Strength sensors. Strength should be between -10dBm (best) and -70dBm (worst). Sometimes reception is temporarily poor due to weather conditions.

- Why do the ECU values ​​differ from the EMA values?

APsystems replied: "The ECU-C is not a continuous energy meter like the one from the electricity company, the sampling frequency can indeed cause a difference, as can the location of the CTs and possible interferences can affect this data.
It gives an indication of the energy but it is not a calibrated value."
EMA performs its own calculations based on data received from the ECU. Sometimes data cannot be posted to the EMA and the data is corrected in the evening (ECU maintenance period). If you would like to help solve this problem and do data analysis, please feel free to contact me.

## Background & acknowledgement
Realization in 2022 was a collaboration between checking12, ksheumaker, HAEdwin on the Home Assistant forum, and all the other people from this forum (https://gathering.tweakers.net/forum/list_messages/2032302/1). Thanks goes out to 12christiaan and ViperRNMC for providing an automated solution to restart the ECU-C and ECU-R (SunSpec logo/ECU-ID starting with 2162xxxxxxxx) models. Best for last all my sponsors who provide me with coffee! Thank you, it keeps me motivated!
