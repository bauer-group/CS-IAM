# Operations

## Health & logs

```bash
docker compose -f docker-compose.traefik.yml ps
docker compose -f docker-compose.traefik.yml logs -f zitadel
docker compose -f docker-compose.traefik.yml logs provisioner   # one-shot
curl https://id.bauer-group.com/debug/healthz
curl https://id.bauer-group.com/.well-known/openid-configuration
```

`database-server` has a `pg_isready` healthcheck; the sidecars have process
healthchecks. `zitadel` itself has no in-container healthcheck (distroless) —
readiness is verified via the discovery endpoint and polled by dependents.

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
  python /tmp/validate-stack.py --issuer http://zitadel:8080 --insecure
# prod: --issuer https://<IAM_HOSTNAME>  (drop --insecure)
```

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
