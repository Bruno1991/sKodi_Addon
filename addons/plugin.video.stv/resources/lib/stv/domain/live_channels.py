from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, Sequence

from saile_epg.models import EpgChannel
from stv.domain.models import MediaItem


@dataclass(frozen=True)
class LiveChannelGroup:
    channel: EpgChannel
    variants: tuple[MediaItem, ...]


@dataclass(frozen=True)
class LiveCatalog:
    groups: tuple[LiveChannelGroup, ...]
    unmatched_items: tuple[MediaItem, ...]

    def get_group(self, channel_key: str) -> LiveChannelGroup | None:
        return next(
            (group for group in self.groups if group.channel.channel_key == channel_key),
            None,
        )

    def visible_category_ids(
        self,
        category_ids: Sequence[str],
        catalog_complete: bool = False,
    ) -> set[str]:
        unmatched_category_ids = {item.category_id for item in self.unmatched_items}
        if catalog_complete:
            return set(category_ids) & unmatched_category_ids
        cached_category_ids = {
            item.category_id
            for group in self.groups
            for item in group.variants
        } | unmatched_category_ids
        return {
            category_id
            for category_id in category_ids
            if category_id not in cached_category_ids
            or category_id in unmatched_category_ids
        }

    def unmatched_in_category(self, category_id: str) -> tuple[MediaItem, ...]:
        return tuple(
            item for item in self.unmatched_items if item.category_id == category_id
        )


_QUALITY_PATTERNS: tuple[tuple[int, str, re.Pattern[str]], ...] = (
    (4, "4K", re.compile(r"\b(4K|UHD|2160P)\b", re.IGNORECASE)),
    (3, "FHD", re.compile(r"\b(FHD|1080P)\b", re.IGNORECASE)),
    (2, "HD", re.compile(r"\b(HD|720P)\b", re.IGNORECASE)),
    (1, "SD", re.compile(r"\b(SD|480P|360P)\b", re.IGNORECASE)),
)
_QUALITY_LIMITS = {"auto": 4, "4k": 4, "fhd": 3, "hd": 2, "sd": 1}
_MINIMUM_MBPS = {4: 18.0, 3: 8.0, 2: 3.5, 1: 1.2, 0: 1.2}


def variant_quality(item: MediaItem) -> tuple[int, str]:
    value = item.source_name or item.name
    for rank, label, pattern in _QUALITY_PATTERNS:
        if pattern.search(value):
            return (rank, label)
    return (0, "AUTO")


def build_live_catalog(
    epg_channels: Sequence[EpgChannel],
    items: Sequence[MediaItem],
) -> LiveCatalog:
    by_id = {
        channel.epg_id.strip().casefold(): channel
        for channel in epg_channels
        if channel.epg_id.strip()
    }
    by_name_candidates: dict[str, list[EpgChannel]] = {}
    for channel in epg_channels:
        if channel.normalized_name:
            by_name_candidates.setdefault(channel.normalized_name, []).append(channel)
    by_unique_name = {
        name: candidates[0]
        for name, candidates in by_name_candidates.items()
        if len(candidates) == 1
    }

    grouped: dict[str, tuple[EpgChannel, list[MediaItem]]] = {}
    unmatched: list[MediaItem] = []
    for item in items:
        channel = by_id.get(item.epg_id.strip().casefold()) if item.epg_id.strip() else None
        if channel is None and item.normalized_name:
            channel = by_unique_name.get(item.normalized_name)
        if channel is None:
            unmatched.append(item)
            continue
        entry = grouped.setdefault(channel.channel_key, (channel, []))
        entry[1].append(item)

    groups = []
    for channel, variants in grouped.values():
        ordered = tuple(
            sorted(
                variants,
                key=lambda item: (-variant_quality(item)[0], item.item_id),
            )
        )
        groups.append(LiveChannelGroup(channel=channel, variants=ordered))
    groups.sort(key=lambda group: (group.channel.display_name.casefold(), group.channel.channel_key))
    unmatched.sort(key=lambda item: (item.name.casefold(), item.item_id))
    return LiveCatalog(tuple(groups), tuple(unmatched))


def choose_live_variant(
    variants: Sequence[MediaItem],
    max_quality: str = "auto",
    bandwidth_limit_mbps: float = 0.0,
    probe: Callable[[MediaItem], float | None] | None = None,
) -> MediaItem:
    if not variants:
        raise ValueError("Canal sem variantes de reprodução")
    limit = _QUALITY_LIMITS.get(max_quality.lower(), 4)
    if bandwidth_limit_mbps > 0:
        safe_bandwidth = bandwidth_limit_mbps * 0.70
        allowed_by_bandwidth = max(
            (rank for rank, minimum in _MINIMUM_MBPS.items() if minimum <= safe_bandwidth),
            default=1,
        )
        limit = min(limit, allowed_by_bandwidth)

    candidates = [
        item
        for item in variants
        if variant_quality(item)[0] <= limit
    ]
    if not candidates:
        candidates = list(variants)
    candidates.sort(key=lambda item: (-variant_quality(item)[0], item.item_id))

    if probe is not None:
        measured_candidates: list[tuple[float, MediaItem]] = []
        for item in candidates[:3]:
            measured = probe(item)
            if measured is None:
                continue
            measured_candidates.append((measured, item))
            minimum = _MINIMUM_MBPS[variant_quality(item)[0]]
            if measured >= minimum * 1.15:
                return item
        if measured_candidates:
            return max(measured_candidates, key=lambda result: result[0])[1]
    return candidates[0]
