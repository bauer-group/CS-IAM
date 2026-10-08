# Backup & Restore

Zitadel keeps all state in PostgreSQL, so a DB dump is a **complete** snapshot
(there is no S3 source in this stack). The `database-backup` sidecar handles it.

## Enable

```bash
docker compose -f docker-compose.traefik.yml --profile backup up -d database-backup
```

Default schedule: cron `15 3 * * *` (03:15), retention 14, local-only.

## Off-site target (optional)

Set in `.env` to also push each snapshot to an S3-compatible bucket
(AWS / Cloudflare R2 / Backblaze B2 / a second MinIO):

```env
BACKUP_S3_ENDPOINT=https://s3.example.com
BACKUP_S3_BUCKET=iam-backups
BACKUP_S3_ACCESS_KEY=...
BACKUP_S3_SECRET_KEY=...
BACKUP_S3_PREFIX=iam/
```

Remote retention mirrors `BACKUP_RETENTION_COUNT`.

## Manage

```bash
docker compose --profile backup run --rm database-backup --now          # snapshot now
docker compose --profile backup run --rm database-backup cli list
docker compose --profile backup run --rm database-backup cli verify <id>  # sha256 vs manifest
docker compose --profile backup run --rm database-backup cli prune
```

## Restore (disaster recovery)

> **Stop Zitadel first** — the sidecar does not stop services.

```bash
docker compose -f docker-compose.traefik.yml stop zitadel
docker compose --profile backup run --rm database-backup cli restore <id>
docker compose -f docker-compose.traefik.yml up -d zitadel
```

The archive is `pg_dump --format=custom`. The source type `zitadel-postgres`
(an engine plugin in `src/database-backup`) restores it in **one** transaction:
it drops the live partitioned tables the dump recreates (Zitadel keeps its
caches in such tables), then runs the dump's `pg_restore --clean --if-exists`
script. The engine's plain `pg_restore --clean` cannot restore over partitioned
tables — see
[src/database-backup/README.md](../src/database-backup/README.md). Any error
rolls the whole restore back. The Zitadel **masterkey must be unchanged** (it
decrypts secrets at rest) — keep `ZITADEL_MASTERKEY` backed up separately from
the DB dump.

## Alerts

Set `BACKUP_ALERT_ENABLED=true`, `BACKUP_ALERT_CHANNELS=email,teams` and the
corresponding SMTP / `BACKUP_TEAMS_WEBHOOK` values.
