"""The engine the database-backup image is built on, and the zitadel-postgres alias.

The compose files back up and restore the Zitadel database with the engine's
`postgres` source. Its restore copes with Zitadel's partitioned cache tables
since BackupHelper 1.9.0; with an older engine every restore of a running
installation rolls back (`cannot drop inherited constraint`). These tests fail
the image build on such an engine, and when the alias for compose files that
still name the old type `zitadel-postgres` is missing.

The end-to-end proof against a real Zitadel database is the backup round trip
in .github/workflows/docker-release.yml.
"""

from backuphelper.plugins.registry import build_source, get_source_class
from backuphelper.sources import postgres
from backuphelper.sources.postgres import PostgresSource

SPEC = {"host": "database-server", "port": 5432, "database": "zitadel", "user": "zitadel",
        "ssl_mode": "disable", "dump_format": "custom"}


def test_zitadel_postgres_is_the_engines_postgres_source():
    assert get_source_class("zitadel-postgres") is PostgresSource


def test_both_types_write_the_same_component():
    # The restore looks a snapshot's components up by name: whichever of the
    # two types wrote "zitadel", the configured source restores it.
    old = build_source({"type": "zitadel-postgres", **SPEC})
    new = build_source({"type": "postgres", **SPEC})
    assert type(old) is type(new) is PostgresSource
    assert old.component_name == new.component_name == "zitadel"


def test_the_engine_restores_over_partitioned_tables():
    # BackupHelper 1.9.0+: a custom-format restore first drops the target's
    # partitioned tables that the dump recreates, in the same transaction.
    assert callable(getattr(postgres, "partitioned_tables_to_replace", None))
