from __future__ import annotations

import gzip
import tempfile
import time
import xml.etree.ElementTree as ET
import zipfile
from datetime import datetime, timedelta, timezone
from typing import BinaryIO
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from saile_epg.errors import EpgSyncError
from saile_epg.models import EpgChannel, EpgProgram, EpgSnapshot
from saile_epg.normalizer import normalize_channel_name

MAX_PROGRAMS = 250_000
MAX_DOWNLOAD_BYTES = 256 * 1024 * 1024
MAX_UNCOMPRESSED_BYTES = 512 * 1024 * 1024
DOWNLOAD_CHUNK_BYTES = 256 * 1024
SPOOL_MEMORY_BYTES = 8 * 1024 * 1024


class XmltvFormatError(ValueError):
    pass


class XmltvEmptyGuideError(ValueError):
    pass


def parse_xmltv_timestamp(value: str) -> int:
    compact = value.strip()
    if len(compact) < 12:
        raise ValueError(f"Timestamp XMLTV inválido: {value!r}")
    digits = compact.split()[0]
    if len(digits) == 12:
        digits += "00"
    moment = datetime.strptime(digits[:14], "%Y%m%d%H%M%S")

    remainder = compact[len(compact.split()[0]) :].strip()
    if remainder and remainder.upper() != "Z":
        sign = -1 if remainder.startswith("-") else 1
        offset = remainder.lstrip("+-")[:4]
        if len(offset) != 4 or not offset.isdigit():
            raise ValueError(f"Fuso XMLTV inválido: {value!r}")
        delta = timedelta(hours=int(offset[:2]), minutes=int(offset[2:])) * sign
        moment = moment.replace(tzinfo=timezone(delta))
    else:
        moment = moment.replace(tzinfo=timezone.utc)
    return int(moment.astimezone(timezone.utc).timestamp())


def _local_tag(element: ET.Element) -> str:
    return element.tag.rsplit("}", 1)[-1]


def _child_text(element: ET.Element, name: str) -> str:
    for child in element:
        if _local_tag(child) == name and child.text:
            return child.text.strip()
    return ""


def _child_icon(element: ET.Element) -> str:
    for child in element:
        if _local_tag(child) == "icon":
            return str(child.attrib.get("src", "")).strip()
    return ""


