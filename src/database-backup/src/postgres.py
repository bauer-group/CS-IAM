"""database-backup — PostgreSQL dump/restore via pg_dump / pg_restore / psql."""

from __future__ import annotations

import gzip
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from logging_setup import format_size, logger

if TYPE_CHECKING:
    from config import Settings


@dataclass
class DumpResult:
    success: bool
    path: Optional[Path] = None
    size: int = 0
    fmt: str = ""
    error: Optional[str] = None


def _env(settings: "Settings") -> dict[str, str]:
    env = {**os.environ}
    env.update(
        {
            "PGHOST": settings.db_host,
            "PGPORT": str(settings.db_port),
            "PGDATABASE": settings.db_name,
            "PGUSER": settings.db_user,
            "PGPASSWORD": settings.db_password_str(),
            "PGSSLMODE": settings.db_ssl_mode,
        }
    )
    return env


def dump_database(settings: "Settings", out_dir: Path) -> DumpResult:
    out_dir.mkdir(parents=True, exist_ok=True)
    fmt = settings.backup_database_dump_format
    timeout = settings.backup_database_dump_timeout_seconds
    env = _env(settings)

    if fmt == "custom":
        out_path = out_dir / "database.dump"
        cmd = ["pg_dump", "--format=custom", "--compress=6", "--no-owner", "--no-acl",
               "--file", str(out_path)]
    else:
        out_path = out_dir / "database.sql.gz"
        cmd = ["pg_dump", "--format=plain", "--no-owner", "--no-acl"]

    try:
        logger.info("running pg_dump (format=%s)", fmt)
        if fmt == "custom":
            r = subprocess.run(cmd, env=env, capture_output=True, timeout=timeout, check=False)
            if r.returncode != 0:
                err = r.stderr.decode("utf-8", "replace").strip()[:500]
                out_path.unlink(missing_ok=True)
                return DumpResult(False, fmt=fmt, error=err)
        else:
            with gzip.open(out_path, "wb", compresslevel=6) as gz:
                proc = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                assert proc.stdout is not None
                shutil.copyfileobj(proc.stdout, gz)
                _, stderr = proc.communicate(timeout=timeout)
                if proc.returncode != 0:
                    err = stderr.decode("utf-8", "replace").strip()[:500]
                    out_path.unlink(missing_ok=True)
                    return DumpResult(False, fmt=fmt, error=err)
        size = out_path.stat().st_size
        logger.info("database dumped (%s, format=%s)", format_size(size), fmt)
        return DumpResult(True, path=out_path, size=size, fmt=fmt)
    except subprocess.TimeoutExpired:
        out_path.unlink(missing_ok=True)
        return DumpResult(False, fmt=fmt, error=f"timeout after {timeout}s")
    except Exception as exc:  # noqa: BLE001
        out_path.unlink(missing_ok=True)
        return DumpResult(False, fmt=fmt, error=str(exc))


def restore_database(settings: "Settings", dump_path: Path) -> bool:
    if not dump_path.exists():
        logger.error("dump file not found: %s", dump_path)
        return False
    env = _env(settings)
    suffix = "".join(dump_path.suffixes)
    try:
        if suffix == ".dump":
            cmd = ["pg_restore", "--clean", "--if-exists", "--no-owner", "--no-acl",
                   "--single-transaction", "--dbname", settings.db_name, str(dump_path)]
            r = subprocess.run(cmd, env=env, capture_output=True, timeout=14400, check=False)
        elif suffix.endswith(".sql.gz"):
            with gzip.open(dump_path, "rb") as gz:
                r = subprocess.run(["psql", "--quiet"], env=env, stdin=gz,
                                   capture_output=True, timeout=14400, check=False)
        elif suffix == ".sql":
            r = subprocess.run(["psql", "--quiet", "--file", str(dump_path)], env=env,
                               capture_output=True, timeout=14400, check=False)
        else:
            logger.error("unrecognised dump suffix: %s", suffix)
            return False
        if r.returncode != 0:
            logger.error("restore failed: %s", r.stderr.decode("utf-8", "replace")[:500])
            return False
        logger.info("database restored")
        return True
    except subprocess.TimeoutExpired:
        logger.error("restore timed out (4h limit)")
        return False
    except Exception as exc:  # noqa: BLE001
        logger.error("restore exception: %s", exc)
        return False
