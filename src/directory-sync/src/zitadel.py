"""
directory-sync — Zitadel API client.

Authenticates as the FirstInstance machine service account (JWT profile) and
wraps the handful of endpoints the sync needs: user lookup/create (with a
caller-supplied userId for subject-preservation), bulk metadata, avatar upload
(Assets API), project/role lookup and user grants.

NOTE ON API PATHS: these target the Zitadel v2 (users) and v1 management
(metadata/projects/roles/grants) APIs. They are validated end-to-end in the
integration smoke test against the deployed Zitadel version (see
docs/directory-sync.md). The unit tests mock the HTTP layer.
"""

from __future__ import annotations

import base64
import json
import time
from pathlib import Path
from typing import Any, Optional

import httpx
import jwt

from logging_setup import logger


class ZitadelError(RuntimeError):
    pass


class ZitadelClient:
    def __init__(self, issuer: str, key_file: str, verify_tls: bool = True, timeout: float = 30.0):
        self.base = issuer.rstrip("/")
        self._key = self._load_key(key_file)
        self._client = httpx.Client(base_url=self.base, verify=verify_tls, timeout=timeout)
        self._token: Optional[str] = None
        self._token_exp: float = 0.0

    # ── auth ──────────────────────────────────────────────────────────────
    @staticmethod
    def _load_key(key_file: str) -> dict[str, Any]:
        data = json.loads(Path(key_file).read_text(encoding="utf-8"))
        for required in ("keyId", "key", "userId"):
            if required not in data:
                raise ZitadelError(f"machine key missing '{required}' field")
        return data

    def _assertion(self) -> str:
        now = int(time.time())
        payload = {
            "iss": self._key["userId"],
            "sub": self._key["userId"],
            "aud": self.base,  # JWT audience == issuer
            "iat": now,
            "exp": now + 3600,
        }
        return jwt.encode(
            payload, self._key["key"], algorithm="RS256", headers={"kid": self._key["keyId"]}
        )

    def token(self) -> str:
        if self._token and self._token_exp > time.time() + 60:
            return self._token
        resp = self._client.post(
            "/oauth/v2/token",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                "scope": "openid urn:zitadel:iam:org:project:id:zitadel:aud",
                "assertion": self._assertion(),
            },
        )
        if resp.status_code != 200:
            raise ZitadelError(f"token request failed ({resp.status_code}): {resp.text[:300]}")
        body = resp.json()
        self._token = body["access_token"]
        self._token_exp = time.time() + int(body.get("expires_in", 3600))
        return self._token

    def _headers(self, extra: Optional[dict[str, str]] = None) -> dict[str, str]:
        h = {"Authorization": f"Bearer {self.token()}", "Content-Type": "application/json"}
        if extra:
            h.update(extra)
        return h

    # ── branding (Login v2 LabelPolicy assets) ─────────────────────────────
    def upload_label_asset(self, path: str, filename: str, content: bytes, content_type: str) -> None:
        """Upload a binary asset to the instance LabelPolicy preview.

        `path` is the asset suffix: "logo", "logo/dark", "icon", "icon/dark",
        "font" (verified against the fork's asset.yaml; perm iam.policy.write).
        Multipart, like the user-avatar upload.
        """
        resp = self._client.post(
            f"/assets/v1/instance/policy/label/{path}",
            headers={"Authorization": f"Bearer {self.token()}"},
            files={"file": (filename, content, content_type)},
        )
        if resp.status_code not in (200, 201):
            raise ZitadelError(
                f"label asset upload '{path}' failed ({resp.status_code}): {resp.text[:200]}"
            )

    def activate_label_policy(self) -> None:
        """Promote the instance LabelPolicy preview (the uploaded assets) to active."""
        resp = self._client.post(
            "/admin/v1/policies/label/_activate", headers=self._headers(), json={}
        )
        if resp.status_code not in (200, 201):
            raise ZitadelError(
                f"label policy activate failed ({resp.status_code}): {resp.text[:200]}"
            )

    # ── users ─────────────────────────────────────────────────────────────
    def find_user_id_by_email(self, email: str) -> Optional[str]:
        resp = self._client.post(
            "/v2/users",
            headers=self._headers(),
            json={
                "queries": [
                    {"emailQuery": {"emailAddress": email, "method": "TEXT_QUERY_METHOD_EQUALS"}}
                ]
            },
        )
        if resp.status_code != 200:
            logger.warning("user search failed for %s (%s)", email, resp.status_code)
            return None
        result = resp.json().get("result") or []
        return result[0].get("userId") if result else None

    def get_user(self, user_id: str) -> Optional[dict[str, Any]]:
        resp = self._client.get(f"/v2/users/{user_id}", headers=self._headers())
        if resp.status_code != 200:
            return None
        return resp.json().get("user")

    def create_human_user(
        self,
        user_id: str,
        email: str,
        given_name: str,
        family_name: str,
        username: Optional[str] = None,
        display_name: Optional[str] = None,
    ) -> Optional[str]:
        """Create a human user with a caller-supplied userId (subject-preservation).

        No password is set → the user can only authenticate via the IdP.
        Returns the userId on success (or if it already exists), else None.
        """
        body = {
            "userId": user_id,
            "username": username or email,
            "profile": {
                "givenName": given_name or email,
                "familyName": family_name or "-",
                "displayName": display_name or f"{given_name} {family_name}".strip(),
            },
            "email": {"email": email, "isVerified": True},
        }
        resp = self._client.post("/v2/users/human", headers=self._headers(), json=body)
        if resp.status_code in (200, 201):
            return resp.json().get("userId", user_id)
        if resp.status_code == 409:  # already exists — idempotent
            return user_id
        logger.error("create user failed for %s (%s): %s", email, resp.status_code, resp.text[:300])
        return None

    # ── metadata (bulk) ───────────────────────────────────────────────────
    def set_metadata_bulk(self, user_id: str, metadata: dict[str, str]) -> bool:
        entries = [
            {"key": k, "value": base64.b64encode(v.encode("utf-8")).decode("ascii")}
            for k, v in metadata.items()
            if v
        ]
        if not entries:
            return True
        resp = self._client.post(
            f"/management/v1/users/{user_id}/metadata/_bulk",
            headers=self._headers(),
            json={"metadata": entries},
        )
        if resp.status_code not in (200, 201):
            logger.warning("metadata bulk-set failed for %s (%s)", user_id, resp.status_code)
            return False
        return True

    # ── avatar (Assets API, multipart) ────────────────────────────────────
    def upload_avatar(self, user_id: str, photo: bytes, content_type: str = "image/jpeg") -> bool:
        try:
            resp = self._client.post(
                f"/assets/v1/users/{user_id}/avatar",
                headers={"Authorization": f"Bearer {self.token()}"},
                files={"file": ("avatar.jpg", photo, content_type)},
            )
        except httpx.HTTPError as exc:  # best-effort
            logger.warning("avatar upload error for %s: %s", user_id, exc)
            return False
        if resp.status_code not in (200, 201):
            logger.warning("avatar upload failed for %s (%s)", user_id, resp.status_code)
            return False
        return True

    # ── projects / roles / grants ─────────────────────────────────────────
    def find_project_id(self, name: str) -> Optional[str]:
        resp = self._client.post(
            "/management/v1/projects/_search",
            headers=self._headers(),
            json={"queries": [{"nameQuery": {"name": name, "method": "TEXT_QUERY_METHOD_EQUALS"}}]},
        )
        if resp.status_code != 200:
            return None
        result = resp.json().get("result") or []
        return result[0].get("id") if result else None

    def ensure_role(self, project_id: str, role_key: str, display_name: str, group: str = "entra") -> bool:
        resp = self._client.post(
            f"/management/v1/projects/{project_id}/roles",
            headers=self._headers(),
            json={"roleKey": role_key, "displayName": display_name, "group": group},
        )
        if resp.status_code in (200, 201):
            return True
        if resp.status_code == 409:  # exists
            return True
        logger.warning("ensure_role failed for %s (%s)", role_key, resp.status_code)
        return False

    def find_user_grant(self, user_id: str, project_id: str) -> Optional[dict[str, Any]]:
        resp = self._client.post(
            "/management/v1/users/grants/_search",
            headers=self._headers(),
            json={
                "queries": [
                    {"userIdQuery": {"userId": user_id}},
                    {"projectIdQuery": {"projectId": project_id}},
                ]
            },
        )
        if resp.status_code != 200:
            return None
        result = resp.json().get("result") or []
        return result[0] if result else None

    def set_user_grant(self, user_id: str, project_id: str, role_keys: list[str]) -> bool:
        """Create or update the user's grant for the project to exactly role_keys."""
        existing = self.find_user_grant(user_id, project_id)
        if existing is None:
            resp = self._client.post(
                f"/management/v1/users/{user_id}/grants",
                headers=self._headers(),
                json={"projectId": project_id, "roleKeys": role_keys},
            )
        else:
            grant_id = existing.get("id") or existing.get("grantId")
            resp = self._client.put(
                f"/management/v1/users/{user_id}/grants/{grant_id}",
                headers=self._headers(),
                json={"roleKeys": role_keys},
            )
        if resp.status_code not in (200, 201):
            logger.warning("set_user_grant failed for %s (%s)", user_id, resp.status_code)
            return False
        return True

    def close(self) -> None:
        self._client.close()
