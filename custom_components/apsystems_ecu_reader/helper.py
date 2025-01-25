""" helper.py """

import binascii


class APsystemsInvalidData(Exception):
    """ Exception for invalid data """


def aps_str(codec, start, amount):
    """ Extract a string from a binary string """
    return codec[start:(start+amount)].decode('utf-8')


def aps_datetimestamp(codec, start, amount):
    """ Extract a date and time from a binary string """	
    timestr = codec[start:start+amount].hex()
    return (
        f"{timestr[0:4]}-{timestr[4:6]}-{timestr[6:8]} "
        f"{timestr[8:10]}:{timestr[10:12]}:{timestr[12:14]}"
    )


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


def validate_ecu_data(data, cmd):
    """ Validate the data received from the ECU """
    # Checksum is the length of the data minus 1
    datalen = len(data) - 1
    try:
        checksum = int(data[5:9])
    except ValueError as e:
        debugdata = binascii.b2a_hex(data).decode('ascii')
        error = f"Could not extract checksum int from '{cmd}' data={debugdata}"
        raise APsystemsInvalidData(error) from e

    if datalen != checksum:
        debugdata = binascii.b2a_hex(data).decode('ascii')
        error = f"Checksum on '{cmd}' failed checksum={checksum} datalen={datalen} data={debugdata}"
        raise APsystemsInvalidData(error)

    # Check start and end signature
    start_str = aps_str(data, 0, 3)
    end_str = aps_str(data, len(data) - 4, 3)

    if start_str != 'APS':
        debugdata = binascii.b2a_hex(data).decode('ascii')
        error = f"Result on '{cmd}' incorrect start signature '{start_str}' != APS data={debugdata}"
        raise APsystemsInvalidData(error)

    if end_str != 'END':
        debugdata = binascii.b2a_hex(data)
        error = f"Result on '{cmd}' incorrect end signature '{end_str}' != END data={debugdata}"
        raise APsystemsInvalidData(error)

    return True
