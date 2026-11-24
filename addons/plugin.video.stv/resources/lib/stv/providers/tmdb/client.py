"""Cliente para busca e enriquecimento de metadados via TMDB API v3 com chave nativa integrada."""

from __future__ import annotations

import urllib.parse
from typing import Any

from stv.infrastructure.http import HttpClient


class TmdbClient:
    """Consome a API v3 do The Movie Database (TMDB) com chave nativa integrada."""

    API_BASE = "https://api.themoviedb.org/3"
    IMAGE_BASE_BACKDROP = "https://image.tmdb.org/t/p/w1280"
    IMAGE_BASE_POSTER = "https://image.tmdb.org/t/p/w500"
    IMAGE_BASE_STILL = "https://image.tmdb.org/t/p/w500"
    DEFAULT_API_KEY = "e5df95f7e157b9709d093c1a6be7e1c5"

    def __init__(
        self,
        api_key: str = DEFAULT_API_KEY,
        language: str = "pt-BR",
        http: HttpClient | None = None,
    ) -> None:
        self.api_key = api_key.strip() if api_key else self.DEFAULT_API_KEY
        self.language = language or "pt-BR"
        self.http = http or HttpClient(timeout=3.0, user_agent="sTv-TMDB/1.0")

    def _request(self, endpoint: str, params: dict[str, str] | None = None) -> dict[str, Any]:
        if not self.api_key:
            return {}

        query_params = {
            "api_key": self.api_key,
            "language": self.language,
            "include_adult": "false",
        }
        if params:
            query_params.update(params)

        url = f"{self.API_BASE}/{endpoint.lstrip('?')}?{urllib.parse.urlencode(query_params)}"
        try:
            result = self.http.get_json(url, headers={"Accept": "application/json"})
            return result if isinstance(result, dict) else {}
        except Exception:
            return {}

    def _first_result(self, endpoint: str, params: dict[str, str]) -> dict[str, Any] | None:
        results = self._request(endpoint, params).get("results", [])
        return results[0] if isinstance(results, list) and results else None

    def _search_catalog(
        self,
        endpoint: str,
        year_param: str,
        title: str,
        year: str = "",
    ) -> dict[str, Any] | None:
        if not title:
            return None
        try:
            from saile_epg.normalizer import clean_media_title

            clean_title, extracted_year = clean_media_title(title)
        except Exception:
            clean_title, extracted_year = title, ""

        use_year = str(year or extracted_year or "").strip()
        if use_year and clean_title:
            hit = self._first_result(endpoint, {"query": clean_title, year_param: use_year})
            if hit:
                return hit

        if clean_title:
            hit = self._first_result(endpoint, {"query": clean_title})
            if hit:
                return hit

        if clean_title != title:
            params = {"query": title}
            if year:
                params[year_param] = str(year)
            return self._first_result(endpoint, params)

        return None

    def search_movie(self, title: str, year: str = "") -> dict[str, Any] | None:
        """Busca filmes pelo título com ano opcional e sanitização automática de tags IPTV."""
        return self._search_catalog("search/movie", "primary_release_year", title, year)

    def search_tv(self, title: str, year: str = "") -> dict[str, Any] | None:
        """Busca séries/programas de TV pelo título com ano opcional e sanitização de tags IPTV."""
        return self._search_catalog("search/tv", "first_air_date_year", title, year)

    def get_season_episodes(
        self,
        tv_id: str | int,
        season_number: str | int,
    ) -> dict[int, dict[str, Any]]:
        """Recupera metadados e still_path dos episódios de uma temporada pelo ID do TMDB."""
        if not tv_id:
            return {}
        data = self._request(f"tv/{tv_id}/season/{season_number}")
        episodes = data.get("episodes", [])
        result: dict[int, dict[str, Any]] = {}
        if isinstance(episodes, list):
            for ep in episodes:
                if isinstance(ep, dict) and "episode_number" in ep:
                    try:
                        ep_num = int(ep["episode_number"])
                    except (ValueError, TypeError):
                        continue
                    still_path = ep.get("still_path")
                    still_url = f"{self.IMAGE_BASE_STILL}{still_path}" if still_path else ""
                    result[ep_num] = {
                        "name": ep.get("name", ""),
                        "overview": ep.get("overview", ""),
                        "still_url": still_url,
                        "still_path": still_path or "",
                        "vote_average": ep.get("vote_average", 0.0),
                    }
        return result

    @classmethod
    def format_fanart_url(cls, backdrop_path: str | None, poster_path: str | None) -> str:
        """Retorna uma URL absoluta de imagem em alta definição."""
        if backdrop_path:
            return f"{cls.IMAGE_BASE_BACKDROP}{backdrop_path}"
        if poster_path:
            return f"{cls.IMAGE_BASE_POSTER}{poster_path}"
        return ""
