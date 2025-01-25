#!/usr/bin/env python3
""" Module to handle the socket connection to the APsystems ECU """

import asyncio
import socket
import binascii
import logging

from .helper import (
    aps_datetimestamp,
    aps_str,
    aps_int_from_bytes,
    aps_uid,
    validate_ecu_data
)

_LOGGER = logging.getLogger(__name__)

class APsystemsInvalidData(Exception):
    ''' Exception for invalid data from the APsystems ECU '''

class APsystemsSocket:
    ''' Class to handle the socket connection to the APsystems ECU '''
    def __init__(self, ipaddr, raw_ecu=None, raw_inverter=None, timeout=10):

        self.ipaddr = ipaddr
        self.data = {}

        # how long to wait on socket commands until we get our recv_suffix
        self.timeout = timeout

        # how big of a buffer to read at a time from the socket
        self.recv_size = 1024

        self.ecu_cmd = "APS1100160001END\n"
        self.inverter_query_prefix = "APS1100280002"
        self.signal_query_prefix = "APS1100280030"
        self.recv_suffix = b'END\n'
        self.ecu_id = None
        self.qty_of_inverters = 0
        self.qty_of_online_inverters = 0
        self.lifetime_energy = 0
        self.current_power = 0
        self.today_energy = 0
        self.inverters = {}
        self.data = {}
        self.firmware = None
        self.timezone = None
        self.last_update = None
        self.vsl = 0
        self.tsl = 0
        self.ecu_raw_data = raw_ecu
        self.inverter_raw_data = raw_inverter
        self.inverter_raw_signal = None
        self.read_buffer = b''
        self.sock = None
        self.socket_open = False


    async def open_socket(self, port_retries, delay=1):
        ''' Open a socket to the ECU '''
        for attempt in range(1, port_retries + 1):
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            try:
                sock.connect((self.ipaddr, 8899))
                self.sock = sock  # Assign the successfully opened socket
                self.socket_open = True
                _LOGGER.warning("Socket successfully claimed")
                return
            except (socket.timeout, socket.gaierror, socket.error) as err:
                _LOGGER.warning("Attempt %s/%s failed: %s", attempt, port_retries, err)
                await asyncio.sleep(delay)  # Wait before retrying
            except Exception as err:
                _LOGGER.error("An unexpected error occurred: %s", err, exc_info=True)
                if self.sock is not None:
                    await self.close_socket()
                raise APsystemsInvalidData(str(err)) from err
        raise APsystemsInvalidData(
            f"Failed to claim socket after {port_retries} attempts, using cached data"
            )


    async def send_read_from_socket(self, cmd):
        ''' Send command to the socket and read the response '''
        try:
            self.sock.settimeout(self.timeout)  # Set timeout once
            self.sock.sendall(cmd.encode('utf-8'))  # Send command
            # Read the response asynchronously to prevent blocking
            self.read_buffer = await asyncio.to_thread(self.sock.recv, self.recv_size)
            return self.read_buffer, "Ok"
        except socket.timeout:
            # Handle timeout specifically
            await self.close_socket()
            # Raise APsystemsInvalidData("Timeout occurred while reading from socket\n")
            return None, "Timeout occurred while reading from socket\n"

    async def close_socket(self):
        ''' Ensure created and allocated resources are properly cleaned up '''
        if self.sock is not None:
            try:
                self.sock.shutdown(socket.SHUT_RDWR)
                self.sock.close()
                self.socket_open = False
                self.sock = None
                _LOGGER.warning("Socket resources released")
            except (OSError, socket.error) as err:
                _LOGGER.warning("Socket shutdown error: %s", err)


    async def query_ecu(self, port_retries, show_graphs):
        ''' Query the ECU for data and return it
        In contrast to ECU 2160 models, the 2162 models require an
        open and close of the port between the individual  queries.
        The best generic solution is to now do this for all models.
        '''
        # ECU base query
        await self.open_socket(port_retries)
        self.ecu_raw_data, status = await self.send_read_from_socket(self.ecu_cmd)
        if status != "Ok" or not self.ecu_raw_data:
            raise APsystemsInvalidData(f"Error occurred while querying ECU: {status}")
        _LOGGER.warning("ECU raw data: %s", self.ecu_raw_data.hex())
        self.process_ecu_data() # extract ECU-ID for other queries
        await self.close_socket()

        # Inverter query
        await self.open_socket(port_retries)
        inverter_cmd = self.inverter_query_prefix + self.ecu_id + "END\n"
        self.inverter_raw_data, status = await self.send_read_from_socket(inverter_cmd)
        _LOGGER.warning("Inverter raw data: %s", self.inverter_raw_data.hex())
        if status != "Ok" or not self.inverter_raw_data:
            _LOGGER.warning("Error occurred while querying inverter: %s", status)
            # return valid datapart (ecu data)
            return self.finalize_data(show_graphs)
        await self.close_socket()

       # Signal query
        await self.open_socket(port_retries)
        signal_cmd = self.signal_query_prefix + self.ecu_id + "END\n"
        self.inverter_raw_signal, status = await self.send_read_from_socket(signal_cmd)
        if status != "Ok" or not self.inverter_raw_signal:
            _LOGGER.warning("Error occurred while querying signal: %s", status)
            # return valid datapart (ecu data + inverter data)
            return self.finalize_data(show_graphs)
        _LOGGER.warning("Signal raw data: %s", self.inverter_raw_signal.hex())
        await self.close_socket()

        # call the method to finalize the data and return it
        return self.finalize_data(show_graphs)

    def finalize_data(self, show_graphs):
        ''' Finalize the data and return it '''
        if self.inverter_raw_data:
            self.data = self.process_inverter_data(show_graphs)
            # Finalize and bugfix the data into a single dict to return

        self.data["ecu_id"] = self.ecu_id
        self.data["last_update"] = self.last_update
        if self.lifetime_energy != 0:
            self.data["lifetime_energy"] = self.lifetime_energy
        self.data["current_power"] = self.current_power

        # apply filter for ECU-R-pro firmware bug where both are zero
        if self.qty_of_inverters > 0:
            self.data["qty_of_inverters"] = self.qty_of_inverters
            self.data["today_energy"] = self.today_energy
        self.data["qty_of_online_inverters"] = self.qty_of_online_inverters
        _LOGGER.warning("data: %s\n\n", self.data)
        return self.data


    def process_ecu_data(self, data=None):
        '''  interpret raw ecu data and return it '''
        if self.ecu_raw_data and (aps_str(self.ecu_raw_data, 9, 4)) == '0001':
            data = self.ecu_raw_data
            _LOGGER.debug(binascii.b2a_hex(data))
            validate_ecu_data(data, "ECU Query")
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
        ''' interpret raw signal data and return it '''
        signal_data = {}
        if self.inverter_raw_signal and (aps_str(self.inverter_raw_signal,9,4)) == '0030':
            data = self.inverter_raw_signal
            _LOGGER.debug(binascii.b2a_hex(data))
            validate_ecu_data(data, "Signal Query")
            if not self.qty_of_inverters:
                return signal_data
            location = 15
            for _ in range(self.qty_of_inverters):
                inverter_uid = aps_uid(data, location, 12)
                location += 6
                signal_strength = data[location]
                location += 1
                signal_strength = int((signal_strength / 255) * 100)
                signal_data[inverter_uid] = signal_strength
        return signal_data


    def process_inverter_data(self, show_graphs, data=None):
        ''' interpret raw inverter data and return it '''
        output = {}
        if self.inverter_raw_data != '' and (aps_str(self.inverter_raw_data,9,4)) == '0002':
            data = self.inverter_raw_data
            _LOGGER.debug(binascii.b2a_hex(data))
            validate_ecu_data(data, "Inverter data")
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

                        # Should graphs be updated?

                        inv["signal"] = (
                            None if not inv["online"] and not show_graphs
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
