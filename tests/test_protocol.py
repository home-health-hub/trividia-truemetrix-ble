from __future__ import annotations

import datetime

from trividia_truemetrix_ble.protocol import (
    decode_sfloat,
    parse_glucose_measurement,
    parse_glucose_measurement_context_sequence_number,
)

# Real Glucose Measurement (0x2A18) notification payloads from a live
# nRF Connect capture against an owned TRUE METRIX AIR -- not synthetic
# data. Sequence 228: 9 Sep 2022 17:51:00, 0.00167 kg/L (167 mg/dL).
# Sequence 235: 13 Sep 2022 06:26:00, 0.00117 kg/L (117 mg/dL). Both
# Undetermined Plasma / Finger (type/location octet 0x18).
_MEASUREMENT_SEQ_228 = bytes.fromhex("12E400E6070909113300A7B018")
_MEASUREMENT_SEQ_235 = bytes.fromhex("12EB00E607090D061A0075B018")

# Paired Glucose Measurement Context (0x2A34) notification for sequence
# 228 -- Tester/Health both "value not available" (0xFF), as every
# context record in the capture had.
_CONTEXT_SEQ_228 = bytes.fromhex("04E400FF")


def test_decode_sfloat_matches_real_captured_reading():
    # A7 B0 little-endian: mantissa=0x0A7=167, exponent=(0xB>>...)-16=-5
    assert decode_sfloat(bytes.fromhex("A7B0")) == 167 * 10**-5


def test_parse_glucose_measurement_decodes_sequence_228():
    reading = parse_glucose_measurement(_MEASUREMENT_SEQ_228)

    assert reading is not None
    assert reading.sequence_number == 228
    assert reading.device_time == datetime.datetime(2022, 9, 9, 17, 51, 0)
    assert reading.value_mg_dl == 167
    assert reading.sample_type == "Undetermined Plasma"
    assert reading.sample_location == "Finger"
    assert reading.is_control_solution is False
    assert reading.raw == _MEASUREMENT_SEQ_228


def test_parse_glucose_measurement_decodes_sequence_235():
    reading = parse_glucose_measurement(_MEASUREMENT_SEQ_235)

    assert reading is not None
    assert reading.sequence_number == 235
    assert reading.device_time == datetime.datetime(2022, 9, 13, 6, 26, 0)
    assert reading.value_mg_dl == 117


def test_parse_glucose_measurement_returns_none_without_concentration_flag():
    # Flags byte with only bit4 (context follows) set, concentration
    # flag (bit1) cleared -- a legal-but-useless record per the spec.
    no_concentration = bytes([0x10]) + _MEASUREMENT_SEQ_228[1:10]
    assert parse_glucose_measurement(no_concentration) is None


def test_parse_glucose_measurement_context_sequence_number_matches_paired_measurement():
    assert parse_glucose_measurement_context_sequence_number(_CONTEXT_SEQ_228) == 228
