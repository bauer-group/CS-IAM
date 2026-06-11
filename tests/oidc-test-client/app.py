"""
OIDC test client — exercises and validates the IAM login end-to-end.

A tiny confidential OIDC client (dev/test only) that runs the real
authorization-code + PKCE flow against the IAM, then validates the issued ID
token: signature, issuer, audience, nonce, subject, email and — the point — the
project roles. Built to test the shipped demo user (demo@bauer-group.com) against
its expected roles in pDemo (rUser + rManager, NOT rAdministrator).

Two surfaces:
  GET /            landing page (config + "Login & validate" button)
  GET /login       start the auth-code+PKCE flow
  GET /callback    finish it, validate, render a pass/fail report (+ store it)
  GET /validate    the last validation result as JSON  → automation hook
  GET /logout      RP-initiated logout

Dev networking: the browser reaches the core at OIDC_ISSUER while the backend
reaches it at OIDC_BACKEND_URL with a Host: OIDC_BACKEND_HOST override (same
pattern as the login service), so the issuer stays consistent in both directions.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
from urllib.parse import urlencode

import jwt
import requests
from flask import Flask, redirect, request, session, url_for

# ── Config (env) ──────────────────────────────────────────────────────────────
ISSUER = os.environ.get("OIDC_ISSUER", "http://localhost:8080").rstrip("/")
BACKEND_URL = os.environ.get("OIDC_BACKEND_URL", ISSUER).rstrip("/")
BACKEND_HOST = os.environ.get("OIDC_BACKEND_HOST", "")  # Host header for backend calls
CLIENT_ID = os.environ.get("OIDC_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("OIDC_CLIENT_SECRET", "")
REDIRECT_URI = os.environ.get("OIDC_REDIRECT_URI", "http://localhost:8888/callback")
SCOPES = os.environ.get("OIDC_SCOPES", "openid profile email offline_access urn:zitadel:iam:user:metadata")
EXPECTED_ROLES = [r for r in os.environ.get("OIDC_EXPECTED_ROLES", "rUser,rManager").split(",") if r]
FORBIDDEN_ROLES = [r for r in os.environ.get("OIDC_FORBIDDEN_ROLES", "rAdministrator").split(",") if r]
ROLES_CLAIM = "urn:zitadel:iam:org:project:roles"
VERIFY_TLS = os.environ.get("OIDC_VERIFY_TLS", "true").lower() != "false"
PORT = int(os.environ.get("PORT", "8888"))

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET", secrets.token_hex(16))


def _backend_headers() -> dict[str, str]:
    return {"Host": BACKEND_HOST} if BACKEND_HOST else {}


def _to_backend(url: str) -> str:
    """Rewrite a public (issuer-based) endpoint URL to the backend base."""
    if url.startswith(ISSUER):
        return BACKEND_URL + url[len(ISSUER):]
    return url


def discovery() -> dict:
    r = requests.get(
        f"{BACKEND_URL}/.well-known/openid-configuration",
        headers=_backend_headers(), verify=VERIFY_TLS, timeout=10,
    )
    r.raise_for_status()
    return r.json()


def signing_key(id_token: str, jwks_uri: str):
    """Fetch JWKS (backend) and return the key matching the token's kid."""
    kid = jwt.get_unverified_header(id_token).get("kid")
    jwks = requests.get(_to_backend(jwks_uri), headers=_backend_headers(), verify=VERIFY_TLS, timeout=10).json()
    for k in jwks.get("keys", []):
        if k.get("kid") == kid:
            return jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(k))
    raise ValueError(f"no JWKS key for kid {kid}")


def validate(id_claims: dict, userinfo: dict, nonce: str) -> dict:
    """Build the pass/fail check list for the logged-in user. Reusable for tests."""
    roles = id_claims.get(ROLES_CLAIM) or userinfo.get(ROLES_CLAIM) or {}
    role_keys = sorted(roles.keys()) if isinstance(roles, dict) else []
    checks = [
        ("issuer matches", id_claims.get("iss") == ISSUER, id_claims.get("iss")),
        ("audience contains client", CLIENT_ID in _aslist(id_claims.get("aud")), id_claims.get("aud")),
        ("nonce matches", id_claims.get("nonce") == nonce, "ok" if id_claims.get("nonce") == nonce else "mismatch"),
        ("subject present", bool(id_claims.get("sub")), id_claims.get("sub")),
        ("email present", bool(id_claims.get("email")), id_claims.get("email")),
        ("roles claim present", bool(role_keys), role_keys),
    ]
    for r in EXPECTED_ROLES:
        checks.append((f"has role {r}", r in role_keys, "present" if r in role_keys else "MISSING"))
    for r in FORBIDDEN_ROLES:
        checks.append((f"lacks role {r}", r not in role_keys, "absent" if r not in role_keys else "PRESENT"))
    ok = all(c[1] for c in checks)
    return {
        "ok": ok,
        "checks": [{"name": n, "ok": bool(p), "detail": d} for n, p, d in checks],
        "roles": role_keys,
        "id_claims": id_claims,
        "userinfo": userinfo,
    }


def _aslist(v):
    return v if isinstance(v, list) else [v] if v else []


