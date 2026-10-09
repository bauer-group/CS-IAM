# database-backup

Thin meta-image `FROM ghcr.io/bauer-group/cs-backuphelper/backuphelper` — the
central BackupHelper engine. All backup logic (pg_dump, retention, manifest,
S3 off-site, notifications, restore CLI) lives there; this image pins the
version, adds the IAM/Zitadel OCI labels and one engine plugin.

It backs up the Zitadel **PostgreSQL** database (component `zitadel`) and, with
the engine's `filesystem` source, the two volumes a restore onto a new host
needs as well: `machinekey` (the FirstInstance machine key and PATs, which
Zitadel writes only once) and `tfstate` (the provisioner's OpenTofu state). See
[docs/backup-and-restore.md](../../docs/backup-and-restore.md).

## The `zitadel-postgres` source

`iam_backup/` is a BackupHelper Source plugin, registered under the type
`zitadel-postgres` and used by every compose file. Backups are the engine's
`postgres` source unchanged (`pg_dump --format=custom`).

The restore differs. Zitadel keeps its caches in partitioned tables (schema
`cache`), and the engine's `pg_restore --clean --if-exists` cannot restore over
them: the clean phase drops each partition's primary key on its own, which
PostgreSQL refuses (`cannot drop inherited constraint`). The restore aborted in
its single transaction — nothing damaged, nothing restored.

`zitadel-postgres` restores in **one** `psql --single-transaction` run: first
`DROP TABLE … CASCADE` for every live partitioned table the dump contains, then
the dump's own clean-and-create script (`pg_restore --clean --if-exists` written
to a file). Any error rolls everything back. With no partitioned tables in the
live database it runs the engine's restore unchanged.

The plugin's tests (`tests/`) run in the image build, against the engine the
image is built on; the end-to-end proof is the backup round trip that gates
every release (see [docs/backup-and-restore.md](../../docs/backup-and-restore.md)).

## Configuration

Everything is driven by the `database-backup` service in the compose files via
`BACKUP_CONFIG_JSON` (plus the `DB_PASSWORD` / `BACKUP_S3_SECRET_KEY` /
`SMTP_PASSWORD` / `WEBHOOK_SECRET` secrets, resolved inside the container). The
service mounts the `machinekey` and `tfstate` volumes read-write at
`/machinekey` and `/tfstate`, so `restore` can write them back.

See the BackupHelper docs:
<https://github.com/bauer-group/CS-BackupHelper>
