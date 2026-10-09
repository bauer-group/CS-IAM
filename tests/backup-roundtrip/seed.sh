#!/usr/bin/env bash
# =============================================================================
# CS-IAM backup round trip - seed
# =============================================================================
# Writes the run's marker into every source the database-backup sidecar backs
# up. Into the Zitadel database (component "zitadel"), twice:
#   * through Zitadel: a human user whose id and username are the marker, created
#     via the API - it lands in Zitadel's event store and projections
#   * directly: a row in the dedicated schema backup_roundtrip, which Zitadel
#     never touches
# Into the machinekey and tfstate volumes (components of the same names): a
# marker file in each, see volumes.py.
# =============================================================================
set -euo pipefail
# shellcheck source=tests/backup-roundtrip/common.sh
source "$(dirname "$0")/common.sh"

iam_sql <<'SQL'
CREATE SCHEMA IF NOT EXISTS backup_roundtrip;
CREATE TABLE IF NOT EXISTS backup_roundtrip.marker (
  marker     text PRIMARY KEY,
  created_at timestamptz NOT NULL DEFAULT now()
);
INSERT INTO backup_roundtrip.marker (marker) VALUES (:'marker');
SQL
echo "seeded marker row for $ROUNDTRIP_MARKER"

zitadel_user create

backup_volumes seed
