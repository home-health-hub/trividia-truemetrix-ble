# TRUE METRIX Air: BLE Protocol Notes

Working notes for building a BLE driver for the Trividia/Nipro TRUE
METRIX Air, as a sibling to `trividia-truemetrix-hid` (which covers the
USB-docked variant via Tidepool's driver).

## Device identification

- BLE advertised name: `NiproBGM` (also responds to `TrueMetrix` as a
  name match, per an unrelated Android app scan, not confirmed against
  this specific unit, but the device seen in the live capture below
  advertised as `NiproBGM`).
- Meter used for verification: address redacted (real BLE MAC, not
  included here since this is a public repo).

## Confirmed on real hardware: standard Bluetooth SIG Glucose Profile, no custom protocol

Live GATT scan + capture (nRF Connect, 2026-08-10) confirms this meter
implements the public **Bluetooth SIG Glucose Profile**: no
manufacturer-proprietary framing, checksum, or command set. Everything
needed to read stored records is the standard, publicly documented spec
("Glucose Service" / "Glucose Profile", bluetooth.com/specifications).

## Full protocol capture (2026-08-10): nRF Connect session, real meter

Full capture log kept locally, not committed here (it contains the
meter's real BLE address and all 621 real historical glucose readings,
meaningfully more personal health data than the couple of example
values transcribed into this doc and into `tests/test_protocol.py`).

### Full GATT table

```
Generic Attribute (0x1801)
- Service Changed [N] (0x2A05)
Generic Access (0x1800)
- Device Name [R] (0x2A00)
- Appearance [R] (0x2A01)
Device Information (0x180A)
- Manufacturer Name String [R] (0x2A29)
- Model Number String [R] (0x2A24)
- System ID [R] (0x2A23)
- Firmware Revision String [R] (0x2A26)
- Serial Number String [R] (0x2A25)
- Software Revision String [R] (0x2A28)
Glucose (0x1808)
- Glucose Measurement [N] (0x2A18)
- Glucose Measurement Context [N] (0x2A34)
- Record Access Control Point [I W] (0x2A52)
- Glucose Feature [R] (0x2A51)
Unknown Service (00a215bd-9b02-4e5a-9a65-98f1095f4755)
- Unknown Characteristic [N] (d6d5556b-cfd1-4c5c-9fec-417cf023a6ca)
- Unknown Characteristic [I W] (448af2d8-36a2-42a1-86b5-f51207c36760)
Unknown Service (b39078a0-4289-11e4-9368-0002a5d5c51b)
- Unknown Characteristic [I W] (b5eb2a20-428c-11e4-b486-0002a5d5c51b)
- Unknown Characteristic [R] (b4eb2a20-428c-11e4-b499-0002a5d5c52b)
```

The first four services are entirely standard (Generic Attribute/Access,
Device Information, Glucose). Two extra vendor-specific services are
also present, not part of the standard profile and not investigated
further yet (see below).

### Key behavioral finding: no RACP command needed for a full dump

Only `setCharacteristicNotification(..., true)` was needed on six
characteristics (`0x2A18`, `0x2A34`, `0x2A52`, and the three vendor
UUIDs), and **no write was ever sent to RACP (`0x2A52`)**. The meter
started streaming immediately after notifications were enabled and
pushed its **entire stored history unprompted**: 621 records, sequence
numbers 228→848 contiguous, spanning 9 Sep 2022 to 20 Aug 2023, all
within ~25 seconds. This deviates from the strict Bluetooth SIG spec
(which expects the collector to write a "Report Stored Records" opcode
to RACP); this meter just dumps everything on subscribe. Practical
implication for a driver: no RACP write needed for a full read. The
open question is how to detect "stream finished" (no completion
indication was observed on RACP in this capture, so it likely just needs
an idle/silence timeout after the last notification, or reading
`0x2A51` Glucose Feature / a known record count some other way). Worth
confirming with a longer capture or an explicit RACP "number of stored
records" read on a future session.

### Glucose Measurement (`0x2A18`): standard IEEE 11073-10101 format, confirmed byte-exact

Example raw notification: `12-E4-00-E6-07-09-09-11-33-00-A7-B0-18`

| Bytes | Field | Value | Decoded |
|---|---|---|---|
| `12` | Flags | `0b00010010` | bit1=Glucose present, bit4=Context follows, bit2=0→units kg/L |
| `E4 00` | Sequence Number (u16 LE) | `0x00E4` | 228 |
| `E6 07` | Year (u16 LE) | `0x07E6` | 2022 |
| `09` | Month | | 9 |
| `09` | Day | | 9 |
| `11` | Hour | `0x11` | 17 |
| `33` | Minute | `0x33` | 51 |
| `00` | Second | | 0 |
| `A7 B0` | Glucose Concentration (SFLOAT, u16 LE) | mantissa=0x0A7=167, exponent=(0xB0A7>>12)=0xB→-5 (two's complement nibble) | 167 × 10⁻⁵ = **0.00167 kg/L** |
| `18` | Type/Sample Location (1 octet) | low nibble=8, high nibble=1 | Type=8 (Undetermined Plasma), Location=1 (Finger) |

No Time Offset (flag bit0=0) or Sensor Status Annunciation (flag bit3=0)
fields present in any record seen. This meter doesn't populate those.
Verified this decode in Python against the raw bytes and it matches
nRF Connect's own parsed output exactly (sequence, date, concentration,
type, location). SFLOAT math is a 4-bit signed exponent, 12-bit signed
mantissa, both two's complement.

### Glucose Measurement Context (`0x2A34`): standard format, confirmed

Example: `04-E4-00-FF` → Flags=`0x04` (bit2=Tester-Health present),
Sequence Number=228 (matches the paired `0x2A18` record), Tester-Health
byte=`0xFF` (both nibbles = 0xF = "value not available"). Every context
record in the capture had Tester and Health as "not available". This
meter doesn't populate that data; the field only exists because the standard flag
bit1 in the Measurement's flags (`Context information follows`) is
always set to true.

### Unfollowed leads (not needed for a working driver, but noted)

- `d6d5556b-cfd1-4c5c-9fec-417cf023a6ca` (vendor service
  `00a215bd-9b02-4e5a-9a65-98f1095f4755`) fired once per glucose record
  (621 times), value format `02-<seq LE16>-00`: an exact echo of each
  record's sequence number through a proprietary channel, purpose
  unclear (possibly legacy/companion format for an older app, or
  unrelated bookkeeping). Not needed since the standard characteristics
  already carry everything.
- `448af2d8-...` and `b5eb2a20-...`/`b4eb2a20-...` (the second vendor
  service) saw zero traffic in this capture, likely control channels
  (e.g. time sync, firmware query) not exercised by a passive
  notification-only session. Not investigated.

### Conclusion

Enough to write a working Python (or any-language) BLE Glucose Profile
client for the TRUE METRIX Air today: connect, subscribe to `0x2A18` +
`0x2A34`, decode using the standard IEEE 11073-10101/SFLOAT format
above, correlate by sequence number, done: no RACP write, no vendor
service needed. Remaining open question before calling it
production-ready is just how to reliably detect end-of-stream (timeout
vs. some other signal), which needs one more capture or a live test to
pin down.

## Next capture pending

A fresh reading is queued (lancet pen currently out of service) to
confirm the decode holds on new data past sequence 848. Expect the new
record's timestamp to land in 2026 and its sequence number to continue
past 848.
