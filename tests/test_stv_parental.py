from __future__ import annotations

import sys
import unittest
from pathlib import Path

LIB_DIR = Path(__file__).resolve().parents[1] / "addons" / "plugin.video.stv" / "resources" / "lib"
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

from stv.parental import is_restricted, get_parental_pin, set_parental_pin


class MockAddon:
    def __init__(self, pin: str = "") -> None:
        self.settings: dict[str, str] = {"parental_pin": pin}

    def getSetting(self, key: str) -> str:
        return self.settings.get(key, "")

    def setSetting(self, key: str, value: str) -> None:
        self.settings[key] = value


class ParentalControlTests(unittest.TestCase):
    def test_restricted_keyword_detection(self) -> None:
        # Positive matches
        self.assertTrue(is_restricted(name="Canal XXX 4K"))
        self.assertTrue(is_restricted(category_name="Filmes Adultos"))
        self.assertTrue(is_restricted(name="Playboy TV HD"))
        self.assertTrue(is_restricted(name="Sessão +18 Noite"))
        self.assertTrue(is_restricted(plot="Conteúdo erótico para maiores de idade"))
        self.assertTrue(is_restricted(tmdb_adult=True))

        # Negative matches
        self.assertFalse(is_restricted(name="Globo SP HD"))
        self.assertFalse(is_restricted(name="Filmes de Ação 2024", category_name="VOD Lançamentos"))
        self.assertFalse(is_restricted(name="Turma da Mônica"))

    def test_pin_storage_and_retrieval(self) -> None:
        addon = MockAddon()
        self.assertEqual(get_parental_pin(addon), "")

        set_parental_pin(addon, "123456")
        self.assertEqual(get_parental_pin(addon), "123456")

        set_parental_pin(addon, "9876")
        self.assertEqual(get_parental_pin(addon), "9876")


if __name__ == "__main__":
    unittest.main()
