# Configuration

Configuration lives in three places:

1. **`.env`** — secrets + instance values + sidecar tuning (this file).
2. **`config/zitadel/defaults.yaml`** — `DefaultInstance` policies/branding/SMTP
   (secret-free, committed). Secrets/instance values are overridden by
   `ZITADEL_*` env vars from the compose file.
3. **`config/zitadel/steps.yaml`** — `FirstInstance` org/admin/machine SA.

> The two `config/zitadel/*.yaml` files are **baked into the `zitadel` image**
> (so the stack doesn't depend on fragile host bind-mounts). To apply changes,
> rebuild/re-pull the image — or, for a quick local override, uncomment the
> config bind-mounts in the compose `zitadel.volumes:` block and edit the host
> files. Either way the source of truth stays `config/zitadel/`.

## When configuration takes effect (three classes)

`.env` is read by `docker compose` on **every** `up`/`restart` and interpolated
into the containers. What a value then *does* depends on which class it falls
into — the key thing to know before changing config on a running stack:

| Class | What (examples) | When it takes effect | Change later? |
|---|---|---|---|
| **A · Operational** | `IAM_HOSTNAME`, `ZITADEL_MASTERKEY`, DB creds, `SMTP_*`, `SYNC_*`, `BACKUP_*` | every affected **container start** | restart the service |
| **B · Terraform (reconciled)** | `AZURE_*`, `EXTERNAL_*`, `INTERNAL_ORG_DOMAINS`, `APP_REDIRECT_URIS`, `DEMO_USER_PASSWORD` → IdPs, login policies, projects, OIDC apps, org domains | every **provisioner run** | edit `.env` + `up` → reconciles |
| **C · Instance bootstrap** | `config/zitadel/defaults.yaml` (incl. **`ValidateOrgDomains`**), `steps.yaml`, the first-admin password | **first init only** (empty DB) | fresh instance, or out-of-band (Console / Admin API) |

**Class B is safe to change on a live stack.** The `provisioner` is a one-shot
init container, but Compose recreates and re-runs it whenever its env changes, so
editing `.env` and `docker compose up` reconciles the running instance to the new
desired state. It is **non-destructive**: if the plan would delete or replace a
managed resource it aborts and prints the plan instead of applying
([provisioning-terraform.md](provisioning-terraform.md)). So you can switch Entra
or external IdPs on **later** without wiping anything.

**Class C is immutable after the first boot — by design.** These seed the
instance identity (policies, the break-glass admin, the domain-verification mode)
once while the database is empty; later starts skip the completed setup steps.
Editing the files afterwards does **not** retro-apply. Change them either by
re-initialising a fresh instance (greenfield) or out-of-band on the live instance
(Console → Default Settings, or the Admin API). `ValidateOrgDomains=false` lives
here — that is why it must be in place **before** the first boot.

> **Rule of thumb:** lives in `terraform/` → Class B (re-applied, changeable
> later). Lives in `config/zitadel/*.yaml` or is a `FIRSTINSTANCE_*` value →
> Class C (first boot only). Plain operational `ZITADEL_*` / sidecar env → Class A.

## `.env` reference (key entries)

| Variable | Purpose |
|---|---|
| `STACK_NAME` | container/volume/network prefix (default `iam`) |
| `IAM_HOSTNAME` | production OIDC issuer host |
| `IAM_DEV_HOSTNAME` / `IAM_DEV_PORT` | dev domain + port (`iam.example.test:8080`) — a network alias on the core and the HTTPS proxy origin; a valid WebAuthn rp.id |
| `PROXY_NETWORK` | external Traefik network |
| `ZITADEL_MASTERKEY` | 32-char secrets-at-rest key (generated) |
| `ZITADEL_ADMIN_PASSWORD` | first admin console password (generated) |
| `ZITADEL_DB_*` | Postgres name/user/password |
| `PG_*` | Postgres tuning |
| `AZURE_TENANT_ID/CLIENT_ID/CLIENT_SECRET` | internal Entra app registration (Class B) |
| `INTERNAL_ORG_DOMAINS` | JSON array of verified workforce domains for discovery (Class B) |
| `EXTERNAL_*` | customer-org IdP creds: Entra multi-tenant, Google, OAuth2/OIDC maps (Class B) |
| `APP_REDIRECT_URIS` | JSON list of OIDC apps for Terraform (Class B) |
| `SYNC_*` | directory-sync intervals, role prefix, project name |
| `BACKUP_*` / `SMTP_*` | backup schedule, retention, off-site S3, alerts |

## Native Zitadel config (`defaults.yaml`)

`DefaultInstance` carries the policies that aren't expressible elsewhere:

- **LoginPolicy** — `AllowUsernamePassword: true`, `AllowExternalIDP: true`,
  `ForceMFALocalOnly: true`, `AllowDomainDiscovery: true`. Local accounts use a
  password (+ MFA); federated users are created password-less → IdP-only.
- **PasswordComplexityPolicy / LockoutPolicy** — local account hardening.
- **LabelPolicy** — brand colours.
- **OIDCSettings** — access/ID/refresh token lifetimes.

Secrets never live in these files. To change a value Zitadel exposes as env,
override it in the compose `environment:` (e.g.
`ZITADEL_DEFAULTINSTANCE_LOGINPOLICY_FORCEMFA: "true"`).

## FirstInstance (`steps.yaml`)

Creates the local break-glass **`System Admins`** org, its Human admin
(`admin@id-admin.example.com`, password via `ZITADEL_ADMIN_PASSWORD` →
`ZITADEL_FIRSTINSTANCE_ORG_HUMAN_PASSWORD`), and the **machine automation user**
`iam-admin` whose JSON key is written to the `machinekey` volume — the credential
Terraform and `directory-sync` use. (The `BAUER GROUP` workforce org is created in
Terraform — `terraform/projects.tf` — not here.)

## What is NOT here

IdPs, projects, OIDC apps, roles and grants are **Terraform** (`terraform/`),
not native config — Zitadel can't express them declaratively. See
[provisioning-terraform.md](provisioning-terraform.md).
