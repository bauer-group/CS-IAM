"""Unit tests for the role-validation logic — the automated-test basis."""

import app as appmod


def _claims(**over):
    base = {
        "iss": appmod.ISSUER,
        "aud": [appmod.CLIENT_ID],
        "nonce": "N",
        "sub": "user-1",
        "email": "demo@bauer-group.com",
        appmod.ROLES_CLAIM: {"rUser": {}, "rManager": {}},
    }
    base.update(over)
    return base


def _check(result, name):
    return next(c for c in result["checks"] if c["name"] == name)


def test_happy_path_passes():
    r = appmod.validate(_claims(), {}, "N")
    assert r["ok"] is True
    assert set(r["roles"]) == {"rUser", "rManager"}


def test_missing_expected_role_fails():
    r = appmod.validate(_claims(**{appmod.ROLES_CLAIM: {"rUser": {}}}), {}, "N")
    assert r["ok"] is False
    assert _check(r, "has role rManager")["ok"] is False


def test_forbidden_role_present_fails():
    roles = {"rUser": {}, "rManager": {}, "rAdministrator": {}}
    r = appmod.validate(_claims(**{appmod.ROLES_CLAIM: roles}), {}, "N")
    assert r["ok"] is False
    assert _check(r, "lacks role rAdministrator")["ok"] is False


def test_roles_from_userinfo_fallback():
    claims = _claims()
    del claims[appmod.ROLES_CLAIM]
    r = appmod.validate(claims, {appmod.ROLES_CLAIM: {"rUser": {}, "rManager": {}}}, "N")
    assert r["ok"] is True


def test_nonce_mismatch_fails():
    r = appmod.validate(_claims(nonce="X"), {}, "N")
    assert r["ok"] is False
    assert _check(r, "nonce matches")["ok"] is False


def test_missing_email_fails():
    claims = _claims()
    del claims["email"]
    r = appmod.validate(claims, {}, "N")
    assert r["ok"] is False
    assert _check(r, "email present")["ok"] is False
