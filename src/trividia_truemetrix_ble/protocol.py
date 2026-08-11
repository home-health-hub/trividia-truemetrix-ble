"""Pure decoding functions for the standard Bluetooth Glucose Profile.

No I/O here -- everything in this module is a pure function over raw
bytes, decoding the standard Glucose Measurement (0x2A18) characteristic
per the Bluetooth SIG Glucose Profile spec (IEEE 11073-10101 record
format, IEEE 11073-20601 SFLOAT encoding for the concentration field).

TRUE METRIX AIR was confirmed to speak this standard format byte-exact
via a live GATT capture against real hardware -- see README.md's
Protocol notes section. The test vectors in tests/test_protocol.py are
real notification payloads from that capture, not synthetic data.
"""

from __future__ import annotations

import datetime

from .const import (
    FLAG_CONCENTRATION_UNITS_MOL_L,
    FLAG_GLUCOSE_CONCENTRATION_PRESENT,
    FLAG_TIME_OFFSET_PRESENT,
    KG_PER_L_TO_MG_PER_DL,
    SAMPLE_LOCATIONS,
    SAMPLE_TYPES,
)
from .data import Reading

#: Glucose concentration in mol/L, per the spec's alternate unit flag,
#: converted to mg/dL using glucose's molar mass (180.156 g/mol). Not
#: observed from real hardware (TRUE METRIX AIR always uses kg/L) --
#: included for spec completeness, since other Glucose Profile devices
#: may set this flag.
MOL_PER_L_GLUCOSE_TO_MG_PER_DL = 18015.6

#: Control-solution markers in the Type/Sample Location octet, per the
#: Bluetooth SIG assigned numbers.
_CONTROL_SOLUTION_TYPE = 10
_CONTROL_SOLUTION_LOCATION = 4


def decode_sfloat(raw: bytes) -> float:
    """Decode a 2-byte little-endian IEEE 11073-20601 SFLOAT.

    A 4-bit signed exponent and 12-bit signed mantissa, both two's
    complement: value = mantissa * 10**exponent. Reserved bit patterns
    (NaN, +/-INFINITY, NRes) aren't special-cased -- never observed from
    real hardware, and this device's concentration field is always a
    normal value.
    """
    value = int.from_bytes(raw, "little")
    mantissa = value & 0x0FFF
    exponent = (value >> 12) & 0x0F
    if exponent >= 8:
        exponent -= 16
    if mantissa >= 2048:
        mantissa -= 4096
    return mantissa * (10**exponent)


def parse_glucose_measurement(raw: bytes) -> Reading | None:
    """Decode a Glucose Measurement (0x2A18) notification payload.

    Returns None if the record has no glucose concentration field
    (legal per the spec, but useless for this package's purpose -- a
    blood-glucose reading with no value).
    """
    flags = raw[0]
    sequence_number = int.from_bytes(raw[1:3], "little")

    year = int.from_bytes(raw[3:5], "little")
    month, day, hour, minute, second = raw[5], raw[6], raw[7], raw[8], raw[9]
    device_time = datetime.datetime(year, month, day, hour, minute, second)

    offset = 10
    if flags & FLAG_TIME_OFFSET_PRESENT:
        offset += 2  # Time Offset (minutes, signed int16) -- not applied

    if not flags & FLAG_GLUCOSE_CONCENTRATION_PRESENT:
        return None

    concentration = decode_sfloat(raw[offset:offset + 2])
    type_location = raw[offset + 2]
    sample_type_code = type_location & 0x0F
    sample_location_code = type_location >> 4

    if flags & FLAG_CONCENTRATION_UNITS_MOL_L:
        value_mg_dl = round(concentration * MOL_PER_L_GLUCOSE_TO_MG_PER_DL)
    else:
        value_mg_dl = round(concentration * KG_PER_L_TO_MG_PER_DL)

    return Reading(
        sequence_number=sequence_number,
        value_mg_dl=value_mg_dl,
        device_time=device_time,
        sample_type=SAMPLE_TYPES.get(sample_type_code, str(sample_type_code)),
        sample_location=SAMPLE_LOCATIONS.get(sample_location_code, str(sample_location_code)),
        is_control_solution=(
            sample_type_code == _CONTROL_SOLUTION_TYPE
            or sample_location_code == _CONTROL_SOLUTION_LOCATION
        ),
        raw=bytes(raw),
    )


def parse_glucose_measurement_context_sequence_number(raw: bytes) -> int:
    """Return the sequence number from a Glucose Measurement Context (0x2A34) payload.

    Used only to correlate a context notification with its paired
    measurement -- the rest of the context payload (tester/health, meal,
    exercise, etc.) is never populated by TRUE METRIX AIR in practice
    (always "value not available"), so it isn't decoded further here.
    """
    return int.from_bytes(raw[1:3], "little")