# ── Routes ────────────────────────────────────────────────────────────────────
@app.get("/")
def index():
    cfg = {
        "issuer": ISSUER, "client_id": CLIENT_ID or "(unset)",
        "scopes": SCOPES, "redirect_uri": REDIRECT_URI,
        "expected_roles": EXPECTED_ROLES, "forbidden_roles": FORBIDDEN_ROLES,
    }
    rows = "".join(f"<tr><td><b>{k}</b></td><td><code>{v}</code></td></tr>" for k, v in cfg.items())
    warn = "" if CLIENT_ID else "<p style='color:#b00'>⚠ OIDC_CLIENT_ID/SECRET not set — set the Demo app creds (tofu output demo_app_client_id / -raw demo_app_client_secret).</p>"
    return _page("IAM OIDC test client", f"""
      <p>Runs the authorization-code + PKCE flow against the IAM and validates the
      ID token (roles for the demo user).</p>{warn}
      <table>{rows}</table>
      <p><a class="btn" href="/login">▶ Login &amp; validate</a></p>
      <p>Automation hook: <code>GET /validate</code> returns the last result as JSON.</p>
    """)


@app.get("/login")
def login():
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    session["pkce_verifier"] = verifier
    session["state"] = secrets.token_urlsafe(16)
    session["nonce"] = secrets.token_urlsafe(16)
    params = {
        "client_id": CLIENT_ID, "response_type": "code", "scope": SCOPES,
        "redirect_uri": REDIRECT_URI, "state": session["state"], "nonce": session["nonce"],
        "code_challenge": challenge, "code_challenge_method": "S256",
    }
    return redirect(f"{ISSUER}/oauth/v2/authorize?{urlencode(params)}")


@app.get("/callback")
def callback():
    if not request.args.get("code") and not request.args.get("error"):
        return redirect("/")  # e.g. landing here after logout
    if request.args.get("error"):
        return _page("Login error", f"<pre>{request.args.get('error')}: {request.args.get('error_description','')}</pre>"), 400
    if request.args.get("state") != session.get("state"):
        return _page("Login error", "<pre>state mismatch (CSRF)</pre>"), 400

    disco = discovery()
    token_res = requests.post(
        _to_backend(disco["token_endpoint"]),
        headers=_backend_headers(),
        auth=(CLIENT_ID, CLIENT_SECRET),
        data={
            "grant_type": "authorization_code", "code": request.args["code"],
            "redirect_uri": REDIRECT_URI, "code_verifier": session.get("pkce_verifier", ""),
        },
        verify=VERIFY_TLS, timeout=15,
    )
    if token_res.status_code != 200:
        return _page("Token error", f"<pre>{token_res.status_code}\n{token_res.text}</pre>"), 400
    tokens = token_res.json()

    id_token = tokens["id_token"]
    key = signing_key(id_token, disco["jwks_uri"])
    id_claims = jwt.decode(id_token, key, algorithms=["RS256"], audience=CLIENT_ID, issuer=ISSUER)

    userinfo = {}
    try:
        ui = requests.get(
            _to_backend(disco["userinfo_endpoint"]),
            headers={**_backend_headers(), "Authorization": f"Bearer {tokens['access_token']}"},
            verify=VERIFY_TLS, timeout=10,
        )
        if ui.status_code == 200:
            userinfo = ui.json()
    except requests.RequestException:
        pass

    result = validate(id_claims, userinfo, session.get("nonce", ""))
    result["access_token"] = tokens.get("access_token", "")[:24] + "… (opaque bearer)"
    session["last_result"] = result

    rows = "".join(
        f"<tr><td>{'✅' if c['ok'] else '❌'}</td><td>{c['name']}</td><td><code>{c['detail']}</code></td></tr>"
        for c in result["checks"]
    )
    banner = ("<div class='ok'>PASS — the demo user has exactly the expected roles.</div>"
              if result["ok"] else "<div class='fail'>FAIL — see the red checks below.</div>")
    return _page("Validation result", f"""
      {banner}
      <table><tr><th></th><th>check</th><th>detail</th></tr>{rows}</table>
      <h3>ID token claims</h3><pre>{json.dumps(result['id_claims'], indent=2, ensure_ascii=False)}</pre>
      <h3>UserInfo</h3><pre>{json.dumps(result['userinfo'], indent=2, ensure_ascii=False)}</pre>
      <p><a class="btn" href="/validate">JSON result</a> · <a href="/logout">logout</a> · <a href="/">home</a></p>
    """)


@app.get("/validate")
def validate_json():
    result = session.get("last_result")
    if not result:
        return {"ok": False, "error": "no result yet — run /login first"}, 409
    return result, (200 if result["ok"] else 422)


@app.get("/logout")
def logout():
    session.clear()
    home = REDIRECT_URI.rsplit("/", 1)[0] + "/"
    return redirect(f"{ISSUER}/oidc/v1/end_session?post_logout_redirect_uri={home}")


def _page(title: str, body: str) -> str:
    return f"""<!doctype html><meta charset="utf-8"><title>{title}</title>
<style>body{{font:15px system-ui;margin:2rem;max-width:54rem}}table{{border-collapse:collapse}}
td,th{{border:1px solid #ddd;padding:.3rem .6rem;text-align:left;vertical-align:top}}
code,pre{{background:#f6f6f6}}pre{{padding:.6rem;overflow:auto}}
.btn{{display:inline-block;background:#FF8500;color:#fff;padding:.5rem 1rem;border-radius:6px;text-decoration:none}}
.ok{{background:#e6ffed;border:1px solid #34a853;padding:.6rem;border-radius:6px;font-weight:600}}
.fail{{background:#ffe6e6;border:1px solid #d33;padding:.6rem;border-radius:6px;font-weight:600}}</style>
<h1>{title}</h1>{body}"""


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
