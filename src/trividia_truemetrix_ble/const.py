"""Constants for the standard Bluetooth SIG Glucose Profile.

TRUE METRIX AIR speaks the public Bluetooth Glucose Service (0x1808) and
Glucose Profile -- not a manufacturer-proprietary protocol -- confirmed
by a live GATT capture against real hardware. See README.md's Protocol
notes section for how that was verified.
"""

from __future__ import annotations

#: Device names this meter advertises under. Matched case-insensitively
#: as a substring, mirroring how the vendor's own companion app filters
#: scan results.
DEVICE_NAME_FILTERS = ("NiproBGM", "TrueMetrix")

# Glucose Service (0x1808) and its characteristics.
GLUCOSE_SERVICE_UUID = "00001808-0000-1000-8000-00805f9b34fb"
GLUCOSE_MEASUREMENT_UUID = "00002a18-0000-1000-8000-00805f9b34fb"
GLUCOSE_MEASUREMENT_CONTEXT_UUID = "00002a34-0000-1000-8000-00805f9b34fb"
GLUCOSE_FEATURE_UUID = "00002a51-0000-1000-8000-00805f9b34fb"
RECORD_ACCESS_CONTROL_POINT_UUID = "00002a52-0000-1000-8000-00805f9b34fb"

# Device Information Service (0x180A) and its characteristics.
DEVICE_INFORMATION_SERVICE_UUID = "0000180a-0000-1000-8000-00805f9b34fb"
MANUFACTURER_NAME_STRING_UUID = "00002a29-0000-1000-8000-00805f9b34fb"
MODEL_NUMBER_STRING_UUID = "00002a24-0000-1000-8000-00805f9b34fb"
SERIAL_NUMBER_STRING_UUID = "00002a25-0000-1000-8000-00805f9b34fb"
FIRMWARE_REVISION_STRING_UUID = "00002a26-0000-1000-8000-00805f9b34fb"
SOFTWARE_REVISION_STRING_UUID = "00002a28-0000-1000-8000-00805f9b34fb"

#: Glucose Measurement flags (byte 0), per the Bluetooth SIG Glucose
#: Profile spec.
FLAG_TIME_OFFSET_PRESENT = 0x01
FLAG_GLUCOSE_CONCENTRATION_PRESENT = 0x02
FLAG_CONCENTRATION_UNITS_MOL_L = 0x04
FLAG_SENSOR_STATUS_ANNUNCIATION_PRESENT = 0x08
FLAG_CONTEXT_INFORMATION_FOLLOWS = 0x10

#: Glucose Measurement Context flags (byte 0).
CONTEXT_FLAG_TESTER_HEALTH_PRESENT = 0x04

#: Glucose Measurement "Type" (low nibble of the type/sample-location
#: octet), per the Bluetooth SIG assigned numbers.
SAMPLE_TYPES = {
    1: "Capillary Whole Blood",
    2: "Capillary Plasma",
    3: "Venous Whole Blood",
    4: "Venous Plasma",
    5: "Arterial Whole Blood",
    6: "Arterial Plasma",
    7: "Undetermined Whole Blood",
    8: "Undetermined Plasma",
    9: "Interstitial Fluid",
    10: "Control Solution",
}

#: Glucose Measurement "Sample Location" (high nibble of the same octet).
SAMPLE_LOCATIONS = {
    1: "Finger",
    2: "Alternate Site Test (AST)",
    3: "Earlobe",
    4: "Control Solution",
    5: "Subcutaneous Tissue",
    15: "Location Not Available",
}

#: Concentration unit conversion: the SFLOAT value is in kg/L (the
#: standard's default unit, used unless FLAG_CONCENTRATION_UNITS_MOL_L is
#: set); multiplying by this factor gives mg/dL. Verified against a real
#: captured reading (0.00167 kg/L -> 167 mg/dL, a plausible blood glucose
#: value) rather than assumed from the spec alone.
KG_PER_L_TO_MG_PER_DL = 100_000

#: How long to wait after the last notification before concluding the
#: meter has finished streaming its stored records. The meter sends its
#: entire history unprompted on subscribe, with no explicit "done" signal
#: observed on Record Access Control Point -- see README.md's Protocol
#: notes section.
DEFAULT_SILENCE_TIMEOUT_SECONDS = 3.0

#: How long to wait for a BLE connection before giving up.
DEFAULT_CONNECT_TIMEOUT_SECONDS = 15.0
