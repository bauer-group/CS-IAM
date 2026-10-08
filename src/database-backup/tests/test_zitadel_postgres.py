"""Tests for the Zitadel database source (partition-safe restore via a fake run).

The end-to-end proof against a real Zitadel database is the backup round trip in
.github/workflows/docker-release.yml; these tests pin the command sequence.
"""

import secrets
import subprocess
from pathlib import Path

import pytest

from backuphelper.plugins.registry import get_source_class
from backuphelper.sources.base import SourceError
from backuphelper.sources.postgres import build_restore_argv
from iam_backup.zitadel_postgres import LIVE_PARTITIONED_SQL, ZitadelPostgresSource, dump_tables

TOC = """\
;
; Archive created at 2026-10-08 11:46:35 UTC
;     dbname: zitadel
;
; Selected TOC Entries:
;
6; 2615 16390 SCHEMA - cache zitadel
240; 1259 16500 TABLE cache objects zitadel
241; 1259 16510 TABLE cache objects_id_p_form_callback zitadel
242; 1259 16520 TABLE cache string_keys zitadel
243; 1259 16530 TABLE cache string_keys_id_p_form_callback zitadel
244; 1259 16540 TABLE eventstore events2 zitadel
3601; 0 0 TABLE ATTACH cache objects_id_p_form_callback zitadel
3602; 0 0 TABLE ATTACH cache string_keys_id_p_form_callback zitadel
3700; 0 16540 TABLE DATA eventstore events2 zitadel
3800; 2606 16600 CONSTRAINT cache string_keys string_keys_pkey zitadel
3801; 0 0 INDEX ATTACH cache string_keys_id_p_form_callback_pkey zitadel
"""


# The dummy password is generated per run: credential-looking literals trip
# secret scanners (GitGuardian) although nothing here is real.
PASSWORD = secrets.token_hex(12)


def _spec(**over):
    spec = {"type": "zitadel-postgres", "host": "database-server", "port": 5432,
            "database": "zitadel", "user": "zitadel", "password": PASSWORD}
    spec.update(over)
    return spec


class FakeRun:
    """Answers each command the source runs; records argv, env and the SQL psql gets."""

    def __init__(self, live="", generate_rc=0, apply_rc=0, live_rc=0, list_rc=0):
        self.live, self.live_rc, self.list_rc = live, live_rc, list_rc
        self.generate_rc, self.apply_rc = generate_rc, apply_rc
        self.calls: list[list[str]] = []
        self.envs: list[dict] = []
        self.applied_sql: list[str] = []

    def __call__(self, argv, **kw):
        self.calls.append(argv)
        self.envs.append(kw.get("env") or {})
        if argv[0] == "psql" and "--command" in argv:
            return self._done(argv, self.live_rc, self.live, "psql: connection refused")
        if argv[:2] == ["pg_restore", "--list"]:
            return self._done(argv, self.list_rc, TOC, "pg_restore: not a valid archive")
        if argv[0] == "pg_restore" and "--file" in argv:
            Path(argv[argv.index("--file") + 1]).write_text("-- script\n", encoding="utf-8")
            return self._done(argv, self.generate_rc, "", "pg_restore: corrupt archive")
        if argv[0] == "psql" and "--single-transaction" in argv:
            files = [argv[i + 1] for i, a in enumerate(argv) if a == "--file"]
            self.applied_sql.append("".join(Path(f).read_text(encoding="utf-8") for f in files))
            return self._done(argv, self.apply_rc, "", "ERROR:  something failed")
        return self._done(argv, 0, "", "")  # the engine's own pg_restore

    @staticmethod
    def _done(argv, rc, stdout, stderr):
        return subprocess.CompletedProcess(argv, rc, stdout.encode(), stderr.encode() if rc else b"")


def _staged(tmp_path, name="zitadel.dump"):
    (tmp_path / name).write_bytes(b"PGDMP")
    return tmp_path


LIVE_CACHE = ("cache\tobjects\tcache.objects\n"
              "cache\tstring_keys\tcache.string_keys\n"
              "other\tlive_only\tother.live_only\n")


def test_registered_as_a_backuphelper_source():
    assert get_source_class("zitadel-postgres") is ZitadelPostgresSource


