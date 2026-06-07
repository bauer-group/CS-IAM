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

## `.env` reference (key entries)

| Variable | Purpose |
|---|---|
| `STACK_NAME` | container/volume/network prefix (default `iam`) |
| `IAM_HOSTNAME` | production OIDC issuer host |
| `IAM_DEV_HOSTNAME` / `IAM_DEV_PORT` | dev issuer (the Docker service name, `zitadel:8080`) |
| `PROXY_NETWORK` | external Traefik network |
| `ZITADEL_MASTERKEY` | 32-char secrets-at-rest key (generated) |
| `ZITADEL_ADMIN_PASSWORD` | first admin console password (generated) |
| `ZITADEL_DB_*` | Postgres name/user/password |
| `PG_*` | Postgres tuning |
| `AZURE_TENANT_ID/CLIENT_ID/CLIENT_SECRET` | Entra app registration |
| `APP_REDIRECT_URIS` | JSON list of OIDC apps for Terraform |
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

Creates the `BAUER GROUP` org, the Human admin (`admin@bauer-group.com`,
password via `ZITADEL_FIRSTINSTANCE_ORG_HUMAN_PASSWORD`), and the **machine
automation user** `iam-admin` whose JSON key is written to the `machinekey`
volume — the credential Terraform and `directory-sync` use.

## What is NOT here

IdPs, projects, OIDC apps, roles and grants are **Terraform** (`terraform/`),
not native config — Zitadel can't express them declaratively. See
[provisioning-terraform.md](provisioning-terraform.md).
