from __future__ import annotations

import gzip
import io
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from urllib.error import URLError

ROOT = Path(__file__).resolve().parents[1]
STV_LIB = ROOT / "addons" / "plugin.video.stv" / "resources" / "lib"
SRADIO_LIB = ROOT / "addons" / "plugin.audio.sradio" / "resources" / "lib"
CORE_LIB = ROOT / "addons" / "script.module.saile.core" / "lib"
EPG_LIB = ROOT / "addons" / "script.module.saile.epg" / "lib"
for _lib in (STV_LIB, SRADIO_LIB, CORE_LIB, EPG_LIB):
    if str(_lib) not in sys.path:
        sys.path.insert(0, str(_lib))

from saile_core.notifications import sanitize_error_message
from saile_epg import EpgChannel, EpgProgram, EpgService, EpgSnapshot, normalize_channel_name
from saile_epg.providers.claro import ClaroEpgProvider, _fetch_claro_live_channels
from sradio.bootstrap import handle_play as sradio_handle_play
from sradio.bootstrap import handle_search as sradio_handle_search
from sradio.catalog import RadioCatalog, TuneInAPI, _SafeRedirectHandler
from sradio.favorites import FavoritesManager
from sradio.routing import Request as SRadioRequest
from stv.app.lan_sync import apply_import_payload, build_export_payload
from stv.app.services import AppContainer
from stv.bootstrap import _play_item, _play_live_channel, _show_search
from stv.domain.models import Category, MediaItem
from stv.infrastructure.http import HttpClient
from stv.infrastructure.http import _SafeRedirectHandler as StvSafeRedirectHandler
from stv.routing import Request as StvRequest
from stv.ui.dialogs import show_sync_dialog


class _FakeHttpResponse:
    def __init__(self, payload: bytes, encoding: str = "") -> None:
        self._buf = io.BytesIO(payload)
        self._encoding = encoding

    def read(self, size: int = -1) -> bytes:
        return self._buf.read(size)

    def info(self) -> dict[str, str]:
        return {"Content-Encoding": self._encoding} if self._encoding else {}

    def __enter__(self) -> _FakeHttpResponse:
        return self

    def __exit__(self, *_args: object) -> None:
        return None


class ErrorSanitizationTests(unittest.TestCase):
    def test_redacts_urls_credentials_and_local_paths(self) -> None:
        raw_err = RuntimeError(
            "Erro em http://painel.exemplo.com:8080/live/meu_user/minha_senha/101.ts "
            "password=segredo123 token:abc999 em C:\\Users\\admin\\stv.db e /storage/emulated/0/x"
        )
        cleaned = sanitize_error_message(raw_err)
        self.assertNotIn("meu_user", cleaned)
        self.assertNotIn("minha_senha", cleaned)
        self.assertNotIn("segredo123", cleaned)
        self.assertNotIn("abc999", cleaned)
        self.assertNotIn("painel.exemplo.com", cleaned)
        self.assertNotIn("C:\\Users", cleaned)
        self.assertNotIn("/storage/emulated", cleaned)
        self.assertIn("[URL]", cleaned)

    def test_empty_message_uses_fallback_and_long_message_truncates(self) -> None:
        self.assertEqual(sanitize_error_message("", fallback="Falha"), "Falha")
        very_long = "Erro " + ("x" * 300)
        self.assertLessEqual(len(sanitize_error_message(very_long)), 160)


