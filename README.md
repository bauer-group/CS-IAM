# CS-IAM — Zitadel OIDC/IAM Stack

> Central, self-hosted **OIDC/IAM provider** for BAUER GROUP, built on
> [Zitadel](https://zitadel.com). It federates to **Microsoft Entra ID**, keeps
> its own accounts, syncs profiles/avatars/groups, and provisions itself as
> code — so it can eventually run fully autonomous.

[![Release & Docker Build](https://github.com/bauer-group/CS-IAM/actions/workflows/docker-release.yml/badge.svg)](https://github.com/bauer-group/CS-IAM/actions/workflows/docker-release.yml)

---

## Highlights

| Capability | How |
|---|---|
| Federates to **Entra ID** (and later Google/GitHub/…) | upstream IdP, provisioned via Terraform |
| **Own local accounts** (need not exist in Entra) | login policy allows local + IdP; federated users are password-less (IdP-only); `ForceMFALocalOnly` |
| **Avatar + extended attributes** kept current | `zitadel-sync` delta job → native phone + metadata (fax/mobile/office/dept) + avatar |
| **Roles/groups** drive app login | Entra groups → namespaced project roles + grants; project authorization-on-auth gate |
| **Self-service UI** | Zitadel Console + Login v2 |
| **Everything as code** | native config → Terraform (IaC init container) → Python sync; non-destructive |
| **Stable migration** | subject-preservation (`sub` = Entra OID) → zero app changes |
| Self-healing, backups, CI/CD | `restart` + healthchecks, `pg_dump` sidecar, reusable-workflow pipeline |

## Architecture

```text
            ┌──────────────┐   OIDC    ┌──────────────┐  upstream
 apps  ───▶ │   Zitadel    │ ───SSO───▶│   Entra ID   │  (+ Google/GitHub later)
(Outline,   │  v4 (h2c)    │           └──────────────┘
 Documenso) │  sub = OID   │
            └──────┬───────┘
                   │ Postgres 18
            ┌──────▼───────┐   zitadel-provision (OpenTofu, one-shot, non-destructive)
            │  zitadel-db  │   zitadel-sync      (Graph delta → profiles/avatar/groups)
            └──────────────┘   zitadel-backup    (pg_dump, --profile backup)
```

## Quick start (development)

```bash
python scripts/generate-env.py          # generate secrets into .env
# edit .env: set AZURE_* (optional for standalone) — IAM_DEV_HOSTNAME defaults to zitadel.localhost
docker compose -f docker-compose.development.yml up -d --build
# console: http://zitadel.localhost:8080   (login admin@bauer-group.com)
curl http://zitadel.localhost:8080/.well-known/openid-configuration
```

Production (Traefik): set `IAM_HOSTNAME`, point DNS at the host, then
`docker compose -f docker-compose.traefik.yml up -d`. See
[docs/installation.md](docs/installation.md).

## Repository layout

```text
config/zitadel/   defaults.yaml + steps.yaml   (native Zitadel config — policies, org, admin, SA)
terraform/        IdPs, project, OIDC apps, role catalog, grants  (IaC)
src/zitadel/             thin-wrapper image
src/zitadel-provision/   OpenTofu init container (guarded, non-destructive)
src/zitadel-sync/        directory-sync (Python)
src/zitadel-backup/      pg_dump sidecar (Python)
scripts/generate-env.py  cross-platform secret generator
docker-compose.{development,traefik,coolify}.yml
docs/             setup / management / operation / migration guides
```

## Layered "everything-as-code"

1. **Native config** (`config/zitadel/*.yaml`) — policies, branding, SMTP, token lifetimes, org + admin + machine SA.
2. **Terraform** (`terraform/`, run by the `zitadel-provision` init container) — IdPs, project, OIDC apps, role catalog, grants. **Non-destructive**: never prunes UI-made resources; aborts on any destroy.
3. **Directory-sync** (`zitadel-sync`) — Graph delta → extended attributes, avatar, Entra groups → namespaced roles/grants. Login-time JIT refresh is native to Zitadel.

## Documentation

| Guide | Topic |
|---|---|
| [installation.md](docs/installation.md) | deploy (dev / Traefik / Coolify), first login |
| [configuration.md](docs/configuration.md) | `.env` + `defaults.yaml`/`steps.yaml` reference |
| [provisioning-terraform.md](docs/provisioning-terraform.md) | IaC, state, non-destructive guard, adding apps/IdPs |
| [identity-providers.md](docs/identity-providers.md) | Entra setup + adding Google/GitHub/Facebook |
| [directory-sync.md](docs/directory-sync.md) | freshness model (JIT + delta), namespacing |
| [users-roles-groups.md](docs/users-roles-groups.md) | local vs federated, role/grant app-gating, self-service |
| [migration.md](docs/migration.md) | Entra → Zitadel cutover (avatar + data preserved) |
| [operations.md](docs/operations.md) | health, upgrades, HA path, decoupling |
| [backup-and-restore.md](docs/backup-and-restore.md) | pg_dump snapshots, off-site, restore |
| [security-hardening.md](docs/security-hardening.md) | security posture |
| [troubleshooting.md](docs/troubleshooting.md) | h2c/502, PG18, duplicate users, … |

## Supported versions

| Component | Pin | Note |
|---|---|---|
| Zitadel | `v4.15.0` | PostgreSQL 18 needs ≥ v4.11.0 |
| PostgreSQL | `18-alpine` | volume path `/var/lib/postgresql` (no `/data`) |
| OpenTofu | `1.10` | provision image base |
| Python | `3.14-alpine` | sync + backup sidecars |

## License

MIT (this stack). Zitadel itself is **AGPL-3.0** — internal self-hosting without
SaaS redistribution is unproblematic.
