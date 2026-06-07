"""
zitadel-sync — sync jobs.

  sync_profiles  : Graph /users delta → Zitadel metadata + avatar (frequent).
  sync_groups    : full recompute of Entra group membership → namespaced
                   project roles + user grants (handles add AND remove).
  import_users   : one-shot bulk import with userId = Entra OID (migration).
  discover_subject_keys : operator helper for the migration cutover.

The group/role objects created here are NAMESPACED with settings.sync_role_prefix
so they never collide with the Terraform-owned native role catalog.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Optional

from config import Settings
from graph import GraphClient, extended_metadata, primary_email
from logging_setup import logger
from zitadel import ZitadelClient

_SAFE_RE = re.compile(r"[^a-zA-Z0-9._:-]+")


def role_key_for_group(prefix: str, group: dict) -> str:
    """Stable, namespaced role key for an Entra group (uses the immutable id)."""
    gid = group.get("id", "")
    return _SAFE_RE.sub("_", f"{prefix}{gid}")


def role_display_for_group(prefix: str, group: dict) -> str:
    name = group.get("displayName") or group.get("id", "group")
    return f"{prefix}{name}"


def _delta_path(settings: Settings, name: str) -> Path:
    return Path(settings.data_dir) / f"{name}.delta"


def _read_delta(path: Path) -> Optional[str]:
    try:
        return path.read_text(encoding="utf-8").strip() or None
    except OSError:
        return None


def _write_delta(path: Path, value: Optional[str]) -> None:
    if not value:
        return
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value, encoding="utf-8")
    except OSError as exc:
        logger.warning("could not persist delta token %s: %s", path.name, exc)


# ── profiles ──────────────────────────────────────────────────────────────
def sync_profiles(settings: Settings, graph: GraphClient, zit: ZitadelClient) -> dict[str, int]:
    delta_file = _delta_path(settings, "profiles")
    token = _read_delta(delta_file)
    changes, new_token = graph.users_delta(token)
    logger.info("sync-profiles: %d changed user(s) since last delta", len(changes))

    updated = skipped = 0
    for u in changes:
        if u.get("@removed"):
            continue
        oid = u.get("id")
        email = primary_email(u)
        if not oid or not email:
            skipped += 1
            continue
        if zit.get_user(oid) is None:
            # Not imported / never logged in yet — created on import or first login.
            skipped += 1
            continue
        zit.set_metadata_bulk(oid, extended_metadata(u))
        photo = graph.user_photo(oid)
        if photo:
            zit.upload_avatar(oid, photo)
        updated += 1

    _write_delta(delta_file, new_token)
    logger.info("sync-profiles: updated=%d skipped=%d", updated, skipped)
    return {"updated": updated, "skipped": skipped}


# ── groups → roles + grants ─────────────────────────────────────────────────
def sync_groups(settings: Settings, graph: GraphClient, zit: ZitadelClient) -> dict[str, int]:
    project_id = zit.find_project_id(settings.sync_project_name)
    if not project_id:
        logger.warning("sync-groups: project %r not found — run provisioning first", settings.sync_project_name)
        return {"users": 0, "grants": 0}

    users = graph.list_users()
    granted = skipped = 0
    for u in users:
        oid = u.get("id")
        if not oid or zit.get_user(oid) is None:
            skipped += 1
            continue
        groups = graph.user_groups(oid)
        role_keys: list[str] = []
        for g in groups:
            rk = role_key_for_group(settings.sync_role_prefix, g)
            zit.ensure_role(project_id, rk, role_display_for_group(settings.sync_role_prefix, g))
            role_keys.append(rk)
        # Replace the grant with exactly the current namespaced role set
        # (handles membership removals too).
        zit.set_user_grant(oid, project_id, role_keys)
        granted += 1

    logger.info("sync-groups: granted=%d skipped=%d", granted, skipped)
    return {"users": granted, "grants": granted, "skipped": skipped}


# ── one-shot import (migration) ─────────────────────────────────────────────
def import_users(
    settings: Settings, graph: GraphClient, zit: ZitadelClient, test_one: bool = False
) -> dict[str, int]:
    changes, _ = graph.users_delta(None)  # full enumeration with attributes
    created = exists = failed = 0
    for u in changes:
        if u.get("@removed"):
            continue
        oid = u.get("id")
        email = primary_email(u)
        if not oid or not email:
            continue
        result = zit.create_human_user(
            user_id=oid,
            email=email,
            given_name=u.get("givenName") or "",
            family_name=u.get("surname") or "",
            display_name=u.get("displayName") or "",
        )
        if result is None:
            failed += 1
        else:
            # Verify subject-preservation on the first user.
            fetched = zit.get_user(oid)
            if fetched and fetched.get("userId", oid) == oid:
                created += 1
            else:
                exists += 1
            zit.set_metadata_bulk(oid, extended_metadata(u))
            photo = graph.user_photo(oid)
            if photo:
                zit.upload_avatar(oid, photo)
        if test_one:
            logger.info("import-users --test-one: oid=%s result=%s", oid, "ok" if result else "FAILED")
            break

    logger.info("import-users: created=%d existing=%d failed=%d", created, exists, failed)
    return {"created": created, "existing": exists, "failed": failed}


# ── discovery helper (migration cutover) ────────────────────────────────────
def discover_subject_keys(settings: Settings) -> None:
    apps_raw = __import__("os").environ.get("APP_REDIRECT_URIS", "[]")
    try:
        apps = json.loads(apps_raw)
    except json.JSONDecodeError:
        apps = []
    logger.info("Per-app subject-key discovery (cutover planning):")
    logger.info("  Zitadel emits sub = Entra OID (subject-preservation via userId).")
    logger.info("  For each app, confirm which claim it persists as the user key:")
    logger.info("    - keyed on `oid`/`sub`(=OID) or `email`  -> seamless, no action")
    logger.info("    - keyed on Entra's pairwise `sub`         -> one-time email re-link")
    if apps:
        for a in apps:
            logger.info("  app: %s -> %s", a.get("name"), a.get("redirect_uris"))
    else:
        logger.info("  (no apps configured in APP_REDIRECT_URIS)")
