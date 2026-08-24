from __future__ import annotations

import sqlite3
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STV_LIB = ROOT / "addons" / "plugin.video.stv" / "resources" / "lib"
EPG_LIB = ROOT / "addons" / "script.module.saile.epg" / "lib"
sys.path.insert(0, str(STV_LIB))
sys.path.insert(0, str(EPG_LIB))

from stv.persistence.database import Database as StvDatabase
from saile_epg.database import EpgDatabase


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
                {
                    "schema_version",
                    "categories",
                    "media_items",
                    "favorites",
                    "live_channel_favorites",
                    "catalog_sync_state",
                    "playback_progress",
                }
                <= names
            )
            self.assertNotIn("epg_programs", names)

    def test_epg_schema_is_owned_by_module(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "epg.db"
            EpgDatabase(path).initialize()
            names = table_names(path)
            self.assertTrue(
                {"schema_version", "epg_channels", "epg_programs", "epg_sync_state"} <= names
            )

    def test_stv_v3_migration_adds_epg_reference_without_deleting_database(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "stv.db"
            with closing(sqlite3.connect(path)) as connection:
                connection.executescript(
                    """
                    CREATE TABLE schema_version (version INTEGER NOT NULL);
                    INSERT INTO schema_version(version) VALUES (3);
                    CREATE TABLE media_items (
                        media_type TEXT NOT NULL,
                        item_id TEXT NOT NULL,
                        category_id TEXT NOT NULL DEFAULT '',
                        name TEXT NOT NULL,
                        icon TEXT NOT NULL DEFAULT '',
                        fanart TEXT NOT NULL DEFAULT '',
                        plot TEXT NOT NULL DEFAULT '',
                        extension TEXT NOT NULL DEFAULT '',
                        payload_json TEXT NOT NULL DEFAULT '{}',
                        generation_id INTEGER NOT NULL DEFAULT 0,
                        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (media_type, item_id)
                    );
                    INSERT INTO media_items(media_type, item_id, name)
                    VALUES ('live', '1', 'BR | GLOBO SP FHD [VIP]');
                    CREATE TABLE favorites (
                        media_type TEXT NOT NULL,
                        item_id TEXT NOT NULL,
                        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (media_type, item_id)
                    );
                    INSERT INTO favorites(media_type, item_id) VALUES ('live', '1');
                    CREATE TABLE epg_programs(channel_key TEXT, start_time TEXT);
                    """
                )

            StvDatabase(path).initialize()
            with closing(sqlite3.connect(path)) as connection:
                columns = {row[1] for row in connection.execute("PRAGMA table_info(media_items)")}
                version = connection.execute("SELECT version FROM schema_version").fetchone()[0]
                preserved = connection.execute(
                    "SELECT name, source_name, normalized_name FROM media_items WHERE item_id = '1'"
                ).fetchone()
                favorite_count = connection.execute(
                    "SELECT COUNT(*) FROM favorites WHERE media_type = 'live' AND item_id = '1'"
                ).fetchone()[0]
            self.assertIn("epg_id", columns)
            self.assertIn("source_name", columns)
            self.assertIn("normalized_name", columns)
            self.assertEqual(version, 8)
            self.assertEqual(preserved, ("Globo SP", "BR | GLOBO SP FHD [VIP]", "GLOBO SP"))
            self.assertEqual(favorite_count, 1)
            self.assertNotIn("epg_programs", table_names(path))

    def test_stv_v7_to_v8_migration_populates_vod_and_series_normalized_names(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "stv.db"
            with closing(sqlite3.connect(path)) as connection:
                connection.executescript(
                    """
                    CREATE TABLE schema_version (version INTEGER NOT NULL);
                    INSERT INTO schema_version(version) VALUES (7);
                    CREATE TABLE media_items (
                        media_type TEXT NOT NULL,
                        item_id TEXT NOT NULL,
                        category_id TEXT NOT NULL DEFAULT '',
                        name TEXT NOT NULL,
                        icon TEXT NOT NULL DEFAULT '',
                        fanart TEXT NOT NULL DEFAULT '',
                        plot TEXT NOT NULL DEFAULT '',
                        extension TEXT NOT NULL DEFAULT '',
                        epg_id TEXT NOT NULL DEFAULT '',
                        source_name TEXT NOT NULL DEFAULT '',
                        normalized_name TEXT NOT NULL DEFAULT '',
                        payload_json TEXT NOT NULL DEFAULT '{}',
                        generation_id INTEGER NOT NULL DEFAULT 0,
                        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (media_type, item_id)
                    );
                    INSERT INTO media_items(media_type, item_id, name, source_name, normalized_name)
                    VALUES 
                        ('vod', '10', 'Pokémon: Detetive Pikachu', 'Pokemon Detetive Pikachu', ''),
                        ('series', '20', 'Capitão América', 'Capitão América', '');
                    CREATE TABLE favorites (
                        media_type TEXT NOT NULL,
                        item_id TEXT NOT NULL,
                        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (media_type, item_id)
                    );
                    CREATE TABLE categories (
                        media_type TEXT NOT NULL,
                        category_id TEXT NOT NULL,
                        name TEXT NOT NULL,
                        parent_id TEXT NOT NULL DEFAULT '0',
                        generation_id INTEGER NOT NULL DEFAULT 0,
                        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (media_type, category_id)
                    );
                    """
                )

            db = StvDatabase(path)
            db.initialize()
            db.optimize()
            with closing(sqlite3.connect(path)) as connection:
                version = connection.execute("SELECT version FROM schema_version").fetchone()[0]
                vod_row = connection.execute(
                    "SELECT normalized_name FROM media_items WHERE item_id = '10'"
                ).fetchone()[0]
                series_row = connection.execute(
                    "SELECT normalized_name FROM media_items WHERE item_id = '20'"
                ).fetchone()[0]
                indices = {row[1] for row in connection.execute("PRAGMA index_list(favorites)")}
                cat_indices = {row[1] for row in connection.execute("PRAGMA index_list(categories)")}

            self.assertEqual(version, 8)
            self.assertEqual(vod_row, "POKEMON DETETIVE PIKACHU")
            self.assertEqual(series_row, "CAPITAO AMERICA")
            self.assertIn("idx_favorites_order", indices)
            self.assertIn("idx_categories_order", cat_indices)


if __name__ == "__main__":
    unittest.main()
