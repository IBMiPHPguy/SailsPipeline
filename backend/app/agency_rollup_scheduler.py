from __future__ import annotations

import logging
import threading
from datetime import UTC, datetime, timedelta

from app.config import settings
from app.database import SessionLocal
from app.services.agency_rollup_service import process_scheduled_agency_rollup_refreshes, refresh_all_agency_rollups

logger = logging.getLogger(__name__)

_scheduler_thread: threading.Thread | None = None
_scheduler_stop = threading.Event()


def _seconds_until_next_daily_refresh(now: datetime) -> float:
    target = now.replace(
        hour=settings.rollup_daily_refresh_hour_utc,
        minute=0,
        second=0,
        microsecond=0,
    )
    if target <= now:
        target += timedelta(days=1)
    return max(1.0, (target - now).total_seconds())


def _run_rollup_scheduler_loop() -> None:
    next_daily_refresh_at = datetime.now(UTC) + timedelta(
        seconds=_seconds_until_next_daily_refresh(datetime.now(UTC))
    )
    while not _scheduler_stop.wait(settings.rollup_refresh_poll_seconds):
        db = SessionLocal()
        try:
            processed = process_scheduled_agency_rollup_refreshes(db)
            if processed:
                logger.info("Processed %s queued agency rollup refresh(es).", processed)
            now = datetime.now(UTC)
            if now >= next_daily_refresh_at:
                count = refresh_all_agency_rollups(db)
                logger.info("Completed daily rollup refresh for %s agencies.", count)
                next_daily_refresh_at = now + timedelta(seconds=_seconds_until_next_daily_refresh(now))
        except Exception:
            logger.exception("Agency rollup scheduler iteration failed.")
            db.rollback()
        finally:
            db.close()


def start_agency_rollup_scheduler() -> None:
    global _scheduler_thread
    if not settings.rollup_scheduler_enabled or settings.app_env == "test":
        return
    if _scheduler_thread and _scheduler_thread.is_alive():
        return
    _scheduler_stop.clear()
    _scheduler_thread = threading.Thread(
        target=_run_rollup_scheduler_loop,
        name="agency-rollup-scheduler",
        daemon=True,
    )
    _scheduler_thread.start()
    logger.info("Agency rollup scheduler started.")


def stop_agency_rollup_scheduler() -> None:
    _scheduler_stop.set()
    thread = _scheduler_thread
    if thread and thread.is_alive():
        thread.join(timeout=5)
