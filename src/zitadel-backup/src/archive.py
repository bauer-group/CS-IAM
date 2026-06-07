"""zitadel-backup — deterministic tar.gz bundling + sha256 + retention."""

from __future__ import annotations

import hashlib
import tarfile
from pathlib import Path

from logging_setup import logger


def sha256sum(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def create_archive(src_dir: Path, archive_path: Path) -> None:
    """tar.gz the staging dir with a stable member order (deterministic-ish)."""
    with tarfile.open(archive_path, "w:gz") as tar:
        for p in sorted(src_dir.rglob("*")):
            tar.add(p, arcname=str(p.relative_to(src_dir)))


def extract_archive(archive_path: Path, dest_dir: Path) -> Path:
    with tarfile.open(archive_path, "r:gz") as tar:
        tar.extractall(dest_dir)  # noqa: S202 — trusted, self-produced archives
    return dest_dir


def apply_local_retention(archive_dir: Path, keep: int) -> int:
    """Delete oldest *.tar.gz beyond `keep` (and their .manifest.json)."""
    if not archive_dir.exists():
        return 0
    archives = sorted(
        (p for p in archive_dir.glob("*.tar.gz") if p.is_file()),
        key=lambda p: p.name, reverse=True,
    )
    deleted = 0
    for archive in archives[keep:]:
        try:
            archive.unlink()
            manifest = archive.with_name(archive.name.replace(".tar.gz", ".manifest.json"))
            manifest.unlink(missing_ok=True)
            deleted += 1
        except OSError as exc:
            logger.error("failed to delete %s: %s", archive, exc)
    if deleted:
        logger.info("local retention pruned %d archive(s)", deleted)
    return deleted
