from __future__ import annotations

import concurrent.futures
import json
import ssl
import time
import urllib.parse
import urllib.request
from typing import Sequence

from saile_epg.errors import EpgSyncError
from saile_epg.models import EpgChannel, EpgProgram, EpgSnapshot
from saile_epg.normalizer import clean_channel_title, normalize_channel_name

# Catálogo oficial de canais da Claro TV+ (site_id, nome oficial, logo, número oficial)
# Permite funcionamento offline/resiliente e mapeamento instantâneo
CLARO_OFFICIAL_CHANNELS: tuple[dict[str, str], ...] = (
    {"id": "1", "name": "DISCOVERY KIDS HD", "logo": "https://www.clarotvmais.com.br/img/channels/discovery_kids.png"},
    {"id": "2", "name": "CARTOON HD", "logo": "https://www.clarotvmais.com.br/img/channels/cartoon.png"},
    {"id": "3", "name": "NICKELODEON HD", "logo": "https://www.clarotvmais.com.br/img/channels/nickelodeon.png"},
    {"id": "5", "name": "BAND SPORTS HD", "logo": "https://www.clarotvmais.com.br/img/channels/band_sports.png"},
    {"id": "6", "name": "BAND NEWS", "logo": "https://www.clarotvmais.com.br/img/channels/band_news.png"},
    {"id": "7", "name": "DISCOVERY HD", "logo": "https://www.clarotvmais.com.br/img/channels/discovery.png"},
    {"id": "8", "name": "DISCOVERY HOME&HEALTH HD", "logo": "https://www.clarotvmais.com.br/img/channels/discovery_home_e_health.png"},
    {"id": "9", "name": "TNT HD", "logo": "https://www.clarotvmais.com.br/img/channels/tnt.png"},
    {"id": "10", "name": "SPACE HD", "logo": "https://www.clarotvmais.com.br/img/channels/space.png"},
    {"id": "11", "name": "CARTOONITO", "logo": "https://www.clarotvmais.com.br/img/channels/cartoonito.png"},
    {"id": "12", "name": "TLC HD", "logo": "https://www.clarotvmais.com.br/img/channels/tlc.png"},
    {"id": "13", "name": "ID HD", "logo": "https://www.clarotvmais.com.br/img/channels/id.png"},
    {"id": "15", "name": "ANIMAL PLANET HD", "logo": "https://www.clarotvmais.com.br/img/channels/animal_planet.png"},
    {"id": "16", "name": "PARAMOUNT NETWORK", "logo": "https://www.clarotvmais.com.br/img/channels/paramount_network.png"},
    {"id": "17", "name": "NICK JR", "logo": "https://www.clarotvmais.com.br/img/channels/nick_jr.png"},
    {"id": "18", "name": "DISCOVERY TURBO HD", "logo": "https://www.clarotvmais.com.br/img/channels/discovery_turbo.png"},
    {"id": "19", "name": "CURTA", "logo": "https://www.clarotvmais.com.br/img/channels/curta.png"},
    {"id": "20", "name": "TNT SERIES HD", "logo": "https://www.clarotvmais.com.br/img/channels/tnt_series.png"},
    {"id": "21", "name": "COMEDY CENTRAL", "logo": "https://www.clarotvmais.com.br/img/channels/comedy_central.png"},
    {"id": "22", "name": "MTV HD", "logo": "https://www.clarotvmais.com.br/img/channels/mtv.png"},
    {"id": "26", "name": "ESPN 4", "logo": "https://www.clarotvmais.com.br/img/channels/espn_4.png"},
    {"id": "27", "name": "ESPN 5", "logo": "https://www.clarotvmais.com.br/img/channels/espn_5.png"},
    {"id": "28", "name": "ESPN 2", "logo": "https://www.clarotvmais.com.br/img/channels/espn_2.png"},
    {"id": "29", "name": "ESPN", "logo": "https://www.clarotvmais.com.br/img/channels/espn.png"},
    {"id": "30", "name": "SPORTV", "logo": "https://www.clarotvmais.com.br/img/channels/sportv.png"},
    {"id": "31", "name": "SPORTV 2", "logo": "https://www.clarotvmais.com.br/img/channels/sportv_2.png"},
    {"id": "32", "name": "SPORTV 3", "logo": "https://www.clarotvmais.com.br/img/channels/sportv_3.png"},
    {"id": "33", "name": "AMC HD", "logo": "https://www.clarotvmais.com.br/img/channels/amc.png"},
    {"id": "34", "name": "ARTE 1 HD", "logo": "https://www.clarotvmais.com.br/img/channels/arte_1.png"},
    {"id": "35", "name": "BLOOMBERG TV", "logo": "https://www.clarotvmais.com.br/img/channels/bloomberg_tv.png"},
    {"id": "39", "name": "ESPN 3", "logo": "https://www.clarotvmais.com.br/img/channels/espn_3.png"},
    {"id": "40", "name": "FISH TV", "logo": "https://www.clarotvmais.com.br/img/channels/fish_tv.png"},
    {"id": "46", "name": "Like + | Claro tv+", "logo": "https://www.clarotvmais.com.br/img/channels/like_claro_tv.png"},
    {"id": "47", "name": "TCM BR", "logo": "https://www.clarotvmais.com.br/img/channels/tcm_br.png"},
    {"id": "48", "name": "WOOHOO HD", "logo": "https://www.clarotvmais.com.br/img/channels/woohoo.png"},
    {"id": "49", "name": "DumDum", "logo": "https://www.clarotvmais.com.br/img/channels/dumdum.png"},
    {"id": "50", "name": "ESPN 6", "logo": "https://www.clarotvmais.com.br/img/channels/espn_6.png"},
    {"id": "51", "name": "FILM & ARTS", "logo": "https://www.clarotvmais.com.br/img/channels/film__e__arts.png"},
    {"id": "52", "name": "FOOD NETWORK HD", "logo": "https://www.clarotvmais.com.br/img/channels/food_network.png"},
    {"id": "53", "name": "GAZETA", "logo": "https://www.clarotvmais.com.br/img/channels/gazeta.png"},
    {"id": "54", "name": "CBI", "logo": "https://www.clarotvmais.com.br/img/channels/cbi.png"},
    {"id": "55", "name": "MUSIC BOX BRAZIL", "logo": "https://www.clarotvmais.com.br/img/channels/music_box_brazil.png"},
    {"id": "56", "name": "PLAY TV", "logo": "https://www.clarotvmais.com.br/img/channels/play_tv.png"},
    {"id": "57", "name": "PRIME BOX BRAZIL", "logo": "https://www.clarotvmais.com.br/img/channels/prime_box_brazil.png"},
    {"id": "58", "name": "RAI INTERNATIONAL", "logo": "https://www.clarotvmais.com.br/img/channels/rai_international.png"},
    {"id": "59", "name": "REDE GOSPEL", "logo": "https://www.clarotvmais.com.br/img/channels/rede_gospel.png"},
    {"id": "60", "name": "REDE VIDA", "logo": "https://www.clarotvmais.com.br/img/channels/rede_vida.png"},
    {"id": "61", "name": "TV BRASIL", "logo": "https://www.clarotvmais.com.br/img/channels/tv_brasil.png"},
    {"id": "62", "name": "TV RA TIM BUM", "logo": "https://www.clarotvmais.com.br/img/channels/tv_ra_tim_bum.png"},
    {"id": "63", "name": "TV5 MONDE", "logo": "https://www.clarotvmais.com.br/img/channels/tv5_monde.png"},
    {"id": "64", "name": "MTV 00's", "logo": "https://www.clarotvmais.com.br/img/channels/mtv_00_s.png"},
    {"id": "66", "name": "DW-TV", "logo": "https://www.clarotvmais.com.br/img/channels/dw_tv.png"},
    {"id": "67", "name": "BBC WORLD NEWS", "logo": "https://www.clarotvmais.com.br/img/channels/bbc_world_news.png"},
    {"id": "68", "name": "TELECINE PREMIUM", "logo": "https://www.clarotvmais.com.br/img/channels/telecine_premium.png"},
    {"id": "69", "name": "TELECINE ACTION", "logo": "https://www.clarotvmais.com.br/img/channels/telecine_action.png"},
    {"id": "70", "name": "TELECINE TOUCH", "logo": "https://www.clarotvmais.com.br/img/channels/telecine_touch.png"},
    {"id": "71", "name": "TELECINE FUN", "logo": "https://www.clarotvmais.com.br/img/channels/telecine_fun.png"},
    {"id": "72", "name": "TELECINE PIPOCA", "logo": "https://www.clarotvmais.com.br/img/channels/telecine_pipoca.png"},
    {"id": "73", "name": "TELECINE CULT", "logo": "https://www.clarotvmais.com.br/img/channels/telecine_cult.png"},
    {"id": "75", "name": "TRAVEL BOX", "logo": "https://www.clarotvmais.com.br/img/channels/travel_box.png"},
    {"id": "76", "name": "FASHION TV", "logo": "https://www.clarotvmais.com.br/img/channels/fashion_tv.png"},
    {"id": "77", "name": "CNN BRASIL", "logo": "https://www.clarotvmais.com.br/img/channels/cnn_brasil.png"},
    {"id": "78", "name": "GLOBONEWS", "logo": "https://www.clarotvmais.com.br/img/channels/globonews.png"},
    {"id": "79", "name": "AXN", "logo": "https://www.clarotvmais.com.br/img/channels/axn.png"},
    {"id": "80", "name": "AGROMAIS", "logo": "https://www.clarotvmais.com.br/img/channels/agromais.png"},
    {"id": "81", "name": "TRACE BRASIL HD", "logo": "https://www.clarotvmais.com.br/img/channels/trace_brasil.png"},
    {"id": "82", "name": "SONY CHANNEL", "logo": "https://www.clarotvmais.com.br/img/channels/sony_channel.png"},
    {"id": "83", "name": "WARNER CHANNEL", "logo": "https://www.clarotvmais.com.br/img/channels/warner_channel.png"},
    {"id": "84", "name": "HISTORY", "logo": "https://www.clarotvmais.com.br/img/channels/history.png"},
    {"id": "85", "name": "HISTORY 2", "logo": "https://www.clarotvmais.com.br/img/channels/history_2.png"},
    {"id": "86", "name": "A&E", "logo": "https://www.clarotvmais.com.br/img/channels/a_e_e.png"},
    {"id": "87", "name": "E!", "logo": "https://www.clarotvmais.com.br/img/channels/e.png"},
    {"id": "88", "name": "LIFETIME", "logo": "https://www.clarotvmais.com.br/img/channels/lifetime.png"},
    {"id": "89", "name": "Paramount+ 1", "logo": "https://www.clarotvmais.com.br/img/channels/paramount_1.png"},
    {"id": "90", "name": "Paramount+ 2", "logo": "https://www.clarotvmais.com.br/img/channels/paramount_2.png"},
    {"id": "91", "name": "Paramount+ 3", "logo": "https://www.clarotvmais.com.br/img/channels/paramount_3.png"},
    {"id": "92", "name": "Paramount+ 4", "logo": "https://www.clarotvmais.com.br/img/channels/paramount_4.png"},
    {"id": "93", "name": "GLOOB HD", "logo": "https://www.clarotvmais.com.br/img/channels/gloob.png"},
    {"id": "94", "name": "GLOOBINHO HD", "logo": "https://www.clarotvmais.com.br/img/channels/gloobinho.png"},
    {"id": "95", "name": "FUTURA HD", "logo": "https://www.clarotvmais.com.br/img/channels/futura.png"},
    {"id": "96", "name": "OFF HD", "logo": "https://www.clarotvmais.com.br/img/channels/off.png"},
    {"id": "97", "name": "GNT HD", "logo": "https://www.clarotvmais.com.br/img/channels/gnt.png"},
    {"id": "98", "name": "MULTISHOW HD", "logo": "https://www.clarotvmais.com.br/img/channels/multishow.png"},
    {"id": "99", "name": "Globoplay Novelas", "logo": "https://www.clarotvmais.com.br/img/channels/globoplay_novelas.png"},
    {"id": "100", "name": "Modo Viagem", "logo": "https://www.clarotvmais.com.br/img/channels/modo_viagem.png"},
    {"id": "101", "name": "BIS HD", "logo": "https://www.clarotvmais.com.br/img/channels/bis.png"},
    {"id": "102", "name": "UNIVERSAL TV HD", "logo": "https://www.clarotvmais.com.br/img/channels/universal_tv.png"},
    {"id": "103", "name": "USA HD", "logo": "https://www.clarotvmais.com.br/img/channels/usa.png"},
    {"id": "104", "name": "CANAL BRASIL HD", "logo": "https://www.clarotvmais.com.br/img/channels/canal_brasil.png"},
    {"id": "105", "name": "MEGAPIX HD", "logo": "https://www.clarotvmais.com.br/img/channels/megapix.png"},
    {"id": "106", "name": "STUDIO UNIVERSAL HD", "logo": "https://www.clarotvmais.com.br/img/channels/studio_universal.png"},
    {"id": "107", "name": "PREMIERE CLUBES HD", "logo": "https://www.clarotvmais.com.br/img/channels/premiere_clubes.png"},
    {"id": "108", "name": "PREMIERE 2 HD", "logo": "https://www.clarotvmais.com.br/img/channels/premiere_2.png"},
    {"id": "109", "name": "PREMIERE 3 HD", "logo": "https://www.clarotvmais.com.br/img/channels/premiere_3.png"},
    {"id": "110", "name": "PREMIERE 4 HD", "logo": "https://www.clarotvmais.com.br/img/channels/premiere_4.png"},
    {"id": "111", "name": "PREMIERE 5 HD", "logo": "https://www.clarotvmais.com.br/img/channels/premiere_5.png"},
    {"id": "112", "name": "PREMIERE 6 HD", "logo": "https://www.clarotvmais.com.br/img/channels/premiere_6.png"},
    {"id": "113", "name": "PREMIERE 7 HD", "logo": "https://www.clarotvmais.com.br/img/channels/premiere_7.png"},
    {"id": "114", "name": "COMBATE HD", "logo": "https://www.clarotvmais.com.br/img/channels/combate.png"},
    {"id": "115", "name": "HGTV HD", "logo": "https://www.clarotvmais.com.br/img/channels/hgtv.png"},
    {"id": "116", "name": "DISCOVERY SCIENCE HD", "logo": "https://www.clarotvmais.com.br/img/channels/discovery_science.png"},
    {"id": "117", "name": "DISCOVERY THEATER HD", "logo": "https://www.clarotvmais.com.br/img/channels/discovery_theater.png"},
    {"id": "118", "name": "DISCOVERY WORLD HD", "logo": "https://www.clarotvmais.com.br/img/channels/discovery_world.png"},
    {"id": "119", "name": "EUROCHANNEL HD", "logo": "https://www.clarotvmais.com.br/img/channels/eurochannel.png"},
    {"id": "124", "name": "GLOBO SÃO PAULO", "logo": "https://www.clarotvmais.com.br/img/channels/globo_s_o_paulo.png"},
    {"id": "129", "name": "FRANCE 24 HD", "logo": "https://www.clarotvmais.com.br/img/channels/france_24.png"},
    {"id": "174", "name": "BAND HD", "logo": "https://www.clarotvmais.com.br/img/channels/band.png"},
    {"id": "175", "name": "CULTURA HD", "logo": "https://www.clarotvmais.com.br/img/channels/cultura.png"},
    {"id": "176", "name": "TVE INTERNATIONAL", "logo": "https://www.clarotvmais.com.br/img/channels/tve_international.png"},
    {"id": "177", "name": "CNN INTERNATIONAL", "logo": "https://www.clarotvmais.com.br/img/channels/cnn_international.png"},
    {"id": "178", "name": "CINEMAX HD", "logo": "https://www.clarotvmais.com.br/img/channels/cinemax.png"},
    {"id": "179", "name": "MTV LIVE", "logo": "https://www.clarotvmais.com.br/img/channels/mtv_live.png"},
    {"id": "182", "name": "RECORD NEWS", "logo": "https://www.clarotvmais.com.br/img/channels/record_news.png"},
    {"id": "183", "name": "LIKE", "logo": "https://www.clarotvmais.com.br/img/channels/like.png"},
    {"id": "184", "name": "SBT", "logo": "https://www.clarotvmais.com.br/img/channels/sbt.png"},
    {"id": "185", "name": "REDE TV! HD", "logo": "https://www.clarotvmais.com.br/img/channels/rede_tv.png"},
    {"id": "187", "name": "JOVEM PAN NEWS", "logo": "https://www.clarotvmais.com.br/img/channels/jovem_pan_news.png"},
    {"id": "188", "name": "MEZZO HD", "logo": "https://www.clarotvmais.com.br/img/channels/mezzo.png"},
    {"id": "260", "name": "HBO", "logo": "https://www.clarotvmais.com.br/img/channels/hbo.png"},
    {"id": "261", "name": "HBO2", "logo": "https://www.clarotvmais.com.br/img/channels/hbo2.png"},
    {"id": "262", "name": "HBO+", "logo": "https://www.clarotvmais.com.br/img/channels/hbo.png"},
    {"id": "263", "name": "HBO Family", "logo": "https://www.clarotvmais.com.br/img/channels/hbo_family.png"},
    {"id": "264", "name": "HBO Signature", "logo": "https://www.clarotvmais.com.br/img/channels/hbo_signature.png"},
    {"id": "265", "name": "HBO Pop", "logo": "https://www.clarotvmais.com.br/img/channels/hbo_pop.png"},
    {"id": "266", "name": "HBO Mundi", "logo": "https://www.clarotvmais.com.br/img/channels/hbo_mundi.png"},
    {"id": "267", "name": "HBO Xtreme", "logo": "https://www.clarotvmais.com.br/img/channels/hbo_xtreme.png"},
    {"id": "268", "name": "DOG TV HD", "logo": "https://www.clarotvmais.com.br/img/channels/dog_tv.png"},
    {"id": "288", "name": "Sabor & Arte", "logo": "https://www.clarotvmais.com.br/img/channels/sabor__e__arte.png"},
    {"id": "296", "name": "SportyNet + 1", "logo": "https://www.clarotvmais.com.br/img/channels/sportynet_1.png"},
    {"id": "297", "name": "SportyNet + 2", "logo": "https://www.clarotvmais.com.br/img/channels/sportynet_2.png"},
    {"id": "298", "name": "SportyNet + 3", "logo": "https://www.clarotvmais.com.br/img/channels/sportynet_3.png"},
    {"id": "299", "name": "TNT NOVELAS", "logo": "https://www.clarotvmais.com.br/img/channels/tnt_novelas.png"},
    {"id": "300", "name": "CANÇÃO NOVA HD", "logo": "https://www.clarotvmais.com.br/img/channels/can_o_nova.png"},
    {"id": "314", "name": "C3-TV", "logo": "https://www.clarotvmais.com.br/img/channels/c3_tv.png"},
    {"id": "315", "name": "SportyNet HD", "logo": "https://www.clarotvmais.com.br/img/channels/sportynet.png"},
    {"id": "316", "name": "CGTN", "logo": "https://www.clarotvmais.com.br/img/channels/cgtn.png"},
    {"id": "317", "name": "RECORD HD", "logo": "https://www.clarotvmais.com.br/img/channels/record.png"},
    {"id": "319", "name": "LMC+HD", "logo": "https://www.clarotvmais.com.br/img/channels/lmc_hd.png"},
    {"id": "320", "name": "TV APARECIDA HD", "logo": "https://www.clarotvmais.com.br/img/channels/tv_aparecida.png"},
    {"id": "321", "name": "BM&C HD", "logo": "https://www.clarotvmais.com.br/img/channels/bm_e_c.png"},
    {"id": "322", "name": "Adult Swim HD", "logo": "https://www.clarotvmais.com.br/img/channels/adult_swim.png"},
    {"id": "323", "name": "UNIVERSAL PREMIERE HD", "logo": "https://www.clarotvmais.com.br/img/channels/universal_premiere.png"},
    {"id": "324", "name": "UNIVERSAL REALITY", "logo": "https://www.clarotvmais.com.br/img/channels/universal_reality.png"},
    {"id": "328", "name": "CANAL DO BOI", "logo": "https://www.clarotvmais.com.br/img/channels/canal_do_boi.png"},
    {"id": "329", "name": "Nsports HD", "logo": "https://www.clarotvmais.com.br/img/channels/nsports.png"},
    {"id": "335", "name": "TRIP BRASIL CHANNEL", "logo": "https://www.clarotvmais.com.br/img/channels/trip_brasil_channel.png"},
    {"id": "337", "name": "LBV", "logo": "https://www.clarotvmais.com.br/img/channels/lbv.png"},
    {"id": "338", "name": "CANAL RURAL", "logo": "https://www.clarotvmais.com.br/img/channels/canal_rural.png"},
    {"id": "339", "name": "TIMES | Exclusivo CNBC", "logo": "https://www.clarotvmais.com.br/img/channels/times_exclusivo_cnbc.png"},
    {"id": "348", "name": "SIC INTERNACIONAL", "logo": "https://www.clarotvmais.com.br/img/channels/sic_internacional.png"},
    {"id": "349", "name": "CNN Brasil Money HD", "logo": "https://www.clarotvmais.com.br/img/channels/cnn_brasil_money.png"},
    {"id": "351", "name": "PREMIERE 8 HD", "logo": "https://www.clarotvmais.com.br/img/channels/premiere_8.png"},
    {"id": "352", "name": "CANAL UOL", "logo": "https://www.clarotvmais.com.br/img/channels/canal_uol.png"},
    {"id": "353", "name": "Travel & Food and Drinks HD", "logo": "https://www.clarotvmais.com.br/img/channels/travel__e__food_and_drinks.png"},
    {"id": "373", "name": "TV Pai Eterno HD", "logo": "https://www.clarotvmais.com.br/img/channels/tv_pai_eterno.png"},
    {"id": "439", "name": "Xsports HD", "logo": "https://www.clarotvmais.com.br/img/channels/xsports.png"},
    {"id": "466", "name": "GE TV HD", "logo": "https://www.clarotvmais.com.br/img/channels/ge_tv.png"},
    {"id": "467", "name": "MARKKET HD", "logo": "https://www.clarotvmais.com.br/img/channels/markket.png"},
)

