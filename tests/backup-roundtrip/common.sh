#!/usr/bin/env bash
# =============================================================================
# CS-IAM backup round trip - shared helpers (sourced, not executed)
# =============================================================================
# Used by seed.sh, mutate.sh and check.sh, which the automation-templates module
# modules-backup-roundtrip-test.yml runs against the started development stack.
# The module exports COMPOSE_FILE, COMPOSE_PROJECT_NAME and COMPOSE_PROFILES, so
# a plain `docker compose` reaches this stack, plus ROUNDTRIP_MARKER - a unique
# token ([a-z0-9-]) per run that tags everything the scripts write.
# =============================================================================

: "${ROUNDTRIP_MARKER:?set by the round-trip module}"

ROUNDTRIP_SCRIPTS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Runs SQL from stdin against the Zitadel database, with the credentials the
# database-server container already has. :'marker' is a psql variable, so psql
# quotes the value - the marker is never pasted into the SQL.
iam_sql() {
  docker compose exec -T database-server sh -c \
    'exec psql -tA -q -v ON_ERROR_STOP=1 -v marker="$1" -U "$POSTGRES_USER" -d "$POSTGRES_DB"' \
    _ "$ROUNDTRIP_MARKER"
}

# Runs zitadel-user.py through the Zitadel API, inside directory-sync: that
# container holds the FirstInstance machine key and the Zitadel client the stack
# itself uses, and it keeps running while zitadel is stopped for the restore.
# $1 = create | delete | present | absent
zitadel_user() {
  docker compose exec -T -e ROUNDTRIP_MARKER="$ROUNDTRIP_MARKER" directory-sync \
    python - "$1" < "$ROUNDTRIP_SCRIPTS/zitadel-user.py"
}

# Runs volumes.py inside the backup sidecar, which mounts the machinekey and
# tfstate volumes as the user that backs them up and restores them (uid 1000).
# $1 = seed | mutate | present | absent
backup_volumes() {
  docker compose exec -T -e ROUNDTRIP_MARKER="$ROUNDTRIP_MARKER" \
    "${ROUNDTRIP_BACKUP_SERVICE:-database-backup}" \
    python - "$1" < "$ROUNDTRIP_SCRIPTS/volumes.py"
}
