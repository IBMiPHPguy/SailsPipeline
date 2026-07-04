from __future__ import annotations

import logging
import threading

from app.config import settings
from app.database import SessionLocal
from app.services.subscription_service import lock_expired_trials

logger = logging.getLogger(__name__)

_scheduler_thread: threading.Thread | None = None
_scheduler_stop = threading.Event()


def _run_trial_scheduler_loop() -> None:
    while not _scheduler_stop.wait(settings.trial_scheduler_poll_seconds):
        db = SessionLocal()
        try:
            locked_count = lock_expired_trials(db)
            if locked_count:
                logger.info("Locked %s expired trial agency workspace(s).", locked_count)
        except Exception:
            logger.exception("Trial expiration scheduler iteration failed.")
            db.rollback()
        finally:
            db.close()


def start_trial_scheduler() -> None:
    global _scheduler_thread
    if not settings.trial_scheduler_enabled or settings.app_env == "test":
        return
    if _scheduler_thread and _scheduler_thread.is_alive():
        return
    _scheduler_stop.clear()
    _scheduler_thread = threading.Thread(
        target=_run_trial_scheduler_loop,
        name="trial-expiration-scheduler",
        daemon=True,
    )
    _scheduler_thread.start()
    logger.info("Trial expiration scheduler started.")


def stop_trial_scheduler() -> None:
    _scheduler_stop.set()
    thread = _scheduler_thread
    if thread and thread.is_alive():
        thread.join(timeout=5)
