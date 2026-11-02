#!/usr/bin/env python3
"""Check ELF machine type and reject RWX loads or an executable stack."""

import re
import subprocess
import sys


def main(argv):
    if len(argv) != 3:
        print("usage: verify-linux-elf.py ELF EXPECTED_MACHINE", file=sys.stderr)
        return 2
    path, expected_machine = argv[1:]
    header = subprocess.run(["llvm-readelf", "-h", path], check=True,
                            capture_output=True, text=True).stdout
    if not re.search(r"Machine:\s+" + re.escape(expected_machine) + r"\b", header):
        raise SystemExit("ELF machine mismatch")
    segments = subprocess.run(["llvm-readelf", "-l", "--wide", path], check=True,
                              capture_output=True, text=True).stdout
    stack_seen = False
    for line in segments.splitlines():
        fields = line.split()
        if not fields or fields[0] not in ("LOAD", "GNU_STACK"):
            continue
        if len(fields) < 3:
            raise SystemExit("could not parse ELF program header")
        flags = "".join(fields[6:-1])
        if fields[0] == "LOAD" and "W" in flags and "E" in flags:
            raise SystemExit("RWX PT_LOAD segment found")
        if fields[0] == "GNU_STACK":
            stack_seen = True
            if "E" in flags:
                raise SystemExit("executable GNU_STACK found")
    if not stack_seen:
        raise SystemExit("GNU_STACK program header not found")
    print("ELF machine, non-RWX loads, and non-executable stack: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
