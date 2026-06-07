"""database-backup — alerting (email / webhook / Teams), gated by level."""

from __future__ import annotations

import hashlib
import hmac
import json
import smtplib
import urllib.request
from dataclasses import dataclass
from email.mime.text import MIMEText
from typing import TYPE_CHECKING

from logging_setup import logger

if TYPE_CHECKING:
    from config import Settings


@dataclass
class Alert:
    snapshot_id: str
    status: str  # success | warning | error
    message: str
    instance_name: str = ""
    archive_size: int = 0
    duration_seconds: float = 0.0
    errors: list[str] | None = None


class AlertManager:
    def __init__(self, settings: "Settings"):
        self.s = settings
        self.channels = settings.get_alert_channels()

    def _should_send(self, status: str) -> bool:
        if not self.s.alert_enabled:
            return False
        if self.s.alert_level == "all":
            return True
        if self.s.alert_level == "warnings":
            return status in ("warning", "error")
        return status == "error"

    def send(self, alert: Alert) -> None:
        if not self._should_send(alert.status):
            return
        for ch in self.channels:
            try:
                getattr(self, f"_send_{ch}")(alert)
                logger.info("alert sent: %s", ch)
            except Exception as exc:  # noqa: BLE001
                logger.error("alert via %s failed: %s", ch, exc)

    def _body(self, alert: Alert) -> str:
        lines = [
            f"Instance:  {alert.instance_name}",
            f"Snapshot:  {alert.snapshot_id}",
            f"Status:    {alert.status.upper()}",
            f"Message:   {alert.message}",
        ]
        if alert.errors:
            lines.append("Errors:")
            lines += [f"  - {e}" for e in alert.errors]
        return "\n".join(lines)

    def _send_email(self, alert: Alert) -> None:
        if not (self.s.smtp_host and self.s.smtp_from and self.s.get_smtp_recipients()):
            raise RuntimeError("smtp not fully configured")
        msg = MIMEText(self._body(alert))
        msg["Subject"] = f"[{alert.instance_name}] backup {alert.status}: {alert.snapshot_id}"
        msg["From"] = self.s.smtp_from
        msg["To"] = ", ".join(self.s.get_smtp_recipients())
        with smtplib.SMTP(self.s.smtp_host, self.s.smtp_port, timeout=30) as smtp:
            if self.s.smtp_tls:
                smtp.starttls()
            if self.s.smtp_user and self.s.smtp_password_str():
                smtp.login(self.s.smtp_user, self.s.smtp_password_str())
            smtp.send_message(msg)

    def _send_webhook(self, alert: Alert) -> None:
        if not self.s.webhook_url:
            raise RuntimeError("webhook_url not set")
        payload = json.dumps(
            {
                "instance": alert.instance_name,
                "snapshot_id": alert.snapshot_id,
                "status": alert.status,
                "message": alert.message,
                "errors": alert.errors or [],
            }
        ).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        secret = getattr(self.s, "webhook_secret", None)
        if secret:
            sig = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
            headers["X-Signature-256"] = f"sha256={sig}"
        req = urllib.request.Request(self.s.webhook_url, data=payload, headers=headers)
        urllib.request.urlopen(req, timeout=30).close()  # noqa: S310

    def _send_teams(self, alert: Alert) -> None:
        if not self.s.teams_webhook_url:
            raise RuntimeError("teams_webhook_url not set")
        colour = {"success": "2DC72D", "warning": "E8A317", "error": "CD3D27"}.get(alert.status, "808080")
        card = {
            "@type": "MessageCard",
            "@context": "http://schema.org/extensions",
            "themeColor": colour,
            "summary": f"Backup {alert.status}",
            "title": f"IAM backup {alert.status}: {alert.snapshot_id}",
            "text": self._body(alert).replace("\n", "  \n"),
        }
        req = urllib.request.Request(
            self.s.teams_webhook_url,
            data=json.dumps(card).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(req, timeout=30).close()  # noqa: S310
