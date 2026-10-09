#!/usr/bin/env bash
# =============================================================================
# CS-IAM backup round trip - mutate
# =============================================================================
# Deletes what seed.sh wrote: the Zitadel user through the API, the way an
# admin removes it, and the marker row. In the volumes it deletes the marker
# files and the FirstInstance PAT and damages the OpenTofu state (volumes.py).
# The restore has to bring back all of it.
# =============================================================================
set -euo pipefail
# shellcheck source=tests/backup-roundtrip/common.sh
source "$(dirname "$0")/common.sh"

zitadel_user delete

DELETED=$(iam_sql <<'SQL'
DELETE FROM backup_roundtrip.marker WHERE marker = :'marker' RETURNING marker;
SQL
)
[ "$DELETED" = "$ROUNDTRIP_MARKER" ] || { echo "marker row was not deleted: '${DELETED}'"; exit 1; }
echo "deleted marker row for $ROUNDTRIP_MARKER"

backup_volumes mutate
