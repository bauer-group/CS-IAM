"""
directory-sync — Configuration (Pydantic Settings from environment variables).
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Microsoft Graph (source) ──────────────────────────────────────────
    azure_tenant_id: str = Field(default="")
    azure_client_id: str = Field(default="")
    azure_client_secret: SecretStr = Field(default=SecretStr(""))

    # ── Zitadel (target) ──────────────────────────────────────────────────
    zitadel_domain: str = Field(default="localhost")
    zitadel_port: int = Field(default=443, ge=1, le=65535)
    zitadel_insecure: bool = Field(default=False)
    zitadel_jwt_profile_file: str = Field(default="/machinekey/iam-admin.json")
    zitadel_wait_timeout: int = Field(default=180, ge=0)

    # ── Sync behaviour ────────────────────────────────────────────────────
    sync_enabled: bool = Field(default=True)
    sync_profiles_interval: int = Field(default=300, ge=30)
    sync_groups_interval: int = Field(default=600, ge=30)
    sync_role_prefix: str = Field(default="entra:")
    sync_project_name: str = Field(default="BAUER GROUP")
    data_dir: str = Field(default="/data", description="Delta-token + report storage")

    # ── Logging ───────────────────────────────────────────────────────────
    sync_log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(default="INFO")
    sync_log_format: Literal["console", "json"] = Field(default="console")

    time_zone: str = Field(default="Etc/UTC", alias="TZ")

    # ── Derived helpers ───────────────────────────────────────────────────
    def issuer(self) -> str:
        """The Zitadel issuer / base URL — must match how Zitadel was started.

        Port is omitted for the canonical 443/https and 80/http cases so the
        string equals Zitadel's own issuer (used as the JWT audience).
        """
        scheme = "http" if self.zitadel_insecure else "https"
        default_port = 80 if self.zitadel_insecure else 443
        if self.zitadel_port == default_port:
            return f"{scheme}://{self.zitadel_domain}"
        return f"{scheme}://{self.zitadel_domain}:{self.zitadel_port}"

    def azure_secret(self) -> str:
        return self.azure_client_secret.get_secret_value()

    def graph_configured(self) -> bool:
        return bool(self.azure_tenant_id and self.azure_client_id and self.azure_secret())
