"""DTOs for the in-app update check."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ReleaseAsset:
    name: str
    download_url: str


@dataclass(frozen=True, slots=True)
class ReleaseInfo:
    version: str
    page_url: str | None
    assets: tuple[ReleaseAsset, ...]


@dataclass(frozen=True, slots=True)
class UpdateStatus:
    current: str
    latest: str
    update_available: bool
    download_url: str | None
    page_url: str | None
