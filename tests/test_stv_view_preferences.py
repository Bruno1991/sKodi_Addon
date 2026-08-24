from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
STV_LIB = ROOT / "addons" / "plugin.video.stv" / "resources" / "lib"
CORE_LIB = ROOT / "addons" / "script.module.saile.core" / "lib"
EPG_LIB = ROOT / "addons" / "script.module.saile.epg" / "lib"
for path in (STV_LIB, CORE_LIB, EPG_LIB):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from stv.app.services import AppContainer
from stv.persistence.database import Database
from stv.persistence.repository import CatalogRepository
from stv.ui.directory import INFOWALL_VIEW_MODE, add_folder, finish_directory, init_directory


class ViewPreferencesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "stv.db")
        self.db = Database(self.db_path)
        self.db.initialize()
        self.repo = CatalogRepository(self.db)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_database_initializes_default_infowall_view_mode(self) -> None:
        mode = self.repo.get_preference("view_mode")
        self.assertEqual(mode, "54")

    def test_database_updates_and_retrieves_view_mode_preference(self) -> None:
        self.repo.set_preference("view_mode", "51")
        self.assertEqual(self.repo.get_preference("view_mode"), "51")

        self.repo.set_preference("view_mode", "54")
        self.assertEqual(self.repo.get_preference("view_mode"), "54")

    def test_app_container_resolves_preferred_view_mode_from_settings_or_db(self) -> None:
        app_default = AppContainer({"profile_path": self.temp_dir.name})
        self.assertEqual(app_default.preferred_view_mode, 54)

        app_custom = AppContainer({"profile_path": self.temp_dir.name, "preferred_view_mode": "500"})
        self.assertEqual(app_custom.preferred_view_mode, 500)

    def test_init_and_finish_directory_enforces_infowall_view_mode(self) -> None:
        calls: list[str] = []
        fake_xbmc = SimpleNamespace(executebuiltin=lambda cmd: calls.append(cmd))
        fake_xbmcplugin = SimpleNamespace(
            SORT_METHOD_UNSORTED=0,
            SORT_METHOD_LABEL_IGNORE_THE=1,
            SORT_METHOD_VIDEO_TITLE=2,
            SORT_METHOD_GENRE=3,
            setContent=lambda *_args: calls.append("setContent"),
            addSortMethod=lambda *_args: None,
            endOfDirectory=lambda *_args, **_kwargs: calls.append("endOfDirectory"),
        )
        with patch.dict(sys.modules, {"xbmc": fake_xbmc, "xbmcplugin": fake_xbmcplugin}):
            init_directory(10, content="movies", view_mode=54)
            finish_directory(10, content="movies", view_mode=54)

        view_cmd = f"Container.SetViewMode({INFOWALL_VIEW_MODE})"
        self.assertIn(view_cmd, calls)
        self.assertEqual(calls.count(view_cmd), 3)  # 1 in init, 2 in finish

    def test_add_folder_sets_poster_fallback_for_infowall(self) -> None:
        created_items: list[object] = []

        class FakeListItem:
            def __init__(self, label: str, label2: str = "", offscreen: bool = True):
                self.label = label
                self.art: dict[str, str] = {}
                self.info: dict[str, object] = {}
                self.props: dict[str, str] = {}
                created_items.append(self)

            def setArt(self, art: dict[str, str]) -> None:
                self.art = art

            def setInfo(self, tag: str, info: dict[str, object]) -> None:
                self.info = info

            def setProperty(self, k: str, v: str) -> None:
                self.props[k] = v

            def addContextMenuItems(self, items: list[tuple[str, str]]) -> None:
                pass

        fake_xbmcgui = SimpleNamespace(ListItem=FakeListItem)
        fake_xbmcplugin = SimpleNamespace(
            addDirectoryItem=lambda handle, url, listitem, isFolder: None
        )
        with patch.dict(sys.modules, {"xbmcgui": fake_xbmcgui, "xbmcplugin": fake_xbmcplugin}):
            add_folder(5, "TV ao Vivo", "plugin://plugin.video.stv/?action=section&section=live", icon="live.png", is_folder=True)

        self.assertEqual(len(created_items), 1)
        item = created_items[0]
        self.assertEqual(item.art.get("poster"), "live.png")
        self.assertEqual(item.art.get("icon"), "live.png")
        self.assertEqual(item.art.get("thumb"), "live.png")


if __name__ == "__main__":
    unittest.main()
