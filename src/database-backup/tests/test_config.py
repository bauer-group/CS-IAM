import pytest
from config import Settings
from pydantic import ValidationError


def _s(**over):
    base = dict(db_password="x")
    base.update(over)
    return Settings(**base)


def test_target_not_configured_by_default():
    assert _s().target_configured() is False


def test_target_configured_when_all_set():
    s = _s(backup_s3_bucket="b", backup_s3_access_key="k", backup_s3_secret_key="s")
    assert s.target_configured() is True


def test_cron_must_have_five_fields():
    with pytest.raises(ValidationError):
        _s(backup_schedule_cron="15 3 * *")


def test_alert_channels_validated():
    assert _s(alert_channels="email, teams").get_alert_channels() == ["email", "teams"]
    with pytest.raises(ValidationError):
        _s(alert_channels="pager")


def test_smtp_recipients_split():
    assert _s(smtp_to="a@x.com, b@y.com").get_smtp_recipients() == ["a@x.com", "b@y.com"]
