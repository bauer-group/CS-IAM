"""Zitadel database source - the engine's postgres source with a restore that
copes with partitioned tables.

Backup is unchanged: ``produce`` is the engine's ``pg_dump --format=custom``.

Restore is where Zitadel needs more. Zitadel keeps its caches in partitioned
tables (schema ``cache``), and the engine's ``pg_restore --clean --if-exists``
fails on them as soon as they exist in the live database: the clean phase
drops each partition's primary key on its own, and PostgreSQL refuses to drop a
constraint a partition inherits from its parent::

    ERROR:  cannot drop inherited constraint "..._pkey" of relation "..."

The restore runs in one transaction, so nothing is damaged - but nothing is
restored either. This source therefore restores in one transaction that first
drops the partitioned tables the dump will recreate (``DROP TABLE ... CASCADE``
takes the partitions, their constraints and indexes with it), then runs the
dump's own clean-and-create script. Any error rolls the whole transaction back.

Without partitioned tables in the live database (a fresh database, or a dump
without them) the engine's restore runs unchanged.
"""

from __future__ import annotations

import re
import tempfile
from pathlib import Path

from backuphelper.sources.base import SourceError
from backuphelper.sources.postgres import PostgresSource, build_env

RESTORE_TIMEOUT = 14400  # seconds, as the engine's postgres restore

# Partitioned tables that are not themselves a partition, with PostgreSQL's own
# identifier quoting for the DROP statement.
LIVE_PARTITIONED_SQL = (
    "SELECT n.nspname, c.relname, format('%I.%I', n.nspname, c.relname) "
    "FROM pg_catalog.pg_class c "
    "JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace "
    "WHERE c.relkind = 'p' AND NOT c.relispartition "
    "ORDER BY 1, 2"
)

# A table entry of `pg_restore --list`: "<id>; <oid> <oid> TABLE <schema> <name> <owner>".
# "TABLE DATA" and "TABLE ATTACH" entries are other objects. The listing does not
# quote names: a table whose name contains a space is not matched, is not dropped
# first, and its restore fails as loudly as the engine's would.
_TOC_TABLE = re.compile(r"^\d+;\s+\d+\s+\d+\s+TABLE\s+(?!DATA\s|ATTACH\s)(\S+)\s+(\S+)")


class ZitadelPostgresSource(PostgresSource):
    type = "zitadel-postgres"

    def restore(self, staged_dir: Path) -> None:
        dumps = sorted(Path(staged_dir).glob(f"{self.cfg.component_name()}.*"))
        if not dumps or "".join(dumps[0].suffixes) != ".dump":
            super().restore(staged_dir)  # missing or plain dump: engine behaviour
            return
        dump = dumps[0]
        env = build_env(self.cfg)
        tables = self.partitioned_tables_to_replace(dump, env)
        if not tables:
            super().restore(staged_dir)
            return
        self._restore_replacing(dump, tables, env)

    def partitioned_tables_to_replace(self, dump: Path, env: dict[str, str]) -> list[str]:
        """Quoted names of the live partitioned tables the dump also contains."""
        live = self._run(
            ["psql", "--no-psqlrc", "--quiet", "--tuples-only", "--no-align",
             "--field-separator", "\t", "--set", "ON_ERROR_STOP=1",
             "--command", LIVE_PARTITIONED_SQL],
            env=env, capture_output=True, timeout=300,
        )
        if live.returncode != 0:
            raise SourceError(f"postgres restore failed: could not list partitioned tables: "
                              f"{_text(live.stderr)}")
        listing = self._run(["pg_restore", "--list", str(dump)],
                            env=env, capture_output=True, timeout=300)
        if listing.returncode != 0:
            raise SourceError(f"postgres restore failed: could not read the dump's table of "
                              f"contents: {_text(listing.stderr)}")
        in_dump = dump_tables(_text(listing.stdout, limit=None))
        tables = []
        for line in _text(live.stdout, limit=None).splitlines():
            fields = line.split("\t")
            if len(fields) == 3 and (fields[0], fields[1]) in in_dump:
                tables.append(fields[2])
        return tables

    def _restore_replacing(self, dump: Path, tables: list[str], env: dict[str, str]) -> None:
        # A file, not a pipe: if pg_restore stopped half-way, psql would commit a
        # truncated script. The script is complete before anything is executed.
        with tempfile.TemporaryDirectory(dir=dump.parent) as tmp:
            prelude = Path(tmp) / "drop-partitioned.sql"
            prelude.write_text(
                "".join(f"DROP TABLE IF EXISTS {name} CASCADE;\n" for name in tables),
                encoding="utf-8",
            )
            script = Path(tmp) / "restore.sql"
            generate = self._run(
                ["pg_restore", "--clean", "--if-exists", "--no-owner", "--no-acl",
                 "--file", str(script), str(dump)],
                env=env, capture_output=True, timeout=RESTORE_TIMEOUT,
            )
            if generate.returncode != 0:
                raise SourceError(f"postgres restore failed: {_text(generate.stderr)}")
            # The clean phase skips every object the prelude already dropped; the
            # notices it prints for that are noise.
            quiet_env = dict(env)
            quiet_env["PGOPTIONS"] = (env.get("PGOPTIONS", "") + " -c client_min_messages=warning").strip()
            apply = self._run(
                ["psql", "--no-psqlrc", "--quiet", "--single-transaction",
                 "--set", "ON_ERROR_STOP=1", "--file", str(prelude), "--file", str(script)],
                env=quiet_env, capture_output=True, timeout=RESTORE_TIMEOUT,
            )
            if apply.returncode != 0:
                raise SourceError(f"postgres restore failed: {_text(apply.stderr)}")


def dump_tables(listing: str) -> set[tuple[str, str]]:
    """(schema, name) of every table in a `pg_restore --list` output."""
    found = set()
    for line in listing.splitlines():
        match = _TOC_TABLE.match(line)
        if match:
            found.add((match.group(1), match.group(2)))
    return found


def _text(data: bytes | str | None, limit: int | None = 500) -> str:
    text = data.decode("utf-8", "replace") if isinstance(data, bytes) else (data or "")
    text = text.strip()
    return text if limit is None else text[:limit]

