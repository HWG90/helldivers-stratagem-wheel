import struct
import unittest
import zipfile
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import build


class PackageTest(unittest.TestCase):
    def test_addon_envelope_and_entry(self):
        with zipfile.ZipFile(ROOT / 'EquippedStratagems.zip') as z:
            self.assertEqual(set(z.namelist()), {
                'manifest.json', 'INSTALL.txt', 'Addon/' + build.ARCHIVE,
                'Addon/' + build.ARCHIVE + '.stream',
                'Addon/' + build.ARCHIVE + '.gpu_resources',
            })
            blob = z.read('Addon/' + build.ARCHIVE)
            magic, types, count = struct.unpack_from('<III', blob)
            self.assertEqual((magic, types, count), (0xf0000011, 1, 1))
            entry = struct.unpack_from('<7Q6I', blob, 104)
            self.assertEqual(entry[:2], (build.resource_hash(build.RESOURCE), build.TYPE))
            payload = blob[entry[2]:entry[2] + entry[7]]
            size, version = struct.unpack_from('<II', payload)
            self.assertEqual(version, 2)
            self.assertEqual(size, len(payload) - 8)
            self.assertEqual(payload[8:], (ROOT / 'EquippedStratagems.lua').read_bytes())
            self.assertEqual(z.read('INSTALL.txt'), (ROOT / 'INSTALL.txt').read_bytes())


if __name__ == '__main__':
    unittest.main()
