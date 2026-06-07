# Directory Sync (freshness from Entra)

Two complementary layers keep Zitadel current with Entra:

## 3a. Login-time JIT (native Zitadel)

The Entra IdP has **auto-update** enabled → on **every login** Zitadel refreshes
the user's profile from the Entra token claims (name, email, …). Free and
instant, but limited to token claims and only for users who log in.

## 3b. Scheduled `zitadel-sync` (Graph delta)

A Python sidecar with **two independently-scheduled jobs** (one container,
shared auth + delta-token store):

| Job | Source | Writes | Interval |
|-----|--------|--------|----------|
| `sync-profiles` | Graph `/users/delta` | native `phone`* + **metadata** (job title, department, company, mobile, office phone, **fax**, office location) + **avatar** (Assets API) | `SYNC_PROFILES_INTERVAL` (300s) |
| `sync-groups` | full user pass + `transitiveMemberOf` | **namespaced** project roles + user **grants** | `SYNC_GROUPS_INTERVAL` (600s) |

Extended attributes land as **user metadata** and reach apps via the metadata
scope `urn:zitadel:iam:user:metadata`. Photos (which Graph delta doesn't flag
reliably) are fetched per profile run.

> *Native `phone` field mapping is best-effort; all phone numbers are also
> stored in metadata so apps get them via the metadata scope regardless.

## Namespacing (overview-preserving)

Synced roles use `SYNC_ROLE_PREFIX` (default `entra:`) + the immutable Entra
group id, with the group's display name as the role's display name. The sync
**only ever manages prefixed objects** and replaces each user's grant with
exactly their current namespaced role set — so membership **removals** propagate
too, and hand-made/native roles are never touched.

## One-shot CLI

```bash
docker compose run --rm zitadel-sync sync-profiles
docker compose run --rm zitadel-sync sync-groups
docker compose run --rm zitadel-sync import-users --test-one
docker compose run --rm zitadel-sync import-users
docker compose run --rm zitadel-sync discover-subject-keys
```

## Why not event-driven (yet)

Pure event-driven (Graph change-notifications → webhook) needs a public HTTPS
receiver + subscription-renewal + a reconcile backstop. With few users the lean
**delta + JIT** model is robust and near-real-time. Webhooks remain a documented
Phase-2 enhancement.

> SCIM-inbound from Entra is **not** used — Zitadel SCIM v2 is preview,
> User-only (no groups), and Entra-inbound isn't ready.
