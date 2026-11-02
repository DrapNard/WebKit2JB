"""Read-only, bounded identification and integrity checks for native artifacts.

This module never extracts, maps, loads, or executes an artifact. NSO/NRO architecture
is reported as a container expectation because these headers do not carry ELF e_machine.
"""

import argparse
import hashlib
import json
import struct
import sys
from pathlib import Path

DEFAULT_MAX_BYTES = 64 * 1024 * 1024
EM_X86_64 = 62
EM_AARCH64 = 183
PT_LOAD = 1
PT_GNU_STACK = 0x6474E551
PF_X = 1
PF_W = 2


def _inspect_elf(data: bytes) -> dict:
    if len(data) < 64 or data[:4] != b"\x7fELF":
        raise ValueError("truncated ELF64 header")
    if data[4:7] != b"\x02\x01\x01":
        raise ValueError("expected ELF64, little-endian, current ELF version")
    elf_type, machine, version = struct.unpack_from("<HHI", data, 16)
    if elf_type not in (2, 3) or version != 1:
        raise ValueError("ELF must be ET_EXEC or ET_DYN with current version")
    if machine == EM_AARCH64:
        architecture = "aarch64"
    elif machine == EM_X86_64:
        architecture = "x86_64"
    else:
        raise ValueError("unsupported ELF machine: {}".format(machine))
    phoff = struct.unpack_from("<Q", data, 32)[0]
    ehsize, phentsize, phnum = struct.unpack_from("<HHH", data, 52)
    if ehsize != 64 or phentsize != 56 or phnum == 0:
        raise ValueError("incompatible ELF64 program-header table")
    if phoff > len(data) or phnum > (len(data) - phoff) // phentsize:
        raise ValueError("ELF program-header table exceeds file bounds")

    load_segments = 0
    executable_stack = False
    for index in range(phnum):
        offset = phoff + index * phentsize
        p_type, p_flags = struct.unpack_from("<II", data, offset)
        p_offset, _vaddr, _paddr, filesz, memsz, _align = struct.unpack_from(
            "<QQQQQQ", data, offset + 8
        )
        if p_type == PT_LOAD:
            load_segments += 1
            if filesz > memsz or p_offset > len(data) or filesz > len(data) - p_offset:
                raise ValueError("ELF PT_LOAD segment {} exceeds file bounds".format(index))
            if p_flags & (PF_W | PF_X) == (PF_W | PF_X):
                raise ValueError("ELF contains a writable and executable PT_LOAD")
        elif p_type == PT_GNU_STACK:
            executable_stack = bool(p_flags & PF_X)
    if load_segments == 0:
        raise ValueError("ELF has no PT_LOAD segments")
    if executable_stack:
        raise ValueError("ELF requests an executable GNU_STACK")
    return {
        "format": "ELF64",
        "architecture": architecture,
        "architectureEvidence": "ELF e_machine",
        "elfType": "ET_EXEC" if elf_type == 2 else "ET_DYN",
        "loadSegments": load_segments,
        "executableStackRequested": executable_stack,
    }


def _inspect_nro(data: bytes) -> dict:
    if len(data) < 0x14 or data[0x10:0x14] != b"NRO0":
        raise ValueError("invalid or truncated NRO0 header")
    if len(data) < 0x80:
        raise ValueError("truncated NRO main header")
    main_size = struct.unpack_from("<I", data, 0x18)[0]
    if main_size < 0x80 or main_size > len(data) - 0x38:
        raise ValueError("NRO main image size is outside file bounds")
    asset = data[main_size:main_size + 0x38]
    if asset[:4] != b"ASET" or struct.unpack_from("<I", asset, 4)[0] != 0:
        raise ValueError("invalid NRO ASET header")
    nacp_offset, nacp_size = struct.unpack_from("<QQ", asset, 24)
    nacp_present = nacp_offset != 0 or nacp_size != 0
    nacp_file_offset = None
    if nacp_present:
        if nacp_size != 0x4000 or nacp_offset < 0x38:
            raise ValueError("invalid embedded NACP metadata bounds")
        nacp_start = main_size + nacp_offset
        if nacp_start > len(data) or nacp_size > len(data) - nacp_start:
            raise ValueError("embedded NACP metadata exceeds file bounds")
        nacp_file_offset = nacp_start
    return {
        "format": "NRO",
        "architecture": "aarch64-expected",
        "architectureEvidence": "Nintendo homebrew container convention; header has no ELF e_machine",
        "mainImageSize": main_size,
        "embeddedNacp": nacp_present,
        "embeddedNacpFileOffset": nacp_file_offset,
    }


def _inspect_nso(data: bytes) -> dict:
    if len(data) < 0x100 or data[:4] != b"NSO0":
        raise ValueError("invalid or truncated NSO0 header")
    return {
        "format": "NSO",
        "architecture": "aarch64-expected",
        "architectureEvidence": "Nintendo system-module container convention; header has no ELF e_machine",
        "validationDepth": "header marker and minimum header length only",
    }


def inspect_bytes(data: bytes, max_bytes: int = DEFAULT_MAX_BYTES) -> dict:
    if not isinstance(data, bytes):
        raise TypeError("artifact data must be bytes")
    if not isinstance(max_bytes, int) or max_bytes < 1:
        raise ValueError("max_bytes must be a positive integer")
    if len(data) > max_bytes:
        raise ValueError("artifact exceeds configured size limit")
    if data.startswith(b"\x7fELF"):
        metadata = _inspect_elf(data)
    elif len(data) >= 0x14 and data[0x10:0x14] == b"NRO0":
        metadata = _inspect_nro(data)
    elif data.startswith(b"NSO0"):
        metadata = _inspect_nso(data)
    else:
        raise ValueError("unsupported executable container")
    return {
        **metadata,
        "size": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def inspect_file(path, max_bytes: int = DEFAULT_MAX_BYTES) -> dict:
    artifact_path = Path(path)
    size = artifact_path.stat().st_size
    if size > max_bytes:
        raise ValueError("artifact exceeds configured size limit")
    data = artifact_path.read_bytes()
    if len(data) != size:
        raise ValueError("artifact changed while being inspected")
    result = inspect_bytes(data, max_bytes)
    return {"path": str(artifact_path), **result}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact", type=Path)
    parser.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_BYTES)
    args = parser.parse_args(argv)
    try:
        print(json.dumps(inspect_file(args.artifact, args.max_bytes), sort_keys=True))
        return 0
    except (OSError, ValueError, TypeError, struct.error) as error:
        print("artifact inspection failed: {}".format(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
