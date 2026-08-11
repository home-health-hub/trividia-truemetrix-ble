#!/usr/bin/env python3
"""Standalone command-line client for Trividia Health TRUE METRIX AIR meters."""

from __future__ import annotations

import argparse
import asyncio
import csv
import dataclasses
import json
import logging
import sys

from ._version import __version__
from .client import TrueMetrixBleClient, TrueMetrixError, discover
from .const import DEFAULT_SILENCE_TIMEOUT_SECONDS

_LOGGER = logging.getLogger("trividia_truemetrix_ble")


def _print_json(obj) -> None:
    data = dataclasses.asdict(obj) if dataclasses.is_dataclass(obj) else obj
    print(json.dumps(data, indent=2, default=str))


async def _run_discover(scan_timeout: float) -> None:
    devices = await discover(timeout=scan_timeout)
    if not devices:
        print("No TRUE METRIX AIR meters found.", file=sys.stderr)
        return
    for device in devices:
        print(f"{device.address}  {device.name}")


def _write_csv(readings, out_path: str) -> None:
    with open(out_path, "w", newline="") as fp:
        writer = csv.writer(fp)
        writer.writerow(["Time", "Glucose(mg/dL)", "Sample Type", "Sample Location"])
        for reading in readings:
            writer.writerow(
                [
                    reading.device_time.isoformat(),
                    reading.value_mg_dl,
                    reading.sample_type,
                    reading.sample_location,
                ]
            )


async def _run(args: argparse.Namespace) -> None:
    address = args.address
    name = None
    if address is None:
        devices = await discover(timeout=args.scan_timeout)
        if not devices:
            raise TrueMetrixError("No TRUE METRIX AIR meter found. Is it powered on?")
        address, name = devices[0].address, devices[0].name

    async with TrueMetrixBleClient(address, name=name, silence_timeout=args.timeout) as client:
        info = await client.get_device_info()
        if args.info:
            _print_json(info)
            return

        readings = await client.get_readings(include_control_solution=args.include_control_solution)
        if args.csv:
            _write_csv(readings, args.csv)
            print(f"Wrote {len(readings)} readings to {args.csv}", file=sys.stderr)
        else:
            _print_json(
                {
                    "device": dataclasses.asdict(info),
                    "readings": [dataclasses.asdict(r) for r in readings],
                }
            )


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-V", "--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument(
        "-d", "--discover", action="store_true", help="scan for meters, list them, and exit"
    )
    parser.add_argument(
        "-a", "--address", help="BLE address to use (from --discover); default: first found"
    )
    parser.add_argument(
        "-i", "--info", action="store_true",
        help="print device info (manufacturer/model/serial/firmware) and exit",
    )
    parser.add_argument("-c", "--csv", metavar="PATH", help="write readings to a CSV file")
    parser.add_argument(
        "-C", "--include-control-solution", action="store_true",
        help="include control-solution test records, excluded by default",
    )
    parser.add_argument(
        "-t", "--timeout", type=float, default=DEFAULT_SILENCE_TIMEOUT_SECONDS,
        metavar="SECONDS",
        help=f"silence timeout to conclude the meter finished streaming "
             f"(default: {DEFAULT_SILENCE_TIMEOUT_SECONDS})",
    )
    parser.add_argument(
        "-s", "--scan-timeout", type=float, default=5.0, metavar="SECONDS",
        help="BLE scan duration when discovering a meter (default: 5.0)",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="enable debug logging")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """Entry point for the trividia-truemetrix-ble console script."""
    args = _parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO)

    try:
        if args.discover:
            asyncio.run(_run_discover(args.scan_timeout))
            return
        asyncio.run(_run(args))
    except TrueMetrixError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
