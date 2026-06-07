# Operations

## Health & logs

```bash
docker compose -f docker-compose.traefik.yml ps
docker compose -f docker-compose.traefik.yml logs -f zitadel
docker compose -f docker-compose.traefik.yml logs zitadel-provision   # one-shot
curl https://id.bauer-group.com/debug/healthz
curl https://id.bauer-group.com/.well-known/openid-configuration
```

`zitadel-db` has a `pg_isready` healthcheck; the sidecars have process
healthchecks. `zitadel` itself has no in-container healthcheck (distroless) —
readiness is verified via the discovery endpoint and polled by dependents.

## Upgrades

- **Zitadel/Postgres/base images**: Dependabot opens PRs; the daily base-image
  monitor pins upstream digests and triggers a rebuild. Bump `ZITADEL_VERSION`
  in `.env` for a manual upgrade, then `docker compose pull && up -d`.
- **Re-provision** after Terraform changes: restart the stack (the init
  container re-applies, non-destructively) or run `tofu apply` from the CLI.

## Backups

Enable the sidecar and see [backup-and-restore.md](backup-and-restore.md):

```bash
docker compose -f docker-compose.traefik.yml --profile backup up -d zitadel-backup
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

Because local accounts + the native role catalog are first-class, you can run
without Entra:

1. Create local accounts (or keep the imported ones) and set passwords.
2. Remove/disable the Entra IdP (delete `terraform/idps.tf` entry, `tofu apply`).
3. Stop `zitadel-sync`.
Zitadel remains the authoritative IdP for all apps — no app reconfiguration.
