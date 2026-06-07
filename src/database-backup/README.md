# database-backup

PostgreSQL snapshot sidecar for the Zitadel stack. Dumps the `zitadel` database
with `pg_dump`, bundles it into a deterministic `tar.gz` + `manifest.json`
(with sha256), applies retention, and optionally uploads off-site to any
S3-compatible target. Cron- or interval-scheduled; alerts via email / webhook /
Microsoft Teams.

> There is **no S3 source** in this stack (unlike `outline-backup`) — Zitadel
> keeps everything in Postgres, so a DB dump is a complete snapshot.

## Run

```bash
# enable the sidecar (scheduler):
docker compose -f docker-compose.traefik.yml --profile backup up -d database-backup

# one-off + management:
docker compose --profile backup run --rm database-backup --now
docker compose --profile backup run --rm database-backup cli list
docker compose --profile backup run --rm database-backup cli verify <id>
docker compose --profile backup run --rm database-backup cli restore <id>   # stop Zitadel first
docker compose --profile backup run --rm database-backup cli prune
```

## Off-site target (optional)

Set `BACKUP_S3_*` to mirror snapshots to AWS S3 / Cloudflare R2 / Backblaze B2 /
a second MinIO. Leave blank for local-only backups on the `backup` volume.

## Restore

`cli restore <id>` extracts the archive and runs `pg_restore`/`psql`. **Stop the
Zitadel container first** — the sidecar does not stop services.
