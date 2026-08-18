from __future__ import annotations

import sys
import unittest
from pathlib import Path

EPG_LIB = Path(__file__).resolve().parents[1] / "addons" / "script.module.saile.epg" / "lib"
if str(EPG_LIB) not in sys.path:
    sys.path.insert(0, str(EPG_LIB))

from saile_epg.normalizer import clean_channel_title, normalize_channel_name


class EpgNormalizerTests(unittest.TestCase):
    def test_clean_channel_title(self) -> None:
        cases = [
            ("BR | GLOBO SP FHD [4K]", "Globo SP"),
            ("BR: SPORTV 1 HD (BACKUP)", "SporTV 1"),
            ("TELECINE PREMIUM 4K HEVC", "Telecine Premium"),
            ("[BR] HBO PLUS FHD", "HBO Plus"),
            ("", ""),
        ]
        for raw, expected in cases:
            with self.subTest(raw=raw):
                self.assertEqual(clean_channel_title(raw), expected)

    def test_normalize_channel_name_preserves_regional_identity(self) -> None:
        self.assertEqual(normalize_channel_name("BR | GLOBO SP FHD"), "GLOBO SP")
        self.assertEqual(normalize_channel_name("Globo São Paulo HD"), "GLOBO SAO PAULO")
        self.assertEqual(normalize_channel_name("SPORTV 2 FHD"), "SPORTV 2")

    def test_quality_variants_share_canonical_channel_key(self) -> None:
        variants = (
            "BR | GLOBO RJ 4K HEVC",
            "Globo RJ FHD",
            "GLOBO RJ HD [BACKUP]",
            "Globo RJ SD",
        )
        self.assertEqual(
            {normalize_channel_name(name) for name in variants},
            {"GLOBO RJ"},
        )
        self.assertEqual(
            {clean_channel_title(name) for name in variants},
            {"Globo RJ"},
        )


if __name__ == "__main__":
    unittest.main()
