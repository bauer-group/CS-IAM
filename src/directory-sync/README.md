# directory-sync

Keeps Zitadel users fresh from Microsoft Entra ID. One container, two
independently-scheduled jobs sharing Graph + Zitadel clients:

| Job | Source | Writes to Zitadel | Interval |
|-----|--------|-------------------|----------|
| `sync-profiles` | Graph `/users/delta` | extended attributes (job title, department, mobile/office/**fax**, …) as user **metadata** + **avatar** (Assets API) | `SYNC_PROFILES_INTERVAL` (300s) |
| `sync-groups` | full user pass + `transitiveMemberOf` | **namespaced** project roles + user **grants** (`SYNC_ROLE_PREFIX`, e.g. `entra:`) | `SYNC_GROUPS_INTERVAL` (600s) |

Login-time freshness is additionally handled natively by Zitadel's IdP
"Automatic update" (§3a) — this sidecar covers what isn't in tokens (photo, fax,
office) and users who don't log in.

## One-shot CLI (migration)

```bash
docker compose run --rm directory-sync import-users --test-one   # verify userId=OID is accepted
docker compose run --rm directory-sync import-users              # bulk import (subject-preservation)
docker compose run --rm directory-sync sync-profiles
docker compose run --rm directory-sync sync-groups
docker compose run --rm directory-sync discover-subject-keys
```

## Subject-preservation

`import-users` creates each Zitadel user with **`userId = Entra OID`** and **no
password** → the app-facing `sub` equals the value apps already store, and the
account is IdP-only. Federation auto-links by email on first login.

## Ownership boundary

This sidecar owns **dynamic, namespaced** roles/grants derived from Entra
groups. The **native role catalog** is owned by Terraform (`terraform/roles.tf`).
The two sets never overlap.

## Notes

- Requires Application Graph permissions: `User.Read.All`, `GroupMember.Read.All`,
  `ProfilePhoto.Read.All` (admin-consented).
- Auth to Zitadel uses the FirstInstance machine key (`/machinekey/iam-admin.json`).
- Zitadel API paths (v2 users + v1 management) are validated in the integration
  smoke test against the deployed version.
- No PII/secrets are logged.
