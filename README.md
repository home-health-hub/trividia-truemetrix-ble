# trividia-truemetrix-ble

A standalone Python Bluetooth LE client for the Trividia Health TRUE
METRIX AIR blood glucose meter. It reads device identity and stored
glucose readings directly from the meter over BLE and keeps everything
local -- there's no dependency on any manufacturer cloud service or
companion app.

> [!WARNING]
> **Work in progress.** The GATT protocol itself (service/characteristic
> UUIDs, record byte format, the "streams everything on subscribe, no
> command needed" behavior) was confirmed against a real, owned TRUE
> METRIX AIR via a live capture -- see [Protocol notes](#protocol-notes).
> This package's own `bleak`-based implementation of that protocol
> hasn't been run against real hardware yet. Treat it as
> protocol-correct-on-paper until that's happened. This notice will be
> removed once confirmed.

## Disclaimer

This is an unofficial, independently developed client, built directly
against the public Bluetooth SIG Glucose Profile specification. The
author and contributors are not affiliated with Trividia Health.
**This is a personal-use tool for reading data from your own meter, not
a medical product.** Don't use it to make treatment decisions -- read
your meter's own display for that.

## Features

- Discovers TRUE METRIX AIR meters over Bluetooth LE by advertised name.
- Reads device identity from the standard Device Information Service:
  manufacturer, model, serial number, firmware/software version.
- Downloads stored glucose readings, decoded from the standard Glucose
  Measurement characteristic.
- Excludes control-solution test strips from readings by default (they
  aren't real patient data), with an opt-in flag to include them.
- Ships a `trividia-truemetrix-ble` CLI for one-off use without writing
  any code.
- Nothing here uploads anywhere -- reads stay local unless you choose to
  write them out yourself (e.g. via `--csv`).

## Requirements

- A Trividia Health TRUE METRIX AIR meter with Bluetooth enabled.
- The [`bleak`](https://pypi.org/project/bleak/) Python package (cross-platform BLE: BlueZ on Linux, Core Bluetooth on macOS, WinRT on Windows).
- On Linux, non-root BLE scanning/connection access typically needs the
  running user to be in the `bluetooth` group (or an equivalent polkit
  rule), depending on distro. No pairing/bonding was needed against the
  real meter during protocol verification -- see Protocol notes.

## Installation

```bash
pip install git+https://github.com/bonelifer/trividia-truemetrix-ble.git
```

## Library usage

```python
import asyncio
from trividia_truemetrix_ble import TrueMetrixBleClient, discover

async def main():
    devices = await discover()
    async with TrueMetrixBleClient(devices[0].address, name=devices[0].name) as client:
        info = await client.get_device_info()
        print(info.manufacturer, info.model, info.serial_number)

        for reading in await client.get_readings():
            print(f"{reading.device_time}  {reading.value_mg_dl} mg/dL")

asyncio.run(main())
```

## CLI usage

```bash
# Scan for and list nearby meters
trividia-truemetrix-ble --discover

# Print device info and exit
trividia-truemetrix-ble --info

# Print device info + all readings as JSON
trividia-truemetrix-ble

# Write readings to a CSV file instead
trividia-truemetrix-ble --csv readings.csv

# Include control-solution test records too
trividia-truemetrix-ble --csv readings.csv --include-control-solution

# Connect to a specific meter address instead of scanning
trividia-truemetrix-ble --address AA:BB:CC:DD:EE:FF
```

Run `trividia-truemetrix-ble --help` for all options.

## Protocol notes

TRUE METRIX AIR speaks the standard **Bluetooth SIG Glucose Profile**
(Glucose Service `0x1808`) -- not a manufacturer-proprietary protocol.
Confirmed by a live GATT capture against a real, owned meter. See
[`docs/TRUEMETRIX_AIR_BLE_NOTES.md`](docs/TRUEMETRIX_AIR_BLE_NOTES.md)
for the full capture writeup; summary below:

- **Glucose Measurement** (`0x2A18`, notify): the actual readings, in
  the standard IEEE 11073-10101 record format (flags byte, sequence
  number, base time, SFLOAT-encoded concentration, type/sample-location
  octet). See [`protocol.py`](src/trividia_truemetrix_ble/protocol.py)
  for the exact byte layout, each field documented at the point it's
  decoded.
- **Glucose Measurement Context** (`0x2A34`, notify): paired with each
  measurement by sequence number. Every context record observed had
  Tester/Health as "value not available" -- this meter doesn't populate
  it, so this package only tracks its sequence number for correlation,
  not its content.
- **Record Access Control Point** (`0x2A52`, indicate/write): present,
  but **never needed**. The meter streams its entire stored history
  unprompted the moment notifications are enabled on Glucose
  Measurement -- no "report stored records" command required, which
  deviates from the strict spec's expected flow. Since no explicit
  "stream finished" signal was observed either, this package concludes
  the read is done after a configurable silence timeout
  (`--timeout`/`silence_timeout`, default 3 seconds) passes with no new
  notification -- a heuristic, not a hard protocol guarantee.
- **Glucose Feature** (`0x2A51`, read): present, not yet read/used by
  this package.
- Two additional vendor-specific GATT services are also present on the
  device but aren't part of the standard profile and aren't used here --
  everything needed for reading glucose values comes from the standard
  characteristics above.

### Known quirks / limitations

- SFLOAT reserved bit patterns (NaN, +/-INFINITY, NRes) aren't specially
  handled in `decode_sfloat` -- never observed from real hardware, where
  the concentration field is always a normal value.
- The mol/L concentration unit (the spec's alternate to kg/L) is
  converted using glucose's molar mass, but this was never observed set
  by the meter (it always uses kg/L) -- included for spec completeness,
  not verified against real data.
- End-of-stream detection is a silence timeout, not a real completion
  signal -- see the Record Access Control Point note above.

### Not yet implemented

- Setting the meter's clock (if a Current Time-style write is
  supported/needed) isn't modeled.
- The two vendor-specific GATT services aren't investigated.
- Ketone measurements (some TRUE METRIX variants support ketone
  testing) aren't modeled -- unknown whether they'd surface through this
  same standard profile.

## Contributing

Contributions are welcome!

- **Bug reports**: [Open an issue](https://github.com/bonelifer/trividia-truemetrix-ble/issues).
- **Everything else** (questions, feature requests, ideas, general discussion): [Use Discussions](https://github.com/bonelifer/trividia-truemetrix-ble/discussions).
- Pull requests are welcome for bug fixes or discussed features.

## Acknowledgments

- Protocol implemented directly against the [Bluetooth SIG Glucose
  Service / Glucose Profile specifications](https://www.bluetooth.com/specifications/specs/),
  confirmed byte-exact against a live GATT capture from the author's own
  TRUE METRIX AIR.
- Code review, implementation, and documentation assisted by [Claude](https://www.anthropic.com/claude).

## License

This project is licensed under the **GNU General Public License v3.0**.

See [LICENSE](LICENSE) for more information.
