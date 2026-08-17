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


def play_video(handle: int, app: "AppContainer", media_type: str, item_id: str, url: str) -> None:
    """Resolve a URL de reprodução para o Kodi, encerrando o spinner de carregamento imediatamente."""
    listitem = xbmcgui.ListItem(path=url, offscreen=True)
    listitem.setProperty("IsPlayable", "true")

    # Retomada de onde parou (Resume Point)
    resume = app.catalog.get_playback_progress(media_type, item_id)
    if resume and resume.get("position", 0) > 0 and resume.get("total", 0) > 0:
        if (resume["position"] / resume["total"]) < 0.95:
            listitem.setProperty("StartOffset", str(resume["position"]))

    # Notifica o Kodi que a URL foi resolvida com sucesso.
    # Isso instrui o motor do Kodi a iniciar a reprodução nativa e FECHAR o diálogo/ícone de carregamento.
    xbmcplugin.setResolvedUrl(handle=handle, succeeded=True, listitem=listitem)
