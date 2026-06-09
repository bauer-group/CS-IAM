"""
directory-sync — entry point.

  (no args)              → run the scheduler (default container mode)
  import-users [--test-one]
  sync-profiles
  sync-groups
  discover-subject-keys → one-shot CLI commands (also used for migration)
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

# Allow `python src/main.py` style imports.
sys.path.insert(0, str(Path(__file__).resolve().parent))

import httpx  # noqa: E402

import jobs  # noqa: E402
import scheduler as scheduler_mod  # noqa: E402
from config import Settings  # noqa: E402
from graph import GraphClient  # noqa: E402
from logging_setup import logger, print_banner, setup_logging  # noqa: E402
from zitadel import ZitadelClient  # noqa: E402

_COMMANDS = {"import-users", "sync-profiles", "sync-groups", "discover-subject-keys", "brand"}


def wait_for_ready(settings: Settings) -> bool:
    """Wait for the machine key + Zitadel discovery endpoint."""
    key = Path(settings.zitadel_jwt_profile_file)
    url = settings.issuer() + "/.well-known/openid-configuration"
    verify = not settings.zitadel_insecure
    deadline = time.time() + settings.zitadel_wait_timeout

    while time.time() < deadline:
        if key.is_file() and key.stat().st_size > 0:
            try:
                r = httpx.get(url, verify=verify, timeout=5.0)
                if r.status_code == 200:
                    return True
            except httpx.HTTPError:
                pass
        time.sleep(5)
    logger.error("Zitadel/machine-key not ready within %ss", settings.zitadel_wait_timeout)
    return False


def make_clients(settings: Settings) -> tuple[GraphClient, ZitadelClient]:
    graph = GraphClient(
        settings.azure_tenant_id, settings.azure_client_id, settings.azure_secret()
    )
    zit = ZitadelClient(
        issuer=settings.issuer(),
        key_file=settings.zitadel_jwt_profile_file,
        verify_tls=not settings.zitadel_insecure,
    )
    return graph, zit


def run_cli(command: str, argv: list[str], settings: Settings) -> int:
    if command == "discover-subject-keys":
        jobs.discover_subject_keys(settings)
        return 0

    # Branding is Zitadel-only (no Graph): wait for readiness, upload, activate.
    if command == "brand":
        if not wait_for_ready(settings):
            return 1
        zit = ZitadelClient(
            issuer=settings.issuer(),
            key_file=settings.zitadel_jwt_profile_file,
            verify_tls=not settings.zitadel_insecure,
        )
        try:
            jobs.brand(settings, zit)
            return 0
        finally:
            zit.close()

    if not settings.graph_configured():
        logger.error("AZURE_* not configured — cannot run %s", command)
        return 2
    if not wait_for_ready(settings):
        return 1

    graph, zit = make_clients(settings)
    try:
        if command == "import-users":
            jobs.import_users(settings, graph, zit, test_one="--test-one" in argv)
        elif command == "sync-profiles":
            jobs.sync_profiles(settings, graph, zit)
        elif command == "sync-groups":
            jobs.sync_groups(settings, graph, zit)
        return 0
    finally:
        graph.close()
        zit.close()


def main() -> int:
    settings = Settings()
    setup_logging(settings.sync_log_level, settings.sync_log_format)
    if settings.sync_log_format == "console":
        print_banner(f"Entra -> Zitadel @ {settings.issuer()}")

    argv = sys.argv[1:]
    if argv and argv[0] in _COMMANDS:
        return run_cli(argv[0], argv[1:], settings)

    # ── Scheduler (default) ────────────────────────────────────────────────
    if not settings.sync_enabled:
        logger.info("SYNC_ENABLED=false — idling (run a CLI subcommand for one-offs)")
        # Stay alive so the container doesn't crash-loop.
        while True:
            time.sleep(3600)

    if not settings.graph_configured():
        logger.warning("AZURE_* not configured — directory-sync idle until credentials are set")
        while True:
            time.sleep(3600)

    if not wait_for_ready(settings):
        return 1

    graph, zit = make_clients(settings)
    sched = scheduler_mod.build_scheduler(
        settings,
        run_profiles=lambda: jobs.sync_profiles(settings, graph, zit),
        run_groups=lambda: jobs.sync_groups(settings, graph, zit),
    )
    try:
        scheduler_mod.run(sched)
    finally:
        graph.close()
        zit.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
