# Backup & Restore

The `database-backup` sidecar writes one snapshot per run. It holds three
components, restored together as one point in time:

| Component | What | Why it is needed |
|-----------|------|------------------|
| `zitadel` | the Zitadel PostgreSQL database (`pg_dump`) | all of Zitadel's own state |
| `machinekey` | the `machinekey` volume: the FirstInstance machine key `iam-admin.json`, the PAT `iam-admin.pat` and, in development, `login-client.pat` | Zitadel writes these files only once, when it sets up a new instance. A restored database never writes them again, and without them the provisioner, `directory-sync`, the branding job and the login cannot authenticate. |
| `tfstate` | the `tfstate` volume: the provisioner's OpenTofu state | without it the provisioner treats every resource as new, although the restored database already holds them. It is also the only copy of the generated OIDC client secrets (`tofu output app_client_secrets`). |

There is no S3 source in this stack. Not backed up: `sync-data` (the delta
tokens of `directory-sync`, which starts with a full sync without them) and, in
development, `certs` (the self-signed certificate, generated again).

> **The snapshot holds credentials in plain text**: the machine key of the
> `IAM_OWNER` automation user, its PAT, and the OpenTofu state with the OIDC
> and identity-provider client secrets. Keep the backup volume and the off-site
> bucket as private as the host. `BACKUP_INCLUDE_MACHINEKEY=false` or
> `BACKUP_INCLUDE_TFSTATE=false` leaves a component out of new snapshots - a
> restore onto a new host then needs those files from somewhere else.

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

The sidecar's entrypoint is the engine CLI `backuphelper`, so the subcommand
follows the service name directly. Use the compose file of your deployment
(`docker-compose.traefik.yml`, `docker-compose.coolify.yml`, or
`docker-compose.development.yml`):

```bash
docker compose -f docker-compose.traefik.yml --profile backup run --rm database-backup --now        # snapshot now
docker compose -f docker-compose.traefik.yml --profile backup run --rm database-backup list
docker compose -f docker-compose.traefik.yml --profile backup run --rm database-backup verify <id>  # sha256 vs manifest
docker compose -f docker-compose.traefik.yml --profile backup run --rm database-backup prune
```

## Restore on the same host

> **Stop Zitadel first** — the sidecar does not stop services.

```bash
docker compose -f docker-compose.traefik.yml stop zitadel
docker compose -f docker-compose.traefik.yml --profile backup run --rm database-backup restore <id>
docker compose -f docker-compose.traefik.yml up -d
```

`restore` asks for confirmation; add `--force` where no terminal is attached
(scripts, CI). It writes back all components of the snapshot: the database, the
machine key files and the OpenTofu state, so state and database match again.
`up -d` starts Zitadel and runs the provisioner and the branding job once more
against them. `--only zitadel` restores the database alone; the OpenTofu state
then stays newer than the database, so restore all components unless you have
a reason not to.

Snapshots taken before the `machinekey` and `tfstate` components existed hold
only `zitadel`; restoring one leaves both volumes as they are.

## Restore onto a new host (disaster recovery)

What the new host needs before it starts anything:

- this repository's compose file and the **same `.env`** — above all
  `ZITADEL_MASTERKEY` (it decrypts the secrets in the database) and
  `IAM_HOSTNAME`, which the restored instance answers to; DNS for
  `IAM_HOSTNAME` points to the new host,
- the snapshot: with the `BACKUP_S3_*` settings of the old host, `list` shows
  the off-site snapshots and `restore` downloads the one you name. Without an
  off-site copy, put `<id>.tar.gz` and `<id>.manifest.json` into the sidecar's
  `/data` first (`docker compose ... --profile backup up -d database-backup`,
  then `docker compose ... cp <dir>/. database-backup:/data/`).

```bash
docker compose -f docker-compose.traefik.yml --profile backup run --rm database-backup list
docker compose -f docker-compose.traefik.yml --profile backup run --rm database-backup restore <id>
docker compose -f docker-compose.traefik.yml up -d
docker compose -f docker-compose.traefik.yml --profile backup up -d database-backup
```

The `database-backup` commands start only PostgreSQL and the one-shot
`prepare-machinekey`, which hands the `machinekey` and `tfstate` volumes to the
sidecar's user (uid 1000) - **not Zitadel**. Do not start the stack before the
restore: on an empty database Zitadel sets up a new instance with new keys. If
that already happened, restore as on the same host (stop `zitadel` first); the
restore replaces the new instance's database, keys and state.

