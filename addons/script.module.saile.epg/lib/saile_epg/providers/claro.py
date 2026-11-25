from __future__ import annotations

import concurrent.futures
import json
import ssl
import time
import urllib.parse
import urllib.request

from saile_epg.errors import EpgSyncError
from saile_epg.models import EpgChannel, EpgProgram, EpgSnapshot
from saile_epg.normalizer import clean_channel_title, normalize_channel_name

# Catálogo oficial de canais da Claro TV+ (site_id, nome oficial, logo, número oficial)
# Permite funcionamento offline/resiliente e mapeamento instantâneo
_LOGO_BASE = "https://www.clarotvmais.com.br/img/channels/"
_CLARO_CHANNEL_SPECS: tuple[tuple[str, str, str], ...] = (
    ("1", "DISCOVERY KIDS HD", "discovery_kids.png"),
    ("2", "CARTOON HD", "cartoon.png"),
    ("3", "NICKELODEON HD", "nickelodeon.png"),
    ("5", "BAND SPORTS HD", "band_sports.png"),
    ("6", "BAND NEWS", "band_news.png"),
    ("7", "DISCOVERY HD", "discovery.png"),
    ("8", "DISCOVERY HOME&HEALTH HD", "discovery_home_e_health.png"),
    ("9", "TNT HD", "tnt.png"),
    ("10", "SPACE HD", "space.png"),
    ("11", "CARTOONITO", "cartoonito.png"),
    ("12", "TLC HD", "tlc.png"),
    ("13", "ID HD", "id.png"),
    ("15", "ANIMAL PLANET HD", "animal_planet.png"),
    ("16", "PARAMOUNT NETWORK", "paramount_network.png"),
    ("17", "NICK JR", "nick_jr.png"),
    ("18", "DISCOVERY TURBO HD", "discovery_turbo.png"),
    ("19", "CURTA", "curta.png"),
    ("20", "TNT SERIES HD", "tnt_series.png"),
    ("21", "COMEDY CENTRAL", "comedy_central.png"),
    ("22", "MTV HD", "mtv.png"),
    ("26", "ESPN 4", "espn_4.png"),
    ("27", "ESPN 5", "espn_5.png"),
    ("28", "ESPN 2", "espn_2.png"),
    ("29", "ESPN", "espn.png"),
    ("30", "SPORTV", "sportv.png"),
    ("31", "SPORTV 2", "sportv_2.png"),
    ("32", "SPORTV 3", "sportv_3.png"),
    ("33", "AMC HD", "amc.png"),
    ("34", "ARTE 1 HD", "arte_1.png"),
    ("35", "BLOOMBERG TV", "bloomberg_tv.png"),
    ("39", "ESPN 3", "espn_3.png"),
    ("40", "FISH TV", "fish_tv.png"),
    ("46", "Like + | Claro tv+", "like_claro_tv.png"),
    ("47", "TCM BR", "tcm_br.png"),
    ("48", "WOOHOO HD", "woohoo.png"),
    ("49", "DumDum", "dumdum.png"),
    ("50", "ESPN 6", "espn_6.png"),
    ("51", "FILM & ARTS", "film__e__arts.png"),
    ("52", "FOOD NETWORK HD", "food_network.png"),
    ("53", "GAZETA", "gazeta.png"),
    ("54", "CBI", "cbi.png"),
    ("55", "MUSIC BOX BRAZIL", "music_box_brazil.png"),
    ("56", "PLAY TV", "play_tv.png"),
    ("57", "PRIME BOX BRAZIL", "prime_box_brazil.png"),
    ("58", "RAI INTERNATIONAL", "rai_international.png"),
    ("59", "REDE GOSPEL", "rede_gospel.png"),
    ("60", "REDE VIDA", "rede_vida.png"),
    ("61", "TV BRASIL", "tv_brasil.png"),
    ("62", "TV RA TIM BUM", "tv_ra_tim_bum.png"),
    ("63", "TV5 MONDE", "tv5_monde.png"),
    ("64", "MTV 00's", "mtv_00_s.png"),
    ("66", "DW-TV", "dw_tv.png"),
    ("67", "BBC WORLD NEWS", "bbc_world_news.png"),
    ("68", "TELECINE PREMIUM", "telecine_premium.png"),
    ("69", "TELECINE ACTION", "telecine_action.png"),
    ("70", "TELECINE TOUCH", "telecine_touch.png"),
    ("71", "TELECINE FUN", "telecine_fun.png"),
    ("72", "TELECINE PIPOCA", "telecine_pipoca.png"),
    ("73", "TELECINE CULT", "telecine_cult.png"),
    ("75", "TRAVEL BOX", "travel_box.png"),
    ("76", "FASHION TV", "fashion_tv.png"),
    ("77", "CNN BRASIL", "cnn_brasil.png"),
    ("78", "GLOBONEWS", "globonews.png"),
    ("79", "AXN", "axn.png"),
    ("80", "AGROMAIS", "agromais.png"),
    ("81", "TRACE BRASIL HD", "trace_brasil.png"),
    ("82", "SONY CHANNEL", "sony_channel.png"),
    ("83", "WARNER CHANNEL", "warner_channel.png"),
    ("84", "HISTORY", "history.png"),
    ("85", "HISTORY 2", "history_2.png"),
    ("86", "A&E", "a_e_e.png"),
    ("87", "E!", "e.png"),
    ("88", "LIFETIME", "lifetime.png"),
    ("89", "Paramount+ 1", "paramount_1.png"),
    ("90", "Paramount+ 2", "paramount_2.png"),
    ("91", "Paramount+ 3", "paramount_3.png"),
    ("92", "Paramount+ 4", "paramount_4.png"),
    ("93", "GLOOB HD", "gloob.png"),
    ("94", "GLOOBINHO HD", "gloobinho.png"),
    ("95", "FUTURA HD", "futura.png"),
    ("96", "OFF HD", "off.png"),
    ("97", "GNT HD", "gnt.png"),
    ("98", "MULTISHOW HD", "multishow.png"),
    ("99", "Globoplay Novelas", "globoplay_novelas.png"),
    ("100", "Modo Viagem", "modo_viagem.png"),
    ("101", "BIS HD", "bis.png"),
    ("102", "UNIVERSAL TV HD", "universal_tv.png"),
    ("103", "USA HD", "usa.png"),
    ("104", "CANAL BRASIL HD", "canal_brasil.png"),
    ("105", "MEGAPIX HD", "megapix.png"),
    ("106", "STUDIO UNIVERSAL HD", "studio_universal.png"),
    ("107", "PREMIERE CLUBES HD", "premiere_clubes.png"),
    ("108", "PREMIERE 2 HD", "premiere_2.png"),
    ("109", "PREMIERE 3 HD", "premiere_3.png"),
    ("110", "PREMIERE 4 HD", "premiere_4.png"),
    ("111", "PREMIERE 5 HD", "premiere_5.png"),
    ("112", "PREMIERE 6 HD", "premiere_6.png"),
    ("113", "PREMIERE 7 HD", "premiere_7.png"),
    ("114", "COMBATE HD", "combate.png"),
    ("115", "HGTV HD", "hgtv.png"),
    ("116", "DISCOVERY SCIENCE HD", "discovery_science.png"),
    ("117", "DISCOVERY THEATER HD", "discovery_theater.png"),
    ("118", "DISCOVERY WORLD HD", "discovery_world.png"),
    ("119", "EUROCHANNEL HD", "eurochannel.png"),
    ("124", "GLOBO SP", "globo.png"),
    ("129", "FRANCE 24 HD", "france_24.png"),
    ("174", "BAND HD", "band.png"),
    ("175", "CULTURA HD", "cultura.png"),
    ("176", "TVE INTERNATIONAL", "tve_international.png"),
    ("177", "CNN INTERNATIONAL", "cnn_international.png"),
    ("178", "CINEMAX HD", "cinemax.png"),
    ("179", "MTV LIVE", "mtv_live.png"),
    ("182", "RECORD NEWS", "record_news.png"),
    ("183", "LIKE", "like.png"),
    ("184", "SBT", "sbt.png"),
    ("185", "REDE TV! HD", "rede_tv.png"),
    ("187", "JOVEM PAN NEWS", "jovem_pan_news.png"),
    ("188", "MEZZO HD", "mezzo.png"),
    ("260", "HBO", "hbo.png"),
    ("261", "HBO2", "hbo2.png"),
    ("262", "HBO+", "hbo.png"),
    ("263", "HBO Family", "hbo_family.png"),
    ("264", "HBO Signature", "hbo_signature.png"),
    ("265", "HBO Pop", "hbo_pop.png"),
    ("266", "HBO Mundi", "hbo_mundi.png"),
    ("267", "HBO Xtreme", "hbo_xtreme.png"),
    ("268", "DOG TV HD", "dog_tv.png"),
    ("269", "ZOOMOO KIDS HD", "zoomoo.png"),
    ("270", "TERRA VIVA", "terraviva.png"),
    ("288", "Sabor & Arte", "sabor__e__arte.png"),
    ("296", "SportyNet + 1", "sportynet_1.png"),
    ("297", "SportyNet + 2", "sportynet_2.png"),
    ("298", "SportyNet + 3", "sportynet_3.png"),
    ("299", "TNT NOVELAS", "tnt_novelas.png"),
    ("300", "CANÇÃO NOVA HD", "can_o_nova.png"),
    ("314", "C3-TV", "c3_tv.png"),
    ("315", "SportyNet HD", "sportynet.png"),
    ("316", "CGTN", "cgtn.png"),
    ("317", "RECORD HD", "record.png"),
    ("319", "LMC+HD", "lmc_hd.png"),
    ("320", "TV APARECIDA HD", "tv_aparecida.png"),
    ("321", "BM&C HD", "bm_e_c.png"),
    ("322", "Adult Swim HD", "adult_swim.png"),
    ("323", "UNIVERSAL PREMIERE HD", "universal_premiere.png"),
    ("324", "UNIVERSAL REALITY", "universal_reality.png"),
    ("328", "CANAL DO BOI", "canal_do_boi.png"),
    ("329", "Nsports HD", "nsports.png"),
    ("335", "TRIP BRASIL CHANNEL", "trip_brasil_channel.png"),
    ("337", "LBV", "lbv.png"),
    ("338", "CANAL RURAL", "canal_rural.png"),
    ("339", "TIMES | Exclusivo CNBC", "times_exclusivo_cnbc.png"),
    ("348", "SIC INTERNACIONAL", "sic_internacional.png"),
    ("349", "CNN Brasil Money HD", "cnn_brasil_money.png"),
    ("351", "PREMIERE 8 HD", "premiere_8.png"),
    ("352", "CANAL UOL", "canal_uol.png"),
    ("353", "Travel & Food and Drinks HD", "travel__e__food_and_drinks.png"),
    ("373", "TV Pai Eterno HD", "tv_pai_eterno.png"),
    ("439", "Xsports HD", "xsports.png"),
    ("466", "GE TV HD", "ge_tv.png"),
    ("467", "MARKKET HD", "markket.png"),
    ("468", "Polishop", "polishop.png"),
    ("469", "SBT NEWS HD", "sbt_news.png"),
    ("470", "TV Camara", "tv_camara.png"),
    ("471", "Canal GOV HD", "canal_gov.png"),
    ("472", "TV Justica", "tv_justica.png"),
    ("473", "Canal Educacao", "canal_educacao.png"),
    ("474", "TV Senado", "tv_senado.png"),
    ("475", "FUEL TV HD", "fuel_tv.png"),
    ("476", "TV Novo Tempo", "tv_novo_tempo.png"),
    ("479", "FONTE TV", "fonte_tv.png"),
    ("754", "Combate HD", "combate.png"),
)
CLARO_OFFICIAL_CHANNELS: tuple[dict[str, str], ...] = tuple(
    {"id": cid, "name": name, "logo": f"{_LOGO_BASE}{slug}"}
    for cid, name, slug in _CLARO_CHANNEL_SPECS
)

