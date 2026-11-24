"""Gerenciador de reprodução de vídeo compatível com Kodi setResolvedUrl e resume point."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import xbmc
import xbmcgui
import xbmcplugin

if TYPE_CHECKING:
    from stv.app.services import AppContainer

# Abaixo disso a retomada é oferecida; acima, o item conta como assistido.
RESUME_MAX_RATIO = 0.95
RESUMABLE_MEDIA_TYPES = frozenset({"vod", "series"})


def resume_progress_to_save(position: float, total: float) -> tuple[float, float] | None:
    """Progresso a gravar ao fim da reprodução; (0, 0) limpa o resume de item assistido."""
    if total <= 0 or position <= 0:
        return None
    if position / total >= RESUME_MAX_RATIO:
        return (0.0, 0.0)
    return (position, total)


def track_playback_progress(
    app: AppContainer,
    media_type: str,
    item_id: str,
    url: str,
    player: Any,
    monitor: Any,
    start_timeout_s: float = 30.0,
) -> None:
    """Acompanha a reprodução de VOD/episódio e grava o ponto de retomada quando ela termina.

    Lê a posição por polling enquanto o próprio item toca: nos callbacks de parada do
    xbmc.Player o getTime() já não responde, então a última posição lida é a que vale.
    """
    waited = 0.0
    while not player.isPlayingVideo():
        if waited >= start_timeout_s or monitor.waitForAbort(0.5):
            return
        waited += 0.5

    position = total = 0.0
    while not monitor.abortRequested() and player.isPlayingVideo():
        try:
            if player.getPlayingFile() != url:
                break  # o usuário trocou de item; não atribuir outro progresso a este
            position = player.getTime()
            total = player.getTotalTime()
        except RuntimeError:
            break
        if monitor.waitForAbort(1):
            break

    progress = resume_progress_to_save(position, total)
    if progress is not None:
        app.catalog.update_playback_progress(media_type, item_id, *progress)


def play_video(
    handle: int,
    app: AppContainer,
    media_type: str,
    item_id: str,
    url: str,
    video_quality: str = "",
) -> None:
    """Resolve a URL de reprodução para o Kodi, encerrando o carregamento imediatamente."""
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
        if (resume["position"] / resume["total"]) < RESUME_MAX_RATIO:
            listitem.setProperty("StartOffset", str(resume["position"]))

    player = xbmc.Player()
    if handle >= 0:
        # Clique em item navegável: resolve a URL pelo handle do diretório.
        xbmcplugin.setResolvedUrl(handle=handle, succeeded=True, listitem=listitem)
    else:
        # Ações de contexto usam RunPlugin e não recebem um handle reproduzível.
        player.play(url, listitem=listitem)

    if media_type in RESUMABLE_MEDIA_TYPES:
        # TV ao vivo não tem ponto de retomada; VOD e episódios gravam onde pararam.
        track_playback_progress(app, media_type, item_id, url, player, xbmc.Monitor())
