"""
CS-IAM backup round trip - a Zitadel user, written and read through the API.

Runs inside the directory-sync container (fed on stdin by common.sh), which has
the FirstInstance machine key and the Zitadel client the stack itself uses:

  create   create a human user whose id and username are the run's marker
  delete   delete that user through the API, the way an admin removes it
  present  wait until Zitadel returns the user with the seeded email
  absent   wait until Zitadel answers that the user does not exist

The two checks poll until the state is reached or DEADLINE_SECONDS pass:
Zitadel's read side (projections) follows its event store asynchronously, and
after the restore the core may still be starting. An error never counts as
"absent" - only Zitadel's own NOT_FOUND answer does. A 404 from the proxy (no
route while the core is down) is plain text, not Zitadel's JSON error, and
keeps the check waiting.
"""

from __future__ import annotations

import os
import sys
import time

import httpx

from config import Settings
from zitadel import ZitadelClient, ZitadelError

DEADLINE_SECONDS = 180
POLL_SECONDS = 3

MARKER = os.environ["ROUNDTRIP_MARKER"]
EMAIL = f"{MARKER}@roundtrip.example.test"
USER_PATH = f"/v2/users/{MARKER}"

SETTINGS = Settings()
VERIFY_TLS = not SETTINGS.zitadel_insecure


def api(zit: ZitadelClient, method: str, path: str, **kwargs) -> httpx.Response:
    headers = {"Authorization": f"Bearer {zit.token()}"}
    with httpx.Client(base_url=zit.base, verify=VERIFY_TLS, timeout=30.0) as client:
        return client.request(method, path, headers=headers, **kwargs)


def is_zitadel_not_found(resp: httpx.Response) -> bool:
    """Zitadel's NOT_FOUND: HTTP 404 with a JSON body carrying gRPC code 5
    (grpc-gateway) or "not_found" (Connect)."""
    if resp.status_code != 404:
        return False
    try:
        code = resp.json().get("code")
    except ValueError:
        return False
    return code in (5, "not_found")


def observe(zit: ZitadelClient) -> str:
    """'present', 'absent', or a description of anything else."""
    resp = api(zit, "GET", USER_PATH)
    if resp.status_code == 200:
        user = resp.json().get("user") or {}
        email = ((user.get("human") or {}).get("email") or {}).get("email")
        if user.get("userId") == MARKER and user.get("username") == MARKER and email == EMAIL:
            return "present"
        return f"user with unexpected content: id={user.get('userId')!r} email={email!r}"
    if is_zitadel_not_found(resp):
        return "absent"
    return f"HTTP {resp.status_code}: {resp.text[:200]}"


def wait_for(zit: ZitadelClient, want: str) -> int:
    deadline = time.monotonic() + DEADLINE_SECONDS
    while True:
        try:
            seen = observe(zit)
        except (httpx.HTTPError, ZitadelError, ValueError, AttributeError) as exc:
            # Reported and retried - never read as "absent".
            seen = f"{type(exc).__name__}: {exc}"
        if seen == want:
            print(f"ok   Zitadel user {MARKER}: {want}")
            return 0
        if seen.startswith("user with unexpected content"):
            print(f"FAIL Zitadel user {MARKER}: {seen}")
            return 1
        if time.monotonic() >= deadline:
            print(f"FAIL Zitadel user {MARKER}: not {want} after {DEADLINE_SECONDS}s, last answer: {seen}")
            return 1
        time.sleep(POLL_SECONDS)


def create(zit: ZitadelClient) -> int:
    body = {
        "userId": MARKER,
        "username": MARKER,
        "profile": {
            "givenName": "Backup",
            "familyName": "Round Trip",
            "displayName": f"Backup round trip {MARKER}",
        },
        "email": {"email": EMAIL, "isVerified": True},
    }
    resp = api(zit, "POST", "/v2/users/human", json=body)
    if resp.status_code not in (200, 201):
        print(f"FAIL create Zitadel user {MARKER}: HTTP {resp.status_code}: {resp.text[:300]}")
        return 1
    print(f"created Zitadel user {MARKER}")
    return 0


def delete(zit: ZitadelClient) -> int:
    resp = api(zit, "DELETE", USER_PATH)
    if resp.status_code != 200:
        print(f"FAIL delete Zitadel user {MARKER}: HTTP {resp.status_code}: {resp.text[:300]}")
        return 1
    print(f"deleted Zitadel user {MARKER}")
    return 0


def main(action: str) -> int:
    zit = ZitadelClient(
        issuer=SETTINGS.issuer(),
        key_file=SETTINGS.zitadel_jwt_profile_file,
        verify_tls=VERIFY_TLS,
    )
    try:
        if action == "create":
            return create(zit)
        if action == "delete":
            return delete(zit)
        if action in ("present", "absent"):
            return wait_for(zit, action)
        print(f"unknown action {action!r}", file=sys.stderr)
        return 2
    finally:
        zit.close()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else ""))
