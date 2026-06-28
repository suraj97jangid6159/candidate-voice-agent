import pytest
import os
import sys
from unittest.mock import AsyncMock, patch, MagicMock

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import db


@pytest.fixture(autouse=True)
def setup_test_db():
    db.init_db()


class TestScheduler:
    def test_get_pending_callbacks_empty(self):
        callbacks = db.get_pending_callbacks()
        assert callbacks == []

    def test_save_and_mark_callback(self):
        candidate_id = "cb_cand_1"
        db.save_candidate(candidate_id, "Callback Test", "+15551112222", "10 LPA", "12 LPA", "30 days", "Python", "Test resume")

        job_id = "cb_job_1"
        db.save_job(job_id, candidate_id, "Callback Corp", "Engineer", "", "JD text", "+15553334444", "hr@callback.com", 8.0)

        call_id = "cb_call_1"
        db.save_call(call_id, job_id, "COMPLETED", "Transcript here")

        db.save_scheduled_callback(call_id, "tomorrow at 11am")
        db.mark_callback_completed(1)

        callbacks = db.get_pending_callbacks()
        assert len(callbacks) == 0


class TestNotificationService:
    @pytest.mark.asyncio
    async def test_send_callback_reminder_no_sendgrid(self):
        from core.notifications import NotificationService
        notifier = NotificationService()
        result = await notifier.send_callback_reminder(
            to_email="hr@test.com",
            candidate_name="Test",
            company_name="Test Corp",
            job_title="Engineer",
            callback_time="tomorrow at 11am",
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_send_transfer_notification_no_sendgrid(self):
        from core.notifications import NotificationService
        notifier = NotificationService()
        result = await notifier.send_transfer_notification(
            to_email="hr@test.com",
            candidate_name="Test",
            company_name="Test Corp",
            job_title="Engineer",
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_send_email_with_sendgrid_mocked(self):
        with patch("sendgrid.SendGridAPIClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 202
            mock_client.return_value.client.mail.send.post.return_value = mock_response

            from core.notifications import NotificationService
            notifier = NotificationService(
                sendgrid_api_key="SG.realkey123",
                from_email="test@agent.com",
            )
            result = await notifier.send_callback_reminder(
                to_email="hr@test.com",
                candidate_name="Test",
                company_name="Test Corp",
                job_title="Engineer",
                callback_time="tomorrow at 11am",
            )
            assert result is True


class TestCallbackScheduler:
    @pytest.mark.asyncio
    async def test_process_pending_callbacks_empty(self):
        with patch("core.scheduler.db.get_pending_callbacks", return_value=[]):
            from core.scheduler import CallbackScheduler
            from core.notifications import NotificationService

            scheduler = CallbackScheduler(NotificationService())
            await scheduler._process_pending_callbacks()

    @pytest.mark.asyncio
    async def test_process_pending_callbacks_no_email(self):
        mock_callback = {
            "id": 1,
            "call_id": "test_call",
            "hr_phone": "+15551234567",
            "scheduled_time": "tomorrow",
            "candidate_name": "Test",
            "company_name": "Test Corp",
            "job_title": "Engineer",
        }
        with patch("core.scheduler.db.get_pending_callbacks", return_value=[mock_callback]), \
             patch("core.scheduler.db.mark_callback_completed") as mock_mark:
            from core.scheduler import CallbackScheduler
            from core.notifications import NotificationService

            scheduler = CallbackScheduler(NotificationService())
            await scheduler._process_pending_callbacks()
            mock_mark.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_scheduler_start(self):
        from core.scheduler import CallbackScheduler
        from core.notifications import NotificationService

        scheduler = CallbackScheduler(NotificationService())
        assert scheduler.is_running is False

        scheduler.start()
        assert scheduler.is_running is True

        jobs = scheduler.get_jobs()
        assert len(jobs) == 1
        assert jobs[0]["id"] == "process_callbacks"

        scheduler.stop()
