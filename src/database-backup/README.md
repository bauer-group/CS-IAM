# database-backup

Thin meta-image `FROM ghcr.io/bauer-group/cs-backuphelper/backuphelper` — the
central BackupHelper engine. All backup logic (pg_dump, retention, manifest,
S3 off-site, notifications, restore CLI) lives there; this image adds the
IAM/Zitadel OCI labels and one source alias.

It backs up the Zitadel **PostgreSQL** database (component `zitadel`) and, with
the engine's `filesystem` source, the two volumes a restore onto a new host
needs as well: `machinekey` (the FirstInstance machine key and PATs, which
Zitadel writes only once) and `tfstate` (the provisioner's OpenTofu state). See
[docs/backup-and-restore.md](../../docs/backup-and-restore.md).

## The Zitadel database: the engine's `postgres` source

The compose files back up the database with the engine's built-in `postgres`
source (`pg_dump --format=custom`). A plain `pg_restore --clean` cannot restore
over a database Zitadel has set up. Zitadel keeps its caches in partitioned
tables (schema `cache`): the clean phase drops each partition's primary key on
its own, which PostgreSQL refuses (`cannot drop inherited constraint`). And
after an upgrade, what the newer Zitadel added and the snapshot lacks blocks
the clean phase or stays behind. The engine therefore restores over such a
database in **one** transaction: `DROP … CASCADE` for the relations of the
snapshot's schemas and the functions and types the snapshot lacks,
`DROP SCHEMA … CASCADE` for the schemas the dump creates - all of Zitadel's -
then the dump's own clean-and-create script. Any error rolls everything back.
BackupHelper 1.9.0 to 1.10.1 dropped only the partitioned tables, so restoring
a snapshot from before a Zitadel upgrade rolled back. See the engine's
[sources documentation](https://github.com/bauer-group/CS-BackupHelper/blob/main/docs/sources.md#postgres).

Before BackupHelper 1.9.0 the engine could not restore over the partitioned
tables at all, and CS-IAM 0.17.29 to 0.17.31 configured a Source plugin of this
image instead, `zitadel-postgres`, with such a restore. Their snapshots record
the database component as kind `zitadel-postgres`; they restore with the
`postgres` source, because the engine picks the source for a component by its
name (`zitadel`), not by its kind.

`zitadel-postgres` stays registered (`pyproject.toml`) as an alias of the
engine's `postgres` source - an entry point, no code of its own - so a compose
file that still names it keeps backing up and restoring. The tests in `tests/`
run in the image build against the engine the image is built on: they fail it
when the alias is missing or the engine has no partitioned-table restore. The
end-to-end proof is the backup round trip that gates every release (see
[docs/backup-and-restore.md](../../docs/backup-and-restore.md)).

## Configuration

Everything is driven by the `database-backup` service in the compose files via
`BACKUP_CONFIG_JSON` (plus the `DB_PASSWORD` / `BACKUP_S3_SECRET_KEY` /
`SMTP_PASSWORD` / `WEBHOOK_SECRET` secrets, resolved inside the container). The
service mounts the `machinekey` and `tfstate` volumes read-write at
`/machinekey` and `/tfstate`, so `restore` can write them back.

See the BackupHelper docs:
<https://github.com/bauer-group/CS-BackupHelper>
