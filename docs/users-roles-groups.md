# Users, Roles & Groups

## Organisations (trust tiers)

| Org | Who | Password policy | App access |
|-----|-----|-----------------|------------|
| **BAUER GROUP** (internal) | company users (federated + local) | strict instance default (12 chars + MFA) | all internal apps via the grant model |
| **External Users** (customers) | external/customer accounts | relaxed (`min_length 8`, org-level override) | **only** apps explicitly granted to this org |

Both orgs live in one Zitadel instance. The internal org is created by
FirstInstance; the **External Users** org, its relaxed password policy, and the
customer **External Apps** project (granted to it) are managed in Terraform
(`terraform/orgs.tf`, `projects.tf`).

**How "externals only reach allowed apps" works:** every project has
`has_project_check = true`, so a token is only issued to a user who holds a
grant. Internal apps live in the `BAUER GROUP` project, which is **never granted
to the external org** → customers can't authenticate to them. Customer apps live
in the `External Apps` project, which **is** granted to the external org →
customers can be granted roles there and only there. Route an app with the
per-app `audience` field (`"internal"` default, or `"external"`).

## Account types

| Type | Auth | Password | MFA |
|------|------|----------|-----|
| **Federated** (from Entra) | Entra only | none (password-less) | Entra |
| **Local** (Zitadel-native) | username/password | yes | enforced (`ForceMFALocalOnly`) |

Both coexist (goals b + i): the stack stays usable even without Entra, which is
what makes a later **decoupling** from Entra possible — local accounts + own
roles make Zitadel self-authoritative.

Federated users are created **without a password** (by `import-users` and by JIT
auto-creation), so the password form simply cannot authenticate them — they are
IdP-only by construction.

## Roles & grants (app-login gating)

Zitadel models "groups" through **project roles** + **user grants**:

- The **project** has authorization-on-auth enabled — a user must hold a grant
  with a role to log into that project's apps (goal d).
- **Native roles** (`user`, `admin`, …) are the Terraform-owned catalog
  (`terraform/roles.tf`).
- **Entra-group roles** are created by `directory-sync`, **namespaced** with
  `entra:` so they're distinct. Each user's grant is recomputed from their
  current Entra group membership (adds + removes).

To gate an app on a specific Entra group, ensure the app is in the project and
grant the corresponding `entra:<group>` role (the sync does this automatically
for group members).

## Grants vs scopes vs roles — what controls what

Three distinct things, often confused:

| Concept | Set where | Controls |
|---|---|---|
| **Scope** | the **app** requests it in the auth request | **what's in the token** (which claims/data) + behaviour — `openid` (required), `profile`/`email`, `offline_access` (refresh), `urn:zitadel:iam:user:metadata`. Not *who* may log in. |
| **Role** | the **project** role catalog (`roles.tf`) | a **named permission** (a label like `user`/`admin`). On its own grants nothing — it must be assigned. |
| **Grant** | binds **user ↔ project ↔ roles** (`grants.tf`, the sync, `demo.tf`, or Console authorizations) | **who may access** the project's apps (with `has_project_check` → no grant, no token) and **which roles** that user carries. |

How they combine on a login:

1. **Access gate = the grant.** `has_project_check` → a user must hold a grant
   (any role) in the app's project to get a token at all. No grant → no login.
2. **What the user may do inside = the roles** in that grant. Role assertion puts
   them in the token (`urn:zitadel:iam:org:project:roles`); the **app** reads the
   claim and enforces feature-level authz (e.g. show admin actions only for `admin`).
3. **What the token carries = the scopes** the app requested. Scopes shape the
   claims (profile, email, metadata, roles/audience), not access.

Mnemonic: **grant = the key (in/out), role = what you may do inside, scope = what
info you carry with you.**

Example (the shipped demo, fully isolated): project `pDemo` defines
`rUser`/`rManager`/`rAdministrator`; `demo.tf` grants the demo user
`rUser`+`rManager` in `pDemo` (→ can sign into the `Demo` app there; token roles
`rUser`,`rManager` — note: not `rAdministrator`); the app requests
`openid profile email … metadata` → the token carries those claims **plus** the
two roles. The grant exists **only in `pDemo`**, so the user can't reach the
BAUER GROUP or External apps — clean isolation.

## Self-service UI (goal f)

Zitadel ships the **Console** and the **Login v2** UI. Users manage their own
profile, security factors (TOTP/passkeys) and sessions there. Admins manage
org/users/roles in the Console. No extra container required.

## Token claims

Apps request:

```text
openid profile email urn:zitadel:iam:user:metadata
```

The metadata scope surfaces synced extended attributes (department, fax, …) and
`entra_oid` (reference only). Project role assertion puts the user's roles into
the token for app-side authorization.
