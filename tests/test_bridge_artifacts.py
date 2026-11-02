import hashlib
import struct
import tempfile
import unittest
from pathlib import Path

from bridge.artifacts import inspect_bytes, inspect_file


def make_elf(machine=183, load_flags=5, stack_flags=None):
    program_headers = 1 + (stack_flags is not None)
    data = bytearray(64 + 56 * program_headers + 8)
    data[:7] = b"\x7fELF\x02\x01\x01"
    struct.pack_into("<HHIQQQIHHHHHH", data, 16,
                     3, machine, 1, 0, 64, 0, 0, 64, 56, program_headers, 0, 0, 0)
    struct.pack_into("<IIQQQQQQ", data, 64, 1, load_flags, len(data) - 8,
                     0, 0, 8, 8, 8)
    if stack_flags is not None:
        struct.pack_into("<IIQQQQQQ", data, 120, 0x6474E551, stack_flags,
                         0, 0, 0, 0, 0, 8)
    return bytes(data)


def make_nro():
    main_size = 0x80
    data = bytearray(main_size + 0x38 + 0x4000)
    data[0x10:0x14] = b"NRO0"
    struct.pack_into("<I", data, 0x18, main_size)
    data[main_size:main_size + 4] = b"ASET"
    struct.pack_into("<I", data, main_size + 4, 0)
    struct.pack_into("<QQ", data, main_size + 24, 0x38, 0x4000)
    return bytes(data)


class ArtifactInspectionTests(unittest.TestCase):
    def test_aarch64_elf_reports_arch_hash_and_wx_policy(self):
        data = make_elf()
        result = inspect_bytes(data)
        self.assertEqual(result["format"], "ELF64")
        self.assertEqual(result["architecture"], "aarch64")
        self.assertEqual(result["sha256"], hashlib.sha256(data).hexdigest())
        self.assertFalse(result["executableStackRequested"])

    def test_rejects_rwx_executable_stack_unknown_machine_and_truncation(self):
        for data in (make_elf(load_flags=7), make_elf(stack_flags=7),
                     make_elf(machine=0xFFFF), b"\x7fELF\x02"):
            with self.subTest(data=data[:12]):
                with self.assertRaises(ValueError):
                    inspect_bytes(data)

    def test_nro_header_asset_bounds_and_nacp_are_checked(self):
        result = inspect_bytes(make_nro())
        self.assertEqual(result["format"], "NRO")
        self.assertEqual(result["architecture"], "aarch64-expected")
        self.assertTrue(result["embeddedNacp"])
        damaged = bytearray(make_nro())
        struct.pack_into("<Q", damaged, 0x80 + 24, 0xFFFFFFFF)
        with self.assertRaisesRegex(ValueError, "NACP"):
            inspect_bytes(bytes(damaged))

    def test_nso_is_marker_only_and_truncated_container_is_rejected(self):
        data = b"NSO0" + bytes(0xFC)
        result = inspect_bytes(data)
        self.assertEqual(result["format"], "NSO")
        self.assertIn("marker", result["validationDepth"])
        with self.assertRaisesRegex(ValueError, "truncated"):
            inspect_bytes(b"NSO0" + bytes(8))

    def test_size_limit_and_file_integrity(self):
        data = make_elf()
        with self.assertRaisesRegex(ValueError, "size limit"):
            inspect_bytes(data, len(data) - 1)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "sample.elf"
            path.write_bytes(data)
            result = inspect_file(path)
            self.assertEqual(result["size"], len(data))
            self.assertEqual(result["sha256"], hashlib.sha256(data).hexdigest())


if __name__ == "__main__":
    unittest.main()
