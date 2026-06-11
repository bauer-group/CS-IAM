#!/usr/bin/env python3
"""
validate-stack.py — detailed post-deploy validation of the CS-IAM stack.

Authenticates with the FirstInstance machine key and asserts, via the Zitadel
Management/Admin/OIDC APIs, that everything the IaC provisions is actually in
place and correct: orgs, projects (+ authorization-on-auth flags), the role
catalogs, the demo app's OIDC config, the demo user + its grant/roles, the
branding LabelPolicy, the LoginPolicy and the OIDC discovery document.

Prints a PASS/FAIL matrix and exits non-zero if any check fails — so it doubles
as an automated full-stack smoke test.

  # inside the directory-sync container (has httpx + pyjwt + the machine key):
  python /tmp/validate-stack.py --issuer http://zitadel:8080 --insecure
"""

from __future__ import annotations

import argparse
import json
import sys
import time

import httpx
import jwt


def get_token(issuer: str, key_file: str, verify: bool) -> str:
    # JWT-profile: `aud` must equal the URL the core is actually reached at (it
    # validates against the request scheme/host, not the public issuer) — so in
    # dev, reach + audience the core directly over http at http://zitadel:8080.
    key = json.loads(open(key_file, encoding="utf-8").read())
    now = int(time.time())
    assertion = jwt.encode(
        {"iss": key["userId"], "sub": key["userId"], "aud": issuer, "iat": now, "exp": now + 3600},
        key["key"], algorithm="RS256", headers={"kid": key["keyId"]},
    )
    r = httpx.post(
        f"{issuer}/oauth/v2/token",
        data={
            "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
            "scope": "openid urn:zitadel:iam:org:project:id:zitadel:aud",
            "assertion": assertion,
        },
        verify=verify, timeout=20,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def main() -> int:
    ap = argparse.ArgumentParser()
    # The URL the core is reached at — also the JWT-profile audience. In dev the
    # containers reach the core directly over http (the public issuer is https
    # via the proxy, but the audience follows the reached scheme); in prod it is
    # the public https origin. See get_token().
    ap.add_argument("--issuer", default="http://zitadel:8080")
    ap.add_argument("--key-file", default="/data/machinekey/iam-admin.json")
    ap.add_argument("--insecure", action="store_true")
    args = ap.parse_args()
    verify = not args.insecure
    base = args.issuer.rstrip("/")

    token = get_token(base, args.key_file, verify)
    cli = httpx.Client(base_url=base, verify=verify, timeout=20,
                       headers={"Authorization": f"Bearer {token}"})

    checks: list[tuple[str, bool, str]] = []

    def check(name: str, ok: bool, detail="") -> None:
        checks.append((name, bool(ok), str(detail)))

    def post(path, body=None, org=None):
        h = {"x-zitadel-orgid": org} if org else {}
        return cli.post(path, json=body or {}, headers=h)

    def get(path, org=None):
        h = {"x-zitadel-orgid": org} if org else {}
        return cli.get(path, headers=h)

    # ── 1. OIDC discovery ─────────────────────────────────────────────────────
    d = httpx.get(f"{base}/.well-known/openid-configuration", verify=verify, timeout=15).json()
    for ep in ["authorization_endpoint", "token_endpoint", "userinfo_endpoint", "jwks_uri", "end_session_endpoint"]:
        check(f"discovery: {ep}", bool(d.get(ep)), d.get(ep))
    check("discovery: grant authorization_code", "authorization_code" in d.get("grant_types_supported", []))
    check("discovery: grant refresh_token", "refresh_token" in d.get("grant_types_supported", []))
    check("discovery: scope openid", "openid" in d.get("scopes_supported", []))

    # ── 2. Organisations ──────────────────────────────────────────────────────
    r = post("/admin/v1/orgs/_search")
    orgs = {o["name"]: o["id"] for o in r.json().get("result", [])} if r.status_code == 200 else {}
    check("org: BAUER GROUP", "BAUER GROUP" in orgs, list(orgs))
    check("org: External Users", "External Users" in orgs, list(orgs))

    # ── 3. Projects (internal org context) ────────────────────────────────────
    r = post("/management/v1/projects/_search")
    projs = {p["name"]: p["id"] for p in r.json().get("result", [])} if r.status_code == 200 else {}
    for pn in ["BAUER GROUP", "External Apps", "pDemo"]:
        check(f"project: {pn}", pn in projs, list(projs))

    # ── 4. Role catalogs ──────────────────────────────────────────────────────
    def roles_of(pid):
        rr = post(f"/management/v1/projects/{pid}/roles/_search")
        return {x["key"] for x in rr.json().get("result", [])} if rr.status_code == 200 else set()

    if "BAUER GROUP" in projs:
        check("roles[BAUER GROUP] = user,admin", {"user", "admin"} <= roles_of(projs["BAUER GROUP"]))
    if "pDemo" in projs:
        rk = roles_of(projs["pDemo"])
        check("roles[pDemo] = rUser,rManager,rAdministrator", {"rUser", "rManager", "rAdministrator"} <= rk, sorted(rk))

    # ── 5. pDemo project settings + the Demo app ──────────────────────────────
    if "pDemo" in projs:
        pj = get(f"/management/v1/projects/{projs['pDemo']}").json().get("project", {})
        check("pDemo: hasProjectCheck", pj.get("hasProjectCheck"), pj.get("hasProjectCheck"))
        check("pDemo: projectRoleCheck", pj.get("projectRoleCheck"))
        check("pDemo: projectRoleAssertion", pj.get("projectRoleAssertion"))
        apps = post(f"/management/v1/projects/{projs['pDemo']}/apps/_search").json().get("result", [])
        demo = next((a for a in apps if a.get("name") == "Demo"), None)
        check("pDemo: app 'Demo' exists", demo is not None, [a.get("name") for a in apps])
        if demo:
            oc = demo.get("oidcConfig", {})
            check("Demo: response type CODE", "OIDC_RESPONSE_TYPE_CODE" in oc.get("responseTypes", []), oc.get("responseTypes"))
            check("Demo: access+id role assertion", bool(oc.get("accessTokenRoleAssertion")) and bool(oc.get("idTokenRoleAssertion")))
            check("Demo: redirect localhost:8888", any("localhost:8888" in u for u in oc.get("redirectUris", [])), oc.get("redirectUris"))

    # ── 6. Demo user + grant + roles (the heart of it) ────────────────────────
    ur = post("/v2/users", {"queries": [{"emailQuery": {"emailAddress": "demo@bauer-group.com", "method": "TEXT_QUERY_METHOD_EQUALS"}}]})
    result = ur.json().get("result") or []
    uid = result[0].get("userId") if result else None
    check("demo user exists", bool(uid), uid)
    if uid:
        gr = post("/management/v1/users/grants/_search", {"queries": [{"userIdQuery": {"userId": uid}}]}).json().get("result", [])
        pdemo = [g for g in gr if g.get("projectName") == "pDemo"]
        other = [g for g in gr if g.get("projectName") != "pDemo"]
        roles = set()
        for g in pdemo:
            roles |= set(g.get("roleKeys", []))
        check("demo: grant in pDemo", bool(pdemo))
        check("demo: roles == {rUser, rManager}", roles == {"rUser", "rManager"}, sorted(roles))
        check("demo: NOT rAdministrator", "rAdministrator" not in roles)
        check("demo: isolated (no other project grants)", not other, [g.get("projectName") for g in other])

    # ── 7. Branding (active LabelPolicy) ──────────────────────────────────────
    lp = get("/management/v1/policies/label").json().get("policy", {})
    check("brand: primaryColor #FF8500", (lp.get("primaryColor") or "").upper() == "#FF8500", lp.get("primaryColor"))
    check("brand: backgroundColorDark #231F1C", (lp.get("backgroundColorDark") or "").upper() == "#231F1C", lp.get("backgroundColorDark"))
    check("brand: logo uploaded", bool(lp.get("logoUrl")), lp.get("logoUrl"))
    check("brand: icon uploaded", bool(lp.get("iconUrl")), lp.get("iconUrl"))

    # ── 8. LoginPolicy ────────────────────────────────────────────────────────
    lo = get("/management/v1/policies/login").json().get("policy", {})
    check("login: allowUsernamePassword", lo.get("allowUsernamePassword"))
    check("login: allowExternalIdp", lo.get("allowExternalIdp"))
    check("login: forceMfaLocalOnly", lo.get("forceMfaLocalOnly"))

    # ── Report ────────────────────────────────────────────────────────────────
    passed = sum(1 for _, ok, _ in checks if ok)
    failed = len(checks) - passed
    print("\n=== CS-IAM full-stack validation ===")
    for name, ok, detail in checks:
        line = f"  {'✅ PASS' if ok else '❌ FAIL'}  {name}"
        if detail and not ok:
            line += f"   → {detail}"
        print(line)
    print(f"\n{passed}/{len(checks)} checks passed" + (f", {failed} FAILED" if failed else " — all green"))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
