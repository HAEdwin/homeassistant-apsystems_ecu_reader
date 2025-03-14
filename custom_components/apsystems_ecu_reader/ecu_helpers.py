""" helper.py """

import logging
import binascii

_LOGGER = logging.getLogger(__name__)

class APsystemsInvalidData(Exception):
    """ Exception for invalid data """


def aps_str(codec: bytes, start: int, amount: int) -> str:
    """ Extract a string from a binary string """
    try:
        return codec[start:(start+amount)].decode('utf-8')
    except IndexError as e:
        error = (
            f"Invalid slice: start={start}, amount={amount}, "
            f"codec_length={len(codec)}"
        )
        raise APsystemsInvalidData(error) from e


def aps_datetimestamp(codec: bytes, start: int, amount: int) -> str:
    """ Extract a date and time from a binary string """	
    try:
        timestr = codec[start:start+amount].hex()
        return (
            f"{timestr[0:4]}-{timestr[4:6]}-{timestr[6:8]} "
            f"{timestr[8:10]}:{timestr[10:12]}:{timestr[12:14]}"
        )
    except IndexError as e:
        error = (
            f"Invalid slice: start={start}, amount={amount}, "
            f"codec_length={len(codec)}"
        )
        raise APsystemsInvalidData(error) from e


def aps_int_from_bytes(codec: bytes, start: int, length: int) -> int:
    """ Extract an integer from a binary string """	
    try:
        return int.from_bytes(codec[start:start + length], byteorder='big')
    except (IndexError, ValueError, Exception) as e:
        # Handle invalid slice or conversion
        debugdata = codec[start:start + length]
        error = (
            f"Unable to convert binary to int at position {start}, "
            f"length {length}, data={debugdata.hex()} "
            f"due to {str(e)}"
        )
        raise APsystemsInvalidData(error) from e


def aps_uid(codec: bytes, start: int, length: int = 12) -> str:
    """ Extract a UID from a binary	string """
    try:
        return codec[start:start + length].hex()[:12]
    except (IndexError, ValueError, Exception) as e:
        error = f"Invalid slice: start={start}, length={length}, codec_length={len(codec)}"
        raise APsystemsInvalidData(error) from e


def validate_data(data: bytes, cmd: str) -> str:
    """ Validate the data received from the ECU """
    datalen = len(data) - 1
    debugdata = binascii.b2a_hex(data).decode('ascii')
    # Validate checksum extraction
    try:
        checksum = int(data[5:9])
    except ValueError:
        return f"extracting checksum from '{cmd}': data={debugdata}"
    # Validate checksum against data length
    if len(data) - 1 != checksum:
        return f"checksum error on '{cmd}': checksum={checksum} datalen={datalen} data={debugdata}"
    # Validate start and end signature
    if aps_str(data, 0, 3) != 'APS' or aps_str(data, len(data) - 4, 3) != 'END':
        return f"signature error on '{cmd}': data={debugdata}"

    return ""
