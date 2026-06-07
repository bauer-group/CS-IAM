"""zitadel-backup — scheduler (cron / interval)."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Callable

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from logging_setup import logger

if TYPE_CHECKING:
    from config import Settings


def build_scheduler(settings: "Settings", run_backup: Callable[[], bool]) -> BlockingScheduler:
    sched = BlockingScheduler(timezone=settings.time_zone)
    if settings.backup_schedule_mode == "cron":
        m, h, dom, mon, dow = settings.backup_schedule_cron.split()
        trigger = CronTrigger(minute=m, hour=h, day=dom, month=mon, day_of_week=dow,
                              timezone=settings.time_zone)
        desc = f"cron '{settings.backup_schedule_cron}'"
    else:
        trigger = IntervalTrigger(hours=settings.backup_schedule_interval_hours,
                                  timezone=settings.time_zone)
        desc = f"every {settings.backup_schedule_interval_hours}h"

    def _guarded() -> None:
        try:
            run_backup()
        except Exception as exc:  # noqa: BLE001
            logger.error("scheduled backup failed: %s", exc, exc_info=True)

    sched.add_job(_guarded, trigger=trigger, id="backup", name="Zitadel Backup",
                  coalesce=True, misfire_grace_time=3600, max_instances=1)
    logger.info("scheduler configured: %s (%s)", desc, settings.time_zone)

    if settings.backup_on_startup:
        sched.add_job(_guarded, trigger="date", run_date=datetime.now(), id="backup_startup")
    return sched


def run(sched: BlockingScheduler) -> None:
    logger.info("zitadel-backup scheduler started")
    try:
        sched.start()
    except (KeyboardInterrupt, SystemExit):
        sched.shutdown(wait=False)
