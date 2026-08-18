from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
for path in (
    ROOT / "addons" / "plugin.video.stv" / "resources" / "lib",
    ROOT / "addons" / "script.module.saile.epg" / "lib",
):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from saile_epg.models import EpgChannel
from saile_epg import EpgSyncError
from stv.app.services import AppContainer
from stv.app.sync import sync_live_catalog
from stv.domain.live_channels import (
    build_live_catalog,
    choose_live_variant,
    variant_quality,
)
from stv.domain.models import MediaItem


class LiveChannelCatalogTests(unittest.TestCase):
    def _variant(
        self,
        item_id: str,
        source_name: str,
        category_id: str = "10",
        epg_id: str = "globo.rj.br",
    ) -> MediaItem:
        return MediaItem(
            media_type="live",
            item_id=item_id,
            name="Globo RJ",
            source_name=source_name,
            normalized_name="GLOBO RJ",
            category_id=category_id,
            epg_id=epg_id,
            extension="ts",
        )

    def test_epg_channel_is_promoted_once_with_all_quality_variants(self) -> None:
        epg = (
            EpgChannel(
                "xtream",
                "globo.rj.br",
                "globo.rj.br",
                "Globo Rio de Janeiro",
                "GLOBO RJ",
                "https://img.example/globo.png",
            ),
        )
        unmatched = MediaItem(
            media_type="live",
            item_id="99",
            name="Canal Comunitário",
            source_name="Canal Comunitário",
            normalized_name="CANAL COMUNITARIO",
            category_id="20",
        )
        catalog = build_live_catalog(
            epg,
            (
                self._variant("1", "Globo RJ SD"),
                self._variant("2", "Globo RJ HD"),
                self._variant("3", "Globo RJ FHD"),
                unmatched,
            ),
        )

        self.assertEqual(len(catalog.groups), 1)
        self.assertEqual(catalog.groups[0].channel.display_name, "Globo Rio de Janeiro")
        self.assertEqual([item.item_id for item in catalog.groups[0].variants], ["3", "2", "1"])
        self.assertEqual([item.item_id for item in catalog.unmatched_items], ["99"])

    def test_only_categories_with_unmatched_or_uncached_channels_remain(self) -> None:
        epg = (EpgChannel("xtream", "globo", "globo", "Globo", "GLOBO"),)
        matched = MediaItem(
            "live", "1", "Globo", "10", epg_id="globo", normalized_name="GLOBO"
        )
        unmatched = MediaItem(
            "live", "2", "Canal Local", "20", normalized_name="CANAL LOCAL"
        )
        catalog = build_live_catalog(epg, (matched, unmatched))

        self.assertEqual(catalog.visible_category_ids(("10", "20", "30")), {"20", "30"})
        self.assertEqual(
            catalog.visible_category_ids(("10", "20", "30"), catalog_complete=True),
            {"20"},
        )
        self.assertEqual([item.item_id for item in catalog.unmatched_in_category("20")], ["2"])

    def test_ambiguous_name_without_epg_id_is_not_promoted(self) -> None:
        epg = (
            EpgChannel("xtream", "a", "a", "Globo A", "GLOBO"),
            EpgChannel("xtream", "b", "b", "Globo B", "GLOBO"),
        )
        item = MediaItem("live", "1", "Globo", normalized_name="GLOBO")
        catalog = build_live_catalog(epg, (item,))
        self.assertEqual(catalog.groups, ())
        self.assertEqual(catalog.unmatched_items, (item,))

    def test_selector_respects_bandwidth_and_probe(self) -> None:
        variants = (
            self._variant("4", "Globo RJ 4K"),
            self._variant("3", "Globo RJ FHD"),
            self._variant("2", "Globo RJ HD"),
            self._variant("1", "Globo RJ SD"),
        )
        selected = choose_live_variant(
            variants,
            bandwidth_limit_mbps=10,
            probe=lambda item: {"2": 8.0, "1": 3.0}.get(item.item_id),
        )
        self.assertEqual(variant_quality(selected), (2, "HD"))

    def test_epg_sync_falls_back_to_short_xtream_api(self) -> None:
        calls: list[str] = []

        class FakeEpg:
            def sync_xmltv(self, _url: str) -> object:
                raise EpgSyncError("EPG-PARSE", "XMLTV incompatível")

            def sync_xtream(self, request: object, live_streams: object) -> object:
                self.request = request
                self.live_streams = live_streams
                return {"channel_count": 1, "program_count": 2, "source": "Xtream API"}

        fake_xtream = SimpleNamespace(
            xmltv_url=lambda: "https://protected.invalid/xmltv.php",
            request=lambda action, **_params: calls.append(action) or [{"stream_id": 1}],
        )
        app = AppContainer({})
        app._xtream_client = fake_xtream
        app._epg_service = FakeEpg()

        result = app.sync_epg()

        self.assertEqual(result["source"], "Xtream API")
        self.assertEqual(calls, ["get_live_streams"])

    def test_epg_sync_falls_back_after_unexpected_xmltv_error(self) -> None:
        class FakeEpg:
            def sync_xmltv(self, _url: str) -> object:
                raise TypeError("NoneType object is not callable")

            def sync_xtream(self, request: object, live_streams: object) -> object:
                self.request = request
                self.live_streams = live_streams
                return {"channel_count": 1, "program_count": 1, "source": "Xtream API"}

        fake_xtream = SimpleNamespace(
            xmltv_url=lambda: "https://protected.invalid/xmltv.php",
            request=lambda _action, **_params: [{"stream_id": 1}],
        )
        app = AppContainer({})
        app._xtream_client = fake_xtream
        app._epg_service = FakeEpg()

        result = app.sync_epg()

        self.assertEqual(result["source"], "Xtream API")

    def test_manual_epg_flow_can_refresh_complete_live_catalog(self) -> None:
        calls: list[tuple[str, object]] = []

        class FakeCatalog:
            def begin_catalog_sync(self, sections: object) -> None:
                calls.append(("begin", tuple(sections)))

            def upsert_categories(self, categories: object) -> None:
                calls.append(("categories", len(categories)))

            def upsert_media_items(self, items: object) -> None:
                calls.append(("items", len(items)))

            def clean_obsolete_categories(self, section: str, _generation: int) -> None:
                calls.append(("clean_categories", section))

            def clean_obsolete_items(self, section: str, _generation: int) -> None:
                calls.append(("clean_items", section))

            def mark_catalog_synced(self, section: str, _generation: int) -> None:
                calls.append(("complete", section))

        xtream = SimpleNamespace(
            is_configured=True,
            request=lambda action, **_params: (
                [{"category_id": "10", "category_name": "Abertos"}]
                if action == "get_live_categories"
                else []
            ),
        )
        app = SimpleNamespace(xtream=xtream, catalog=FakeCatalog())
        result = sync_live_catalog(
            app,
            raw_streams=[
                {
                    "stream_id": 1,
                    "name": "Globo HD",
                    "category_id": "10",
                    "epg_channel_id": "globo",
                }
            ],
        )

        self.assertEqual(result, {"category_count": 1, "stream_count": 1})
        self.assertIn(("complete", "live"), calls)


if __name__ == "__main__":
    unittest.main()
