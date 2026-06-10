# Managing in the Console (vs. code)

Everything this stack provisions can also be **viewed, tested and changed
visually** in the Zitadel **Console** (`https://<IAM_HOSTNAME>`, sign in as the
admin). This page maps each area to where you find it — and the crucial rule for
keeping the Console and the code in sync.

## The sync rule (read this first)

The stack has three configuration layers with **different persistence**:

| Layer | Re-applied when? | A change you make in the Console… |
|---|---|---|
| **Terraform** (`provisioner`) — IdPs, projects, apps, roles, grants, demo | on every **(re)deploy** (one-shot, reconciles to code) | **reverts** on the next deploy. Codify it to keep it. |
| **Branding assets** (`zitadel-brand`) — logo/icon/font | on every **(re)deploy** (re-uploads + activates) | **reverts**. Swap the files in `src/directory-sync/branding/` to keep it. |
| **Native config** (`defaults.yaml`/`steps.yaml`) — colours, login/password/MFA/lockout policies, SMTP | **first boot only** (DefaultInstance) | **persists on this instance**, but a *fresh* deploy uses the file → mirror it back into `defaults.yaml`. |

Plus the safety net: the provisioner is **non-destructive** — a brand-**new**
object you create *only* in the Console (not in code) is **never deleted**. But
it's **drift**: not reproducible, not in `tofu output`. And `org` + both projects
carry `prevent_destroy`.

> **Rule of thumb:** *View and test freely in the Console.* For anything managed
> in **code** (Terraform / branding), a Console edit is **temporary** — make it
> permanent by updating the code and redeploying. There is no `ignore_changes`,
> so every Terraform-managed field is code-authoritative.

## Where to find each thing

| What | Console location | Source of truth (code) |
|---|---|---|
| Brand **colours** | Settings → Branding | `config/zitadel/defaults.yaml` (LabelPolicy) |
| **Logo / icon / font** | Settings → Branding | `src/directory-sync/branding/` (uploaded by `zitadel-brand`) |
| **Login / password / MFA / lockout** policies | Settings → Login Behavior / Complexity / Lockout | `config/zitadel/defaults.yaml` |
| **Organisations** | Organizations | `terraform/orgs.tf` (prevent_destroy) |
| **Projects** (BAUER GROUP / External Apps) | Projects | `terraform/projects.tf` (prevent_destroy) |
| **Identity Providers** (Entra / Google / social) | Settings → Identity Providers (per org) | `terraform/idps.tf`, `idps_external.tf` + `.env` creds |
| **OIDC apps** + redirect URIs + secrets | Project → Applications | `APP_REDIRECT_URIS` / `terraform/applications.tf` |
| **Project roles** | Project → Roles | `terraform/roles.tf` (`project_roles` var) |
| **Grants** (authorizations) | Project → Authorizations · User → Authorizations | `terraform/grants.tf` (break-glass) · `directory-sync` (`entra:` roles) · `terraform/demo.tf` (demo) |
| **Users** (profile, metadata, avatar) | Users | `directory-sync` (from Entra) · `terraform/demo.tf` (demo user) |

## Workflow: prototype in the UI → codify the keepers

1. **Explore / test** in the Console (create a throwaway app, try a redirect URI, grant a role).
2. Decide it's permanent → **put it in code**:
   - app → add to `APP_REDIRECT_URIS` (or `applications.tf`)
   - role → `project_roles` / `roles.tf`
   - IdP → `idps*.tf` + `.env`
   - stable grant → `grants.tf` (break-glass) or let `directory-sync` own it (`entra:` group roles)
   - logo/favicon/colour → `src/directory-sync/branding/`, `src/login/branding/`, `defaults.yaml`
3. **Redeploy** — the provisioner re-applies; your code is now the source of truth and the Console matches it.

> Synced user fields (profile, group-derived `entra:` grants, avatar) are owned by
> `directory-sync` and **recomputed every run** — change those at the source
> (Entra), not in the Console. See [directory-sync.md](directory-sync.md).
