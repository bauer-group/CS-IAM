import hashlib
import hmac

from alerting import Alert, AlertManager
from config import Settings


def _capture_webhook(monkeypatch) -> dict:
    """Patch urllib so _send_webhook records the outgoing request instead of sending."""
    captured: dict = {}

    def fake_urlopen(req, timeout=0):  # noqa: ANN001
        captured["url"] = req.full_url
        captured["data"] = req.data
        captured["headers"] = {k.lower(): v for k, v in req.headers.items()}

        class _R:
            def close(self):
                pass

        return _R()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    return captured


def _alert() -> Alert:
    return Alert(snapshot_id="2026-01-01_00-00-00", status="success",
                 message="ok", instance_name="iam")


def test_webhook_hmac_signature_when_secret_set(monkeypatch):
    captured = _capture_webhook(monkeypatch)
    s = Settings(db_password="x", alert_enabled=True, alert_level="all",
                 alert_channels="webhook", webhook_url="http://example.test/hook",
                 webhook_secret="topsecret")
    AlertManager(s).send(_alert())

    assert captured["url"] == "http://example.test/hook"
    expected = "sha256=" + hmac.new(b"topsecret", captured["data"], hashlib.sha256).hexdigest()
    assert captured["headers"]["x-signature-256"] == expected


def test_webhook_unsigned_when_no_secret(monkeypatch):
    captured = _capture_webhook(monkeypatch)
    s = Settings(db_password="x", alert_enabled=True, alert_level="all",
                 alert_channels="webhook", webhook_url="http://example.test/hook")
    AlertManager(s).send(_alert())

    assert "x-signature-256" not in captured["headers"]
