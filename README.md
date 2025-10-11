[![hacs_badge](https://img.shields.io/github/v/release/haedwin/homeassistant-apsystems_ecu_reader)](https://github.com/haedwin/homeassistant-apsystems_ecu_reader)
[![Validate with Hassfest](https://github.com/HAEdwin/homeassistant-apsystems_ecu_reader/actions/workflows/validate%20with%20Hassfest.yaml/badge.svg)](https://github.com/HAEdwin/homeassistant-apsystems_ecu_reader/actions/workflows/validate%20with%20Hassfest.yaml)
[![Validate with HACS](https://github.com/HAEdwin/homeassistant-apsystems_ecu_reader/actions/workflows/validate%20with%20HACS.yaml/badge.svg)](https://github.com/HAEdwin/homeassistant-apsystems_ecu_reader/actions/workflows/validate%20with%20HACS.yaml)
[![hacs_badge](https://img.shields.io/maintenance/yes/2025)](https://github.com/haedwin/homeassistant-apsystems_ecu_reader)

# APsystems ECU Reader

> Over 800 active installations and growing — thank you!  
> If you enjoy using this integration, please leave a ⭐ star to show your support.  
> Consider making a donation to help me keep improving!

## Overview

APsystems ECU Reader is a custom Home Assistant integration project for communicating with APsystems ECU hubs. It is an extended and improved version of ksheumaker's "homeassistant-apsystems_ecur" integration.  
Key features include:
- Robust data integrity checks
- Enhanced communication control with the ECU
- Individual inverter on/off switching (ECU-R-Pro 2162 and ECU-C only)
- Improved error handling and query efficiency
- Support for L2 and L3 voltages (three-phase inverters)
- Multiple ECU hub support
- Individual inverter online sensors for automations
- Zero Export capability (ECU-C and ECU-3)
- Per-panel maximum power limiting (ECU-R-Pro, ECU-C, ECU-3)
- Zigbee signal strength in dBm

> **Note:**
> For in-dept information about sensors etc. please read the Wiki on this project page.

---

## Prerequisites

- Supported ECU models: ECU-B, ECU-R, ECU-C (with YC600, YC1000/QT2, DS3, QS1 series inverters).
- ECU must be connected to your LAN with a fixed IP address.
- Home Assistant must have network access to the ECU.
- HACS must be installed in Home Assistant.
- Home Assistant log should not show repetitive errors that could cause resource exhaustion.

| Connection Required | ECU Model                  | Automated Restart* |
|---------------------|---------------------------|--------------------|
| Wireless            | ECU-R (2160 series), ECU-B| No                 |
| Wireless/Wired      | ECU-R (2162 series)       | Yes                |
| Wireless/Wired      | ECU-C                     | Yes                |

_ECU-3 owners: See [ha-apc-ecu-3](https://github.com/jeeshofone/ha-apc-ecu-3)_

---

## Wireless ECU Setup

1. **Install EMA Manager**: Download from your app store.
2. **Access Point Mode**: Press and hold the ECU-R button until Wi-Fi starts.
3. **Connect to ECU-R Wi-Fi**: Default password is `88888888`.
4. **Launch EMA Manager**: Choose "Local" connection.
5. **Configure Network**: Connect ECU-R to the same Wi-Fi as Home Assistant.

---

## Testing ECU Connection

Find your ECU on the network (look for "Espressif Inc." or "ESP").  
Test with ping or Netcat:
```
nc -v <ECU_IP> 8899
APS1100160001END
APS11009400012160000xxxxxxxz%10012ECU_R_1.2.22009Etc/GMT-8
```
Assign a fixed IP address to your ECU.

---

## Required Ports

| Domain                | Ports                                      | Protocol |
|-----------------------|--------------------------------------------|----------|
| ecu.apsystemsema.com  | 8995, 8996, 8997, 8998, 9227, 9228, 9001-9004 | TCP      |
| ecu2.apsema.com       | 9220, 9222                                 | TCP      |
| ecu2.apsema.com       | 9219, 21                                   | FTP      |
| ecuna.apsema.com      | 9220, 9222                                 | TCP      |
| ecuna.apsema.com      | 9219, 21                                   | FTP      |
| ecueu.apsema.com      | 9220, 9222                                 | TCP      |
| ecueu.apsema.com      | 9219, 21                                   | FTP      |

---

## Installation

1. **Download via HACS**:
   - Add custom repository: `https://github.com/HAEdwin/homeassistant-apsystems_ecu_reader`
   - Download and restart Home Assistant.
2. **Integrate**:
   - Go to [Settings] > [Devices & Services] > [+ ADD INTEGRATION]
   - Search for "APsystems ECU Reader" and configure with your ECU's IP address.

> **Note:**  
> If you see "No ECU found at this IP-address or ECU is recovering from restart," ensure the ECU has been running for at least 10 minutes.

---

## Configuration Options

- **ECU-IP address**: Enter your assigned ECU IP.
- **Query interval**: Recommended: 300 seconds.
- **Retries**: Number of connection attempts before using cache.
- **Cache count before auto reboot**: For ECU-R-Pro & ECU-C.
- **Update graphs when inverters offline**: On/Off.
- **SSID and Password**: For forced ECU reboot (ECU-R-Pro & ECU-C).

---

## Feature Compatibility

| Type    | Entity                        | ECU-B | ECU-R | ECU-R-Pro | ECU-C | ECU-3 |
|---------|-------------------------------|-------|-------|-----------|-------|-------|
| switch  | ecu_{ECU-ID}_zero_export      | No    | No    | No        | Yes   | Yes   |
| switch  | inverter_{Inverter-ID}_on_off | No    | No    | Yes       | Yes   | Yes   |
| button  | ecu_{ECU-ID}_reboot           | No    | No    | Yes       | Yes   | Yes   |
| number  | inverter_{Inverter-ID}_maxpwr | No    | No    | Yes       | Yes   | Yes   |

---

## Troubleshooting

- If frequent cache usage or crashes occur, check `home-assistant.log` for errors.
- Disable integrations that are causing connection/communication errors.
- Choose the best location for your ECU where it has the best reception for both Zigbee and WiFi.
- Make sure that nothing is blocking the reception of the signals.
- Check if the firmware has been changed.

## Data cache is used if

- The integration cannot connect to the ECU
- Received data is incomplete
- A timeout occurs
- Another error occurs

However, this does not prevent the integration from continuing to function normally.
If you really can't figure it out, create an issue and remember that the more time you spend specifying the problem, the faster and more precise the answer can be.

---

## Temperature Sensors

If inverter temperature returns zero when offline, use a template to convert non-numeric values:
```yaml
template:
  - sensor:
      - name: "Temperature non numeric 4080xxxxxxxx"
        state: "{{ states('sensor.inverter_4080xxxxxxxx_temperature')|float(0) }}"
        unit_of_measurement: "°C"
      - name: "Temperature non numeric 8060xxxxxxxx"
        state: "{{ states('sensor.inverter_8060xxxxxxxx_temperature')|float(0) }}"
        unit_of_measurement: "°C"
```

---

## Additional Resources

- For in-depth information on available sensors, read the [Wiki](https://github.com/HAEdwin/homeassistant-apsystems_ecu_reader/wiki)
- [German Guide](https://smart-home-assistant.de/ap-systems-ecu-b-einbinden)
- [Dutch Guide](https://doe-duurzaam.nl/artikel/je-apsystems-micro-omvormers-slim-uitzetten-via-web-of-home-assistant/#teruglevering-beperken-per-micro-omvormer)

---

## FAQ

**Why is my inverter offline during the day?**  
- Possible Zigbee signal loss or poor reception.  
- Overvoltage due to wiring or grid conditions.

**Why do ECU values differ from EMA values?**  
- Sampling frequency and CT location differences.

**Why can't the integration find my ECU?**  
- Network configuration issues or ECU not running long enough.

---

## Acknowledgements

Developed in collaboration with checking12, ksheumaker, HAEdwin, and the Home Assistant community.  
Special thanks to 12christiaan, ViperRNMC, and all sponsors for their support!
