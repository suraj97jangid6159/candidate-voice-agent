import logging
from datetime import datetime
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

import db
from core.notifications import NotificationService

logger = logging.getLogger(__name__)


class CallbackScheduler:
    def __init__(self, notification_service: Optional[NotificationService] = None):
        self.scheduler = AsyncIOScheduler()
        self.notifier = notification_service or NotificationService()

    def start(self):
        if self.scheduler.running:
            logger.warning("Scheduler already running")
            return

        self.scheduler.add_job(
            self._process_pending_callbacks,
            IntervalTrigger(seconds=60),
            id="process_callbacks",
            name="Process pending scheduled callbacks",
            replace_existing=True,
        )
        self.scheduler.start()
        logger.info("Callback scheduler started — polling every 60 seconds")

    def stop(self):
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            logger.info("Callback scheduler stopped")

    async def _process_pending_callbacks(self):
        try:
            callbacks = db.get_pending_callbacks()
            if not callbacks:
                return

            logger.info(f"Processing {len(callbacks)} pending callback(s)")
            for cb in callbacks:
                await self._notify_callback(cb)
                db.mark_callback_completed(cb["id"])
                logger.info(f"Callback {cb['id']} processed and marked completed")
        except Exception as e:
            logger.error(f"Error processing callbacks: {e}")

    async def _notify_callback(self, callback: dict):
        hr_email = callback.get("hr_phone", "")
        if not hr_email or "@" not in hr_email:
            logger.info(f"No valid email for callback {callback['id']} — skipping notification")
            return

        await self.notifier.send_callback_reminder(
            to_email=hr_email,
            candidate_name=callback.get("candidate_name", "Candidate"),
            company_name=callback.get("company_name", "Company"),
            job_title=callback.get("job_title", "Position"),
            callback_time=callback.get("scheduled_time", "Unknown"),
        )

    @property
    def is_running(self) -> bool:
        return self.scheduler.running

    def get_jobs(self) -> list:
        return [
            {
                "id": job.id,
                "name": job.name,
                "next_run": str(job.next_run_time) if job.next_run_time else None,
            }
            for job in self.scheduler.get_jobs()
        ]
