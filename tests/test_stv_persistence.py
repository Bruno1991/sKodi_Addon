from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

LIB_DIR = Path(__file__).resolve().parents[1] / "addons" / "plugin.video.stv" / "resources" / "lib"
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

from stv.domain.models import Category, MediaItem
from stv.persistence.database import Database
from stv.persistence.repository import CatalogRepository


class PersistenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.temp_dir.name) / "test.db")
        self.db.initialize()
        self.repo = CatalogRepository(self.db)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_categories_and_items_lifecycle(self) -> None:
        # 1. Upsert categories
        cats = [
            Category(category_id="1", name="Canais Abertos", media_type="live", generation_id=1),
            Category(category_id="2", name="Filmes Ação", media_type="vod", generation_id=1),
        ]
        self.repo.upsert_categories(cats)
        live_cats = self.repo.get_categories("live")
        self.assertEqual(len(live_cats), 1)
        self.assertEqual(live_cats[0].name, "Canais Abertos")

        # 2. Upsert media items
        items = [
            MediaItem(
                media_type="live",
                item_id="101",
                name="Canal 1 HD",
                category_id="1",
                extension="ts",
                generation_id=1,
            ),
            MediaItem(
                media_type="vod",
                item_id="201",
                name="Matrix",
                category_id="2",
                extension="mkv",
                generation_id=1,
            ),
        ]
        self.repo.upsert_media_items(items)
        live_items = self.repo.get_media_items("live", "1")
        self.assertEqual(len(live_items), 1)
        self.assertEqual(live_items[0].name, "Canal 1 HD")

        # 3. Search
        search_results = self.repo.search_media("vod", "matr")
        self.assertEqual(len(search_results), 1)
        self.assertEqual(search_results[0].item_id, "201")

        # 4. Favorites toggle
        self.assertTrue(self.repo.toggle_favorite("vod", "201"))  # Added
        favs = self.repo.get_favorites("vod")
        self.assertEqual(len(favs), 1)
        self.assertEqual(favs[0].name, "Matrix")
        self.assertFalse(self.repo.toggle_favorite("vod", "201"))  # Removed
        self.assertEqual(len(self.repo.get_favorites("vod")), 0)

        # 5. Metadata Enrichment
        self.repo.enrich_media_item("vod", "201", plot="Um clássico de ficção", fanart="https://img.com/fan.jpg")
        enriched = self.repo.get_media_items("vod", "2")
        self.assertEqual(enriched[0].plot, "Um clássico de ficção")
        self.assertEqual(enriched[0].fanart, "https://img.com/fan.jpg")

        # 6. Obsolete cleanup
        deleted_cats = self.repo.clean_obsolete_categories("live", current_generation=2)
        self.assertEqual(deleted_cats, 1)
        deleted_items = self.repo.clean_obsolete_items("live", current_generation=2)
        self.assertEqual(deleted_items, 1)
        self.assertEqual(len(self.repo.get_categories("live")), 0)

    def test_playback_progress(self) -> None:
        self.repo.update_playback_progress("vod", "123", 10.5, 100.0)
        progress = self.repo.get_playback_progress("vod", "123")
        self.assertIsNotNone(progress)
        assert progress is not None
        self.assertEqual(progress["position"], 10.5)
        self.assertEqual(progress["total"], 100.0)

    def test_cache_ttl_logic(self) -> None:
        self.assertFalse(self.repo.is_cache_valid("live", 12))

        cat = Category(category_id="1", name="News", media_type="live", generation_id=1)
        self.repo.upsert_categories([cat])

        self.assertTrue(self.repo.is_cache_valid("live", 12))

        with self.db.connect() as conn:
            conn.execute("UPDATE categories SET updated_at = datetime('now', '-24 hours')")

        self.assertFalse(self.repo.is_cache_valid("live", 12))
        self.assertTrue(self.repo.is_cache_valid("live", 48))


if __name__ == "__main__":
    unittest.main()