class XmltvProvider:
    def __init__(
        self,
        url: str,
        provider_id: str = "xtream",
        timeout: int = 30,
        window_before_hours: int = 12,
        window_after_hours: int = 48,
    ) -> None:
        self.url = url
        self.provider_id = provider_id
        self.timeout = timeout
        self.window_before_hours = window_before_hours
        self.window_after_hours = window_after_hours

    def fetch(self) -> EpgSnapshot:
        if not self.url.startswith(("http://", "https://")):
            raise EpgSyncError("EPG-URL", "URL XMLTV inválida")
        request = Request(
            self.url,
            headers={
                "Accept": "application/xml, text/xml, application/gzip",
                "Accept-Encoding": "gzip",
                "User-Agent": "SAILE-EPG/1.2.0",
            },
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                with tempfile.SpooledTemporaryFile(
                    max_size=SPOOL_MEMORY_BYTES,
                    mode="w+b",
                ) as buffer:
                    self._download(response, buffer)
                    return self._parse_download(buffer)
        except EpgSyncError:
            raise
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            # A exceção pública não inclui a URL, que contém credenciais Xtream.
            raise EpgSyncError(
                "EPG-DOWNLOAD",
                "Não foi possível baixar o XMLTV do provedor",
            ) from exc

    @staticmethod
    def _download(response: object, buffer: BinaryIO) -> None:
        read = getattr(response, "read", None)
        if not callable(read):
            raise EpgSyncError(
                "EPG-HTTP-READ",
                "O provedor retornou uma resposta HTTP incompatível",
            )

        downloaded = 0
        try:
            while True:
                chunk = read(DOWNLOAD_CHUNK_BYTES)
                if not chunk:
                    break
                if not isinstance(chunk, (bytes, bytearray)):
                    raise EpgSyncError(
                        "EPG-HTTP-DATA",
                        "O provedor retornou dados XMLTV incompatíveis",
                    )
                downloaded += len(chunk)
                if downloaded > MAX_DOWNLOAD_BYTES:
                    raise EpgSyncError(
                        "EPG-DOWNLOAD-LIMIT",
                        "O XMLTV excede o limite seguro de download",
                    )
                buffer.write(chunk)
        except EpgSyncError:
            raise
        except (TimeoutError, OSError, TypeError) as exc:
            raise EpgSyncError(
                "EPG-DOWNLOAD",
                "Não foi possível baixar o XMLTV do provedor",
            ) from exc

        if downloaded == 0:
            raise EpgSyncError("EPG-EMPTY", "O provedor retornou um XMLTV vazio")
        buffer.seek(0)

    def _parse_download(self, buffer: BinaryIO) -> EpgSnapshot:
        magic = buffer.read(4)
        buffer.seek(0)

        try:
            # Os bytes reais são a fonte de verdade. Alguns proxies mantêm
            # Content-Encoding: gzip mesmo depois de descompactar a resposta.
            if magic.startswith(b"\x1f\x8b"):
                with gzip.GzipFile(fileobj=buffer, mode="rb") as stream:
                    return self.parse(stream)
            if magic.startswith(b"PK\x03\x04"):
                return self._parse_zip(buffer)
            return self.parse(buffer)
        except EpgSyncError:
            raise
        except XmltvFormatError as exc:
            raise EpgSyncError(
                "EPG-FORMAT",
                "O provedor não retornou um arquivo XMLTV",
            ) from exc
        except XmltvEmptyGuideError as exc:
            raise EpgSyncError(
                "EPG-NO-PROGRAMS",
                "O XMLTV não contém programação válida para o período atual",
            ) from exc
        except ET.ParseError as exc:
            raise EpgSyncError(
                "EPG-XML",
                "O XMLTV recebido contém XML inválido",
            ) from exc
        except (gzip.BadGzipFile, zipfile.BadZipFile, EOFError) as exc:
            raise EpgSyncError(
                "EPG-COMPRESSION",
                "O arquivo XMLTV compactado está corrompido",
            ) from exc
        except (OSError, TypeError, ValueError) as exc:
            raise EpgSyncError(
                "EPG-PARSE",
                "O XMLTV recebido é inválido ou incompatível",
            ) from exc

    def _parse_zip(self, buffer: BinaryIO) -> EpgSnapshot:
        with zipfile.ZipFile(buffer) as archive:
            files = [item for item in archive.infolist() if not item.is_dir()]
            xml_files = [
                item
                for item in files
                if item.filename.lower().endswith((".xml", ".xmltv"))
            ]
            candidates = xml_files or (files if len(files) == 1 else [])
            if not candidates:
                raise XmltvFormatError("ZIP sem arquivo XMLTV identificável")
            entry = candidates[0]
            if entry.file_size > MAX_UNCOMPRESSED_BYTES:
                raise EpgSyncError(
                    "EPG-UNPACK-LIMIT",
                    "O XMLTV excede o limite seguro após a descompactação",
                )
            with archive.open(entry, mode="r") as stream:
                return self.parse(stream)

    def parse(self, stream: BinaryIO, fetched_at_utc: int | None = None) -> EpgSnapshot:
        fetched_at = int(time.time()) if fetched_at_utc is None else int(fetched_at_utc)
        minimum = fetched_at - (self.window_before_hours * 3600)
        maximum = fetched_at + (self.window_after_hours * 3600)
        channels: dict[str, EpgChannel] = {}
        programs: list[EpgProgram] = []

        root_seen = False
        for event, element in ET.iterparse(stream, events=("start", "end")):
            tag = _local_tag(element)
            if event == "start":
                if not root_seen:
                    root_seen = True
                    if tag != "tv":
                        raise XmltvFormatError("Elemento raiz XMLTV deve ser tv")
                continue
            if tag == "channel":
                channel_key = str(element.attrib.get("id", "")).strip()
                if channel_key:
                    display_name = _child_text(element, "display-name") or channel_key
                    channels[channel_key] = EpgChannel(
                        provider_id=self.provider_id,
                        channel_key=channel_key,
                        epg_id=channel_key,
                        display_name=display_name,
                        normalized_name=normalize_channel_name(display_name),
                        icon_url=_child_icon(element),
                    )
                element.clear()
                continue

            if tag != "programme":
                continue
            channel_key = str(element.attrib.get("channel", "")).strip()
            try:
                start_utc = parse_xmltv_timestamp(str(element.attrib.get("start", "")))
                end_utc = parse_xmltv_timestamp(str(element.attrib.get("stop", "")))
            except ValueError:
                element.clear()
                continue
            title = _child_text(element, "title")
            if (
                channel_key
                and title
                and end_utc > start_utc
                and end_utc >= minimum
                and start_utc <= maximum
            ):
                programs.append(
                    EpgProgram(
                        provider_id=self.provider_id,
                        channel_key=channel_key,
                        title=title,
                        start_utc=start_utc,
                        end_utc=end_utc,
                        description=_child_text(element, "desc"),
                        category=_child_text(element, "category"),
                        icon_url=_child_icon(element),
                    )
                )
                if len(programs) > MAX_PROGRAMS:
                    raise ValueError("XMLTV excede o limite seguro de programas")
            element.clear()

        # A identidade do canal não depende de haver programação na janela
        # atual. Isso permite ao consumidor projetar todos os canais declarados
        # pelo guia e degradar somente o texto para "sem programação".
        filtered_channels = tuple(channel for _key, channel in sorted(channels.items()))
        filtered_programs = tuple(
            program for program in programs if program.channel_key in channels
        )
        if not root_seen:
            raise XmltvFormatError("XMLTV sem elemento raiz")
        if not filtered_channels:
            raise XmltvEmptyGuideError(
                "XMLTV não contém canais declarados"
            )
        return EpgSnapshot(
            provider_id=self.provider_id,
            channels=filtered_channels,
            programs=filtered_programs,
            fetched_at_utc=fetched_at,
        )
