"""
CS-IAM backup round trip - the machinekey and tfstate volumes.

Runs inside the database-backup sidecar (fed on stdin by common.sh), which
mounts both volumes as the backup user (uid 1000) - the user that backs them up
and writes them back on a restore:

  seed     write a marker file into each volume. It holds a fingerprint of the
           real file the mutation removes or damages:
             /machinekey  the sha256 of iam-admin.pat (the FirstInstance PAT)
             /tfstate     the lineage of terraform.tfstate (the identity of the
                          OpenTofu state - a new state gets a new lineage)
  mutate   delete both marker files and iam-admin.pat, and overwrite
           terraform.tfstate in place - the restore has to overwrite it too
  present  each marker file is there and its file matches the fingerprint
  absent   no marker file, no iam-admin.pat, no lineage in terraform.tfstate

The provisioner runs again after the restore. Even when it applies changes it
keeps the lineage, so the tfstate check still passes; a state it had to create
from scratch has another lineage and fails the check. A file that cannot be
read is an error, never "absent".
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

MARKER = os.environ["ROUNDTRIP_MARKER"]
MACHINEKEY = Path("/machinekey")
TFSTATE = Path("/tfstate")
PAT = MACHINEKEY / "iam-admin.pat"
STATE = TFSTATE / "terraform.tfstate"


def marker_file(volume: Path) -> Path:
    return volume / f"roundtrip-{MARKER}"


def read_marker(volume: Path) -> str | None:
    path = marker_file(volume)
    return path.read_text(encoding="utf-8").strip() if path.exists() else None


def pat_fingerprint() -> str | None:
    return hashlib.sha256(PAT.read_bytes()).hexdigest() if PAT.exists() else None


def state_lineage() -> str | None:
    if not STATE.exists():
        return None
    try:
        return json.loads(STATE.read_text(encoding="utf-8")).get("lineage") or None
    except ValueError:  # not JSON (any more) - no lineage
        return None


def observe(marker: str | None, current: str | None, what: str) -> str:
    """'present', 'absent', or a description of anything in between."""
    if marker is not None and current == marker:
        return "present"
    if marker is None and current is None:
        return "absent"
    marker_state = "missing" if marker is None else "present"
    if current is None:
        current_state = "missing"
    elif marker is None:
        current_state = "present"
    else:
        current_state = "differs from the marker"
    return f"marker file {marker_state}, {what} {current_state}"


def check(want: str) -> int:
    seen = {
        "machinekey": observe(read_marker(MACHINEKEY), pat_fingerprint(), "iam-admin.pat"),
        "tfstate": observe(read_marker(TFSTATE), state_lineage(), "terraform.tfstate lineage"),
    }
    failed = 0
    for volume, state in seen.items():
        if state == want:
            print(f"ok   {volume} volume: {want}")
        else:
            print(f"FAIL {volume} volume: {state} (expected {want})")
            failed = 1
    return failed


def seed() -> int:
    pat, lineage = pat_fingerprint(), state_lineage()
    if pat is None:
        print(f"FAIL seed: {PAT} does not exist - did Zitadel write the FirstInstance PAT?")
        return 1
    if lineage is None:
        print(f"FAIL seed: {STATE} has no lineage - did the provisioner run?")
        return 1
    marker_file(MACHINEKEY).write_text(pat + "\n", encoding="utf-8")
    marker_file(TFSTATE).write_text(lineage + "\n", encoding="utf-8")
    print(f"seeded marker files in {MACHINEKEY} and {TFSTATE} (state lineage {lineage})")
    return 0


def mutate() -> int:
    for path in (marker_file(MACHINEKEY), marker_file(TFSTATE), PAT):
        path.unlink()
    try:
        STATE.write_text('{"damaged_by": "backup round trip"}\n', encoding="utf-8")
    except PermissionError:
        print(f"FAIL mutate: {STATE} is not writable by uid {os.getuid()} - "
              "the restore cannot write it back either")
        return 1
    print(f"deleted the marker files and {PAT}, overwrote {STATE}")
    return 0


def main(action: str) -> int:
    if action == "seed":
        return seed()
    if action == "mutate":
        return mutate()
    if action in ("present", "absent"):
        return check(action)
    print(f"unknown action {action!r}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else ""))
