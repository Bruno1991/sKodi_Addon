"""Cliente para busca e enriquecimento de metadados via TMDB API v3."""
from __future__ import annotations

import urllib.parse
from typing import Any

from stv.infrastructure.http import HttpClient


class TmdbClient:
    """Consome a API v3 do The Movie Database (TMDB) usando autenticação Bearer."""

    API_BASE = "https://api.themoviedb.org/3"
    IMAGE_BASE_BACKDROP = "https://image.tmdb.org/t/p/w1280"
    IMAGE_BASE_POSTER = "https://image.tmdb.org/t/p/w500"

    def __init__(
        self,
        bearer_token: str = "",
        language: str = "pt-BR",
        http: HttpClient | None = None,
    ) -> None:
        self.bearer_token = bearer_token.strip()
        self.language = language
        self.http = http or HttpClient(timeout=8.0, user_agent="sTv-TMDB/1.0")

    def _request(self, endpoint: str, params: dict[str, str] | None = None) -> dict[str, Any]:
        if not self.bearer_token:
            return {}

        query_params = {"language": self.language, "include_adult": "false"}
        if params:
            query_params.update(params)

        url = f"{self.API_BASE}/{endpoint.lstrip('?')}"
        if query_params:
            url = f"{url}?{urllib.parse.urlencode(query_params)}"

        headers = {
            "Authorization": f"Bearer {self.bearer_token}",
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

    @classmethod
    def format_fanart_url(cls, backdrop_path: str | None, poster_path: str | None) -> str:
        """Retorna uma URL absoluta de imagem em alta definição."""
        if backdrop_path:
            return f"{cls.IMAGE_BASE_BACKDROP}{backdrop_path}"
        if poster_path:
            return f"{cls.IMAGE_BASE_POSTER}{poster_path}"
        return ""
