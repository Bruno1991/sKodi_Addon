"""Cliente para consulta da grade de programação (EPG) da Claro TV."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Sequence
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request as UrlRequest, urlopen

from stv.domain.models import EpgProgram
from stv.providers.epg.normalizer import normalize_channel_name

DEFAULT_CLARO_API_URL = "https://programacao.claro.com.br/gatekeeper/exibicao/consultarExibicoes"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"


class ClaroEpgClient:
    """Consome a API de programação pública da Claro TV e normaliza os programas."""

    def __init__(self, base_url: str = DEFAULT_CLARO_API_URL, timeout: int = 5) -> None:
        self.base_url = base_url
        self.timeout = timeout

    def fetch_channel_programs(
        self,
        channel_name: str,
        start_dt: datetime | None = None,
        end_dt: datetime | None = None,
    ) -> list[EpgProgram]:
        """Consulta a programação de um canal para um período específico."""
        channel_key = normalize_channel_name(channel_name)
        if not channel_key:
            return []

        now = datetime.now()
        start = start_dt or (now - timedelta(hours=2))
        end = end_dt or (now + timedelta(hours=12))

        # Formatação de datas para a query da Claro
        data_inicio = start.strftime("%Y-%m-%d %H:%M")
        data_fim = end.strftime("%Y-%m-%d %H:%M")

        params = {
            "dataInicio": data_inicio,
            "dataFim": data_fim,
            "canal": channel_key,
        }
        url = f"{self.base_url}?{urlencode(params)}"

        try:
            req = UrlRequest(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
            with urlopen(req, timeout=self.timeout) as resp:
                if resp.status != 200:
                    return []
                raw_data = resp.read().decode("utf-8", errors="replace")
                data = json.loads(raw_data)
                return self._parse_programs(data, channel_key)
        except (URLError, TimeoutError, json.JSONDecodeError, Exception):
            # Resiliência total: em caso de erro de rede ou indisponibilidade, não derruba o add-on
            return []

    def _parse_programs(self, payload: dict | list, default_channel_key: str) -> list[EpgProgram]:
        """Converte o payload JSON da Claro para uma lista de EpgProgram."""
        programs: list[EpgProgram] = []

        raw_items: list[dict] = []
        if isinstance(payload, list):
            raw_items = [item for item in payload if isinstance(item, dict)]
        elif isinstance(payload, dict):
            # Formatos comuns da API Claro/Gatekeeper
            exibicoes = payload.get("exibicoes") or payload.get("response", {}).get("docs") or payload.get("programas") or []
            if isinstance(exibicoes, list):
                raw_items = [item for item in exibicoes if isinstance(item, dict)]

        for item in raw_items:
            prog = self._parse_single_item(item, default_channel_key)
            if prog:
                programs.append(prog)

        return programs

    def _parse_single_item(self, item: dict, default_channel_key: str) -> EpgProgram | None:
        title = (
            item.get("titulo")
            or item.get("nomePrograma")
            or item.get("title")
            or item.get("nome")
            or ""
        ).strip()
        if not title:
            return None

        synopsis = (
            item.get("sinopse")
            or item.get("descricao")
            or item.get("overview")
            or item.get("resumo")
            or ""
        ).strip()

        # Extração de início e fim
        raw_start = item.get("dhInicio") or item.get("dataInicio") or item.get("start") or item.get("dh_inicio") or ""
        raw_end = item.get("dhFim") or item.get("dataFim") or item.get("end") or item.get("dh_fim") or ""

        start_iso = self._normalize_datetime(raw_start)
        end_iso = self._normalize_datetime(raw_end)

        if not start_iso:
            return None

        # Canal do item se fornecido
        item_channel = item.get("nomeCanal") or item.get("canal") or ""
        channel_key = normalize_channel_name(item_channel) if item_channel else default_channel_key

        duration = int(item.get("duracao") or item.get("duration") or 0)

        return EpgProgram(
            channel_key=channel_key,
            title=title,
            start_time=start_iso,
            end_time=end_iso,
            synopsis=synopsis,
            duration_minutes=duration,
        )

    def _normalize_datetime(self, raw_val: str | int | float) -> str:
        """Converte diversos formatos de timestamp/string em formato padrão 'YYYY-MM-DD HH:MM'."""
        if not raw_val:
            return ""

        if isinstance(raw_val, (int, float)):
            # Timestamp em milissegundos ou segundos
            ts = raw_val / 1000.0 if raw_val > 1e11 else float(raw_val)
            return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")

        str_val = str(raw_val).strip()
        for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ", "%d/%m/%Y %H:%M"):
            try:
                dt = datetime.strptime(str_val[:19], fmt)
                return dt.strftime("%Y-%m-%d %H:%M")
            except ValueError:
                continue

        return str_val
