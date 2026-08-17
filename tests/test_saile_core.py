from __future__ import annotations

import sys
import unittest
from pathlib import Path

LIB_DIR = Path(__file__).resolve().parents[1] / "addons" / "script.module.saile.core" / "lib"
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

from saile_core.artwork import _ALLOWED_SCOPES
from saile_core.capabilities import detect_capabilities
from saile_core.errors import SaileError


class SaileCoreTests(unittest.TestCase):
    def test_allowed_artwork_scopes(self) -> None:
        self.assertEqual(_ALLOWED_SCOPES, frozenset({"common", "stv"}))

    def test_saile_error_formatting(self) -> None:
        err = SaileError("ERR_AUTH", "Falha de autenticação")
        self.assertEqual(err.code, "ERR_AUTH")
        self.assertEqual(err.message, "Falha de autenticação")
        self.assertIn("ERR_AUTH", str(err))

    def test_capabilities_detection(self) -> None:
        caps = detect_capabilities()
        d = caps.to_dict()
        self.assertIn("python", d)
        self.assertIn("sqlite", d)
        self.assertIn("sqlite_fts5", d)


if __name__ == "__main__":
    unittest.main()