def test_component_name_and_backup_are_the_engines():
    src = ZitadelPostgresSource(_spec())
    assert src.component_name == "zitadel"
    assert src.type == "zitadel-postgres"


def test_dump_tables_reads_only_table_entries():
    assert dump_tables(TOC) == {
        ("cache", "objects"), ("cache", "objects_id_p_form_callback"),
        ("cache", "string_keys"), ("cache", "string_keys_id_p_form_callback"),
        ("eventstore", "events2"),
    }


def test_without_live_partitioned_tables_the_engine_restore_runs(tmp_path):
    run = FakeRun(live="")
    src = ZitadelPostgresSource(_spec(), run=run)
    src.restore(_staged(tmp_path))
    assert run.calls[-1] == build_restore_argv(src.cfg, tmp_path / "zitadel.dump")
    assert run.applied_sql == []


def test_live_partitioned_tables_in_the_dump_are_dropped_in_the_same_transaction(tmp_path):
    run = FakeRun(live=LIVE_CACHE)
    src = ZitadelPostgresSource(_spec(), run=run)
    src.restore(_staged(tmp_path))

    query = run.calls[0]
    assert query[0] == "psql" and query[query.index("--command") + 1] == LIVE_PARTITIONED_SQL
    generate = next(c for c in run.calls if c[0] == "pg_restore" and "--file" in c)
    assert {"--clean", "--if-exists", "--no-owner", "--no-acl"} <= set(generate)
    assert "--single-transaction" not in generate  # psql owns the transaction
    apply = run.calls[-1]
    assert apply[0] == "psql" and "--single-transaction" in apply
    assert apply[apply.index("--set") + 1] == "ON_ERROR_STOP=1"
    # Only what the dump recreates; the prelude runs before the dump's script.
    assert run.applied_sql == [
        "DROP TABLE IF EXISTS cache.objects CASCADE;\n"
        "DROP TABLE IF EXISTS cache.string_keys CASCADE;\n"
        "-- script\n"
    ]


def test_password_never_on_a_command_line(tmp_path):
    run = FakeRun(live=LIVE_CACHE)
    ZitadelPostgresSource(_spec(), run=run).restore(_staged(tmp_path))
    assert all(PASSWORD not in " ".join(argv) for argv in run.calls)
    assert all(env.get("PGPASSWORD") == PASSWORD for env in run.envs)


def test_notices_are_silenced_for_the_apply_only(tmp_path):
    run = FakeRun(live=LIVE_CACHE)
    ZitadelPostgresSource(_spec(), run=run).restore(_staged(tmp_path))
    assert "client_min_messages=warning" in run.envs[-1]["PGOPTIONS"]


def test_temporary_files_are_removed(tmp_path):
    run = FakeRun(live=LIVE_CACHE)
    ZitadelPostgresSource(_spec(), run=run).restore(_staged(tmp_path))
    assert sorted(p.name for p in tmp_path.iterdir()) == ["zitadel.dump"]


@pytest.mark.parametrize("failure", [
    {"live_rc": 2}, {"list_rc": 1}, {"generate_rc": 1}, {"apply_rc": 3},
])
def test_every_failing_step_fails_the_restore(tmp_path, failure):
    run = FakeRun(live=LIVE_CACHE, **failure)
    with pytest.raises(SourceError, match="postgres restore failed"):
        ZitadelPostgresSource(_spec(), run=run).restore(_staged(tmp_path))


def test_a_failed_script_generation_never_reaches_the_database(tmp_path):
    run = FakeRun(live=LIVE_CACHE, generate_rc=1)
    with pytest.raises(SourceError):
        ZitadelPostgresSource(_spec(), run=run).restore(_staged(tmp_path))
    assert run.applied_sql == []


def test_plain_dumps_keep_the_engine_restore(tmp_path):
    run = FakeRun(live=LIVE_CACHE)
    staged = _staged(tmp_path, "zitadel.sql.gz")
    import gzip
    (staged / "zitadel.sql.gz").write_bytes(gzip.compress(b"SELECT 1;"))
    ZitadelPostgresSource(_spec(dump_format="plain"), run=run).restore(staged)
    assert all("--command" not in c for c in run.calls)
    assert run.calls[-1][0] == "psql" and "--single-transaction" not in run.calls[-1]