API_BASE_URL = "https://www.clarotvmais.com.br/avsclient/1.2/epg/livechannels"


def _fetch_claro_chunk(
    chunk_ids: list[str],
    start_time: int,
    end_time: int,
    headers: dict[str, str],
    timeout: float = 12.0,
) -> list[dict[str, object]]:
    param_ids = ",".join(chunk_ids)
    url = f"{API_BASE_URL}?types=&channelIds={param_ids}&startTime={start_time}&endTime={end_time}&location=SAO%20PAULO,AMAZONAS&channel=PCTV"
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, context=ctx, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data.get("response", {}).get("liveChannels", [])


class ClaroEpgProvider:
    """Provedor oficial de guia de programação (EPG) da Claro TV+."""

    def __init__(
        self,
        provider_id: str = "claro",
        timeout: float = 12.0,
        chunk_size: int = 20,
        max_workers: int = 6,
    ) -> None:
        self.provider_id = provider_id
        self.timeout = timeout
        self.chunk_size = chunk_size
        self.max_workers = max_workers

    def _create_ssl_context(self) -> ssl.SSLContext:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx

    def fetch(self, window_hours: int = 24) -> EpgSnapshot:
        now = int(time.time())
        start_time = now - 3600  # 1h atrás para cobrir com precisão o programa em exibição
        end_time = now + max(3600 * 12, window_hours * 3600)
        fetched_at_utc = now

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
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

        all_ids = [str(ch_info["id"]) for ch_info in CLARO_OFFICIAL_CHANNELS]
        chunks = [all_ids[i:i + self.chunk_size] for i in range(0, len(all_ids), self.chunk_size)]

        programs: list[EpgProgram] = []
        dedup_programs: set[tuple[str, int]] = set()

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
                    live_channels = future.result()
                    for ch in live_channels:
                        cid = str(ch.get("id", ""))
                        if not cid:
                            continue

                        schedules = ch.get("schedules", [])
                        for prog in schedules:
                            p_title = str(prog.get("title") or "").strip()
                            if not p_title:
                                continue

                            st_raw = prog.get("startTime") or 0
                            et_raw = prog.get("endTime") or 0
                            if not isinstance(st_raw, (int, float)) or not isinstance(et_raw, (int, float)):
                                continue
                            if st_raw <= 0 or et_raw <= st_raw:
                                continue

                            st_utc = int(st_raw)
                            et_utc = int(et_raw)

                            dedup_key = (f"claro_{cid}", st_utc)
                            if dedup_key in dedup_programs:
                                continue
                            dedup_programs.add(dedup_key)

                            ep_name = str(prog.get("episodeName") or "").strip()
                            desc = str(prog.get("description") or "").strip()
                            season = prog.get("seasonNumber")
                            episode = prog.get("episodeNumber")
                            cat = str(ch.get("type") or "").strip()

                            # Monta descrição rica
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
                except Exception as exc:
                    import logging
                    logging.getLogger("saile_epg.claro").warning(f"Error processing Claro EPG chunk: {exc}")
                    continue

        if not channel_map:
            raise EpgSyncError("EPG-CLARO-EMPTY", "Nenhum canal foi retornado pela API da Claro TV+")

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
