# Project notes for trividia-truemetrix-ble

## Related repos to watch

- **trividia-truemetrix-hid** --
  https://github.com/bonelifer/trividia-truemetrix-hid -- the sibling
  library for the same meter family, over USB HID instead of BLE. Not a
  code dependency, but the architecture/API shape here (Reading/
  DeviceInfo dataclasses, pure protocol.py decoding functions, thin
  client.py wrapper, argparse CLI with short+long flags) was
  deliberately mirrored from it. If that repo adopts a new pattern
  worth borrowing, or documents a hardware quirk relevant to TRUE
  METRIX AIR specifically, it's worth checking.

- **trividia-truemetrix-daemon** --
  https://github.com/bonelifer/trividia-truemetrix-daemon -- the daemon
  that currently consumes trividia-truemetrix-hid for sync/reporting.
  Once this package is verified against real hardware, it's the likely
  second consumer (BLE path alongside the existing USB HID path).

## Protocol verification status

The GATT protocol (service/characteristic UUIDs, Glucose Measurement
byte format, the "streams everything on subscribe, no RACP command
needed" behavior) was confirmed against a real, owned TRUE METRIX AIR
via a live BLE capture -- see README.md's Protocol notes section for
the details, and `tests/test_protocol.py`'s test vectors, which are
real captured notification payloads, not synthetic data.

What is *not* yet verified: this package's own `bleak`-based
`client.py` has not been run against real hardware. The protocol
understanding is solid; the implementation built on top of it isn't
confirmed working end-to-end yet. Once tested, update or remove the
README's warning banner.

## Open questions for a future session

- End-of-stream detection is a silence-timeout heuristic
  (`DEFAULT_SILENCE_TIMEOUT_SECONDS`), not a real completion signal --
  worth revisiting if a longer real capture ever reveals an actual
  "done" indication on Record Access Control Point.
- Two vendor-specific GATT services exist on the device but are
  unexplored (see README's Protocol notes) -- not needed for a working
  read today, but could matter for meter-initiated pushes, time sync,
  or firmware-version-specific behavior later.
