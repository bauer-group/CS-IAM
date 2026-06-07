"""
database-backup — Configuration (Pydantic Settings).

Postgres-only snapshots (pg_dump). There is no S3 *source* in this stack;
BACKUP_S3_* is an optional off-site *target* for the finished archive.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    # ── Source: PostgreSQL ────────────────────────────────────────────────
    db_host: str = Field(default="database-server")
    db_port: int = Field(default=5432, ge=1, le=65535)
    db_name: str = Field(default="zitadel")
    db_user: str = Field(default="zitadel")
    db_password: SecretStr = Field(default=SecretStr(""))
    db_ssl_mode: str = Field(default="disable")

    backup_database_dump_format: Literal["plain", "custom"] = Field(default="custom")
    backup_database_dump_timeout_seconds: int = Field(default=1800, ge=60, le=14400)

    # ── Target: optional external S3 ──────────────────────────────────────
    backup_s3_endpoint: Optional[str] = Field(default=None)
    backup_s3_bucket: str = Field(default="")
    backup_s3_access_key: str = Field(default="")
    backup_s3_secret_key: SecretStr = Field(default=SecretStr(""))
    backup_s3_region: str = Field(default="eu-central-1")
    backup_s3_prefix: str = Field(default="iam/")

    # ── Retention / storage ───────────────────────────────────────────────
    backup_retention_count: int = Field(default=14, ge=1)
    data_dir: str = Field(default="/data")
    keep_local_archive: bool = Field(default=True)

    # ── Scheduler ─────────────────────────────────────────────────────────
    backup_schedule_enabled: bool = Field(default=True)
    backup_schedule_mode: Literal["cron", "interval"] = Field(default="cron")
    backup_schedule_cron: str = Field(default="15 3 * * *")
    backup_schedule_interval_hours: int = Field(default=24, ge=1, le=168)
    backup_on_startup: bool = Field(default=False)

    # ── Metadata ──────────────────────────────────────────────────────────
    instance_name: str = Field(default="iam")
    time_zone: str = Field(default="Etc/UTC", alias="TZ")

    # ── Alerting ──────────────────────────────────────────────────────────
    alert_enabled: bool = Field(default=False)
    alert_level: Literal["errors", "warnings", "all"] = Field(default="warnings")
    alert_channels: str = Field(default="")
    smtp_host: Optional[str] = Field(default=None)
    smtp_port: int = Field(default=587)
    smtp_tls: bool = Field(default=True)
    smtp_user: Optional[str] = Field(default=None)
    smtp_password: Optional[SecretStr] = Field(default=None)
    smtp_from: Optional[str] = Field(default=None)
    smtp_to: str = Field(default="")
    webhook_url: Optional[str] = Field(default=None)
    teams_webhook_url: Optional[str] = Field(default=None)

    # ── Logging ───────────────────────────────────────────────────────────
    backup_log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(default="INFO")
    backup_log_format: Literal["console", "json"] = Field(default="console")

    @field_validator("backup_schedule_cron")
    @classmethod
    def _validate_cron(cls, v: str) -> str:
        if not v.strip():
            return ""
        if len(v.strip().split()) != 5:
            raise ValueError("backup_schedule_cron must have 5 fields (m h dom mon dow)")
        return v.strip()

    @field_validator("alert_channels")
    @classmethod
    def _validate_channels(cls, v: str) -> str:
        if not v:
            return v
        valid = {"email", "webhook", "teams"}
        chans = [c.strip().lower() for c in v.split(",") if c.strip()]
        invalid = set(chans) - valid
        if invalid:
            raise ValueError(f"invalid alert channels {invalid!r}; valid: {valid!r}")
        return ",".join(chans)

    # ── helpers ───────────────────────────────────────────────────────────
    def db_password_str(self) -> str:
        return self.db_password.get_secret_value()

    def backup_secret(self) -> str:
        return self.backup_s3_secret_key.get_secret_value()

    def smtp_password_str(self) -> Optional[str]:
        return self.smtp_password.get_secret_value() if self.smtp_password else None

    def target_configured(self) -> bool:
        return bool(self.backup_s3_bucket and self.backup_s3_access_key and self.backup_secret())

    def get_alert_channels(self) -> list[str]:
        return [c.strip().lower() for c in self.alert_channels.split(",") if c.strip()]

    def get_smtp_recipients(self) -> list[str]:
        return [r.strip() for r in self.smtp_to.split(",") if r.strip()]
