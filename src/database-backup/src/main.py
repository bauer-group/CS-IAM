"""
database-backup — entry point.

  (no args)  → scheduler daemon (cron/interval)
  --now      → run a single snapshot and exit
  cli ...    → list / verify / restore / prune (see cli.py)
"""

from __future__ import annotations

import json
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import postgres  # noqa: E402
import scheduler as scheduler_mod  # noqa: E402
from alerting import Alert, AlertManager  # noqa: E402
from archive import apply_local_retention, create_archive, sha256sum  # noqa: E402
from config import Settings  # noqa: E402
from logging_setup import format_size, logger, print_banner, setup_logging  # noqa: E402


def _snapshot_id() -> str:
    return time.strftime("%Y-%m-%d_%H-%M-%S")


def run_snapshot(settings: Settings) -> bool:
    start = time.time()
    sid = _snapshot_id()
    data_dir = Path(settings.data_dir)
    staging = data_dir / "staging" / sid
    archive_path = data_dir / f"{sid}.tar.gz"
    manifest_path = data_dir / f"{sid}.manifest.json"
    alerts = AlertManager(settings)
    errors: list[str] = []

    try:
        logger.info("=== snapshot %s ===", sid)
        staging.mkdir(parents=True, exist_ok=True)

        dump = postgres.dump_database(settings, staging / "database")
        if not dump.success:
            errors.append(f"pg_dump failed: {dump.error}")
            return _finish(alerts, settings, sid, start, 0, errors)

        manifest = {
            "snapshot_id": sid,
            "instance_name": settings.instance_name,
            "database_format": dump.fmt,
            "database_dump_size": dump.size,
        }
        (staging / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

        create_archive(staging, archive_path)
        size = archive_path.stat().st_size
        manifest["archive_size"] = size
        manifest["archive_sha256"] = sha256sum(archive_path)
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        shutil.rmtree(staging, ignore_errors=True)
        logger.info("archive created (%s)", format_size(size))

        if settings.target_configured():
            from s3_target import S3Target
            target = S3Target(settings)
            if target.ensure_bucket():
                url = target.upload(archive_path, manifest_path, sid)
                if url:
                    logger.info("uploaded → %s", url)
                    target.apply_retention(settings.backup_retention_count)
                else:
                    errors.append("off-site upload failed — kept local archive")
                if not settings.keep_local_archive and url:
                    archive_path.unlink(missing_ok=True)
                    manifest_path.unlink(missing_ok=True)
            else:
                errors.append("target bucket unreachable — local only")
        else:
            logger.info("no off-site target configured — local only")

        apply_local_retention(data_dir, settings.backup_retention_count)
        return _finish(alerts, settings, sid, start, size, errors)

    except Exception as exc:  # noqa: BLE001
        logger.error("snapshot crashed: %s", exc, exc_info=True)
        shutil.rmtree(staging, ignore_errors=True)
        errors.append(str(exc))
        return _finish(alerts, settings, sid, start, 0, errors)


def _finish(alerts, settings, sid, start, size, errors) -> bool:  # noqa: ANN001
    ok = not errors
    duration = time.time() - start
    logger.info("snapshot %s %s in %.1fs", sid, "OK" if ok else "with errors", duration)
    alerts.send(Alert(
        snapshot_id=sid,
        status="success" if ok else "error",
        message="snapshot completed" if ok else "snapshot completed with errors",
        instance_name=settings.instance_name,
        archive_size=size,
        duration_seconds=duration,
        errors=errors or None,
    ))
    return ok


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "cli":
        sys.argv = [sys.argv[0]] + sys.argv[2:]
        from cli import main as cli_main
        return cli_main()

    try:
        settings = Settings()
    except Exception as exc:  # noqa: BLE001
        print(f"FATAL: invalid configuration: {exc}", file=sys.stderr)
        return 2
    setup_logging(settings.backup_log_level, settings.backup_log_format)
    if settings.backup_log_format == "console":
        print_banner(f"PostgreSQL snapshots for {settings.instance_name}")

    if "--now" in sys.argv:
        return 0 if run_snapshot(settings) else 1

    if not settings.backup_schedule_enabled:
        logger.info("BACKUP_SCHEDULE_ENABLED=false — idle (use --now or cli create)")
        while True:
            time.sleep(3600)

    sched = scheduler_mod.build_scheduler(settings, lambda: run_snapshot(settings))
    scheduler_mod.run(sched)
    return 0


if __name__ == "__main__":
    sys.exit(main())
