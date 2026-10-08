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

## Release gate: backup round trip in CI

Every release is gated on a real backup and restore of this stack. The job
`🧪 Backup Round Trip` in [docker-release.yml](../.github/workflows/docker-release.yml)
calls the reusable
[`modules-backup-roundtrip-test.yml`](https://github.com/bauer-group/automation-templates/blob/main/docs/workflows/modules-backup-roundtrip-test.md)
and runs before the release job, which needs it to pass. It also runs when the
base-image monitor dispatches a release after a new Zitadel, login, PostgreSQL or
BackupHelper image, so a base-image update ships only after it restored Zitadel
data.

| Phase | What happens |
|-------|--------------|
| Build | `zitadel`, `login`, `provisioner`, `directory-sync` and `database-backup` are built from the commit, with fresh base images |
| Start | `docker-compose.development.yml` with the `backup` profile, a `.env` from `scripts/generate-env.py`, CI-sized PostgreSQL memory |
| Seed | A human user created through the Zitadel API (id and username = the run's marker) and a row in the dedicated schema `backup_roundtrip` |
| Back up | `create`, then `show` must list `zitadel` without errors or warnings, `verify` must report `OK` |
| Delete | The user through the API, and the marker row |
| Restore | `zitadel` is stopped, `restore <id> --force` runs, the stack is started again — the provisioner and the branding job run again against the restored database |
| Check | The marker row is back, and Zitadel returns the user with its seeded email through the API |

The scripts live in [`tests/backup-roundtrip/`](../tests/backup-roundtrip/). The
check runs three times — before the backup (data present), after the deletion
(data absent) and after the restore (data present) — so a restore that writes
nothing cannot pass.

A run takes about two minutes on a GitHub-hosted runner: building the five
images, the first start with Zitadel's setup and the provisioning, the backup,
the restore with a second provisioning run, and the checks through the Zitadel
API.

The round trip starts on pushes to `main` (except pushes that only change
documentation or `.github/`), on every `workflow_dispatch`, and on pull requests
that touch `src/`, `terraform/`, `config/`, a compose file, `.env.example`,
`scripts/generate-env.py`, the round-trip scripts or the release workflow. When
it fails, the run's summary names the failed phase, and the
`backup-roundtrip-diagnostics` artifact holds every service's log,
`docker compose ps`, the snapshot list and the manifest.

Not covered by the gate:

- **Off-site S3** — the bucket is empty in CI, so the `s3` destination is skipped.
- **`docker-compose.traefik.yml` / `docker-compose.coolify.yml`** — their
  `database-backup` service is identical to the development one; the rest of
  those stacks is not started.
- **A restore onto a new host** — the `machinekey` and `tfstate` volumes stay in
  place during the test; the sidecar does not back them up.
