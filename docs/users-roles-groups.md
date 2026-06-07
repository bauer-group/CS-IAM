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
