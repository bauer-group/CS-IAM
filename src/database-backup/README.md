# database-backup

Thin meta-image `FROM ghcr.io/bauer-group/cs-backuphelper/backuphelper` — the
central BackupHelper engine. All backup logic (pg_dump, retention, manifest,
S3 off-site, notifications, restore CLI) lives there; this image only pins the
version and adds the IAM/Zitadel OCI labels.

It backs up the Zitadel **PostgreSQL** database. There is no separate source —
Zitadel keeps all state in Postgres, so a DB dump is a complete snapshot.

## Configuration

Everything is driven by the `database-backup` service in the compose files via
`BACKUP_CONFIG_JSON` (plus the `DB_PASSWORD` / `BACKUP_S3_SECRET_KEY` /
`SMTP_PASSWORD` / `WEBHOOK_SECRET` secrets, resolved inside the container).

See the BackupHelper docs:
https://github.com/bauer-group/CS-BackupHelper
