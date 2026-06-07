"""
directory-sync — scheduler.

Two independently-scheduled jobs in one process (shared clients):
  - sync-profiles every SYNC_PROFILES_INTERVAL seconds
  - sync-groups   every SYNC_GROUPS_INTERVAL  seconds
"""

from __future__ import annotations

from typing import Callable

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger

from config import Settings
from logging_setup import logger


def build_scheduler(
    settings: Settings,
    run_profiles: Callable[[], object],
    run_groups: Callable[[], object],
) -> BlockingScheduler:
    sched = BlockingScheduler(timezone=settings.time_zone)

    sched.add_job(
        _guard(run_profiles, "sync-profiles"),
        trigger=IntervalTrigger(seconds=settings.sync_profiles_interval, timezone=settings.time_zone),
        id="sync_profiles",
        name="Sync Profiles",
        next_run_time=None,
        coalesce=True,
        max_instances=1,
        misfire_grace_time=settings.sync_profiles_interval,
    )
    sched.add_job(
        _guard(run_groups, "sync-groups"),
        trigger=IntervalTrigger(seconds=settings.sync_groups_interval, timezone=settings.time_zone),
        id="sync_groups",
        name="Sync Groups",
        next_run_time=None,
        coalesce=True,
        max_instances=1,
        misfire_grace_time=settings.sync_groups_interval,
    )

    logger.info(
        "scheduler: profiles every %ss, groups every %ss",
        settings.sync_profiles_interval,
        settings.sync_groups_interval,
    )
    return sched


def _guard(fn: Callable[[], object], label: str) -> Callable[[], None]:
    """Wrap a job so a single failure never kills the scheduler."""

    def _run() -> None:
        try:
            fn()
        except Exception as exc:  # noqa: BLE001 — keep the loop alive
            logger.error("%s failed: %s", label, exc, exc_info=True)

    return _run


def run(sched: BlockingScheduler) -> None:
    logger.info("directory-sync scheduler started")
    try:
        sched.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("scheduler stopping")
        sched.shutdown(wait=False)
