"""Cliente HTTP seguro, resiliente e leve para consumo de APIs remotas."""
from __future__ import annotations

import gzip
import json
import ssl
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class HttpClient:
    """Cliente HTTP com suporte a gzip, tolerância a certificados SSL e User-Agent IPTV."""

    def __init__(
        self,
        timeout: float = 30.0,
        user_agent: str = "IPTVSmartersPro/3.1.5.1 (Windows NT 10.0; Win64; x64)",
    ) -> None:
        self.timeout = timeout
        self.user_agent = user_agent
        self._ssl_context = self._create_ssl_context()

    @staticmethod
    def _create_ssl_context() -> ssl.SSLContext:
        """Cria um contexto SSL tolerante a servidores IPTV com certificados autoassinados."""
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx

    def get_raw(
        self,
        url: str,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
    ) -> bytes:
        """Executa uma requisição GET retornando os bytes decodificados (descomprimindo gzip se necessário)."""
        request_headers = {
            "User-Agent": self.user_agent,
            "Accept-Encoding": "gzip, deflate",
            "Accept": "*/*",
            **(headers or {}),
        }
        request = Request(url, headers=request_headers, method="GET")
        try:
            with urlopen(
                request,
                timeout=self.timeout if timeout is None else timeout,
                context=self._ssl_context,
            ) as response:
                content = response.read()
                # Verifica se a resposta está comprimida em Gzip
                is_gzip = response.info().get("Content-Encoding") == "gzip" or content.startswith(b"\x1f\x8b")
                if is_gzip:
                    try:
                        content = gzip.decompress(content)
                    except Exception:
                        pass
                return content
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            # HTTPError pode conter a URL completa com credenciais Xtream.
            raise RuntimeError("Falha ao conectar ao servidor IPTV") from exc

    def get_json(
        self,
        url: str,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
    ) -> object:
        """Executa uma requisição GET retornando a resposta decodificada como JSON."""
        content = self.get_raw(url, headers=headers, timeout=timeout)
        text = content.decode("utf-8", errors="replace").lstrip("\ufeff").strip()
        if not text:
            return []
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            # Fallback para latin-1 caso contenha caracteres especiais não-UTF8
            try:
                fallback_text = content.decode("latin-1", errors="replace").strip()
                return json.loads(fallback_text)
            except Exception:
                raise RuntimeError(f"Resposta JSON inválida do servidor: {exc}") from exc

    def probe_stream(
        self,
        url: str,
        sample_bytes: int = 128 * 1024,
        timeout: float = 4.0,
    ) -> float | None:
        """Mede uma amostra curta sem registrar a URL autenticada; retorna Mbps."""
        request = Request(
            url,
            headers={
                "User-Agent": self.user_agent,
                "Accept": "*/*",
                "Range": f"bytes=0-{sample_bytes - 1}",
                "Connection": "close",
            },
            method="GET",
        )
        started = time.monotonic()
        received = 0
        try:
            with urlopen(request, timeout=timeout, context=self._ssl_context) as response:
                while received < sample_bytes:
                    chunk = response.read(min(32 * 1024, sample_bytes - received))
                    if not chunk:
                        break
                    received += len(chunk)
        except (HTTPError, URLError, TimeoutError, OSError, TypeError):
            return None
        elapsed = max(time.monotonic() - started, 0.001)
        if received < 188:
            return None
        return (received * 8) / elapsed / 1_000_000
