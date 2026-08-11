"""Bluetooth LE client for Trividia Health TRUE METRIX AIR blood glucose meters.

The meter speaks the standard Bluetooth SIG Glucose Profile -- confirmed
by a live GATT capture against real hardware, not assumed from the spec
alone. There's no persistent "connection" logic beyond a normal BLE GATT
session: connect, subscribe to Glucose Measurement, collect until the
meter goes quiet. See protocol.py's module docstring and README.md's
Protocol notes section for how the format and this "stream everything on
subscribe, no RACP needed" behavior were verified.

Uses the `bleak` package for cross-platform BLE access (BlueZ on Linux,
Core Bluetooth on macOS, WinRT on Windows).
"""

from __future__ import annotations

import asyncio
import logging

from bleak import BleakClient, BleakScanner
from bleak.backends.device import BLEDevice
from bleak.exc import BleakError

from . import protocol
from .const import (
    DEFAULT_CONNECT_TIMEOUT_SECONDS,
    DEFAULT_SILENCE_TIMEOUT_SECONDS,
    DEVICE_NAME_FILTERS,
    FIRMWARE_REVISION_STRING_UUID,
    GLUCOSE_MEASUREMENT_CONTEXT_UUID,
    GLUCOSE_MEASUREMENT_UUID,
    MANUFACTURER_NAME_STRING_UUID,
    MODEL_NUMBER_STRING_UUID,
    SERIAL_NUMBER_STRING_UUID,
    SOFTWARE_REVISION_STRING_UUID,
)
from .data import DeviceInfo, Reading

_LOGGER = logging.getLogger(__name__)


class TrueMetrixError(RuntimeError):
    """Raised for meter communication failures not covered by a more specific error."""


async def discover(timeout: float = 5.0) -> list[BLEDevice]:
    """Scan for and return BLE devices matching TRUE METRIX AIR's advertised name."""
    devices = await BleakScanner.discover(timeout=timeout)
    return [
        device
        for device in devices
        if device.name and any(f.lower() in device.name.lower() for f in DEVICE_NAME_FILTERS)
    ]


async def _read_optional_string(client: BleakClient, uuid: str) -> str | None:
    """Read a Device Information Service string characteristic, if present.

    Not every meter/firmware combination is guaranteed to expose every
    optional DIS characteristic -- absence is a normal outcome, not an
    error worth surfacing to callers.
    """
    try:
        value = await client.read_gatt_char(uuid)
    except BleakError:
        return None
    return value.decode("utf-8", errors="replace").strip() or None


class TrueMetrixBleClient:
    """Client for one TRUE METRIX AIR meter over Bluetooth LE.

    Usage:

        async with TrueMetrixBleClient(address) as client:
            info = await client.get_device_info()
            readings = await client.get_readings()

    `address` is a BLE address (a platform-specific identifier on
    macOS), typically from a `BLEDevice` returned by `discover()`.
    """

    def __init__(
        self,
        address: str,
        *,
        name: str | None = None,
        connect_timeout: float = DEFAULT_CONNECT_TIMEOUT_SECONDS,
        silence_timeout: float = DEFAULT_SILENCE_TIMEOUT_SECONDS,
    ) -> None:
        self._address = address
        self._name = name
        self._connect_timeout = connect_timeout
        self._silence_timeout = silence_timeout
        self._client: BleakClient | None = None

    async def __aenter__(self) -> TrueMetrixBleClient:
        await self.connect()
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.disconnect()

    async def connect(self) -> None:
        if self._client is not None:
            return
        client = BleakClient(self._address, timeout=self._connect_timeout)
        await client.connect()
        self._client = client

    async def disconnect(self) -> None:
        if self._client is None:
            return
        try:
            await self._client.disconnect()
        finally:
            self._client = None

    async def get_device_info(self) -> DeviceInfo:
        """Read device identity from the standard Device Information Service."""
        if self._client is None:
            raise TrueMetrixError("Not connected")
        return DeviceInfo(
            manufacturer=await _read_optional_string(self._client, MANUFACTURER_NAME_STRING_UUID),
            model=await _read_optional_string(self._client, MODEL_NUMBER_STRING_UUID),
            serial_number=await _read_optional_string(self._client, SERIAL_NUMBER_STRING_UUID),
            firmware_version=await _read_optional_string(
                self._client, FIRMWARE_REVISION_STRING_UUID
            ),
            software_version=await _read_optional_string(
                self._client, SOFTWARE_REVISION_STRING_UUID
            ),
            address=self._address,
            name=self._name,
        )

    async def get_readings(self, *, include_control_solution: bool = False) -> list[Reading]:
        """Subscribe and collect the meter's full stored history.

        Confirmed by a live capture against real hardware: the meter
        streams its entire history unprompted as soon as notifications
        are enabled on Glucose Measurement -- there's no Record Access
        Control Point command to send for a full read. Since no "stream
        finished" signal was observed, collection ends once
        silence_timeout seconds pass with no new notification.
        """
        if self._client is None:
            raise TrueMetrixError("Not connected")

        readings: dict[int, Reading] = {}
        loop = asyncio.get_running_loop()
        last_notification_at = loop.time()

        def _on_measurement(_handle: int, data: bytearray) -> None:
            nonlocal last_notification_at
            last_notification_at = loop.time()
            reading = protocol.parse_glucose_measurement(bytes(data))
            if reading is not None:
                readings[reading.sequence_number] = reading

        def _on_context(_handle: int, _data: bytearray) -> None:
            # Content discarded -- see
            # protocol.parse_glucose_measurement_context_sequence_number's
            # docstring. Still tracked for the silence timeout, since it's
            # unclear whether the meter needs this subscription active to
            # keep streaming (matched what worked in the real capture).
            nonlocal last_notification_at
            last_notification_at = loop.time()

        await self._client.start_notify(GLUCOSE_MEASUREMENT_UUID, _on_measurement)
        await self._client.start_notify(GLUCOSE_MEASUREMENT_CONTEXT_UUID, _on_context)
        try:
            while loop.time() - last_notification_at < self._silence_timeout:
                await asyncio.sleep(self._silence_timeout / 4)
        finally:
            await self._client.stop_notify(GLUCOSE_MEASUREMENT_UUID)
            await self._client.stop_notify(GLUCOSE_MEASUREMENT_CONTEXT_UUID)

        result = sorted(readings.values(), key=lambda reading: reading.sequence_number)
        if not include_control_solution:
            result = [reading for reading in result if not reading.is_control_solution]
        return result
