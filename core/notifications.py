import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(self, sendgrid_api_key: Optional[str] = None, from_email: Optional[str] = None):
        self.sendgrid_api_key = sendgrid_api_key or os.getenv("SENDGRID_API_KEY", "")
        self.from_email = from_email or os.getenv("SENDGRID_FROM_EMAIL", "noreply@voiceagent.local")
        self._sendgrid_available = bool(self.sendgrid_api_key and "YOUR_" not in self.sendgrid_api_key)

        if not self._sendgrid_available:
            logger.warning("SendGrid not configured — notifications will be logged only")

    async def send_callback_reminder(
        self,
        to_email: str,
        candidate_name: str,
        company_name: str,
        job_title: str,
        callback_time: str
    ) -> bool:
        subject = f"Callback Reminder: {candidate_name} - {job_title} at {company_name}"
        body = (
            f"Hi,\n\n"
            f"This is a reminder that {candidate_name} has a scheduled callback regarding "
            f"the {job_title} position at {company_name}.\n\n"
            f"Scheduled Time: {callback_time}\n\n"
            f"Please ensure you are available to take the call.\n\n"
            f"Best regards,\nCandidate Voice Agent"
        )
        return await self._send_email(to_email, subject, body)

    async def send_transfer_notification(
        self,
        to_email: str,
        candidate_name: str,
        company_name: str,
        job_title: str
    ) -> bool:
        subject = f"Warm Transfer: {candidate_name} connected with {company_name}"
        body = (
            f"Hi,\n\n"
            f"{candidate_name} was successfully warm-transferred to the HR team at "
            f"{company_name} for the {job_title} position.\n\n"
            f"Best regards,\nCandidate Voice Agent"
        )
        return await self._send_email(to_email, subject, body)

    async def _send_email(self, to_email: str, subject: str, body: str) -> bool:
        if not self._sendgrid_available:
            logger.info(f"[MOCK EMAIL] To: {to_email} | Subject: {subject} | Body: {body[:100]}...")
            return True

        try:
            import sendgrid
            from sendgrid.helpers.mail import Mail, Email, To, Content

            sg = sendgrid.SendGridAPIClient(api_key=self.sendgrid_api_key)
            mail = Mail(
                from_email=Email(self.from_email),
                to_emails=To(to_email),
                subject=subject,
                html_content=Content("text/plain", body)
            )
            response = sg.client.mail.send.post(request_body=mail.get())
            logger.info(f"Email sent to {to_email}: {response.status_code}")
            return response.status_code in (200, 201, 202)
        except ImportError:
            logger.warning("sendgrid package not installed — falling back to log")
            logger.info(f"[LOG EMAIL] To: {to_email} | Subject: {subject}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False
