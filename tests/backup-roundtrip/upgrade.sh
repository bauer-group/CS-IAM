#!/usr/bin/env bash
# =============================================================================
# CS-IAM backup round trip - upgrade the sidecar, then mutate
# =============================================================================
# The mutate script of the round trip with a snapshot of the zitadel-postgres
# source (legacy-snapshot.yml). The module has just taken that snapshot with a
# release that backed up the database through the plugin. Before mutate.sh
# deletes the seeded data, this script upgrades the database-backup sidecar the
# way an operator does: the image built from this commit and the source type of
# the compose files go into the .env, then `up -d` recreates the sidecar. The
# module's restore then reads the old snapshot with the new sidecar.
#
# It fails when the snapshot's database component is not of the old kind, or
# when the recreated sidecar does not run the new image and source type - the
# round trip would prove nothing about old snapshots then.
# =============================================================================
set -euo pipefail
# shellcheck source=tests/backup-roundtrip/common.sh
source "$(dirname "$0")/common.sh"
: "${ROUNDTRIP_SNAPSHOT_ID:?set by the round-trip module after the backup}"

SERVICE="${ROUNDTRIP_BACKUP_SERVICE:-database-backup}"
# A local tag only: no registry has it, so nothing can pull over the build.
UPGRADE_VERSION=roundtrip-upgrade

bh() { docker compose exec -T "$SERVICE" backuphelper "$@"; }

# Replaces KEY=... in the .env (the module wrote the key from env-overrides).
set_env() {
  grep -q "^$1=" .env || { echo "FAIL $1 is not in the .env"; exit 1; }
  sed -i "s|^$1=.*|$1=$2|" .env
}

# -- the snapshot: the database as the old source wrote it -------------------
KIND=$(bh show "$ROUNDTRIP_SNAPSHOT_ID" | jq -r '.components[] | select(.name == "zitadel") | .kind')
if [ "$KIND" != "zitadel-postgres" ]; then
  echo "FAIL snapshot $ROUNDTRIP_SNAPSHOT_ID: component zitadel is of kind '${KIND}', expected zitadel-postgres"
  exit 1
fi
echo "ok   snapshot $ROUNDTRIP_SNAPSHOT_ID: component zitadel is of kind zitadel-postgres"

# -- upgrade -----------------------------------------------------------------
# The database source type the compose files ship, from the development file
# alone (without legacy-snapshot.yml).
SHIPPED_TYPE=$(COMPOSE_FILE=docker-compose.development.yml docker compose config --format json \
  | jq -r --arg s "$SERVICE" '.services[$s].environment.BACKUP_CONFIG_JSON | fromjson | .jobs[0].sources[0].type')
set_env DATABASE_BACKUP_VERSION "$UPGRADE_VERSION"
set_env ROUNDTRIP_SOURCE_TYPE "$SHIPPED_TYPE"
IMAGE=$(docker compose config --format json | jq -r --arg s "$SERVICE" '.services[$s].image')

echo "::group::Build $IMAGE from src/database-backup"
docker build --pull --tag "$IMAGE" src/database-backup
echo "::endgroup::"
docker compose up -d --no-deps --wait --wait-timeout "${WAIT_TIMEOUT:-300}" "$SERVICE"

# -- the sidecar: new image, shipped source type ------------------------------
RUNNING=$(docker inspect --format '{{.Config.Image}}' "$(docker compose ps -q "$SERVICE")")
TYPE=$(bh config | jq -r '.jobs[0].sources[0].type')
if [ "$RUNNING" != "$IMAGE" ] || [ "$TYPE" != "$SHIPPED_TYPE" ]; then
  echo "FAIL $SERVICE runs $RUNNING with source type '$TYPE', expected $IMAGE with '$SHIPPED_TYPE'"
  exit 1
fi
echo "ok   $SERVICE upgraded: $IMAGE, database source type $TYPE"

bash "$(dirname "$0")/mutate.sh"
