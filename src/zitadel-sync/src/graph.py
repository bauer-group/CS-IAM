"""
zitadel-sync — Microsoft Graph client.

App-only auth (ClientSecretCredential). Provides:
  - users_delta()  → changed users since the stored delta token (profiles)
  - list_users()   → full enumeration (group recompute, few users)
  - user_groups()  → a user's transitive group memberships
  - user_photo()   → profile photo bytes (None if absent)

Requires Application permissions (admin-consented):
  User.Read.All, GroupMember.Read.All, ProfilePhoto.Read.All
"""

from __future__ import annotations

import time
from typing import Any, Optional

import httpx

from logging_setup import logger

GRAPH = "https://graph.microsoft.com/v1.0"
SCOPE = "https://graph.microsoft.com/.default"

USER_SELECT = (
    "id,displayName,givenName,surname,mail,userPrincipalName,accountEnabled,"
    "jobTitle,department,companyName,mobilePhone,businessPhones,faxNumber,officeLocation"
)


class GraphClient:
    def __init__(self, tenant_id: str, client_id: str, client_secret: str, timeout: float = 30.0):
        # Lazy import so the pure helpers (primary_email, extended_metadata) and
        # the module are usable without azure-identity installed.
        from azure.identity import ClientSecretCredential

        self._cred = ClientSecretCredential(tenant_id, client_id, client_secret)
        self._client = httpx.Client(timeout=timeout)
        self._token: Optional[str] = None
        self._token_exp: float = 0.0

    def _bearer(self) -> str:
        if self._token and self._token_exp > time.time() + 60:
            return self._token
        tok = self._cred.get_token(SCOPE)
        self._token = tok.token
        self._token_exp = float(tok.expires_on)
        return self._token

    def _get(self, url: str) -> httpx.Response:
        if url.startswith("/"):
            url = GRAPH + url
        return self._client.get(url, headers={"Authorization": f"Bearer {self._bearer()}"})

    # ── users delta (profiles) ────────────────────────────────────────────
    def users_delta(self, delta_link: Optional[str]) -> tuple[list[dict[str, Any]], Optional[str]]:
        """Return (changed_users, next_delta_link).

        Pass the previously stored delta_link to fetch only changes; pass None
        for the initial full sync.
        """
        url = delta_link or f"/users/delta?$select={USER_SELECT}"
        changes: list[dict[str, Any]] = []
        new_delta: Optional[str] = None
        while url:
            resp = self._get(url)
            if resp.status_code != 200:
                logger.error("users delta failed (%s): %s", resp.status_code, resp.text[:300])
                break
            body = resp.json()
            changes.extend(body.get("value", []))
            if "@odata.nextLink" in body:
                url = body["@odata.nextLink"]
            else:
                new_delta = body.get("@odata.deltaLink")
                url = ""
        return changes, new_delta

    # ── full user list (group recompute) ──────────────────────────────────
    def list_users(self) -> list[dict[str, Any]]:
        users: list[dict[str, Any]] = []
        url = f"/users?$select=id,mail,userPrincipalName,accountEnabled&$top=999"
        while url:
            resp = self._get(url)
            if resp.status_code != 200:
                logger.error("list users failed (%s): %s", resp.status_code, resp.text[:300])
                break
            body = resp.json()
            users.extend(body.get("value", []))
            url = body.get("@odata.nextLink", "")
        return users

    # ── a user's transitive group memberships ─────────────────────────────
    def user_groups(self, user_id: str) -> list[dict[str, Any]]:
        groups: list[dict[str, Any]] = []
        url = (
            f"/users/{user_id}/transitiveMemberOf/microsoft.graph.group"
            f"?$select=id,displayName&$top=999"
        )
        while url:
            resp = self._get(url)
            if resp.status_code != 200:
                logger.warning("user_groups failed for %s (%s)", user_id, resp.status_code)
                break
            body = resp.json()
            groups.extend(body.get("value", []))
            url = body.get("@odata.nextLink", "")
        return groups

    # ── profile photo ─────────────────────────────────────────────────────
    def user_photo(self, user_id: str) -> Optional[bytes]:
        resp = self._get(f"/users/{user_id}/photo/$value")
        if resp.status_code == 200:
            return resp.content
        if resp.status_code not in (404, 401, 403):
            logger.debug("photo fetch for %s returned %s", user_id, resp.status_code)
        return None

    def close(self) -> None:
        self._client.close()


# ── pure helpers (unit-tested) ────────────────────────────────────────────

def primary_email(user: dict[str, Any]) -> Optional[str]:
    mail = (user.get("mail") or user.get("userPrincipalName") or "").strip().lower()
    return mail or None


def extended_metadata(user: dict[str, Any]) -> dict[str, str]:
    """Map Graph user fields to Zitadel metadata keys (non-native attributes)."""
    business = user.get("businessPhones") or []
    return {
        "entra_oid": user.get("id", ""),
        "job_title": user.get("jobTitle") or "",
        "department": user.get("department") or "",
        "company_name": user.get("companyName") or "",
        "mobile_phone": user.get("mobilePhone") or "",
        "office_phone": business[0] if business else "",
        "fax_number": user.get("faxNumber") or "",
        "office_location": user.get("officeLocation") or "",
    }
