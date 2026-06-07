"""database-backup — CLI (argparse): create / list / verify / restore / prune."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import postgres  # noqa: E402
from archive import apply_local_retention, extract_archive, sha256sum  # noqa: E402
from config import Settings  # noqa: E402
from logging_setup import format_size, logger, setup_logging  # noqa: E402


def _settings() -> Settings:
    s = Settings()
    setup_logging(s.backup_log_level, s.backup_log_format)
    return s


def cmd_create(_args, s: Settings) -> int:
    from main import run_snapshot
    return 0 if run_snapshot(s) else 1


def cmd_list(_args, s: Settings) -> int:
    rows = []
    for a in sorted(Path(s.data_dir).glob("*.tar.gz"), reverse=True):
        rows.append((a.stem.replace(".tar", ""), "local", format_size(a.stat().st_size)))
    if s.target_configured():
        from s3_target import S3Target
        for snap in S3Target(s).list_snapshots():
            rows.append((snap.snapshot_id, "remote", format_size(snap.size)))
    if not rows:
        print("no snapshots found")
        return 0
    for sid, src, size in rows:
        print(f"{sid:24s} {src:7s} {size}")
    return 0


def cmd_verify(args, s: Settings) -> int:
    with tempfile.TemporaryDirectory() as td:
        archive = Path(s.data_dir) / f"{args.snapshot_id}.tar.gz"
        manifest = Path(s.data_dir) / f"{args.snapshot_id}.manifest.json"
        if not archive.exists():
            if not s.target_configured():
                print("snapshot not found locally and no remote target")
                return 1
            from s3_target import S3Target
            archive = Path(td) / "a.tar.gz"
            if not S3Target(s).download(args.snapshot_id, archive):
                return 1
        if not manifest.exists():
            print("local manifest missing — cannot verify sha256")
            return 1
        expected = json.loads(manifest.read_text()).get("archive_sha256")
        actual = sha256sum(archive)
        if expected and actual == expected:
            print(f"OK sha256 {actual[:16]}...")
            return 0
        print(f"MISMATCH expected={expected} actual={actual}")
        return 2


def cmd_restore(args, s: Settings) -> int:
    if not args.force:
        print("This OVERWRITES the Zitadel database. Stop Zitadel first.")
        if input("Proceed? [y/N] ").strip().lower() != "y":
            print("aborted")
            return 0
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        archive = Path(s.data_dir) / f"{args.snapshot_id}.tar.gz"
        if not archive.exists():
            if not s.target_configured():
                print("snapshot not found locally and no remote target")
                return 1
            from s3_target import S3Target
            archive = td_path / "a.tar.gz"
            if not S3Target(s).download(args.snapshot_id, archive):
                return 1
        extracted = extract_archive(archive, td_path / "x")
        dumps = list((extracted / "database").glob("database.*"))
        if not dumps:
            print("snapshot has no database dump")
            return 1
        if not postgres.restore_database(s, dumps[0]):
            return 1
    print("restore complete — restart Zitadel")
    return 0


def cmd_prune(args, s: Settings) -> int:
    keep = args.keep if args.keep is not None else s.backup_retention_count
    local = apply_local_retention(Path(s.data_dir), keep)
    print(f"local: pruned {local}")
    if s.target_configured():
        from s3_target import S3Target
        remote = S3Target(s).apply_retention(keep)
        print(f"remote: pruned {remote}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="database-backup", description="Zitadel backup CLI")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("create", help="run a snapshot now")
    sub.add_parser("list", help="list snapshots")
    v = sub.add_parser("verify", help="verify a snapshot's sha256")
    v.add_argument("snapshot_id")
    r = sub.add_parser("restore", help="restore a snapshot (destructive)")
    r.add_argument("snapshot_id")
    r.add_argument("-f", "--force", action="store_true")
    pr = sub.add_parser("prune", help="apply retention")
    pr.add_argument("-k", "--keep", type=int, default=None)
    return p


def main() -> int:
    args = build_parser().parse_args()
    s = _settings()
    dispatch = {
        "create": cmd_create, "list": cmd_list, "verify": cmd_verify,
        "restore": cmd_restore, "prune": cmd_prune,
    }
    return dispatch[args.command](args, s)


if __name__ == "__main__":
    sys.exit(main())
