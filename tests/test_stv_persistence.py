from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
LIB_DIR = ROOT / "addons" / "plugin.video.stv" / "resources" / "lib"
EPG_LIB = ROOT / "addons" / "script.module.saile.epg" / "lib"
for path in (LIB_DIR, EPG_LIB):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

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
                epg_id="canal-1.br",
                source_name="BR | CANAL 1 FHD",
                normalized_name="CANAL 1",
                generation_id=1,
            ),
            MediaItem(
                media_type="vod",
                item_id="201",
                name="Matrix Resurrections",
                category_id="2",
                extension="mkv",
                plot="Neo vive uma vida normal sob a identidade de Thomas Anderson",
                generation_id=1,
            ),
        ]
        self.repo.upsert_media_items(items)
        live_items = self.repo.get_media_items("live", "1")
        self.assertEqual(len(live_items), 1)
        self.assertEqual(live_items[0].name, "Canal 1 HD")
        self.assertEqual(live_items[0].epg_id, "canal-1.br")
        self.assertEqual(live_items[0].source_name, "BR | CANAL 1 FHD")
        self.assertEqual(live_items[0].normalized_name, "CANAL 1")

        normalized_results = self.repo.search_media("live", "canal 1 FHD")
        self.assertEqual([item.item_id for item in normalized_results], ["101"])

        # 3. FTS5 Search by keyword / prefix
        search_results = self.repo.search_media("vod", "matrix")
        self.assertEqual(len(search_results), 1)
        self.assertEqual(search_results[0].item_id, "201")

        search_resur = self.repo.search_media("vod", "resur")
        self.assertEqual(len(search_resur), 1)
        self.assertEqual(self.repo.search_media("vod", "inexistente"), [])

        # 4. Favorites toggle
        self.assertTrue(self.repo.toggle_favorite("vod", "201"))  # Added
        favs = self.repo.get_favorites("vod")
        self.assertEqual(len(favs), 1)
        self.assertEqual(favs[0].name, "Matrix Resurrections")

        # 5. Metadata Enrichment
        self.repo.enrich_media_item("vod", "201", plot="Um clássico de ficção", fanart="https://img.com/fan.jpg")
        enriched = self.repo.get_media_items("vod", "2")
        self.assertEqual(enriched[0].plot, "Um clássico de ficção")
        self.assertEqual(enriched[0].fanart, "https://img.com/fan.jpg")

        # 6. Obsolete cleanup with strict favorite removal
        deleted_cats = self.repo.clean_obsolete_categories("live", current_generation=2)
        self.assertEqual(deleted_cats, 1)
        deleted_items = self.repo.clean_obsolete_items("live", current_generation=2)
        self.assertEqual(deleted_items, 1)
        self.assertEqual(len(self.repo.get_categories("live")), 0)

        # Limpeza de catálogo nunca apaga o estado do usuário.
        self.repo.clean_obsolete_items("vod", current_generation=2)
        with self.db.connect() as connection:
            favorite_count = connection.execute(
                "SELECT COUNT(*) AS total FROM favorites WHERE media_type = 'vod'"
            ).fetchone()["total"]
        self.assertEqual(favorite_count, 1)
        self.assertEqual(self.repo.get_favorite_ids("vod"), ["201"])

    def test_playback_progress(self) -> None:
        self.repo.update_playback_progress("vod", "123", 10.5, 100.0)
        progress = self.repo.get_playback_progress("vod", "123")
        self.assertIsNotNone(progress)
        assert progress is not None
        self.assertEqual(progress["position"], 10.5)
        self.assertEqual(progress["total"], 100.0)

    def test_group_favorite_absorbs_legacy_variant_favorite(self) -> None:
        self.repo.add_favorite("live", "101")
        self.assertFalse(
            self.repo.toggle_channel_favorite("globo.rj.br", ("101", "102"))
        )
        self.assertEqual(self.repo.get_favorite_ids("live"), [])

        self.assertTrue(
            self.repo.toggle_channel_favorite("globo.rj.br", ("101", "102"))
        )
        self.assertEqual(self.repo.get_favorite_channel_keys(), ["globo.rj.br"])

    def test_cache_ttl_logic(self) -> None:
        self.assertFalse(self.repo.is_cache_valid("live", 12))
        self.assertFalse(self.repo.is_catalog_complete("live"))

        cat = Category(category_id="1", name="News", media_type="live", generation_id=1)
        self.repo.upsert_categories([cat])

        self.assertTrue(self.repo.is_cache_valid("live", 12))

        with self.db.connect() as conn:
            conn.execute("UPDATE categories SET updated_at = datetime('now', '-24 hours')")

        self.assertFalse(self.repo.is_cache_valid("live", 12))
        self.assertTrue(self.repo.is_cache_valid("live", 48))
        self.repo.mark_catalog_synced("live", 1)
        self.assertTrue(self.repo.is_catalog_complete("live"))
        self.repo.begin_catalog_sync(("live",))
        self.assertFalse(self.repo.is_catalog_complete("live"))

    def test_search_accent_insensitivity_pokemon_and_capitao(self) -> None:
        items = [
            MediaItem(
                media_type="vod",
                item_id="301",
                name="Pokémon: Detetive Pikachu",
                source_name="Pokemon: Detetive Pikachu",
                normalized_name="POKEMON DETETIVE PIKACHU",
                plot="Um filme com Pokémons",
            ),
            MediaItem(
                media_type="vod",
                item_id="302",
                name="Pokemon 2000",
                source_name="Pokemon 2000",
                normalized_name="POKEMON 2000",
                plot="Lugia e os pássaros lendários",
            ),
            MediaItem(
                media_type="vod",
                item_id="303",
                name="Capitão América: Guerra Civil",
                source_name="Capitão América: Guerra Civil",
                normalized_name="CAPITAO AMERICA GUERRA CIVIL",
                plot="Guerra entre heróis",
            ),
            MediaItem(
                media_type="vod",
                item_id="304",
                name="Capitao Fantastico",
                source_name="Capitao Fantastico",
                normalized_name="CAPITAO FANTASTICO",
                plot="Família na floresta",
            ),
            MediaItem(
                media_type="series",
                item_id="305",
                name="Pokémon: A Série",
                source_name="Pokemon: A Serie",
                normalized_name="POKEMON A SERIE",
                plot="Ash e Pikachu",
            ),
        ]
        self.repo.upsert_media_items(items)

        # 1. Busca sem acento "pokemon" retorna ambos os itens VOD
        res_pokemon = self.repo.search_media("vod", "pokemon")
        self.assertEqual({i.item_id for i in res_pokemon}, {"301", "302"})

        # 2. Busca com acento "pokémon" retorna ambos os itens VOD
        res_pokemon_accent = self.repo.search_media("vod", "pokémon")
        self.assertEqual({i.item_id for i in res_pokemon_accent}, {"301", "302"})

        # 3. Busca em maiúsculas com acento "POKÉMON"
        res_pokemon_caps = self.repo.search_media("vod", "POKÉMON")
        self.assertEqual({i.item_id for i in res_pokemon_caps}, {"301", "302"})

        # 4. Busca com pontuação "pokemon: detetive"
        res_pokemon_punct = self.repo.search_media("vod", "pokemon: detetive")
        self.assertEqual([i.item_id for i in res_pokemon_punct], ["301"])

        # 5. Busca "capitao" vs "capitão"
        self.assertEqual({i.item_id for i in self.repo.search_media("vod", "capitao")}, {"303", "304"})
        self.assertEqual({i.item_id for i in self.repo.search_media("vod", "capitão")}, {"303", "304"})
        self.assertEqual({i.item_id for i in self.repo.search_media("vod", "america")}, {"303"})
        self.assertEqual({i.item_id for i in self.repo.search_media("vod", "américa")}, {"303"})

        # 6. Busca em séries
        self.assertEqual([i.item_id for i in self.repo.search_media("series", "pokemon")], ["305"])
        self.assertEqual([i.item_id for i in self.repo.search_media("series", "pokémon")], ["305"])

    def test_search_fallback_when_fts_is_disabled(self) -> None:
        items = [
            MediaItem(
                media_type="vod",
                item_id="401",
                name="Pokémon: O Filme",
                source_name="Pokemon: O Filme",
                normalized_name="POKEMON O FILME",
            ),
            MediaItem(
                media_type="vod",
                item_id="402",
                name="Pokemon Heroes",
                source_name="Pokemon Heroes",
                normalized_name="POKEMON HEROES",
            ),
        ]
        self.repo.upsert_media_items(items)

        # Força desativação temporária do FTS no repo
        with tempfile.TemporaryDirectory() as tmp:
            custom_db = Database(Path(tmp) / "no_fts.db")
            custom_db.initialize()
            custom_db.fts_available = False
            custom_repo = CatalogRepository(custom_db)
            custom_repo.upsert_media_items(items)

            # Mesmo sem FTS5 (fallback LIKE puro com normalização), a busca insensível a acentos funciona 100%
            res_without_accent = custom_repo.search_media("vod", "pokemon")
            self.assertEqual({i.item_id for i in res_without_accent}, {"401", "402"})

            res_with_accent = custom_repo.search_media("vod", "pokémon")
            self.assertEqual({i.item_id for i in res_with_accent}, {"401", "402"})

    def test_database_initializes_and_upserts_when_fts5_is_completely_absent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            custom_db = Database(Path(tmp) / "no_fts_simulated.db")
            with patch("stv.persistence.database._setup_fts", return_value=False):
                custom_db.initialize()
                self.assertFalse(custom_db.fts_available)
                custom_repo = CatalogRepository(custom_db)
                items = [
                    MediaItem("live", "99", "Canal Teste", "10", normalized_name="CANAL TESTE")
                ]
                custom_repo.upsert_media_items(items)
                found = custom_repo.get_all_media_items("live")
                self.assertEqual(len(found), 1)
                self.assertEqual(found[0].name, "Canal Teste")

    def test_database_optimize(self) -> None:
        self.repo.optimize()
        self.db.optimize()


if __name__ == "__main__":
    unittest.main()

