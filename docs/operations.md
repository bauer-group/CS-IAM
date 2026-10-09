# Operations

## Health & logs

```bash
docker compose -f docker-compose.traefik.yml ps
docker compose -f docker-compose.traefik.yml logs -f zitadel
docker compose -f docker-compose.traefik.yml logs provisioner   # one-shot
curl https://id.example.com/debug/healthz
curl https://id.example.com/.well-known/openid-configuration
```

`database-server` has a `pg_isready` healthcheck and `directory-sync` a process
healthcheck. `database-backup` has the BackupHelper engine's functional one: it
turns unhealthy when the last backup failed or no backup ran for 26 hours (see
[Backup & Restore](backup-and-restore.md#health)). `zitadel` runs the probe
Zitadel ships, `/app/zitadel ready` (it asks `/debug/ready`; the image is
distroless, so there is no shell). Traefik routes to Zitadel only while it is
healthy: during the first start (init + setup) and while it is unhealthy,
`IAM_HOSTNAME` answers 404. The provisioner and the sync/branding jobs still
poll readiness + the machine-key file themselves.

## Validate the deployment

`scripts/validate-stack.py` asserts — via the Management/Admin/OIDC APIs, using
the machine key — that everything the IaC provisions is actually in place:
discovery, orgs, projects + authorization flags, role catalogs, the Demo app's
OIDC config, the demo user + grant/roles, the branding LabelPolicy and the
LoginPolicy. It prints a PASS/FAIL matrix and exits non-zero on any failure (a
full-stack smoke test). Run it from the toolkit container (it has the deps +
the machine key):

```bash
docker compose -f docker-compose.development.yml cp \
  scripts/validate-stack.py directory-sync:/tmp/validate-stack.py
docker compose -f docker-compose.development.yml exec directory-sync \
  python /tmp/validate-stack.py
```

It reaches Zitadel exactly like the stack's automation, with directory-sync's
own issuer: in development `https://iam.example.test:8080` through the dev
proxy, whose self-signed certificate the container trusts (`SSL_CERT_FILE`), in
production `https://<IAM_HOSTNAME>` — run the same two commands with
`docker-compose.traefik.yml` or `docker-compose.coolify.yml`. `--issuer` names
another URL; it must use the instance domain, because Zitadel picks the
instance by host (`http://zitadel:8080` is rejected). `--insecure` skips TLS
verification.

## Upgrades

- **Zitadel/Postgres/base images**: Dependabot opens PRs; the daily base-image
  monitor pins upstream digests and triggers a rebuild. Bump `ZITADEL_VERSION`
  in `.env` for a manual upgrade, then `docker compose pull && up -d`.
- **Re-provision** after Terraform changes: restart the stack (the init
  container re-applies, non-destructively) or run `tofu apply` from the CLI.

## Backups

Enable the sidecar and see [backup-and-restore.md](backup-and-restore.md):

```bash
docker compose -f docker-compose.traefik.yml --profile backup up -d database-backup
```

## Scaling path (goal g)

This stack is single-host self-healing (`restart: unless-stopped` + healthchecks).
Zitadel is **stateless beyond Postgres**, so the HA path is:

1. **HA / managed PostgreSQL** (primary + replica, or a managed cluster).
2. **N `zitadel` replicas** behind Traefik (round-robin; still h2c).
3. A **shared cache connector** (`ZITADEL_CACHES_*` → postgres or redis) so the
   replicas share login/session caches.

The sidecars stay single-instance (cron). Move them to scheduled jobs
(k0s CronJob / CI) in a multi-node setup.

## Decoupling from Entra (goal i)

Because local accounts + the native role catalog are first-class, the stack can
run fully MS-free. At runtime nothing breaks if Entra is removed (`directory-sync`
idles, local + admin logins keep working) — decoupling is a deliberate user
migration, not a fix. The critical step is that **federated users are
password-less**, so they need their own credential (a passkey covers credential +
MFA) **before** Entra is dropped; the Entra IdP must also be retired cleanly so
the non-destructive provisioner doesn't abort on the destroy.

→ Full, step-by-step process: **[decoupling-from-entra.md](decoupling-from-entra.md)**.
