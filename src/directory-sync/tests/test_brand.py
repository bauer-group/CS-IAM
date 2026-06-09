"""Tests for the Login v2 branding upload (jobs.brand)."""

from __future__ import annotations

import jobs
from config import Settings


class _FakeZit:
    """Duck-typed stand-in for ZitadelClient — records what brand() would send."""

    def __init__(self) -> None:
        self.uploads: list[tuple[str, str, str]] = []
        self.activated = False

    def upload_label_asset(self, path, filename, content, content_type):
        assert isinstance(content, (bytes, bytearray)) and len(content) > 0
        self.uploads.append((path, filename, content_type))

    def activate_label_policy(self):
        self.activated = True


def _settings(branding_dir, enabled=True) -> Settings:
    return Settings(branding_dir=str(branding_dir), branding_enabled=enabled)


def test_brand_uploads_present_assets_and_activates(tmp_path):
    (tmp_path / "logo-light.svg").write_text("<svg/>")
    (tmp_path / "logo-dark.svg").write_text("<svg/>")
    (tmp_path / "icon.png").write_bytes(b"\x89PNG\r\n")
    zit = _FakeZit()

    jobs.brand(_settings(tmp_path), zit)

    paths = {p for p, _, _ in zit.uploads}
    assert paths == {"logo", "logo/dark", "icon"}
    content_types = {p: ct for p, _, ct in zit.uploads}
    assert content_types["logo"] == "image/svg+xml"
    assert content_types["icon"] == "image/png"
    assert zit.activated is True


def test_brand_skips_when_disabled(tmp_path):
    (tmp_path / "logo-light.svg").write_text("<svg/>")
    zit = _FakeZit()

    jobs.brand(_settings(tmp_path, enabled=False), zit)

    assert zit.uploads == []
    assert zit.activated is False


def test_brand_no_assets_does_not_activate(tmp_path):
    zit = _FakeZit()

    jobs.brand(_settings(tmp_path), zit)

    assert zit.uploads == []
    assert zit.activated is False


def test_brand_ignores_unknown_extensions(tmp_path):
    (tmp_path / "logo-light.txt").write_text("not an image")
    zit = _FakeZit()

    jobs.brand(_settings(tmp_path), zit)

    assert zit.uploads == []
    assert zit.activated is False
