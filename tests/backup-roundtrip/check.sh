#!/usr/bin/env bash
# =============================================================================
# CS-IAM backup round trip - check
# =============================================================================
# Exits 0 when the seeded data is in the state ROUNDTRIP_EXPECT names:
#   present  the marker row in backup_roundtrip.marker, Zitadel returns the
#            marker user with its seeded email through the API, and the
#            machinekey and tfstate volumes hold their seeded files
#   absent   no marker row, Zitadel answers NOT_FOUND for the user, and the
#            seeded files are gone from both volumes
# Each item is checked on its own, so "absent" proves the mutation removed all
# of them and "present" proves the restore brought all of them back - the API
# answer also proves that Zitadel runs on the restored database.
# =============================================================================
set -euo pipefail
# shellcheck source=tests/backup-roundtrip/common.sh
source "$(dirname "$0")/common.sh"

case "${ROUNDTRIP_EXPECT:?set by the round-trip module}" in
  present) WANT=1 ;;
  absent)  WANT=0 ;;
  *) echo "unknown ROUNDTRIP_EXPECT '$ROUNDTRIP_EXPECT'" >&2; exit 2 ;;
esac
FAILED=0

# -- database row ------------------------------------------------------------
# A failing query ends the script here (set -e) - an error is never read as
# "absent".
ROWS=$(iam_sql <<'SQL'
SELECT count(*) FROM backup_roundtrip.marker WHERE marker = :'marker';
SQL
)
if [ "$ROWS" = "$WANT" ]; then
  echo "ok   marker row: $ROWS (expected $WANT)"
else
  echo "FAIL marker row: ${ROWS:-?} (expected $WANT)"; FAILED=1
fi

# -- Zitadel user, through the API -----------------------------------------
zitadel_user "$ROUNDTRIP_EXPECT" || FAILED=1

# -- machinekey and tfstate volumes ------------------------------------------
backup_volumes "$ROUNDTRIP_EXPECT" || FAILED=1

exit "$FAILED"