After `up -d`, the provisioner log ends with `no changes` or an additive apply
(`docker compose -f docker-compose.traefik.yml logs provisioner`), and
`scripts/validate-stack.py` (see [Operations](operations.md#validate-the-deployment))
checks the restored instance.

## How the database is restored

The archive is `pg_dump --format=custom`, written by the BackupHelper engine's
`postgres` source. Zitadel keeps its caches in partitioned tables, and a plain
`pg_restore --clean` cannot restore over them. Since BackupHelper 1.9.0 the
source therefore restores in **one** transaction: it drops the live partitioned
tables the dump recreates, then runs the dump's `pg_restore --clean --if-exists`
script. Any error rolls the whole restore back. On this path the sidecar first
writes the database as uncompressed SQL to its `/tmp`, which needs room for the
extracted snapshot plus the uncompressed database - see the engine's
[sources documentation](https://github.com/bauer-group/CS-BackupHelper/blob/main/docs/sources.md#postgres).
The Zitadel **masterkey must be unchanged** (it decrypts secrets at rest) — keep
`ZITADEL_MASTERKEY` backed up separately from the DB dump.

### Snapshots of the `zitadel-postgres` source (0.17.29 to 0.17.31)

CS-IAM 0.17.29 to 0.17.31 backed up the database with `zitadel-postgres`, a
source plugin of the `database-backup` image that restored over partitioned
tables before the engine could. Their snapshots record the
database component's kind as `zitadel-postgres` (`show <id>`), newer ones as
`postgres`. Both restore with the current compose files: the engine picks the
source for a component by its name (`zitadel`), not by its kind. Every release
proves it with a snapshot of 0.17.29 (see
[the release gate](#release-gate-backup-round-trip-in-ci)).

`zitadel-postgres` remains a valid source type of the image, as an alias of the
engine's `postgres` source, so a compose file that still names it keeps backing
up and restoring. Update the compose file and the image together all the same:
a compose file with `postgres` and a `database-backup` image older than 0.17.31
(built before BackupHelper 1.9.0) backs up, but its restore rolls back
(`cannot drop inherited constraint`).

## Alerts

Alerts go to the channels listed in `BACKUP_ALERT_CHANNELS` (comma-separated,
e.g. `email,teams`; empty = no alerts), filtered by `BACKUP_ALERT_LEVEL`. Fill in
the matching SMTP / `BACKUP_ALERT_EMAIL` / `BACKUP_TEAMS_WEBHOOK` /
`BACKUP_WEBHOOK_URL` values. The channel list alone decides; there is no
separate on/off switch.

## Health

The `database-backup` container's healthcheck (`backuphelper healthcheck`, from
the BackupHelper engine) reports whether backups work. Since BackupHelper 1.7.7
the container is unhealthy when

- the backup volume (`/data`) is not writable by the sidecar,
- the most recent backup ended in `error` (e.g. `pg_dump` failed) or its snapshot
  has a failed component, until a newer backup ends in `success` or `warning`,
- the most recent backup started more than 26 hours ago, or
- no backup has run yet and the sidecar started more than 26 hours ago.

The check prints the reason:

```bash
docker compose -f docker-compose.traefik.yml --profile backup exec database-backup backuphelper healthcheck
# healthy: the last backup is fresh: snapshot 2026-07-05_03-15-00 (job main) ran 7.2 h ago
```

A run with a failed component ends `--now` with exit 1 and alerts at every
`BACKUP_ALERT_LEVEL`. Up to 1.7.6 the healthcheck only looked at the age of the
newest snapshot, so a deployment whose newest snapshot already has a failed
component turns unhealthy right after the upgrade, until a complete snapshot
exists.

The 26 hours are the image default of `BACKUP_HEALTHCHECK_MAX_AGE_HOURS`, which
the compose files do not pass through. With a `BACKUP_SCHEDULE_CRON` that runs
less often than daily, the container is unhealthy from 26 hours after each run
until the next one. The full rules are in the BackupHelper
[deployment guide](https://github.com/bauer-group/CS-BackupHelper/blob/main/docs/deployment.md#the-functional-healthcheck).

## Release gate: backup round trip in CI

Every release is gated on real backups and restores of this stack. Three jobs
in [docker-release.yml](../.github/workflows/docker-release.yml) call the
reusable
[`modules-backup-roundtrip-test.yml`](https://github.com/bauer-group/automation-templates/blob/main/docs/workflows/modules-backup-roundtrip-test.md)
and run before the release job, which needs all of them to pass. They also run
when the base-image monitor dispatches a release after a new Zitadel, login,
PostgreSQL or BackupHelper image, so a base-image update ships only after it
restored Zitadel data.

The first job, `🧪 Backup Round Trip`, is a fresh installation:

| Phase | What happens |
|-------|--------------|
| Build | `zitadel`, `login`, `provisioner`, `directory-sync` and `database-backup` are built from the commit, with fresh base images |
| Start | `docker-compose.development.yml` with the `backup` profile, a `.env` from `scripts/generate-env.py`, CI-sized PostgreSQL memory |
| Seed | A human user created through the Zitadel API (id and username = the run's marker), a row in the dedicated schema `backup_roundtrip`, and a marker file in the `machinekey` and `tfstate` volumes |
| Back up | `create`, then `show` must list `zitadel`, `machinekey` and `tfstate` without errors or warnings, `verify` must report `OK` |
| Delete | The user through the API, the marker row, both marker files and `iam-admin.pat`; `terraform.tfstate` is overwritten in place |
| Restore | `zitadel` is stopped, `restore <id> --force` runs, the stack is started again — the provisioner and the branding job run again against the restored database and state |
| Check | The marker row is back, Zitadel returns the user with its seeded email through the API, the marker files are back, `iam-admin.pat` has its old checksum and `terraform.tfstate` its old lineage |

The scripts live in [`tests/backup-roundtrip/`](../tests/backup-roundtrip/); the
volume checks run as the sidecar's own user, the one that writes the files back.
The check runs three times — before the backup (data present), after the deletion
(data absent) and after the restore (data present) — so a restore that writes
nothing cannot pass.

The second job, `🧪 Backup Round Trip (legacy snapshot)`, restores a snapshot
of the old `zitadel-postgres` source with the current image and configuration.
It runs the same phases with an upgrade between the backup and the deletion:

- **Back up:** `database-backup` starts as the image of 0.17.29 - the first
  release with the plugin, on BackupHelper 1.7.6 - with the source type
  `zitadel-postgres`
  ([`legacy-snapshot.yml`](../tests/backup-roundtrip/legacy-snapshot.yml)), so
  `create` writes a snapshot of that release. The other four images are the
  commit's builds from the start.
- **Upgrade:** [`upgrade.sh`](../tests/backup-roundtrip/upgrade.sh) fails unless
  the snapshot's database component is of kind `zitadel-postgres`. Then the
  module upgrades the sidecar the way an operator does: the image built from the
  commit, `docker-compose.development.yml` without `legacy-snapshot.yml` (the
  source type the compose files ship), `up -d`. It fails unless the recreated
  sidecar runs the build of the commit. The data must still be there and the
  new sidecar's healthcheck must pass.
- **Restore:** the upgraded sidecar restores the old snapshot.

The third job, `🧪 Backup Round Trip (upgrade, S3, <variant>)`, is the way
production gets to a release, once per compose file operators run:
`development`, `traefik` and `coolify`.

- **Start:** all five images start as the latest release (`vX.Y.Z` → image tag
  `X.Y.Z`). The snapshot also goes to an S3 bucket, a throwaway MinIO the module
  starts, through the `BACKUP_S3_*` settings; the archive must arrive there with
  its local size.
- **Upgrade:** the stack switches to the images built from the commit,
  `up -d` recreates every container whose image changed — the provisioner and
  the branding job run again. The data must still be there, and the new
  sidecar must be healthy with the previous release's snapshot and run records.
- **New host:** after the deletion the sidecar's container is removed and its
  data volume emptied; the new sidecar must list the snapshot as off-site only.
- **Restore:** the new sidecar downloads the old snapshot from S3 and restores
  it; afterwards it is local again and passes `verify`.

The Traefik and Coolify files reach Zitadel through the host's proxy at
`https://${IAM_HOSTNAME}`, which a runner does not have.
[`proxy-standin.yml`](../tests/backup-roundtrip/proxy-standin.yml) adds a
Traefik with a self-signed certificate for `IAM_HOSTNAME` that routes by the
variant's own labels; the provisioner, `directory-sync` and the branding job
trust that certificate, as in development. The proxy network the variant
declares external is created for the run.

A run takes a few minutes on a GitHub-hosted runner: building the five images,
the first start with Zitadel's setup and the provisioning (twice in the
upgrade jobs), the backup, the restore with another provisioning run, and the
checks through the Zitadel API. All jobs and legs run in parallel.

The round trip starts on pushes to `main` (except pushes that only change
documentation or `.github/`), on every `workflow_dispatch`, and on pull requests
that touch `src/`, `terraform/`, `config/`, a compose file, `.env.example`,
`scripts/generate-env.py`, the round-trip scripts or the release workflow. When
it fails, the run's summary names the failed phase, and the diagnostics
artifact of the job - `backup-roundtrip-diagnostics`,
`backup-roundtrip-legacy-diagnostics` or
`backup-roundtrip-upgrade-<variant>-diagnostics` - holds every service's log,
`docker compose ps`, the snapshot list and the manifest.

Right after a release, its image jobs push the version tags a minute or two
after the GitHub release exists. An upgrade job that starts in that window, or
after an image job of the latest release failed, fails at *Pull previous
release*: re-run it once the images are published.

Not covered by the gate:

- **Real S3 providers** — the off-site copy is tested against MinIO over plain
  HTTP; AWS addressing, R2 or B2 specifics and TLS are not.
- **The real proxy** — the stand-in Traefik routes by the variants' labels, but
  Let's Encrypt (the Traefik file's `certresolver`), Coolify's own proxy
  configuration and the HTTP to HTTPS redirect are not exercised.
- **A completely new host** — the upgrade jobs restore with an emptied backup
  volume, but into the running stack's database and volumes. A new host starts
  from empty volumes and an empty database, following the procedure above.
- **Upgrades across several releases** — the upgrade jobs start from the latest
  release only.
- **Snapshots of 0.17.30 and 0.17.31** — the legacy job restores one of 0.17.29.
  0.17.30 has the same plugin on the same engine, 0.17.31 the same plugin on
  BackupHelper 1.10.0, the engine that restores.
