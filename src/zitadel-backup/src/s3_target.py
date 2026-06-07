"""zitadel-backup — optional off-site S3 target (boto3, S3-compatible)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Optional

import boto3
from botocore.client import Config

from logging_setup import logger

if TYPE_CHECKING:
    from config import Settings


@dataclass
class RemoteSnapshot:
    snapshot_id: str
    size: int
    last_modified: str


class S3Target:
    def __init__(self, settings: "Settings"):
        self.bucket = settings.backup_s3_bucket
        self.prefix = settings.backup_s3_prefix.rstrip("/") + "/" if settings.backup_s3_prefix else ""
        self._client = boto3.client(
            "s3",
            endpoint_url=settings.backup_s3_endpoint or None,
            aws_access_key_id=settings.backup_s3_access_key,
            aws_secret_access_key=settings.backup_secret(),
            region_name=settings.backup_s3_region,
            config=Config(s3={"addressing_style": "path"}, signature_version="s3v4"),
        )

    def _key(self, snapshot_id: str, suffix: str) -> str:
        return f"{self.prefix}{snapshot_id}{suffix}"

    def ensure_bucket(self) -> bool:
        try:
            self._client.head_bucket(Bucket=self.bucket)
            return True
        except Exception:  # noqa: BLE001
            try:
                self._client.create_bucket(Bucket=self.bucket)
                return True
            except Exception as exc:  # noqa: BLE001
                logger.error("cannot reach/create target bucket %s: %s", self.bucket, exc)
                return False

    def upload(self, archive: Path, manifest: Path, snapshot_id: str) -> Optional[str]:
        try:
            self._client.upload_file(str(archive), self.bucket, self._key(snapshot_id, ".tar.gz"))
            self._client.upload_file(str(manifest), self.bucket, self._key(snapshot_id, ".manifest.json"))
            return f"s3://{self.bucket}/{self._key(snapshot_id, '.tar.gz')}"
        except Exception as exc:  # noqa: BLE001
            logger.error("upload failed: %s", exc)
            return None

    def list_snapshots(self) -> list[RemoteSnapshot]:
        snaps: list[RemoteSnapshot] = []
        paginator = self._client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self.bucket, Prefix=self.prefix):
            for obj in page.get("Contents", []):
                key = obj["Key"]
                if key.endswith(".tar.gz"):
                    sid = key[len(self.prefix):-len(".tar.gz")]
                    snaps.append(RemoteSnapshot(sid, obj["Size"], obj["LastModified"].isoformat()))
        return sorted(snaps, key=lambda s: s.snapshot_id, reverse=True)

    def delete_snapshot(self, snapshot_id: str) -> None:
        for suffix in (".tar.gz", ".manifest.json"):
            try:
                self._client.delete_object(Bucket=self.bucket, Key=self._key(snapshot_id, suffix))
            except Exception as exc:  # noqa: BLE001
                logger.warning("delete %s%s failed: %s", snapshot_id, suffix, exc)

    def download(self, snapshot_id: str, dest: Path) -> bool:
        try:
            self._client.download_file(self.bucket, self._key(snapshot_id, ".tar.gz"), str(dest))
            return True
        except Exception as exc:  # noqa: BLE001
            logger.error("download failed: %s", exc)
            return False

    def apply_retention(self, keep: int) -> int:
        snaps = self.list_snapshots()
        deleted = 0
        for snap in snaps[keep:]:
            self.delete_snapshot(snap.snapshot_id)
            deleted += 1
        if deleted:
            logger.info("remote retention pruned %d snapshot(s)", deleted)
        return deleted
