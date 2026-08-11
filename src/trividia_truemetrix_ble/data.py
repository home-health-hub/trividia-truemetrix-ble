"""Data types for the standard Bluetooth Glucose Profile."""

from __future__ import annotations

import dataclasses
import datetime


@dataclasses.dataclass
class Reading:
    """A single decoded Glucose Measurement record.

    Attributes:
        sequence_number: The record's sequence number, as reported by the
            meter. Used to correlate a Glucose Measurement with its
            paired Glucose Measurement Context notification.
        value_mg_dl: Blood glucose value, converted to mg/dL from the
            device's raw kg/L SFLOAT encoding (see
            const.KG_PER_L_TO_MG_PER_DL).
        device_time: Timestamp as read from the record's embedded base
            time field. Not timezone-aware -- the meter has no timezone
            concept.
        sample_type: Decoded Type field (e.g. "Undetermined Plasma"), or
            the raw integer as a string if not in const.SAMPLE_TYPES.
        sample_location: Decoded Sample Location field (e.g. "Finger"),
            or the raw integer as a string if not in
            const.SAMPLE_LOCATIONS.
        is_control_solution: True if sample_type/sample_location
            indicate a control-solution test rather than a real reading
            (Type 10, or Location 4). TrueMetrixBleClient excludes these
            from get_readings() by default, matching
            trividia-truemetrix-hid's convention for the same meter
            family over USB.
        raw: The undecoded Glucose Measurement notification bytes this
            reading was parsed from.
    """

    sequence_number: int
    value_mg_dl: int
    device_time: datetime.datetime
    sample_type: str
    sample_location: str
    is_control_solution: bool
    raw: bytes


@dataclasses.dataclass
class DeviceInfo:
    """Device identity, from the standard Device Information Service (0x180A).

    Attributes:
        manufacturer: Manufacturer Name String (0x2A29), if the device
            exposes it.
        model: Model Number String (0x2A24), if the device exposes it.
        serial_number: Serial Number String (0x2A25), if the device
            exposes it.
        firmware_version: Firmware Revision String (0x2A26), if the
            device exposes it.
        software_version: Software Revision String (0x2A28), if the
            device exposes it.
        address: BLE address (or platform-specific identifier) the
            device was connected at.
        name: Advertised BLE device name (e.g. "NiproBGM").
    """

    manufacturer: str | None
    model: str | None
    serial_number: str | None
    firmware_version: str | None
    software_version: str | None
    address: str
    name: str | None
