"""Gerenciador de reprodução de vídeo compatível com Kodi setResolvedUrl e resume point."""
from __future__ import annotations

import xbmc
import xbmcgui
import xbmcplugin

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from stv.app.services import AppContainer


class SailePlayer(xbmc.Player):
    """Monitor de eventos de reprodução para salvar progresso do usuário."""

    def __init__(self, app: "AppContainer", media_type: str, item_id: str) -> None:
        super().__init__()
        self.app = app
        self.media_type = media_type
        self.item_id = item_id

    def onPlayBackStopped(self) -> None:
        try:
            position = self.getTime()
            total = self.getTotalTime()
            if total > 0 and position > 0:
                self.app.catalog.update_playback_progress(self.media_type, self.item_id, position, total)
        except Exception:
            pass

    def onPlayBackEnded(self) -> None:
        try:
            self.app.catalog.update_playback_progress(self.media_type, self.item_id, 0, 0)
        except Exception:
            pass


def play_video(
    handle: int,
    app: "AppContainer",
    media_type: str,
    item_id: str,
    url: str,
    video_quality: str = "",
) -> None:
    """Resolve a URL de reprodução para o Kodi, encerrando o spinner de carregamento imediatamente."""
    listitem = xbmcgui.ListItem(path=url, offscreen=True)
    listitem.setProperty("IsPlayable", "true")
    if video_quality:
        dimensions = {
            "4K": (3840, 2160),
            "FHD": (1920, 1080),
            "HD": (1280, 720),
            "SD": (720, 480),
        }.get(video_quality)
        listitem.setProperty("sTv.Quality", video_quality)
        if dimensions:
            try:
                stream = xbmc.VideoStreamDetail(*dimensions, aspect=16 / 9)
                listitem.getVideoInfoTag().addVideoStream(stream)
            except Exception:
                try:
                    listitem.addStreamInfo(
                        "video",
                        {
                            "width": dimensions[0],
                            "height": dimensions[1],
                            "aspect": 16 / 9,
                        },
                    )
                except Exception:
                    pass

    # Retomada de onde parou (Resume Point)
    resume = app.catalog.get_playback_progress(media_type, item_id)
    if resume and resume.get("position", 0) > 0 and resume.get("total", 0) > 0:
        if (resume["position"] / resume["total"]) < 0.95:
            listitem.setProperty("StartOffset", str(resume["position"]))

    if handle >= 0:
        # Clique em item navegável: resolve a URL pelo handle do diretório.
        xbmcplugin.setResolvedUrl(handle=handle, succeeded=True, listitem=listitem)
    else:
        # Ações de contexto usam RunPlugin e não recebem um handle reproduzível.
        xbmc.Player().play(url, listitem=listitem)
