#!/usr/bin/env python3
"""
Utility script to print the field mappings used by tc-resource-top.

This script reads the sample resource-usage.json file and displays
the exact field paths used for extracting metrics.

No external dependencies required (uses only stdlib json).
"""

import json
import sys
from pathlib import Path


def main():
    # Find the samples directory relative to this script
    script_dir = Path(__file__).parent
    sample_file = script_dir.parent / "samples" / "resource-usage.json"

    if not sample_file.exists():
        print(f"Error: Sample file not found at {sample_file}", file=sys.stderr)
        sys.exit(1)

    print(f"Reading sample file: {sample_file}\n")

    try:
        with open(sample_file) as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error reading JSON: {e}", file=sys.stderr)
        sys.exit(1)

    # Display structure
    print("=" * 79)
    print("FIELD MAPPINGS USED BY tc-resource-top")
    print("=" * 79)
    print()

    # Check if samples exist
    samples = data.get("samples", [])
    if not samples:
        print("Error: No samples found in file", file=sys.stderr)
        sys.exit(1)

    first_sample = samples[0]
    last_sample = samples[-1]

    print(f"Total samples in file: {len(samples)}")
    print()

    # CPU Percent
    print("1. CPU PERCENT")
    print("   Path: samples[*].cpu_percent_mean")
    print("   Type: Float (0-100 percentage)")
    cpu_value = first_sample.get("cpu_percent_mean")
    print(f"   Example (first sample): {cpu_value}")
    print(f"   Computation: Mean of all sample cpu_percent_mean values")
    print()

    # Virtual Memory
    print("2. VIRTUAL MEMORY")
    print("   Path: samples[*].virt[0]")
    print("   Type: Integer (bytes)")
    virt_array = first_sample.get("virt", [])
    if virt_array:
        virt_value = virt_array[0]
        print(f"   Example (first sample): {virt_value} bytes")
        print(f"   Example (first sample): {virt_value / (1024**3):.2f} GiB")
    print(f"   Computation: Mean of all sample virt[0] values")
    print()

    # IO Counters
    print("3. IO COUNTERS")
    print("   Path: samples[*].io[2] (read_bytes), samples[*].io[3] (write_bytes)")
    print("   Type: Integer (bytes, cumulative counters)")
    io_first = first_sample.get("io", [])
    io_last = last_sample.get("io", [])
    if len(io_first) > 3 and len(io_last) > 3:
        print(f"   Example (first sample): read={io_first[2]}, write={io_first[3]}")
        print(f"   Example (last sample):  read={io_last[2]}, write={io_last[3]}")
        delta_read = io_last[2] - io_first[2]
        delta_write = io_last[3] - io_first[3]
        print(f"   Delta over all samples: read={delta_read}, write={delta_write}")
    print(f"   Computation: (Δread_bytes + Δwrite_bytes) / Δtime")
    print()

    # Timestamps
    print("4. TIMESTAMPS")
    print("   Path: samples[*].start, samples[*].end")
    print("   Type: Float (seconds)")
    start_first = first_sample.get("start")
    end_first = first_sample.get("end")
    start_last = last_sample.get("start")
    end_last = last_sample.get("end")
    print(f"   Example (first sample): start={start_first:.3f}s, end={end_first:.3f}s")
    print(f"   Example (last sample):  start={start_last:.3f}s, end={end_last:.3f}s")
    if start_first is not None and end_last is not None:
        total_time = end_last - start_first
        print(f"   Total duration: {total_time:.2f} seconds")
    print()

    print("=" * 79)
    print()
    print("These field paths are defined in src/tc_resource_top/metrics.py")
    print("and documented in the README.md file.")


if __name__ == "__main__":
    main()
