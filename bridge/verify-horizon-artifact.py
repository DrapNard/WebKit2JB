#!/usr/bin/env python3
"""Static format checks for the bridge's homebrew ELF/NRO/NACP outputs."""

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from artifacts import inspect_file


def main(argv):
    if len(argv) not in (4, 5):
        print("usage: verify-horizon-artifact.py ELF NRO NACP [BUILD-MANIFEST]", file=sys.stderr)
        return 2
    elf, nro, nacp = map(Path, argv[1:4])
    for artifact in (elf, nro, nacp):
        if not artifact.is_file() or artifact.stat().st_size == 0:
            raise SystemExit("missing or empty artifact: " + str(artifact))

    elf_inspection = inspect_file(elf)
    nro_inspection = inspect_file(nro)
    if elf_inspection.get("architecture") != "aarch64":
        raise SystemExit("shared artifact inspector did not identify an AArch64 ELF")
    if nro_inspection.get("format") != "NRO" or not nro_inspection.get("embeddedNacp"):
        raise SystemExit("shared artifact inspector did not validate the NRO/NACP container")

    elf_bytes = elf.read_bytes()
    if len(elf_bytes) < 64 or elf_bytes[:4] != b"\x7fELF":
        raise SystemExit("ELF header is invalid")
    if (elf_bytes[4] != 2 or elf_bytes[5] != 1
            or int.from_bytes(elf_bytes[16:18], "little") != 3
            or int.from_bytes(elf_bytes[18:20], "little") != 183):
        raise SystemExit("expected a little-endian ELF64 AArch64 executable")
    phoff = int.from_bytes(elf_bytes[32:40], "little")
    phentsize = int.from_bytes(elf_bytes[54:56], "little")
    phnum = int.from_bytes(elf_bytes[56:58], "little")
    if phentsize < 56 or phoff + phentsize * phnum > len(elf_bytes):
        raise SystemExit("ELF program-header table is invalid")
    stack_header_seen = False
    for index in range(phnum):
        offset = phoff + index * phentsize
        p_type = int.from_bytes(elf_bytes[offset:offset + 4], "little")
        p_flags = int.from_bytes(elf_bytes[offset + 4:offset + 8], "little")
        if p_type == 1 and (p_flags & 0x3) == 0x3:
            raise SystemExit("RWX PT_LOAD segment found")
        if p_type == 0x6474E551:
            stack_header_seen = True
            if p_flags & 0x1:
                raise SystemExit("executable GNU_STACK program header found")

    nro_bytes = nro.read_bytes()
    if len(nro_bytes) < 0x14 or nro_bytes[0x10:0x14] != b"NRO0":
        raise SystemExit("NRO0 magic not found at the standard NRO header offset")
    nro_size = int.from_bytes(nro_bytes[0x18:0x1c], "little")
    if nro_size < 0x80 or nro_size + 0x38 > len(nro_bytes):
        raise SystemExit("NRO main image size or asset-header offset is invalid")
    asset_header = nro_bytes[nro_size:nro_size + 0x38]
    if asset_header[:4] != b"ASET" or int.from_bytes(asset_header[4:8], "little") != 0:
        raise SystemExit("NRO asset header magic/version is invalid")
    nacp_offset = int.from_bytes(asset_header[24:32], "little")
    nacp_size = int.from_bytes(asset_header[32:40], "little")
    nacp_start = nro_size + nacp_offset
    if nacp_size != 0x4000 or nacp_start < nro_size + 0x38 or nacp_start + nacp_size > len(nro_bytes):
        raise SystemExit("NRO embedded NACP section bounds are invalid")

    nacp_bytes = nacp.read_bytes()
    if len(nacp_bytes) != 0x4000:
        raise SystemExit("NACP output is not the standard 0x4000-byte metadata structure")
    embedded_nacp = nro_bytes[nacp_start:nacp_start + nacp_size]
    if embedded_nacp != nacp_bytes:
        raise SystemExit("embedded NACP does not match the generated sidecar")
    title = nacp_bytes[:0x200].split(b"\0", 1)[0].decode("utf-8", "replace")
    author = nacp_bytes[0x200:0x300].split(b"\0", 1)[0].decode("utf-8", "replace")
    version = nacp_bytes[0x3060:0x3070].split(b"\0", 1)[0].decode("utf-8", "replace")
    if (title, author, version) != ("WebKit2JB Bridge Demo", "WebKit2JB Lab", "0.1.0"):
        raise SystemExit("NACP title/author/version metadata do not match the demo")
    native_message = b"UwU from Nintendo Switch 2"
    if native_message not in elf_bytes or native_message not in nro_bytes:
        raise SystemExit("native demo message is missing from the ELF or NRO")
    if (b"horizon-memory-policy" not in elf_bytes or b"horizon-memory-policy" not in nro_bytes or
            b"W^X policy query" not in elf_bytes or b"W^X policy query" not in nro_bytes):
        raise SystemExit("NRO does not contain the Horizon relay W^X policy request")

    hashes = {artifact.name: hashlib.sha256(artifact.read_bytes()).hexdigest()
              for artifact in (elf, nro, nacp)}
    if len(argv) == 5:
        repository = elf.resolve().parents[2]
        commit = subprocess.run(["git", "-C", str(repository), "rev-parse", "HEAD"],
                                capture_output=True, text=True)
        dirty = subprocess.run(["git", "-C", str(repository), "status", "--porcelain", "--", "bridge"],
                               capture_output=True, text=True)
        gcc = Path(os.environ.get("DEVKITA64", "")) / "bin" / "aarch64-none-elf-gcc"
        version_result = subprocess.run([str(gcc), "--version"], capture_output=True, text=True) if gcc.is_file() else None
        manifest = {
            "schema": "webkit2jb-horizon-build/1",
            "status": "HORIZON_COMPILED",
            "target": "horizon-homebrew",
            "architecture": "aarch64",
            "artifact": nro.name,
            "artifactSize": len(nro_bytes),
            "artifactSha256": hashes[nro.name],
            "elfSha256": hashes[elf.name],
            "nacpSha256": hashes[nacp.name],
            "title": title,
            "author": author,
            "version": version,
            "sourceCommit": commit.stdout.strip() if commit.returncode == 0 else "unknown",
            "sourceDirty": bool(dirty.stdout.strip()) if dirty.returncode == 0 else True,
            "toolchain": version_result.stdout.splitlines()[0] if version_result and version_result.returncode == 0 else "unknown",
            "executionConfirmed": False,
        }
        Path(argv[4]).write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    for artifact in (elf, nro, nacp):
        print("{}: {} bytes sha256={}".format(artifact, artifact.stat().st_size, hashes[artifact.name]))
    stack_note = "GNU_STACK absent; runtime stack permissions are not specified by this ELF" \
        if not stack_header_seen else "GNU_STACK is non-executable"
    print("ELF64/AArch64, non-RWX PT_LOAD, " + stack_note + ", NRO0, and embedded NACP metadata checks: PASS")
    print("Shared bounded artifact inspection and SHA-256 identification: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