API_BASE_URL = "https://www.clarotvmais.com.br/avsclient/1.2/epg/livechannels"
_CLARO_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


_MAX_CLARO_RESPONSE_BYTES = 64 * 1024 * 1024


def _to_positive_timestamp(value: object) -> int:
    if isinstance(value, bool) or value is None:
        return 0
    if isinstance(value, (int, float)):
        return int(value) if value > 0 else 0
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.isdigit():
            return int(stripped)
    return 0


def _fetch_claro_live_channels(
    url: str,
    headers: dict[str, str],
    timeout: float,
) -> list[dict[str, object]]:
    if not url.startswith(("http://", "https://")):
        raise ValueError("Esquema de URL não suportado para EPG Claro")

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, context=ctx, timeout=timeout) as resp:  # noqa: S310
        raw = resp.read(_MAX_CLARO_RESPONSE_BYTES + 1)
    if len(raw) > _MAX_CLARO_RESPONSE_BYTES:
        raise ValueError("Resposta EPG Claro excedeu o limite máximo de memória")
    data = json.loads(raw.decode("utf-8", errors="replace"))
    if not isinstance(data, dict):
        return []
    response_obj = data.get("response")
    if not isinstance(response_obj, dict):
        return []
    live_channels = response_obj.get("liveChannels")
    if not isinstance(live_channels, list):
        return []
    return [ch for ch in live_channels if isinstance(ch, dict)]


