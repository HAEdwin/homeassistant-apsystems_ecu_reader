[![hacs_badge](https://img.shields.io/github/v/release/haedwin/homeassistant-apsystems_ecu_reader)](https://github.com/haedwin/homeassistant-apsystems_ecu_reader)
[![Validate with Hassfest](https://github.com/HAEdwin/homeassistant-apsystems_ecu_reader/actions/workflows/validate%20with%20Hassfest.yaml/badge.svg)](https://github.com/HAEdwin/homeassistant-apsystems_ecu_reader/actions/workflows/validate%20with%20Hassfest.yaml)
[![Validate with HACS](https://github.com/HAEdwin/homeassistant-apsystems_ecu_reader/actions/workflows/validate%20with%20HACS.yaml/badge.svg)](https://github.com/HAEdwin/homeassistant-apsystems_ecu_reader/actions/workflows/validate%20with%20HACS.yaml)
[![hacs_badge](https://img.shields.io/maintenance/yes/2025)](https://github.com/haedwin/homeassistant-apsystems_ecu_reader)
<!--
![Home Assistant Dashboard](https://github.com/haedwin/homeassistant-apsystems_ecu_reader/blob/main/dashboard.PNG)
-->

# APsystems ECU Reader
📢 We have over 780 active installations! 🎉 Please give me a star ⭐ if you like this integration! 👍 

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
- dBm expression for Zigbee Signal Strength, ideally between -10dBm (best signal) and -25dBm (worst signal).


> [!CAUTION]
> - ECU entities are not migrated from the predecessor of this integration (https://github.com/ksheumaker) because the ECU-ID is now part of the ECU specific entities to enable the use of multiple ECU's.
> - Inverter entities have remained the same, except for the Zigbee signal (this unit is converted from % to dBm). To avoid possible duplication of inverter entities (where "inverter_408000123456_power_ch_1" becomes two entities: "inverter_408000123456_power_ch_1" and "inverter_408000123456_power_ch_1-1"), you have to completely remove the old integration and reboot before activating the new one. The old entities are then first removed and later added again without losing historical data. Always use the UI to remove an integration.

## Prerequisites
You own an APSystems ECU model ECU-B, ECU-R or ECU-C and any combination of YC600, YC1000/QT2 series, DS3-series or QS1 series inverter. If your inverter is not supported, please raise an issue. Your ECU is connected to your LAN, correctly configured (assigned a fixed IP address) and Home Assistant has free access to it. You also have HACS installed in Home Assistant. You allready have an APsystemsema (Energy Monitoring & Analysis System) account and are succesfully uploading data to the EMA site.
Required connection method (ethernet or WiFi) for this integration to work depends on your ECU model, follow the table below.
Connection required | ECU Model | Automated Restart*
--- | --- | ---
Wireless | ECU-R (2160 series) and ECU-B | No
Wireless/Wired | ECU-R (2162 series) | Yes
Wired | ECU-C | Yes

_ECU-3 owners might want to take a look at: https://github.com/jeeshofone/ha-apc-ecu-3_

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
Final step to the prerequisites is testing the connection between HomeAssistant and the ECU. Sometimes it is difficult to find the ECU among all the other (esp) nodes, especially if you have many IoT devices. In any case, also look for **Espressif Inc. or ESP** because the ECU's WiFi interface is from this brand. Testing the connection can be done by using ping or from the terminal using the Netcat command, follow the example below but use the correct (fixed) IP address of your ECU. If connected you'll see line 2, then type in the command APS1100160001END if you get a response (line 4) you are ready to install the integration. If not, power cycle your ECU wait for it to get started and try again. **It is highly recommended to assign a fixed IP-Address to the ECU**.
```
[core-ssh .storage]$ nc -v 172.16.0.4 8899 <┘
172.16.0.4 (172.16.0.4:8899) open
APS1100160001END <┘
APS11009400012160000xxxxxxxz%10012ECU_R_1.2.22009Etc/GMT-8
```

Your ECU uses the following ports. Make sure that they are accessible and not blocked by a firewall rule.
![image](https://github.com/user-attachments/assets/2dfb520e-f3a2-4516-a427-d63788c6d1f7)



## Migrating from "APSystems PV solar ECU" to the "APsystems ECU Reader" integration
> [!CAUTION]
> ECU entities are not migrated from the predecessor of this integration (https://github.com/ksheumaker) because the ECU-ID is now part of the ECU specific entities to enable the use of multiple ECU's.

Go to [Settings] > [Devices & Services]. In the default integration tab you will find the "APSystems PV solar ECU" integration. Select the integration and choose the overflow menu. Delete the integration.
You are prompted to restart Home Assistant, do so but note that this will not remove the integration files from the custom_components folder, you will have to go to HACS in order to remove the files entirely.
### Removing the old "APSystems PV solar ECU" integration files from Home Assistant
Go to [HACS] and under "Downloaded" you will find the "APSystems ECU-R" integration with on the right the overflow menu. From that menu select [X Remove]. When prompted again select [REMOVE]. The integration files are now permanently removed.



## Installing the "APsystems ECU Reader" integration
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
- Retries when ECU fails to respond: The integration tries to open the connection to the ECU for this number of times. If that fails it a +1 for the cache counter.
- Cache count before auto ECU reboot (ECU-R-Pro & ECU-C models): The integration will reboot the ECU and sets the Using Cache Counter to zero.
If you own a ECU-R (2160xxxxx) or ECU-B a reboot will not take place, the ECU firmware does not provide this option on these models. Instead you can use an automation where you use the UCC sensor to trigger a smartplug to turn Off and On again after a 10 seconds wait. When you use a smartplug to reboot the ECU, you should set the UCC value higher than the value you would like to reboot the ECU at. The UCC will increase until the set value.
- Update graphs when inverters are offline: You can turn this on or off. In the On state most entities will be set to zero when the inverters are offline. The temperature and zigbee sensors will never be plotted when the inverters are offline.
- SSID and Password (ECU-R-Pro & ECU-C models): Using these fields will force the ECU to reboot when submitted. It's a workaround for the missing command to enable a forced reboot by the integration. The fields are not used to authenticate so can be randomly filled.


### Old versus renamed or expired ECU entities
|Old entity  |New entity |
|-------|-------------|
|sensor.ecu_current_power | sensor.ecu_{ECU-ID}_current_power|
|sensor.ecu_lifetime_energy | sensor.ecu_{ECU-ID}_lifetime_energy|
|sensor.ecu_today_energy | sensor.ecu_{ECU-ID}_today_energy|
|switch.ecu_inverters_online | switch.ecu_{ECU-ID}_all_inverters_on_off|
|switch.ecu_query_device | expired entity|
|sensor.ecu_inverters | sensor.ecu_{ECU-ID}_inverters|
|sensor.ecu_inverters_online | sensor.ecu_{ECU-ID}_inverters_online|
|binary_sensor.ecu_restart | expired entity|
|binary_sensor.ecu_using_cached_data | binary_sensor.ecu_{ECU-ID}_using_cached_data|

### New ECU entities
- sensor.ecu_{ECU-ID}_lifetime_maximum_power
- switch.ecu_{ECU-ID}_zero_export
- button.ecu_{ECU-ID}_reboot
- sensor.ecu_{ECU-ID}_using_cache_counter

### New Inverter entities
- switch.inverter_{UID}_on_off
- number.inverter_{UID}_maxpwr

## Compatibility of extra features
|Type	|Entity		|ECU-B |ECU-R |ECU-R-Pro |ECU-C |ECU-3|
|---|---|---|---|---|---|---|
|switch	|ecu_{ECU-ID}_zero_export [^1]	|No |No |No |Yes |Yes |
|switch	|inverter_{Inverter-ID}_on_off [^2]	|No |No |Yes |Yes |Yes |
|button	|ecu_{ECU-ID}_reboot [^4]	|No |No	|Yes |Yes |Yes |
|number	|inverter_{Inverter-ID}_maxpwr [^5]		|No |No |Yes |Yes |Yes |

_Note that the switch/number effects only the specified ECU-ID or Inverter-ID_

[^1]: This switch will dynamically regulate the inverters to ensure that no energy is being exported
[^2]: Switch to turn On/Off the individual inverter completely
[^3]: Switch to turn On/Off all the inverters completely at once
[^4]: Momentairy button which will reboot the ECU (take recovery into account)
[^5]: Number regulator to set the maximum amount of power on each individual inverter (per channel)

## In case of ECU firmware issues
In some cases the ECU firmware is not handling the Daily Energy or Lifetime Energy well. I recommend the utility meter integration to accommodate this. Below is an example of a Lifetime Energy Meter.
Edit in configuration.yaml:
```
utility_meter:
  lifetime_energy:
    source: sensor.ecu_xxxxxxxxxxxx_current_power

template:
  - sensor:
      - name: "Lifetime Energy (kWh)"
        unit_of_measurement: "kWh"
        state: "{{ states('sensor.lifetime_energy')|float(0) / 1000 }}"
```


## The temperature sensors
When the inverters are turned off at sundown the ECU returns zero for inverters temperature. Users prefer to keep them as null values instead of zero so the graphs are not being updated during the offline periods. In return, this causes a non-numeric error message for the gauge if you use that as a temperature indicator. In that case you can use this template part in configuration.yaml which converts the value to zero:
```
template:
  - sensor:
      - name: "Temperature non numeric 4080xxxxxxxx"
        state: "{{ states('sensor.inverter_4080xxxxxxxx_temperature')|float(0) }}"
        unit_of_measurement: "°C"

      - name: "Temperature non numeric 8060xxxxxxxx"
        state: "{{ states('sensor.inverter_8060xxxxxxxx_temperature')|float(0) }}"
        unit_of_measurement: "°C"
```

### How to derive new sensors from excisting sensors
* Total power for each inverter: Settings > Devices and Services > Helpers (top of the screen) > +Create Helper > +/- Combine the state of several sensors
* Use the Home Assistant Utility-Meter integration


## Other languages
German: https://smart-home-assistant.de/ap-systems-ecu-b-einbinden
Dutch: https://doe-duurzaam.nl/artikel/je-apsystems-micro-omvormers-slim-uitzetten-via-web-of-home-assistant/#teruglevering-beperken-per-micro-omvormer

## Firmware updates
ECU-C 2025-04-17, V1.2.18
- Optimize PV-storage linkage function
- Optimize automatic upgrades
- Change Redundant Energy Control to Relay Control
- Optimize function

ECU-R-Pro 2025-04-17, V2.1.24
- Add master-slave function
- Optimize PV-storage linkage function
- Optimize automatic upgrades
- Optimize function

ECU-R 2025-03-25, V1.3.17
- Optimize master-slave function
- Optimize PV-storage linkage function
- Optimize function

ECU-B 2024-12-30, V1.2.35
- Support ZigBee Router
- Optimize the display of data
- Optimize function

## FAQ
- Why is my inverter going offline sometimes during the day?

1. This might be due to a lost Zigbee connection between the ECU and inverter and will not effect the power returned to the grid. There may be poor reception of the Zigbee signal (< -70dBm), causing the inverter to appear to be offline. Move the ECU to a better position or point the Zigbee antenna towards the inverter and keep a close eye on the Signal Strength sensors. Strength should be between -10dBm (best) and -70dBm (worst). Sometimes reception is temporarily poor due to weather conditions. Although Zigbee is a mesh protocol, it can be easily disrupted by other (smart) devices and WiFi because it also works on the 2.4Ghz band. A meter cupboard is a bad place for the ECU as well as reinforced concrete walls, large refrigerators - well everything in the line of sight.
2. Another reason can be overvoltage, this is caused by bad AC voltage wiring (wire diameter too small) or cable too long. As a result, the resistance increases and there is a voltage drop on the cable. The inverter thinks that the voltage is too high, because it measures its own output voltage which has been increased by the voltage drop in the cable, the inverter will then shut down. A grid over voltage can occur when there are many solarpanels producing at the same time (in the neighbourhood). So always measure on the inverter side but also on the grid side to determen what the cause might be.

- Why do the ECU values ​​differ from the EMA values?

The ECU is not a continuous energy meter like the one from the electricity company, the sampling frequency can indeed cause a difference, as can the location of the CTs on a ECU-C and possible interferences can affect this data. Results from data samples requested by this integration may differ from data samples sent to EMA. Overall it gives an indication of the energy but it is not a calibrated value.

- Why doesn't this integration find my ECU?

9.99 out of 10 cases it turns out that a wrong node or network configuration is applicable. Make sure that HA can reach the ECU and that you can ping the ECU. Also make sure the ECU is running for at least 10 minutes before attempting to connect using this integration.

## Background & acknowledgement
Realization in 2022 was a collaboration between checking12, ksheumaker, HAEdwin on the Home Assistant forum, and all the other people from this forum (https://gathering.tweakers.net/forum/list_messages/2032302/1). Thanks goes out to 12christiaan and ViperRNMC for providing an automated solution to restart the ECU-C and ECU-R (SunSpec logo/ECU-ID starting with 2162xxxxxxxx) models. Best for last all my sponsors who provide me with coffee! Thank you, it keeps me motivated!
