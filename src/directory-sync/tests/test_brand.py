"""Tests for the Login v2 branding upload (jobs.brand)."""

from __future__ import annotations

import jobs
from config import Settings


_PATH_FIELD = {
    "logo": "logoUrl",
    "logo/dark": "logoUrlDark",
    "icon": "iconUrl",
    "icon/dark": "iconUrlDark",
    "font": "fontUrl",
}


class _FakeZit:
    """Duck-typed stand-in for ZitadelClient — records what brand() would send.

    get_label_policy() reflects the uploaded assets as the active policy would
    after an activate, so brand()'s verify passes on the first attempt.
    """

    def __init__(self) -> None:
        self.uploads: list[tuple[str, str, str]] = []
        self.activated = False
        self.activate_count = 0

    def upload_label_asset(self, path, filename, content, content_type):
        assert isinstance(content, (bytes, bytearray)) and len(content) > 0
        self.uploads.append((path, filename, content_type))

    def activate_label_policy(self):
        self.activated = True
        self.activate_count += 1

    def get_label_policy(self):
        return {_PATH_FIELD[p]: f"https://assets/{p}" for p, _, _ in self.uploads if p in _PATH_FIELD}


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
    # Complete policy on the first read → no retry needed.
    assert zit.activate_count == 1


def test_brand_retries_activate_until_policy_complete(tmp_path, monkeypatch):
    """The upload→activate projection race: iconUrl only appears on a later read,
    so brand() must re-activate until the active policy carries every asset."""
    monkeypatch.setattr(jobs.time, "sleep", lambda *_: None)
    (tmp_path / "logo-light.svg").write_text("<svg/>")
    (tmp_path / "icon.png").write_bytes(b"\x89PNG\r\n")

    class _LaggyZit(_FakeZit):
        def get_label_policy(self):
            policy = {"logoUrl": "https://assets/logo"}
            if self.activate_count >= 2:  # icon becomes visible only after a retry
                policy["iconUrl"] = "https://assets/icon"
            return policy

    zit = _LaggyZit()
    jobs.brand(_settings(tmp_path), zit)

    assert zit.activate_count == 2  # retried once, until iconUrl projected


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