class BatchEpgResolutionTests(unittest.TestCase):
    def test_get_items_epg_schedule_eliminates_n_plus_1_sqlite_connections(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            epg = EpgService.for_profile(tmp)
            now = 1_700_000_500
            channels = tuple(
                EpgChannel(
                    provider_id="claro",
                    channel_key=f"claro_{idx}",
                    epg_id=f"id_{idx}",
                    display_name=f"Emissora {idx}",
                    normalized_name=normalize_channel_name(f"Emissora {idx}"),
                )
                for idx in range(50)
            )
            programs = tuple(
                EpgProgram(
                    provider_id="claro",
                    channel_key=f"claro_{idx}",
                    title=f"Programa {idx}",
                    start_utc=now - 300,
                    end_utc=now + 1500,
                )
                for idx in range(50)
            )
            epg.repository.replace_snapshot(
                EpgSnapshot(
                    provider_id="claro",
                    channels=channels,
                    programs=programs,
                    fetched_at_utc=now,
                )
            )

            app = AppContainer({"profile_path": tmp, "epg_profile_path": tmp})
            app._epg_service = epg

            items = [
                MediaItem(
                    media_type="live",
                    item_id=str(1000 + idx),
                    name=f"Emissora {idx} FHD",
                    epg_id=f"id_{idx}" if idx % 2 == 0 else "",
                )
                for idx in range(50)
            ]

            connect_calls = 0
            orig_connect = epg.database.connect

            def tracked_connect():
                nonlocal connect_calls
                connect_calls += 1
                return orig_connect()

            with (
                patch.object(epg.database, "connect", side_effect=tracked_connect),
                patch("saile_epg.repository.time.time", return_value=now),
            ):
                schedule = app.get_items_epg_schedule(items)

            self.assertEqual(len(schedule), 50)
            # 1 conexão para resolve_channels_many + 1 conexão para get_now_next_many (antes: 51)
            self.assertLessEqual(connect_calls, 2)
            for idx in range(50):
                cur, _nxt = schedule[str(1000 + idx)]
                self.assertIsNotNone(cur)
                assert cur is not None
                self.assertEqual(cur.title, f"Programa {idx}")


class HttpHardeningTests(unittest.TestCase):
    def test_stv_http_client_blocks_non_http_and_oversized_or_gzip_bomb(self) -> None:
        client = HttpClient(max_response_bytes=1024)
        with self.assertRaises(ValueError):
            client.get_raw("file:///etc/passwd")
        with self.assertRaises(ValueError):
            client.get_raw("ftp://example.com/list.m3u")
        self.assertIsNone(client.probe_stream("file:///etc/passwd"))

        redirect_handler = StvSafeRedirectHandler()
        req = MagicMock()
        with self.assertRaises(URLError):
            redirect_handler.redirect_request(req, None, 302, "Found", {}, "file:///etc/passwd")

        # Resposta simples acima do teto
        oversized = _FakeHttpResponse(b"a" * 2048)
        with patch.object(client._opener, "open", return_value=oversized):
            with self.assertRaises(RuntimeError):
                client.get_raw("http://example.com/api")

        # Gzip bomb: comprimido < 1024 bytes, descomprimido > 1024 bytes
        compressed_bomb = gzip.compress(b"z" * 8192)
        self.assertLess(len(compressed_bomb), 1024)
        bomb_resp = _FakeHttpResponse(compressed_bomb, encoding="gzip")
        with patch.object(client._opener, "open", return_value=bomb_resp):
            with self.assertRaises(RuntimeError):
                client.get_raw("http://example.com/bomb")

    def test_sradio_tunein_blocks_non_http_redirects_and_oversized_payload(self) -> None:
        self.assertIsNone(TuneInAPI._fetch_json("file:///etc/passwd"))
        self.assertIsNone(TuneInAPI._fetch_json("ftp://radiotime.com/Browse.ashx"))

        handler = _SafeRedirectHandler()
        with self.assertRaises(URLError):
            handler.redirect_request(MagicMock(), None, 301, "Moved", {}, "file:///sdcard/secret")

        huge = _FakeHttpResponse(b"x" * (TuneInAPI.MAX_RESPONSE_BYTES + 10))
        with patch("sradio.catalog._HTTP_OPENER.open", return_value=huge):
            self.assertIsNone(TuneInAPI._fetch_json("http://opml.radiotime.com/Browse.ashx"))


class ClaroNullAndTimestampTests(unittest.TestCase):
    def test_claro_handles_null_response_null_schedules_and_bool_timestamps(self) -> None:
        with patch(
            "urllib.request.urlopen",
            return_value=_FakeHttpResponse(b'{"response": null}'),
        ):
            self.assertEqual(
                _fetch_claro_live_channels("https://www.clarotvmais.com.br/epg", {}, 5.0),
                [],
            )

        provider = ClaroEpgProvider()
        channel_map: dict[str, EpgChannel] = {}
        programs: list[EpgProgram] = []
        dedup: set[tuple[str, int]] = set()
        provider._parse_live_channels_data(
            [
                {"id": "1", "name": "Canal Null Schedules", "schedules": None},
                {
                    "id": "2",
                    "name": "Canal Timestamps",
                    "schedules": [
                        {"title": "Bool Invalido", "startTime": True, "endTime": 2000},
                        {
                            "title": "String Valida",
                            "startTime": "1700000000",
                            "endTime": "1700003600",
                        },
                    ],
                },
            ],
            channel_map,
            programs,
            dedup,
        )
        self.assertEqual(len(programs), 1)
        self.assertEqual(programs[0].title, "String Valida")
        self.assertEqual(programs[0].start_utc, 1700000000)


class ParentalAndPlayResilienceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.app = AppContainer(
            {
                "profile_path": self.tmp.name,
                "xtream_url": "http://iptv.local:8080",
                "xtream_username": "u1",
                "xtream_password": "p1",
            }
        )
        self.app.catalog.upsert_categories(
            [Category(category_id="99", name="Adultos +18", media_type="vod", generation_id=1)]
        )
        self.app.catalog.upsert_media_items(
            [
                MediaItem(
                    media_type="vod",
                    item_id="500",
                    name="Titulo Neutro Sem Palavra Chave",
                    category_id="99",
                    extension="mp4",
                    generation_id=1,
                )
            ]
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_play_item_blocks_neutral_title_inside_adult_category_when_pin_denied(self) -> None:
        resolved: list[tuple[int, bool]] = []
        fake_xbmcaddon = SimpleNamespace(Addon=lambda *_a: SimpleNamespace())
        fake_xbmcgui = SimpleNamespace(ListItem=lambda **_kw: SimpleNamespace())
        fake_xbmcplugin = SimpleNamespace(
            setResolvedUrl=lambda h, ok, _li: resolved.append((h, ok))
        )

        req = StvRequest.from_argv(["plugin://plugin.video.stv/", "7", "?action=play"])
        fake_player_mod = SimpleNamespace(play_video=MagicMock())
        with (
            patch.dict(
                sys.modules,
                {
                    "xbmcaddon": fake_xbmcaddon,
                    "xbmcgui": fake_xbmcgui,
                    "xbmcplugin": fake_xbmcplugin,
                    "stv.ui.player": fake_player_mod,
                },
            ),
            patch("stv.bootstrap.verify_parental_pin", return_value=False) as mock_pin,
        ):
            _play_item(req, self.app, "vod", "500", "mp4", title="Titulo Neutro Sem Palavra Chave")

        mock_pin.assert_called_once()
        fake_player_mod.play_video.assert_not_called()
        self.assertEqual(resolved, [(7, False)])

    def test_play_live_channel_fails_gracefully_and_sanitizes_errors(self) -> None:
        resolved: list[tuple[int, bool]] = []
        notifications: list[str] = []
        fake_xbmcaddon = SimpleNamespace(Addon=lambda *_a: SimpleNamespace())
        fake_xbmcgui = SimpleNamespace(
            ListItem=lambda **_kw: SimpleNamespace(),
            Dialog=lambda: SimpleNamespace(
                notification=lambda _t, msg, *_rest: notifications.append(msg)
            ),
        )
        fake_xbmcplugin = SimpleNamespace(
            setResolvedUrl=lambda h, ok, _li: resolved.append((h, ok))
        )

        req = StvRequest.from_argv(["plugin://plugin.video.stv/", "9", "?action=play_channel"])
        with (
            patch.dict(
                sys.modules,
                {
                    "xbmcaddon": fake_xbmcaddon,
                    "xbmcgui": fake_xbmcgui,
                    "xbmcplugin": fake_xbmcplugin,
                },
            ),
            patch.object(
                self.app,
                "choose_live_variant",
                side_effect=ValueError("Falha em http://iptv.local:8080/live/u1/p1/9.ts"),
            ),
        ):
            _play_live_channel(req, self.app, "claro_globo", "Globo")

        self.assertEqual(resolved, [(9, False)])
        self.assertEqual(len(notifications), 1)
        self.assertNotIn("u1/p1", notifications[0])
        self.assertIn("[URL]", notifications[0])


class LanSyncChannelFavoritesAndTombstonesTests(unittest.TestCase):
    def test_exports_and_imports_channel_favorites_and_applies_deletions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp1, tempfile.TemporaryDirectory() as tmp2:
            app_a = AppContainer({"profile_path": tmp1})
            app_a.catalog.add_favorite("vod", "101")
            app_a.catalog.add_channel_favorite("claro_sportv")

            exported = build_export_payload(app_a)
            app_b = AppContainer({"profile_path": tmp2})
            app_b.catalog.add_favorite("live", "old_fav")
            app_b.catalog.add_channel_favorite("claro_old_ch")

            res1 = apply_import_payload(app_b, exported)
            self.assertEqual(res1["favorites_applied"], 2)
            self.assertIn("101", app_b.catalog.get_favorite_ids("vod"))
            self.assertIn("claro_sportv", app_b.catalog.get_favorite_channel_keys())

            tombstone_payload = {
                "protocol_version": 1,
                "addon_id": "plugin.video.stv",
                "device_id": "peer-2",
                "entities": [
                    {"entity": "favorite", "scope": "live", "key": "old_fav", "deleted": True},
                    {
                        "entity": "channel_favorite",
                        "scope": "live_channel",
                        "key": "claro_old_ch",
                        "deleted": True,
                    },
                ],
            }
            res2 = apply_import_payload(app_b, tombstone_payload)
            self.assertEqual(res2["favorites_removed"], 2)
            self.assertNotIn("old_fav", app_b.catalog.get_favorite_ids("live"))
            self.assertNotIn("claro_old_ch", app_b.catalog.get_favorite_channel_keys())


class UiDialogsAndSearchNavigationTests(unittest.TestCase):
    def test_stv_search_cancel_and_confirm_update(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            app = AppContainer({"profile_path": tmp})
            ended: list[bool] = []
            builtins: list[str] = []

            class CancelledKeyboard:
                def __init__(self, *_a: object) -> None:
                    pass

                def doModal(self) -> None:
                    pass

                def isConfirmed(self) -> bool:
                    return False

                def getText(self) -> str:
                    return ""

            class ConfirmedKeyboard(CancelledKeyboard):
                def isConfirmed(self) -> bool:
                    return True

                def getText(self) -> str:
                    return "Matrix"

            fake_xbmc = SimpleNamespace(
                Keyboard=CancelledKeyboard,
                executebuiltin=lambda cmd: builtins.append(cmd),
            )
            fake_xbmcplugin = SimpleNamespace(
                endOfDirectory=lambda _h, succeeded=True, **_kw: ended.append(succeeded)
            )

            req = StvRequest.from_argv(
                ["plugin://plugin.video.stv/", "4", "?action=search&section=vod"]
            )
            with patch.dict(sys.modules, {"xbmc": fake_xbmc, "xbmcplugin": fake_xbmcplugin}):
                _show_search(req, app, "vod", "")
                self.assertEqual(ended, [False])
                self.assertEqual(builtins, [])

                fake_xbmc.Keyboard = ConfirmedKeyboard
                _show_search(req, app, "vod", "")
                self.assertEqual(ended, [False, False])
                self.assertEqual(len(builtins), 1)
                self.assertIn("Container.Update(", builtins[0])
                self.assertIn("query=Matrix", builtins[0])

    def test_sync_dialog_export_import_and_clear_cache(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            app = AppContainer({"profile_path": tmp})
            app.catalog.add_favorite("vod", "888")
            notifications: list[str] = []
            refreshes: list[str] = []
            selected_choice = 4

            class FakeDialog:
                def select(self, *_a: object) -> int:
                    return selected_choice

                def yesno(self, *_a: object) -> bool:
                    return True

                def ok(self, *_a: object) -> None:
                    pass

                def notification(self, _t: str, msg: str, *_r: object) -> None:
                    notifications.append(msg)

            fake_xbmc = SimpleNamespace(executebuiltin=lambda cmd: refreshes.append(cmd))
            fake_xbmcgui = SimpleNamespace(Dialog=FakeDialog, DialogProgress=MagicMock)

            with patch.dict(sys.modules, {"xbmc": fake_xbmc, "xbmcgui": fake_xbmcgui}):
                # Opção 4: Exportar backup
                show_sync_dialog(app)
                self.assertTrue((Path(tmp) / "stv_backup.json").is_file())

                # Remove favorito e restaura via Opção 5: Importar backup
                app.catalog.remove_favorite("vod", "888")
                selected_choice = 5
                show_sync_dialog(app)
                self.assertIn("888", app.catalog.get_favorite_ids("vod"))

                # Opção 6: Limpar cache local preservando favoritos
                app.catalog.upsert_categories(
                    [Category(category_id="1", name="Filmes", media_type="vod", generation_id=1)]
                )
                app._epg_service = MagicMock()
                selected_choice = 6
                show_sync_dialog(app)
                self.assertEqual(app.catalog.get_categories("vod"), [])
                self.assertIn("888", app.catalog.get_favorite_ids("vod"))

    def test_sradio_play_negative_handle_and_search_cancel(self) -> None:
        resolved_calls: list[int] = []
        end_calls: list[tuple[int, bool]] = []
        fake_xbmc = SimpleNamespace(executebuiltin=lambda _c: None)
        fake_xbmcgui = SimpleNamespace(
            ListItem=lambda **_kw: SimpleNamespace(),
            INPUT_ALPHANUM=0,
            Dialog=lambda: SimpleNamespace(
                notification=lambda *_a: None,
                input=lambda *_a, **_kw: "",
            ),
        )
        fake_xbmcplugin = SimpleNamespace(
            setResolvedUrl=lambda h, *_a: resolved_calls.append(h),
            endOfDirectory=lambda h, succeeded=True, **_kw: end_calls.append((h, succeeded)),
        )

        catalog = MagicMock(spec=RadioCatalog)
        catalog.get_station.return_value = None
        catalog.resolve_station_stream.return_value = None
        favorites = MagicMock(spec=FavoritesManager)

        with patch.dict(
            sys.modules,
            {"xbmc": fake_xbmc, "xbmcgui": fake_xbmcgui, "xbmcplugin": fake_xbmcplugin},
        ):
            # handle = -1 não deve chamar setResolvedUrl
            req_neg = SRadioRequest.from_argv(
                ["plugin://plugin.audio.sradio/", "-1", "?action=play"]
            )
            sradio_handle_play(req_neg, catalog)
            self.assertEqual(resolved_calls, [])

            # handle = 3 deve chamar setResolvedUrl(3, False, ...)
            req_pos = SRadioRequest.from_argv(
                ["plugin://plugin.audio.sradio/", "3", "?action=play"]
            )
            sradio_handle_play(req_pos, catalog)
            self.assertEqual(resolved_calls, [3])

            # Cancelar busca no sRadio encerra com succeeded=False sem duplicar Home
            req_search = SRadioRequest.from_argv(
                ["plugin://plugin.audio.sradio/", "5", "?action=search"]
            )
            sradio_handle_search(req_search, catalog, favorites, "")
            self.assertEqual(end_calls, [(5, False)])


if __name__ == "__main__":
    unittest.main()
