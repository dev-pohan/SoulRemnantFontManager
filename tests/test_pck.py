import hashlib
import struct
import tempfile
from pathlib import Path
from unittest import TestCase

from srfontmanager import pck


def make_pck(path: Path, entries: dict[str, bytes]) -> None:
    header = bytearray(40)
    header[:4] = b"GDPC"
    struct.pack_into("<5I", header, 4, 4, 4, 7, 0, 0)
    struct.pack_into("<Q", header, 24, 40)
    directory = bytearray(struct.pack("<I", len(entries)))
    body = bytearray()
    for name, data in entries.items():
        offset = len(body)
        body += data
        body += b"\0" * ((-(40 + len(body))) % 16)
        encoded = name.encode() + b"\0"
        directory += struct.pack("<I", len(encoded)) + encoded
        directory += struct.pack("<QQ", offset, len(data))
        directory += hashlib.md5(data).digest() + struct.pack("<I", 0)
    directory_offset = 40 + len(body)
    struct.pack_into("<Q", header, 32, directory_offset)
    path.write_bytes(header + body + directory)


class PckTests(TestCase):
    def test_delta_install_update_and_restore(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / pck.PCK_NAME
            make_pck(target, {"a.txt": b"original", "b.txt": b"untouched"})
            original_hash = pck.sha256_file(target)
            self.assertEqual(pck.install(root, {"a.txt": b"patched"}), "installed")
            self.assertEqual(pck.status(root), "installed")
            self.assertEqual(pck.install(root, {"a.txt": b"patched"}), "already-installed")
            self.assertEqual(pck.install(root, {"a.txt": b"patched-again"}), "installed")
            self.assertEqual(pck.read_base_entries(root, ["a.txt"])["a.txt"], b"original")
            self.assertEqual(pck.uninstall(root), "restored")
            self.assertEqual(pck.sha256_file(target), original_hash)

