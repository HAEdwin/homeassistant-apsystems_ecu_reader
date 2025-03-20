#!/usr/bin/env python3

"""  ecu_api.py """

import asyncio
import socket
import logging

from .ecu_helpers import (
    aps_datetimestamp,
    aps_str,
    aps_int_from_bytes,
    aps_uid,
    validate_data
)

_LOGGER = logging.getLogger(__name__)

class APsystemsInvalidData(Exception):
    """ Exception for invalid data from the APsystems ECU."""

class APsystemsSocket:
    """ Class to handle the socket connection to the APsystems ECU. """
    def __init__(self, ipaddr, raw_ecu=None, raw_inverter=None, timeout=5):

        self.ipaddr = ipaddr

        # how long to wait for response on socket commands
        self.timeout = timeout
        # how big of a buffer to read at a time from the socket
        self.recv_size = 1024

        self.ecu_cmd = "APS1100160001END\n"
        self.inverter_query_prefix = "APS1100280002"
        self.signal_query_prefix = "APS1100280030"
        self.ecu_raw_data = raw_ecu
        self.inverter_raw_data = raw_inverter
        self.signal_raw_data = None
        self.qty_of_inverters = 0
        self.qty_of_online_inverters = 0
        self.lifetime_energy = 0
        self.current_power = 0
        self.today_energy = 0
        self.vsl = 0
        self.tsl = 0
        self.inverters = {}
        self.data = {}
        self.ecu_id = None
        self.firmware = None
        self.timezone = None
        self.last_update = None
        self.read_buffer = None
        self.sock = None

    async def open_socket(self, port_retries, delay=1):
        """ Open a socket to the ECU. """
        for attempt in range(1, port_retries + 1):
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            try:
                sock.connect((self.ipaddr, 8899))
                self.sock = sock  # Assign the successfully opened socket
                _LOGGER.debug("Socket successfully claimed")
                return
            except (socket.timeout, socket.gaierror, socket.error) as err:
                _LOGGER.debug("Socket claim attempt %s/%s failed: %s", attempt, port_retries, err)
                await asyncio.sleep(delay)  # Wait before retrying
            except Exception as err:
                _LOGGER.error("An unexpected error occurred: %s", err, exc_info=True)
                await self.close_socket()
                raise APsystemsInvalidData(str(err)) from err
        raise APsystemsInvalidData(
            f"failure to claim socket after {port_retries} attempts, using cached data"
            )


    async def send_read_from_socket(self, cmd):
        """ Send command to the socket and read the response. """
        try:
            self.sock.settimeout(self.timeout)  # Set timeout once
            self.sock.sendall(cmd.encode('utf-8'))  # Send command
            # Read the response asynchronously to prevent blocking
            self.read_buffer = await asyncio.to_thread(self.sock.recv, self.recv_size)
            return self.read_buffer, None
        except socket.timeout:
            # Handle timeout specifically
            await self.close_socket()
            return None, "timeout occurred while reading from socket\n"
        except ConnectionResetError:
            # Handle connection reset error
            await self.close_socket()
            return None, "Connection reset by peer\n"
        except BrokenPipeError:
            # Handle broken pipe (connection closed by peer)
            await self.close_socket()
            return None, "Connection closed by peer\n"
        except asyncio.CancelledError:
            # Handle the case when the task is cancelled
            await self.close_socket()
            return None, "Operation was cancelled\n"
        except OSError as err:
            # Handle general socket errors
            await self.close_socket()
            return None, f"General OS error occurred: {err}\n"

    async def close_socket(self):
        """ Ensure created and allocated resources are properly cleaned up. """
        if self.sock is not None:
            try:
                self.sock.shutdown(socket.SHUT_RDWR)
                self.sock.close()
                self.sock = None
                _LOGGER.debug("Socket resources released")
            except (OSError, socket.error) as err:
                _LOGGER.warning("Socket shutdown error: %s", err)


    async def query_ecu(self, port_retries, show_graphs):
        """ 
        Query the ECU for data and return it.
        In contrast to ECU 2160 models, the 2162 models require an
        open and close on the port between the individual  queries.
        The best generic solution is to now do this for all models.
        """
        # ECU base query
        await self.open_socket(port_retries)
        self.ecu_raw_data, status = await self.send_read_from_socket(self.ecu_cmd)
        await self.close_socket()
        if status or not self.ecu_raw_data:
            raise APsystemsInvalidData(
                f"querying ECU where status is: {status}"
                if status
                else "querying ECU where received data is none"
            )

        # Extract ECU-ID needed for other queries
        self.ecu_id = aps_str(self.ecu_raw_data, 13, 12)

        # Inverter query
        inverter_cmd = self.inverter_query_prefix + self.ecu_id + "END\n"
        await self.open_socket(port_retries)
        self.inverter_raw_data, status = await self.send_read_from_socket(inverter_cmd)
        await self.close_socket()
        _LOGGER.debug("Inverter raw data: %s", self.inverter_raw_data.hex())
        if status or not self.inverter_raw_data or len(self.inverter_raw_data) < 40:
            raise APsystemsInvalidData(
                f"querying inverter. Status is: "
                f"{status or 'incomplete inverter data received due to ECU recovery'}"
            )

        # Signal query
        signal_cmd = self.signal_query_prefix + self.ecu_id + "END\n"
        await self.open_socket(port_retries)
        self.signal_raw_data, status = await self.send_read_from_socket(signal_cmd)
        await self.close_socket()
        _LOGGER.debug("Signal raw data: %s", self.signal_raw_data.hex())
        if status or not self.signal_raw_data:
            _LOGGER.warning("an error occurred while querying signal where status is: %s", status)

        # Finally all went right so call finalize and return it
        self.process_ecu_data()
        return self.finalize_data(show_graphs)


    def finalize_data(self, show_graphs):
        """ Finalize the data and return it. """
        try:
            self.data["ecu_id"] = self.ecu_id
            self.data["last_update"] = self.last_update
            self.data["current_power"] = self.current_power
            self.data["qty_of_online_inverters"] = self.qty_of_online_inverters

            # apply filters for ECU firmware bug where sometimes values are zero
            if self.qty_of_inverters:
                self.data["qty_of_inverters"] = self.qty_of_inverters
            if (
                self.today_energy != 0 or
                (self.today_energy == 0 and self.qty_of_online_inverters == 0)
            ):
                self.data["today_energy"] = self.today_energy
            if self.lifetime_energy:
                self.data["lifetime_energy"] = self.lifetime_energy

            # Add inverter and signal data to the dictionary
            self.data.update(self.process_inverter_data(show_graphs))

            return self.data
        except Exception as err:
            raise APsystemsInvalidData(f"finalization: {err}") from err


    def process_ecu_data(self, data=None):
        """  interpret raw ecu data and return it. """
        if self.ecu_raw_data and (aps_str(self.ecu_raw_data, 9, 4)) == '0001':
            data = self.ecu_raw_data
            error = validate_data(data, "ECU Query")
            if error:
                raise APsystemsInvalidData(error)

            self.ecu_id = aps_str(data, 13, 12)
            self.lifetime_energy = aps_int_from_bytes(data, 27, 4) / 10
            self.current_power = aps_int_from_bytes(data, 31, 4)
            self.today_energy = aps_int_from_bytes(data, 35, 4) / 100
            if aps_str(data, 25, 2) == "01":
                self.qty_of_inverters = aps_int_from_bytes(data, 46, 2)
                self.qty_of_online_inverters = aps_int_from_bytes(data, 48, 2)
                self.vsl = int(aps_str(data, 52, 3))
                self.firmware = aps_str(data, 55, self.vsl)
                self.tsl = int(aps_str(data, 55 + self.vsl, 3))
                self.timezone = aps_str(data, 58 + self.vsl, self.tsl)
            elif aps_str(data,25,2) == "02":
                self.qty_of_inverters = aps_int_from_bytes(data, 39, 2)
                self.qty_of_online_inverters = aps_int_from_bytes(data, 41, 2)
                self.vsl = int(aps_str(data, 49, 3))
                self.firmware = aps_str(data, 52, self.vsl)


    def process_signal_data(self, data=None):
        """ interpret raw signal data and return it. """	
        signal_data = {}
        if self.signal_raw_data and (aps_str(self.signal_raw_data,9,4)) == '0030':
            data = self.signal_raw_data
            error = validate_data(data, "Signal Query")
            if error:
                raise APsystemsInvalidData(error)
            if not self.qty_of_inverters:
                return signal_data
            location = 15
            for _ in range(self.qty_of_inverters):
                inverter_uid = aps_uid(data, location, 12)
                location += 6
                signal_strength = data[location]
                location += 1
                signal_strength = int(-100 + (signal_strength / 255) * 100)
                signal_data[inverter_uid] = signal_strength
        return signal_data


    def process_inverter_data(self, show_graphs, data=None):
        """ interpret raw inverter data and return it. """
        output = {}
        if self.inverter_raw_data != '' and (aps_str(self.inverter_raw_data,9,4)) == '0002':
            data = self.inverter_raw_data
            error = validate_data(data, "Inverter Query")
            if error:
                raise APsystemsInvalidData(error)
            istr = ''
            cnt1 = 0
            cnt2 = 26
            if aps_str(data, 14, 2) == '00':
                timestamp = aps_datetimestamp(data, 19, 14)
                inverter_qty = aps_int_from_bytes(data, 17, 2)
                self.last_update = timestamp
                output["timestamp"] = timestamp
                output["inverters"] = {}
                signal = self.process_signal_data()
                inverters = {}

                while cnt1 < inverter_qty:
                    inv={}
                    if aps_str(data, 15, 2) == '01':
                        inverter_uid = aps_uid(data, cnt2)
                        inv["uid"] = inverter_uid
                        inv["online"] = bool(aps_int_from_bytes(data, cnt2 + 6, 1))
                        istr = aps_str(data, cnt2 + 7, 2) #inverter type

                        # Should the signal graphs be updated?
                        inv["signal"] = (
                            None if not inv["online"]
                            else signal.get(inverter_uid, 0)
                        )

                        # Distinguishes the different inverters from this point down
                        if istr in [ '01', '04', '05']: #01 (=YC600/DS3) 04 (=DS3D-L) 05 (=DS3-H)
                            power = []
                            voltages = []

                            # Should graphs be updated?
                            if inv["online"]:
                                inv["temperature"] = aps_int_from_bytes(data, cnt2 + 11, 2) - 100

                            if not inv["online"] and not show_graphs:
                                inv["frequency"] = None
                                power.extend([None, None])
                                voltages.extend([None, None])
                            else:
                                inv["frequency"] = aps_int_from_bytes(data, cnt2 + 9, 2) / 10
                                power.append(aps_int_from_bytes(data, cnt2 + 13, 2))
                                voltages.append(aps_int_from_bytes(data, cnt2 + 15, 2))
                                power.append(aps_int_from_bytes(data, cnt2 + 17, 2))

                            inv_details = {
                            "model" : "YC600/DS3 series",
                            "channel_qty" : 2,
                            "power" : power,
                            "voltage" : voltages
                            }
                            inv.update(inv_details)
                            cnt2 = cnt2 + 21
                        elif istr == '02': #YC1000/QT2 3 phase inverters
                            power = []
                            voltages = []

                            # Should graphs be updated?
                            if inv["online"]:
                                inv["temperature"] = aps_int_from_bytes(data, cnt2 + 11, 2) - 100

                            if not inv["online"] and not show_graphs:
                                inv["frequency"] = None
                                power.extend([None, None, None, None])
                                voltages.extend([None, None, None])
                            else:
                                inv["frequency"] = aps_int_from_bytes(data, cnt2 + 9, 2) / 10
                                power.append(aps_int_from_bytes(data, cnt2 + 13, 2))
                                voltages.append(aps_int_from_bytes(data, cnt2 + 15, 2))
                                power.append(aps_int_from_bytes(data, cnt2 + 17, 2))
                                voltages.append(aps_int_from_bytes(data, cnt2 + 19, 2))
                                power.append(aps_int_from_bytes(data, cnt2 + 21, 2))
                                voltages.append(aps_int_from_bytes(data, cnt2 + 23, 2))
                                power.append(aps_int_from_bytes(data, cnt2 + 25, 2))

                            inv_details = {
                            "model" : "YC1000/QT2",
                            "channel_qty" : 4,
                            "power" : power,
                            "voltage" : voltages
                            }
                            inv.update(inv_details)
                            cnt2 = cnt2 + 27
                        elif istr == '03':
                            power = []
                            voltages = []

                            # Should graphs be updated?
                            if inv["online"]:
                                inv["temperature"] = aps_int_from_bytes(data, cnt2 + 11, 2) - 100
                            if not inv["online"] and not show_graphs:
                                inv["frequency"] = None
                                voltages.append(None)
                                power.extend([None, None, None, None])
                            else:
                                inv["frequency"] = aps_int_from_bytes(data, cnt2 + 9, 2) / 10
                                power.append(aps_int_from_bytes(data, cnt2 + 13, 2))
                                voltages.append(aps_int_from_bytes(data, cnt2 + 15, 2))
                                power.append(aps_int_from_bytes(data, cnt2 + 17, 2))
                                power.append(aps_int_from_bytes(data, cnt2 + 19, 2))
                                power.append(aps_int_from_bytes(data, cnt2 + 21, 2))

                            inv_details = {
                            "model" : "QS1",
                            "channel_qty" : 4,
                            "power" : power,
                            "voltage" : voltages
                            }
                            inv.update(inv_details)
                            cnt2 = cnt2 + 23
                        else:
                            cnt2 = cnt2 + 9
                        inverters[inverter_uid] = inv
                    cnt1 = cnt1 + 1
                self.inverters = inverters
                output["inverters"] = inverters
                return output
