#!/usr/bin/env python3

import socket
import binascii
import logging
import time

_LOGGER = logging.getLogger(__name__)

class APSystemsInvalidData(Exception):
    pass

class APSystemsSocket:
    def __init__(self, ipaddr, graphs, port=8899, raw_ecu=None, raw_inverter=None):

        self.graphs = graphs
        self.ipaddr = ipaddr
        self.port = port

        # what do we expect socket data to end in
        self.recv_suffix = b'END\n'

        # how long to wait on socket commands until we get our recv_suffix
        self.timeout = 10

        # how big of a buffer to read at a time from the socket
        # https://github.com/ksheumaker/homeassistant-apsystems_ecur/issues/108
        self.recv_size = 1024

        # how long to wait between socket open/closes
        self.socket_sleep_time = 5

        self.ecu_query = "APS1100160001END\n"
        self.inverter_query_prefix = "APS1100280002"
        self.inverter_signal_prefix = "APS1100280030"
        self.ecu_id = None
        self.qty_of_inverters = 0
        self.qty_of_online_inverters = 0
        self.lifetime_energy = 0
        self.current_power = 0
        self.today_energy = 0
        self.inverters = {}
        self.firmware = None
        self.timezone = None
        self.last_update = None
        self.vsl = 0
        self.tsl = 0
        self.ecu_raw_data = raw_ecu
        self.inverter_raw_data = raw_inverter
        self.inverter_raw_signal = None
        self.read_buffer = b''
        self.socket = None
        self.socket_open = False
        self.errors = []


    def open_socket(self, retries=3, delay=1):
        """Open a socket connection with retry logic."""
        if self.socket_open:
            return  # Socket is already open
        attempt = 0
        while attempt < retries:
            try:
                # Create a new socket and set timeout
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.settimeout(self.timeout)
                self.sock.connect((self.ipaddr, self.port))
                self.socket_open = True
                return  # Successful connection, exit function
            except (socket.timeout, socket.gaierror, socket.error) as err:
                attempt += 1
                if attempt < retries:
                    time.sleep(delay)  # Wait before retrying
                else:
                    raise APSystemsInvalidData("Failed to open socket after %s attempts: %s", retries, err)
            except Exception as err:
                raise APSystemsInvalidData(f"Unexpected error while opening socket: {err}")


    def close_socket(self):
        """Close the socket and handle any related exceptions."""
        if not self.socket_open:
            _LOGGER.warning("Socket is already closed or was never opened.")
            return
        try:
            _LOGGER.debug("Closing socket")
            self.sock.shutdown(socket.SHUT_RDWR)
            self.sock.close()
            _LOGGER.debug("Socket successfully closed")
        except socket.error as err:
            # Handle socket-related errors during shutdown or closure
            _LOGGER.error("Error closing socket: %s", err)
            raise APSystemsInvalidData("Socket error during closure: %s", err)
        except Exception as err:
            # Catch any unexpected errors
            _LOGGER.error("Unexpected error while closing socket: %s", err)
        finally:
            # Ensure socket is reset after closing
            self.sock = None
            self.socket_open = False


    def send_read_from_socket(self, cmd):
        try:
            self.sock.settimeout(self.timeout)
            self.sock.sendall(cmd.encode('utf-8'))
            time.sleep(self.socket_sleep_time)
            self.read_buffer = b''
            self.sock.settimeout(self.timeout)
            # An infinite loop was causing the integration to block
            # https://github.com/ksheumaker/homeassistant-apsystems_ecur/issues/115
            # Solution might cause a new issue when large solar array's applies
            self.read_buffer = self.sock.recv(self.recv_size)
            return self.read_buffer
        except Exception as err:
            raise APSystemsInvalidData(err)
        finally:
            # Ensure the socket is closed regardless of success or failure
            self.close_socket()


    def query_ecu(self):
        #read ECU data
        self.open_socket()
        self.ecu_raw_data = self.send_read_from_socket(self.ecu_query)
        try:
            self.process_ecu_data()
        except Exception as err:
            raise APSystemsInvalidData(err)
        
        #read inverter data
        # Some ECUs like the socket to be closed and re-opened between commands
        self.open_socket()
        cmd = self.inverter_query_prefix + self.ecu_id + "END\n"
        self.inverter_raw_data = self.send_read_from_socket(cmd)


        #read signal data
        # Some ECUs like the socket to be closed and re-opened between commands
        self.open_socket()
        cmd = self.inverter_signal_prefix + self.ecu_id + "END\n"
        self.inverter_raw_signal = self.send_read_from_socket(cmd)

        data = self.process_inverter_data()
        data["ecu_id"] = self.ecu_id
        if self.lifetime_energy != 0:
            data["lifetime_energy"] = self.lifetime_energy
        data["current_power"] = self.current_power
        # apply filter for ECU-R-pro firmware bug where both are zero
        if self.qty_of_inverters > 0:
            data["qty_of_inverters"] = self.qty_of_inverters
            data["today_energy"] = self.today_energy
        data["qty_of_online_inverters"] = self.qty_of_online_inverters
        return(data)

    def aps_int_from_bytes(self, codec: bytes, start: int, length: int) -> int:
        try:
            return int (binascii.b2a_hex(codec[(start):(start+length)]), 16)
        except ValueError:
            debugdata = binascii.b2a_hex(codec)
            error = f"Unable to convert binary to int with length={length} at location={start} with data={debugdata}"
            raise APSystemsInvalidData(error)

    def aps_uid(self, codec, start):
        return str(binascii.b2a_hex(codec[(start):(start+12)]))[2:14]
    
    def aps_str(self, codec, start, amount):
        return str(codec[start:(start+amount)])[2:(amount+2)]
    
    def aps_datetimestamp(self, codec, start, amount):
        timestr=str(binascii.b2a_hex(codec[start:(start+amount)]))[2:(amount+2)]
        return timestr[0:4]+"-"+timestr[4:6]+"-"+timestr[6:8]+" "+timestr[8:10]+":"+timestr[10:12]+":"+timestr[12:14]

    def check_ecu_checksum(self, data, cmd):
        datalen = len(data) - 1
        try:
            checksum = int(data[5:9])
        except ValueError:
            debugdata = binascii.b2a_hex(data)
            error = f"could not extract checksum int from '{cmd}' data={debugdata}"
            raise APSystemsInvalidData(error)

        if datalen != checksum:
            debugdata = binascii.b2a_hex(data)
            error = f"Checksum on '{cmd}' failed checksum={checksum} datalen={datalen} data={debugdata}"
            raise APSystemsInvalidData(error)

        start_str = self.aps_str(data, 0, 3)
        end_str = self.aps_str(data, len(data) - 4, 3)

        if start_str != 'APS':
            debugdata = binascii.b2a_hex(data)
            error = f"Result on '{cmd}' incorrect start signature '{start_str}' != APS data={debugdata}"
            raise APSystemsInvalidData(error)

        if end_str != 'END':
            debugdata = binascii.b2a_hex(data)
            error = f"Result on '{cmd}' incorrect end signature '{end_str}' != END data={debugdata}"
            raise APSystemsInvalidData(error)

        return True

    def process_ecu_data(self, data=None):
        if self.ecu_raw_data != '' and (self.aps_str(self.ecu_raw_data,9,4)) == '0001':
            data = self.ecu_raw_data
            _LOGGER.debug(binascii.b2a_hex(data))
            self.check_ecu_checksum(data, "ECU Query")
            self.ecu_id = self.aps_str(data, 13, 12)
            self.lifetime_energy = self.aps_int_from_bytes(data, 27, 4) / 10
            self.current_power = self.aps_int_from_bytes(data, 31, 4)
            self.today_energy = self.aps_int_from_bytes(data, 35, 4) / 100
            if self.aps_str(data,25,2) == "01":
                self.qty_of_inverters = self.aps_int_from_bytes(data, 46, 2)
                self.qty_of_online_inverters = self.aps_int_from_bytes(data, 48, 2)
                self.vsl = int(self.aps_str(data, 52, 3))
                self.firmware = self.aps_str(data, 55, self.vsl)
                self.tsl = int(self.aps_str(data, 55 + self.vsl, 3))
                self.timezone = self.aps_str(data, 58 + self.vsl, self.tsl)
            elif self.aps_str(data,25,2) == "02":
                self.qty_of_inverters = self.aps_int_from_bytes(data, 39, 2)
                self.qty_of_online_inverters = self.aps_int_from_bytes(data, 41, 2)
                self.vsl = int(self.aps_str(data, 49, 3))
                self.firmware = self.aps_str(data, 52, self.vsl)