def _fetch_claro_chunk(
    chunk_ids: list[str],
    start_time: int,
    end_time: int,
    headers: dict[str, str],
    timeout: float = 12.0,
) -> list[dict[str, object]]:
    param_ids = ",".join(chunk_ids)
    url = (
        f"{API_BASE_URL}?types=&channelIds={param_ids}"
        f"&startTime={start_time}&endTime={end_time}&location=SAO%20PAULO,AMAZONAS&channel=PCTV"
    )
    return _fetch_claro_live_channels(url, headers, timeout)


def _fetch_claro_dynamic(
    start_time: int,
    end_time: int,
    headers: dict[str, str],
    timeout: float = 15.0,
) -> list[dict[str, object]]:
    url = (
        f"{API_BASE_URL}?types=&channelIds="
        f"&startTime={start_time}&endTime={end_time}&location=&channel=PCTV"
    )
    return _fetch_claro_live_channels(url, headers, timeout)


class ClaroEpgProvider:
    """Provedor oficial de guia de programação (EPG) da Claro TV+."""

    def __init__(
        self,
        provider_id: str = "claro",
        timeout: float = 15.0,
        chunk_size: int = 20,
        max_workers: int = 6,
    ) -> None:
        self.provider_id = provider_id
        self.timeout = timeout
        self.chunk_size = chunk_size
        self.max_workers = max_workers

    def _parse_live_channels_data(
        self,
        live_channels: list[dict[str, object]],
        channel_map: dict[str, EpgChannel],
        programs: list[EpgProgram],
        dedup_programs: set[tuple[str, int]],
    ) -> None:
        for ch in live_channels:
            if not isinstance(ch, dict):
                continue
            cid = str(ch.get("id", "")).strip()
            if not cid:
                continue

            raw_name = str(ch.get("name") or "").strip()
            if cid not in channel_map and raw_name:
                norm = normalize_channel_name(raw_name)
                disp_name = clean_channel_title(raw_name)
                logo = str(ch.get("logo") or ch.get("channelLogo") or "").strip()
                channel_map[cid] = EpgChannel(
                    provider_id=self.provider_id,
                    channel_key=f"claro_{cid}",
                    epg_id=cid,
                    display_name=disp_name,
                    normalized_name=norm,
                    icon_url=logo,
                )

            schedules = ch.get("schedules")
            if not isinstance(schedules, list):
                continue
            for prog in schedules:
                if not isinstance(prog, dict):
                    continue
                p_title = str(prog.get("title") or "").strip()
                if not p_title:
                    continue

                st_utc = _to_positive_timestamp(prog.get("startTime"))
                et_utc = _to_positive_timestamp(prog.get("endTime"))
                if st_utc <= 0 or et_utc <= st_utc:
                    continue

                dedup_key = (f"claro_{cid}", st_utc)
                if dedup_key in dedup_programs:
                    continue
                dedup_programs.add(dedup_key)

                ep_name = str(prog.get("episodeName") or "").strip()
                desc = str(prog.get("description") or "").strip()
                season = prog.get("seasonNumber")
                episode = prog.get("episodeNumber")
                cat = str(ch.get("type") or "").strip()

                full_desc_parts = []
                if ep_name and ep_name != p_title:
                    full_desc_parts.append(f"Episódio: {ep_name}")
                if season and episode:
                    full_desc_parts.append(f"Temporada {season}, Episódio {episode}")
                if desc:
                    full_desc_parts.append(desc)
                final_desc = "\n".join(full_desc_parts)

                programs.append(
                    EpgProgram(
                        provider_id=self.provider_id,
                        channel_key=f"claro_{cid}",
                        title=p_title,
                        start_utc=st_utc,
                        end_utc=et_utc,
                        description=final_desc,
                        category=cat,
                        icon_url="",
                    )
                )

    def fetch(self, window_hours: int = 36) -> EpgSnapshot:
        now = int(time.time())
        start_time = now - 3600  # 1h atrás para cobrir com precisão o programa em exibição
        end_time = now + max(3600 * 12, window_hours * 3600)
        fetched_at_utc = now

        headers = {
            "User-Agent": _CLARO_USER_AGENT,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "Origin": "https://www.clarotvmais.com.br",
            "Referer": "https://www.clarotvmais.com.br/grade",
        }

        channel_map: dict[str, EpgChannel] = {}
        for ch_info in CLARO_OFFICIAL_CHANNELS:
            site_id = str(ch_info["id"])
            raw_name = ch_info["name"]
            norm = normalize_channel_name(raw_name)
            disp_name = clean_channel_title(raw_name)
            logo = ch_info.get("logo", "")
            channel_map[site_id] = EpgChannel(
                provider_id=self.provider_id,
                channel_key=f"claro_{site_id}",
                epg_id=site_id,
                display_name=disp_name,
                normalized_name=norm,
                icon_url=logo,
            )

        programs: list[EpgProgram] = []
        dedup_programs: set[tuple[str, int]] = set()

        # 1. Tentativa Dinâmica Rápida (1 única requisição trazendo todos os canais ao vivo)
        try:
            live_channels = _fetch_claro_dynamic(start_time, end_time, headers, self.timeout)
            if live_channels:
                self._parse_live_channels_data(live_channels, channel_map, programs, dedup_programs)
        except Exception:
            pass

        # 2. Se a tentativa dinâmica não obteve programas, usa fallback em paralelo por chunks
        if not programs:
            all_ids = [str(ch_info["id"]) for ch_info in CLARO_OFFICIAL_CHANNELS]
            chunks = [
                all_ids[i : i + self.chunk_size] for i in range(0, len(all_ids), self.chunk_size)
            ]

            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_to_chunk = {
                    executor.submit(
                        _fetch_claro_chunk,
                        chunk,
                        start_time,
                        end_time,
                        headers,
                        self.timeout,
                    ): chunk
                    for chunk in chunks
                }
                for future in concurrent.futures.as_completed(future_to_chunk):
                    try:
                        chunk_channels = future.result()
                        if chunk_channels:
                            self._parse_live_channels_data(
                                chunk_channels, channel_map, programs, dedup_programs
                            )
                    except Exception:
                        continue

        if not channel_map:
            raise EpgSyncError(
                "EPG-CLARO-EMPTY", "Nenhum canal foi retornado pela API da Claro TV+"
            )

        channels_tuple = tuple(
            sorted(
                channel_map.values(),
                key=lambda ch: (ch.display_name.casefold(), ch.channel_key),
            )
        )
        programs_tuple = tuple(programs)

        return EpgSnapshot(
            provider_id=self.provider_id,
            channels=channels_tuple,
            programs=programs_tuple,
            fetched_at_utc=fetched_at_utc,
        )
