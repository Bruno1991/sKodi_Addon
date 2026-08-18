from __future__ import annotations

import sys
import unittest
from pathlib import Path

LIB_DIR = Path(__file__).resolve().parents[1] / "addons" / "plugin.video.stv" / "resources" / "lib"
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

from stv.providers.epg.normalizer import clean_channel_title, normalize_channel_name


class EpgNormalizerTests(unittest.TestCase):
    def test_clean_channel_title(self) -> None:
        cases = [
            ("BR | GLOBO SP FHD [4K]", "Globo SP"),
            ("BR: SPORTV 1 HD (BACKUP)", "SporTV 1"),
            ("TELECINE PREMIUM 4K HEVC", "Telecine Premium"),
            ("[BR] HBO PLUS FHD", "HBO Plus"),
            ("ESPN 4 FHD (VIP)", "ESPN 4"),
            ("DISCOVERY KIDS HD 720P", "Discovery Kids"),
            ("CNN BRASIL HD", "CNN Brasil"),
            ("BANDNEWS 60FPS", "BandNews"),
            ("MEGAPIX FHD", "Megapix"),
            ("CARTOONITO HD", "Cartoonito"),
            ("", ""),
        ]
        for raw, expected in cases:
            with self.subTest(raw=raw):
                self.assertEqual(clean_channel_title(raw), expected)

    def test_normalize_channel_name(self) -> None:
        cases = [
            ("BR | GLOBO SP FHD", "GLOBO"),
            ("GLOBO RJ HD [4K]", "GLOBO"),
            ("GLOBO MINAS FHD", "GLOBO"),
            ("BR: SPORTV 1 HD", "SPORTV"),
            ("SPORTV 2 FHD", "SPORTV 2"),
            ("SPORTV 3 HD [BACKUP]", "SPORTV 3"),
            ("TELECINE PIPOCA FHD", "TELECINE PIPOCA"),
            ("TELECINE ACTION HD", "TELECINE ACTION"),
            ("ESPN BRASIL 4K", "ESPN"),
            ("ESPN 2 FHD", "ESPN 2"),
            ("RECORD SP HD", "RECORD"),
            ("RECORD NEWS HD", "RECORD NEWS"),
            ("SBT SP HD [OPCAO 2]", "SBT"),
            ("BAND SP FHD", "BAND"),
            ("BANDNEWS HD", "BANDNEWS"),
            ("BANDSPORTS HD", "BANDSPORTS"),
            ("DISCOVERY KIDS 720P", "DISCOVERY KIDS"),
            ("GLÓBO SP (LOCAL)", "GLOBO"),
            ("", ""),
        ]
        for raw, expected in cases:
            with self.subTest(raw=raw):
                self.assertEqual(normalize_channel_name(raw), expected)


if __name__ == "__main__":
    unittest.main()