#    def process_signal_data(self, data=None):
#        signal_data = {}
#        if self.inverter_raw_signal != '' and (self.aps_str(self.inverter_raw_signal,9,4)) == '0030':
#            data = self.inverter_raw_signal
#            _LOGGER.debug(binascii.b2a_hex(data))
#            self.check_ecu_checksum(data, "Signal Query")
#            if not self.qty_of_inverters:
#                return signal_data
#            location = 15
#            for i in range(0, self.qty_of_inverters):
#                uid = self.aps_uid(data, location)
#                location += 6
#                strength = data[location]
#                location += 1
#                strength = int((strength / 255) * 100)
#                signal_data[uid] = strength
#            return signal_data


    def process_signal_data(self, data=None):
        signal_data = {}

        # Check if inverter raw signal is valid and matches expected pattern
        if self.inverter_raw_signal and (self.aps_str(self.inverter_raw_signal, 9, 4)) == '0030':
            data = self.inverter_raw_signal  # Use raw signal data if not provided

            _LOGGER.debug(binascii.b2a_hex(data))  # Log data in hexadecimal form
            self.check_ecu_checksum(data, "Signal Query")  # Check ECU checksum

            # Return early if no inverters are available
            if not self.qty_of_inverters:
                _LOGGER.warning("No inverters to process")
                return signal_data

            # Ensure that the data has enough length to process
            expected_length = 15 + (self.qty_of_inverters * 6)  # Based on the loop logic (15 + 6 per inverter)
            if len(data) < expected_length:
                _LOGGER.error(f"Data length {len(data)} is shorter than expected {expected_length}")
                return signal_data

            # Iterate over inverters and process their signal strengths
            location = 15  # Start from the 15th byte after the header
            for i in range(self.qty_of_inverters):
                # Extract the unique identifier (UID) and strength
                uid = self.aps_uid(data, location)
                location += 6  # Move to next location for next inverter

                strength = data[location]  # Get strength byte
                location += 1  # Move to next byte

                # Calculate strength as a percentage (0-100)
                strength_percentage = int((strength / 255) * 100)
                signal_data[uid] = strength_percentage

            # Return the processed signal data
            return signal_data

        else:
            _LOGGER.warning("Invalid inverter signal or data format mismatch")
            return signal_data


    def process_inverter_data(self, data=None):
        output = {}
        if self.inverter_raw_data != '' and (self.aps_str(self.inverter_raw_data,9,4)) == '0002':
            data = self.inverter_raw_data
            _LOGGER.debug(binascii.b2a_hex(data))
            self.check_ecu_checksum(data, "Inverter data")
            istr = ''
            cnt1 = 0
            cnt2 = 26
            if self.aps_str(data, 14, 2) == '00':
                timestamp = self.aps_datetimestamp(data, 19, 14)
                inverter_qty = self.aps_int_from_bytes(data, 17, 2)
                self.last_update = timestamp
                output["timestamp"] = timestamp
                output["inverters"] = {}
                signal = self.process_signal_data()
                inverters = {}
                
                while cnt1 < inverter_qty:
                    inv={}
                    if self.aps_str(data, 15, 2) == '01':
                        inverter_uid = self.aps_uid(data, cnt2)
                        inv["uid"] = inverter_uid
                        inv["online"] = bool(self.aps_int_from_bytes(data, cnt2 + 6, 1))
                        istr = self.aps_str(data, cnt2 + 7, 2)
                        _LOGGER.warning("graphs is: %s", self.graphs)
                        # Should graphs be updated?
                        if not inv["online"] and self.graphs:
                            inv["signal"] = None
                        else:
                            inv["signal"] = signal.get(inverter_uid, 0)
                       
                        # Distinguishes the different inverters from this point down
                        if istr in [ '01', '04', '05']:
                            power = []
                            voltages = []

                            # Should graphs be updated? 
                            if inv["online"]:
                                inv["temperature"] = self.aps_int_from_bytes(data, cnt2 + 11, 2) - 100
                            _LOGGER.warning("graphs is: %s", self.graphs)
                            if not inv["online"] and self.graphs:
                                inv["frequency"] = None
                                power.append(None)
                                voltages.append(None)
                                power.append(None)
                                voltages.append(None)
                            else:
                                inv["frequency"] = self.aps_int_from_bytes(data, cnt2 + 9, 2) / 10
                                power.append(self.aps_int_from_bytes(data, cnt2 + 13, 2))
                                voltages.append(self.aps_int_from_bytes(data, cnt2 + 15, 2))
                                power.append(self.aps_int_from_bytes(data, cnt2 + 17, 2))
                                voltages.append(self.aps_int_from_bytes(data, cnt2 + 19, 2))

                            inv_details = {
                            "model" : "YC600/DS3 series",
                            "channel_qty" : 2,
                            "power" : power,
                            "voltage" : voltages
                            }
                            inv.update(inv_details)
                            cnt2 = cnt2 + 21
                        elif istr == '02':
                            power = []
                            voltages = []

                            # Should graphs be updated? 
                            if inv["online"]:
                                inv["temperature"] = self.aps_int_from_bytes(data, cnt2 + 11, 2) - 100
                            _LOGGER.warning("graphs is: %s", self.graphs)
                            if not inv["online"] and self.graphs:
                                inv["frequency"] = None
                                power.append(None)
                                voltages.append(None)
                                power.append(None)
                                voltages.append(None)
                                power.append(None)
                                voltages.append(None)
                                power.append(None)
                            else:
                                inv["frequency"] = self.aps_int_from_bytes(data, cnt2 + 9, 2) / 10
                                power.append(self.aps_int_from_bytes(data, cnt2 + 13, 2))
                                voltages.append(self.aps_int_from_bytes(data, cnt2 + 15, 2))
                                power.append(self.aps_int_from_bytes(data, cnt2 + 17, 2))
                                voltages.append(self.aps_int_from_bytes(data, cnt2 + 19, 2))
                                power.append(self.aps_int_from_bytes(data, cnt2 + 21, 2))
                                voltages.append(self.aps_int_from_bytes(data, cnt2 + 23, 2))
                                power.append(self.aps_int_from_bytes(data, cnt2 + 25, 2))

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
                                inv["temperature"] = self.aps_int_from_bytes(data, cnt2 + 11, 2) - 100
                            _LOGGER.warning("graphs is: %s", self.graphs)
                            if not inv["online"] and self.graphs:
                                inv["frequency"] = None
                                power.append(None)
                                voltages.append(None)
                                power.append(None)
                                power.append(None)
                                power.append(None)
                            else:
                                inv["frequency"] = self.aps_int_from_bytes(data, cnt2 + 9, 2) / 10
                                power.append(self.aps_int_from_bytes(data, cnt2 + 13, 2))
                                voltages.append(self.aps_int_from_bytes(data, cnt2 + 15, 2))
                                power.append(self.aps_int_from_bytes(data, cnt2 + 17, 2))
                                power.append(self.aps_int_from_bytes(data, cnt2 + 19, 2))
                                power.append(self.aps_int_from_bytes(data, cnt2 + 21, 2))

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
                return (output)
