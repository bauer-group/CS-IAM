#!/usr/bin/env bash
# =============================================================================
# CS-IAM backup round trip - upgrade script of the legacy snapshot round trip
# =============================================================================
# The module runs it after the 0.17.29 sidecar took the snapshot and before it
# upgrades the stack: the image built from this commit, and
# docker-compose.development.yml without legacy-snapshot.yml - the source type
# the compose files ship. The restore then reads this snapshot with the new
# sidecar.
#
# It fails when the snapshot's database component is not of the old kind
# zitadel-postgres: the round trip would prove nothing about old snapshots
# then. That the new sidecar runs the build of this commit, the module checks
# itself after the upgrade.
# =============================================================================
set -euo pipefail
: "${ROUNDTRIP_SNAPSHOT_ID:?set by the round-trip module after the backup}"

SERVICE="${ROUNDTRIP_BACKUP_SERVICE:-database-backup}"

KIND=$(docker compose exec -T "$SERVICE" backuphelper show "$ROUNDTRIP_SNAPSHOT_ID" \
  | jq -r '.components[] | select(.name == "zitadel") | .kind')
if [ "$KIND" != "zitadel-postgres" ]; then
  echo "FAIL snapshot $ROUNDTRIP_SNAPSHOT_ID: component zitadel is of kind '${KIND}', expected zitadel-postgres"
  exit 1
fi
echo "ok   snapshot $ROUNDTRIP_SNAPSHOT_ID: component zitadel is of kind zitadel-postgres"
