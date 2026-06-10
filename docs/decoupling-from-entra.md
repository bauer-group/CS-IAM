# Decoupling from Entra ID (going MS-free)

This runbook removes the **internal** Microsoft Entra ID dependency so the stack
runs fully self-authoritative — for when BAUER GROUP retires Microsoft products.
It does **not** touch the **external**-org IdPs (Google, social logins); those are
independent and keep working.

> **This is design goal (i), and it is safe to plan for.** Local accounts, the
> native role catalog and a local break-glass admin are all first-class. At
> runtime, removing Entra never crashes anything — `directory-sync` idles, local
> and admin logins keep working. The steps below are a **deliberate user
> migration**, not a fix for a failure.

## What depends on internal Entra — and what doesn't

| Keeps working without Entra | Needs a deliberate step before cut-over |
|---|---|
| Local accounts (`AllowUsernamePassword: true`) | **Federated users are password-less** → must get their own credential |
| Break-glass admin (local password, IAM_OWNER) | The Entra IdP (Terraform-managed) → remove cleanly, not by blanking env |
| core / login / `zitadel-brand` / external IdPs | `directory-sync` (Graph reads) → stop it |
| Entra-sourced roles + grants (persist, become static) | MFA: every login becomes "local" → all users need an MFA factor |

`★ The one critical fact ──────────────────────────`
Imported/federated users are created **without a password** ("IdP-only"). Once
Entra is gone they cannot authenticate until they hold their own credential.
Registering a **passkey** for each solves both the credential *and* the
`ForceMFALocalOnly` MFA requirement in one step. The local admin is unaffected.
`──────────────────────────────────────────────────`

## Pre-flight

- [ ] Confirm the **local break-glass admin** logs in (username + password + its MFA factor) — your safety net throughout.
- [ ] Take a fresh backup — see [backup-and-restore.md](backup-and-restore.md).
- [ ] Inventory the **federated users** (Entra-linked / password-less):
  - Console → Users → each shows *Authentication* (no password set) and a linked *Identity Provider* (Entra), **or**
  - the import report on the `sync` volume lists every imported `userId`.
- [ ] Decide the per-user credential strategy (passkey recommended — Phase 1).

## Phase 1 — Make federated users self-sufficient (do this first, while Entra still works)

Per user, pick one (passkey preferred):

1. **Passkey (recommended — credential + MFA in one):** the user logs in via Entra
   one last time → Self-service → *Passwordless / Passkeys* → register. They no
   longer need Entra afterwards, and the passkey satisfies `ForceMFALocalOnly`.
2. **Password + MFA:** admin sets an initial password (Console → User → *Set password*,
   `PasswordChangeRequired: true`) communicated out-of-band, or send an init-email
   link; the user then also registers an MFA factor (required for local logins).
3. **Service-style accounts:** set a password and store it in the secret manager.

- [ ] Verify a sample migrated user logs in **without** Entra (incognito session) before the mass cut-over.
- [ ] Confirm their **app access** is intact — roles/grants persist independently of the sync.

## Phase 2 — Stop the Entra reads (`directory-sync`)

- [ ] Set `SYNC_ENABLED=false` in `.env` → `directory-sync` idles (no crash, no Graph calls).
      Alternatively remove the `directory-sync` service entirely. `zitadel-brand`
      does **not** use Entra and stays.
- [ ] Redeploy: `docker compose -f docker-compose.<variant>.yml up -d`.

Leave `AZURE_*` **set for now** — blanking it before Phase 3 would make Terraform
want to *destroy* the IdP, and the non-destructive provisioner would abort.

## Phase 3 — Remove the Entra IdP cleanly (avoid the destroy-guard)

The provisioner refuses any plan containing a destroy/replace (it protects
UI-made resources). So retire the resource deliberately instead of blanking env:

1. Drop it from Terraform's state **without** a guarded destroy:
   ```bash
   cd terraform
   tofu state rm 'zitadel_idp_azure_ad.entra[0]'
   ```
2. Remove the `zitadel_idp_azure_ad "entra"` block from `terraform/idps.tf`
   (and, if you like, the now-unused `azure_*` variables). Commit.
3. Delete the now-orphaned IdP in **Console → (Default) Settings → Identity
   Providers** (optional — with MS gone it is a dead link anyway).
4. (Optional) Tidy the internal-org LoginPolicy: domain-discovery routing to Entra
   (`AllowDomainDiscovery` / `DefaultRedirectURI`) can be dropped.

After this, `tofu plan` is clean (no destroy) → the provisioner stays green and
`directory-sync` / `zitadel-brand` (which depend on its success) start normally.

## Phase 4 — Decommission the Azure side

- [ ] Remove `AZURE_TENANT_ID` / `AZURE_CLIENT_ID` / `AZURE_CLIENT_SECRET` from `.env`
      (safe now — the IdP is out of state and the sync is off). Redeploy.
- [ ] In Azure: delete the **App Registration** (the Zitadel SSO app + its Graph permissions).

## Phase 5 — Verify MS-free operation

- [ ] Every user logs in locally (password/passkey) **with MFA** (`ForceMFALocalOnly`
      now applies to all; exemptions via the per-role org policy if configured).
- [ ] App access (project grants) intact for every app.
- [ ] `docker compose … logs provisioner` → clean apply, **no destroy pending**, exit 0.
- [ ] `directory-sync` idle/removed; `zitadel-brand` still brands on deploy.
- [ ] `/.well-known/openid-configuration` + Console reachable; break-glass admin works.

## What persists vs. what's gone

| Persists | Gone |
|---|---|
| All users (ids, profiles, metadata, avatars) | Live profile/group refresh from Entra |
| Roles + grants (now static) → app gating | Auto-creation of new users from Entra logins |
| External-org IdPs (Google, …) | The internal Entra login button |
| Branding, projects, apps, OIDC clients | The Microsoft App Registration |

## Re-coupling later (if needed)

Reverse it: re-add the `zitadel_idp_azure_ad "entra"` block, set `AZURE_*`, set
`SYNC_ENABLED=true`. Federation **auto-links returning users by email**
(`AUTO_LINKING_OPTION_EMAIL`), so existing accounts re-attach without duplicates.

See also: [users-roles-groups.md](users-roles-groups.md) (local vs federated),
[directory-sync.md](directory-sync.md), [provisioning-terraform.md](provisioning-terraform.md).
