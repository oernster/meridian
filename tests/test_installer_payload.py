"""Reading the embedded payload and its manifest.

Four small accessors that everything else in the installer depends on: they
resolve the payload zip and manifest through the resource resolver, which
answers differently when running frozen, and turn the manifest JSON into the
entries `repair` walks.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from installer.ops import payload
from installer.ops.payload import (
    ManifestEntry,
    PayloadManifest,
    iter_manifest_entries,
    load_manifest,
    manifest_json_path,
    payload_zip_path,
)


def test_payload_paths_come_from_the_resource_resolver(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(payload, "resource_path", lambda rel: tmp_path / rel)

    assert payload_zip_path() == tmp_path / "installer/payload/payload.zip"
    assert manifest_json_path() == tmp_path / "installer/payload/manifest.json"


def test_a_manifest_is_read_into_entries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "manifest.json"
    path.write_text(
        json.dumps(
            {
                "installer_version": "2.5.0",
                "entries": [{"path": "Meridian.exe", "size": 12, "sha256": "abc"}],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(payload, "manifest_json_path", lambda: path)

    manifest = load_manifest()

    assert manifest.installer_version == "2.5.0"
    assert manifest.entries == (
        ManifestEntry(path="Meridian.exe", size=12, sha256="abc"),
    )


def test_a_manifest_without_entries_reads_as_empty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A manifest that lost its entries must not read as a valid empty one."""
    path = tmp_path / "manifest.json"
    path.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(payload, "manifest_json_path", lambda: path)

    manifest = load_manifest()

    assert manifest.installer_version == ""
    assert manifest.entries == ()


def test_iterating_a_manifest_yields_its_entries() -> None:
    entry = ManifestEntry(path="Meridian.exe", size=1, sha256="x")
    manifest = PayloadManifest(installer_version="2.5.0", entries=(entry,))

    assert list(iter_manifest_entries(manifest)) == [entry]
