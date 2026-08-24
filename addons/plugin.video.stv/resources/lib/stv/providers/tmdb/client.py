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
        self.http = http or HttpClient(timeout=8.0, user_agent="sTv-TMDB/1.0")

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
        headers = {
            "Accept": "application/json",
        }

        try:
            result = self.http.get_json(url, headers=headers)
            if isinstance(result, dict):
                return result
            return {}
        except Exception:
            return {}

    def search_movie(self, title: str, year: str = "") -> dict[str, Any] | None:
        """Busca filmes pelo título com ano opcional."""
        if not title:
            return None
        params = {"query": title}
        if year:
            params["primary_release_year"] = str(year)
        data = self._request("search/movie", params)
        results = data.get("results", [])
        if results and isinstance(results, list):
            return results[0]
        return None

    def search_tv(self, title: str, year: str = "") -> dict[str, Any] | None:
        """Busca séries/programas de TV pelo título com ano opcional."""
        if not title:
            return None
        params = {"query": title}
        if year:
            params["first_air_date_year"] = str(year)
        data = self._request("search/tv", params)
        results = data.get("results", [])
        if results and isinstance(results, list):
            return results[0]
        return None

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
                    still_url = (
                        f"{self.IMAGE_BASE_STILL}{still_path}"
                        if still_path
                        else ""
                    )
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

