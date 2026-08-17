from __future__ import annotations

import sqlite3
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STV_LIB = ROOT / "addons" / "plugin.video.stv" / "resources" / "lib"
sys.path.insert(0, str(STV_LIB))

from stv.persistence.database import Database as StvDatabase


def table_names(path: Path) -> set[str]:
    with closing(sqlite3.connect(path)) as connection:
        return {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}


class DatabaseTests(unittest.TestCase):
    def test_stv_schema_initializes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "stv.db"
            StvDatabase(path).initialize()
            names = table_names(path)
            self.assertTrue(
                {"schema_version", "categories", "media_items", "favorites", "playback_progress"} <= names
            )


if __name__ == "__main__":
    unittest.main()
