import logging
import uuid
from typing import Dict, Any, Optional
import requests

from config.settings import settings

logger = logging.getLogger("orthobite.brevo")

BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"


# ---------------------------------------------------------------------------
# Base Styled HTML Email Layout
# ---------------------------------------------------------------------------

def _render_email_wrapper(title: str, content_html: str, action_url: Optional[str] = None, action_label: Optional[str] = None) -> str:
    """Wraps body content in a responsive, branded HTML email template."""
    action_button_html = ""
    if action_url and action_label:
        action_button_html = f"""
        <table role="presentation" border="0" cellpadding="0" cellspacing="0" style="margin: 28px 0;">
            <tr>
                <td align="center">
                    <a href="{action_url}" style="background-color: #0d9488; color: #ffffff; padding: 14px 28px; text-decoration: none; border-radius: 8px; font-weight: 600; font-size: 15px; display: inline-block; box-shadow: 0 2px 4px rgba(13,148,136,0.25);">
                        {action_label}
                    </a>
                </td>
            </tr>
        </table>
        """

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
</head>
<body style="margin: 0; padding: 0; background-color: #f8fafc; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #1e293b; line-height: 1.6;">
    <table role="presentation" width="100%" border="0" cellpadding="0" cellspacing="0" style="background-color: #f8fafc; padding: 32px 16px;">
        <tr>
            <td align="center">
                <table role="presentation" width="100%" border="0" cellpadding="0" cellspacing="0" style="max-width: 580px; background-color: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -2px rgba(0, 0, 0, 0.05); border: 1px solid #e2e8f0;">
                    <!-- Brand Header -->
                    <tr>
                        <td style="background: linear-gradient(135deg, #0f766e 0%, #0d9488 50%, #14b8a6 100%); padding: 32px 36px; text-align: left;">
                            <table role="presentation" width="100%" border="0" cellpadding="0" cellspacing="0">
                                <tr>
                                    <td>
                                        <h1 style="margin: 0; color: #ffffff; font-size: 24px; font-weight: 800; letter-spacing: -0.5px;">
                                            Ortho<span style="color: #99f6e4;">Bite</span>
                                        </h1>
                                        <p style="margin: 4px 0 0 0; color: #ccfbf1; font-size: 13px; font-weight: 500;">
                                            Orthodontics & Bite Alignment Platform
                                        </p>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>

                    <!-- Body Content -->
                    <tr>
                        <td style="padding: 36px 36px 28px 36px;">
                            {content_html}
                            {action_button_html}
                        </td>
                    </tr>

                    <!-- Footer -->
                    <tr>
                        <td style="background-color: #f1f5f9; padding: 24px 36px; border-top: 1px solid #e2e8f0; font-size: 12px; color: #64748b; text-align: center;">
                            <p style="margin: 0 0 6px 0; font-weight: 600; color: #475569;">
                                OrthoBite Orthodontics Clinic
                            </p>
                            <p style="margin: 0 0 6px 0;">
                                2nd Floor, High Street Plaza, Bonifacio Global City, Taguig, Philippines
                            </p>
                            <p style="margin: 0; color: #94a3b8;">
                                Hotline: (02) 8888-BITE | Email: support@orthobite.com
                            </p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Template Generators
# ---------------------------------------------------------------------------

def render_booking_confirmation_template(
    recipient_name: str,
    doctor_name: str,
    specialty: str,
    appointment_date: str,
    appointment_time: str,
    consultation_fee: Optional[str] = None,
    reason: Optional[str] = None,
) -> str:
    """Template for immediate booking confirmation."""
    fee_row = ""
    if consultation_fee:
        fee_row = f"""
        <tr>
            <td style="padding: 10px 14px; font-size: 14px; color: #64748b; font-weight: 500;">Consultation Fee:</td>
            <td style="padding: 10px 14px; font-size: 14px; color: #0f766e; font-weight: 700; text-align: right;">₱{consultation_fee}</td>
        </tr>
        """

    reason_row = ""
    if reason:
        reason_row = f"""
        <tr>
            <td style="padding: 10px 14px; font-size: 14px; color: #64748b; font-weight: 500;">Reason for Visit:</td>
            <td style="padding: 10px 14px; font-size: 14px; color: #0f172a; font-weight: 600; text-align: right;">{reason}</td>
        </tr>
        """

    content = f"""
    <div style="margin-bottom: 24px;">
        <span style="background-color: #dcfce7; color: #15803d; font-size: 12px; font-weight: 700; padding: 4px 10px; border-radius: 9999px; text-transform: uppercase; letter-spacing: 0.5px;">
            Booking Confirmed
        </span>
    </div>
    <h2 style="margin: 0 0 16px 0; font-size: 20px; color: #0f172a; font-weight: 700;">
        Hello, {recipient_name}!
    </h2>
    <p style="margin: 0 0 24px 0; color: #334155; font-size: 15px;">
        Your orthodontic consultation has been successfully reserved with <strong>{doctor_name}</strong>. Here are your visit details:
    </p>

    <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px; overflow: hidden; margin-bottom: 24px;">
        <table role="presentation" width="100%" border="0" cellpadding="0" cellspacing="0">
            <tr style="border-bottom: 1px solid #e2e8f0;">
                <td style="padding: 10px 14px; font-size: 14px; color: #64748b; font-weight: 500;">Doctor:</td>
                <td style="padding: 10px 14px; font-size: 14px; color: #0f172a; font-weight: 600; text-align: right;">{doctor_name} ({specialty})</td>
            </tr>
            <tr style="border-bottom: 1px solid #e2e8f0;">
                <td style="padding: 10px 14px; font-size: 14px; color: #64748b; font-weight: 500;">Date:</td>
                <td style="padding: 10px 14px; font-size: 14px; color: #0f172a; font-weight: 600; text-align: right;">{appointment_date}</td>
            </tr>
            <tr style="border-bottom: 1px solid #e2e8f0;">
                <td style="padding: 10px 14px; font-size: 14px; color: #64748b; font-weight: 500;">Time:</td>
                <td style="padding: 10px 14px; font-size: 14px; color: #0f172a; font-weight: 600; text-align: right;">{appointment_time}</td>
            </tr>
            {reason_row}
            {fee_row}
        </table>
    </div>

    <div style="background-color: #f0fdfa; border-left: 4px solid #0d9488; padding: 14px 16px; border-radius: 0 8px 8px 0; margin-bottom: 24px;">
        <p style="margin: 0; font-size: 13px; color: #134e4a; line-height: 1.5;">
            <strong>Patient Tip:</strong> Please arrive 10 minutes prior to your appointment. If you need to reschedule or cancel, please provide at least <strong>2 hours advance notice</strong> via your patient portal.
        </p>
    </div>
    """
    return _render_email_wrapper(
        title="Appointment Confirmed - OrthoBite",
        content_html=content,
        action_url=f"{settings.FRONTEND_URL}/portal/appointments",
        action_label="View Appointment Details",
    )


def render_cancellation_notice_template(
    recipient_name: str,
    doctor_name: str,
    appointment_date: str,
    appointment_time: str,
    cancellation_reason: Optional[str] = None,
) -> str:
    """Template for appointment cancellation notice."""
    reason_html = ""
    if cancellation_reason:
        reason_html = f"""
        <div style="background-color: #fff1f2; border: 1px solid #fecdd3; border-radius: 8px; padding: 12px 16px; margin: 20px 0;">
            <p style="margin: 0; font-size: 13px; color: #9f1239;">
                <strong>Reason:</strong> {cancellation_reason}
            </p>
        </div>
        """

    content = f"""
    <div style="margin-bottom: 24px;">
        <span style="background-color: #fee2e2; color: #b91c1c; font-size: 12px; font-weight: 700; padding: 4px 10px; border-radius: 9999px; text-transform: uppercase; letter-spacing: 0.5px;">
            Appointment Cancelled
        </span>
    </div>
    <h2 style="margin: 0 0 16px 0; font-size: 20px; color: #0f172a; font-weight: 700;">
        Hello, {recipient_name}
    </h2>
    <p style="margin: 0 0 16px 0; color: #334155; font-size: 15px;">
        This email confirms that your appointment scheduled for <strong>{appointment_date}</strong> at <strong>{appointment_time}</strong> with <strong>{doctor_name}</strong> has been cancelled.
    </p>

    {reason_html}

    <p style="margin: 0 0 20px 0; color: #475569; font-size: 14px;">
        Need to re-book? You can easily select an alternate slot from our doctor carousel anytime through our online portal.
    </p>
    """
    return _render_email_wrapper(
        title="Appointment Cancelled - OrthoBite",
        content_html=content,
        action_url=f"{settings.FRONTEND_URL}/doctors",
        action_label="Schedule a New Visit",
    )


def render_24h_reminder_template(
    recipient_name: str,
    doctor_name: str,
    appointment_date: str,
    appointment_time: str,
    clinic_phone: str = "(02) 8888-BITE",
) -> str:
    """Template for 24-hour advance appointment reminder."""
    content = f"""
    <div style="margin-bottom: 24px;">
        <span style="background-color: #fef3c7; color: #b45309; font-size: 12px; font-weight: 700; padding: 4px 10px; border-radius: 9999px; text-transform: uppercase; letter-spacing: 0.5px;">
            Reminder: Tomorrow
        </span>
    </div>
    <h2 style="margin: 0 0 16px 0; font-size: 20px; color: #0f172a; font-weight: 700;">
        See You Tomorrow, {recipient_name}!
    </h2>
    <p style="margin: 0 0 20px 0; color: #334155; font-size: 15px;">
        This is a friendly reminder that your dental visit with <strong>{doctor_name}</strong> is scheduled for <strong>tomorrow, {appointment_date}</strong> at <strong>{appointment_time}</strong>.
    </p>

    <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px; padding: 18px 20px; margin-bottom: 24px;">
        <h3 style="margin: 0 0 10px 0; font-size: 15px; color: #0f172a; font-weight: 700;">
            Preparation Checklist:
        </h3>
        <ul style="margin: 0; padding-left: 20px; font-size: 14px; color: #475569; line-height: 1.8;">
            <li>Bring a valid government-issued photo ID.</li>
            <li>If you have existing dental X-rays or panoramic scans, please bring them along.</li>
            <li>Arrive 10 minutes early to complete initial health screening.</li>
        </ul>
    </div>

    <p style="margin: 0 0 8px 0; font-size: 13px; color: #64748b;">
        If you are experiencing any sudden illness or need to reschedule, please call our front desk at <strong>{clinic_phone}</strong> as soon as possible.
    </p>
    """
    return _render_email_wrapper(
        title="Appointment Reminder: Tomorrow - OrthoBite",
        content_html=content,
        action_url=f"{settings.FRONTEND_URL}/portal/appointments",
        action_label="Review Appointment",
    )


def render_2h_reminder_template(
    recipient_name: str,
    doctor_name: str,
    appointment_time: str,
    clinic_phone: str = "(02) 8888-BITE",
) -> str:
    """Template for urgent 2-hour advance appointment reminder."""
    content = f"""
    <div style="margin-bottom: 24px;">
        <span style="background-color: #ede9fe; color: #6d28d9; font-size: 12px; font-weight: 700; padding: 4px 10px; border-radius: 9999px; text-transform: uppercase; letter-spacing: 0.5px;">
            Starting in 2 Hours
        </span>
    </div>
    <h2 style="margin: 0 0 16px 0; font-size: 20px; color: #0f172a; font-weight: 700;">
        Your Appointment is in 2 Hours!
    </h2>
    <p style="margin: 0 0 20px 0; color: #334155; font-size: 15px;">
        Hi {recipient_name}, your consultation with <strong>{doctor_name}</strong> begins at <strong>{appointment_time}</strong> today.
    </p>

    <div style="background-color: #f1f5f9; border-radius: 10px; padding: 16px 20px; margin-bottom: 20px;">
        <p style="margin: 0 0 6px 0; font-size: 14px; color: #0f172a; font-weight: 600;">
            📍 Clinic Location:
        </p>
        <p style="margin: 0 0 10px 0; font-size: 13px; color: #475569;">
            2nd Floor, High Street Plaza, Bonifacio Global City, Taguig (Near Market Market)
        </p>
        <p style="margin: 0; font-size: 13px; color: #475569;">
            Need directions or running late? Call us directly: <strong>{clinic_phone}</strong>
        </p>
    </div>

    <p style="margin: 0; font-size: 13px; color: #64748b;">
        Safe travels, and we look forward to seeing you shortly!
    </p>
    """
    return _render_email_wrapper(
        title="Your OrthoBite Appointment is in 2 Hours",
        content_html=content,
        action_url=f"{settings.FRONTEND_URL}/portal/appointments",
        action_label="Directions & Check-in",
    )


# ---------------------------------------------------------------------------
# Brevo API Client
# ---------------------------------------------------------------------------

class BrevoEmailService:
    """Client for dispatching transactional emails via Brevo v3 API."""

    def __init__(self):
        self.api_key = settings.BREVO_API_KEY
        self.sender_email = settings.BREVO_SENDER_EMAIL
        self.sender_name = settings.BREVO_SENDER_NAME

    def send_email(
        self,
        recipient_email: str,
        recipient_name: str,
        subject: str,
        html_content: str,
    ) -> Dict[str, Any]:
        """
        Sends transactional email via Brevo v3 HTTP API.
        If BREVO_API_KEY is not configured or in test mode, gracefully simulates delivery.
        """
        if not self.api_key or self.api_key.strip() == "" or self.api_key.startswith("test_"):
            # Simulation / development fallback mode
            simulated_id = f"sim-{uuid.uuid4().hex[:12]}"
            logger.info(
                f"[BREVO SIMULATED] To: {recipient_email} | Subject: '{subject}' | MessageId: {simulated_id}"
            )
            return {
                "success": True,
                "status": "simulated",
                "message_id": simulated_id,
                "detail": "Email delivery simulated successfully (no active Brevo API key provided).",
            }

        headers = {
            "accept": "application/json",
            "api-key": self.api_key,
            "content-type": "application/json",
        }

        payload = {
            "sender": {
                "name": self.sender_name,
                "email": self.sender_email,
            },
            "to": [
                {
                    "email": recipient_email,
                    "name": recipient_name,
                }
            ],
            "subject": subject,
            "htmlContent": html_content,
        }

        try:
            response = requests.post(
                BREVO_API_URL,
                json=payload,
                headers=headers,
                timeout=10,
            )
            if response.status_code in (200, 201, 202):
                data = response.json()
                message_id = data.get("messageId", f"brevo-{uuid.uuid4().hex[:8]}")
                logger.info(f"[BREVO SENT] To: {recipient_email} | MessageId: {message_id}")
                return {
                    "success": True,
                    "status": "sent",
                    "message_id": message_id,
                    "detail": "Delivered to Brevo transactional mail queue.",
                }
            else:
                error_msg = f"Brevo API error (Status {response.status_code}): {response.text}"
                logger.error(error_msg)
                return {
                    "success": False,
                    "status": "failed",
                    "message_id": None,
                    "detail": error_msg,
                }
        except Exception as e:
            error_msg = f"Network or execution error dispatching Brevo email: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "status": "failed",
                "message_id": None,
                "detail": error_msg,
            }

    # -----------------------------------------------------------------------
    # High-Level Notification Convenience Methods
    # -----------------------------------------------------------------------

    def send_booking_confirmation(
        self,
        recipient_email: str,
        recipient_name: str,
        doctor_name: str,
        specialty: str,
        appointment_date: str,
        appointment_time: str,
        consultation_fee: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Dispatch instant booking confirmation."""
        subject = f"Appointment Confirmed: OrthoBite Consultation with {doctor_name}"
        html_content = render_booking_confirmation_template(
            recipient_name=recipient_name,
            doctor_name=doctor_name,
            specialty=specialty,
            appointment_date=appointment_date,
            appointment_time=appointment_time,
            consultation_fee=consultation_fee,
            reason=reason,
        )
        return self.send_email(
            recipient_email=recipient_email,
            recipient_name=recipient_name,
            subject=subject,
            html_content=html_content,
        )

    def send_cancellation_notice(
        self,
        recipient_email: str,
        recipient_name: str,
        doctor_name: str,
        appointment_date: str,
        appointment_time: str,
        cancellation_reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Dispatch appointment cancellation notification."""
        subject = f"Appointment Cancelled: OrthoBite Consultation with {doctor_name}"
        html_content = render_cancellation_notice_template(
            recipient_name=recipient_name,
            doctor_name=doctor_name,
            appointment_date=appointment_date,
            appointment_time=appointment_time,
            cancellation_reason=cancellation_reason,
        )
        return self.send_email(
            recipient_email=recipient_email,
            recipient_name=recipient_name,
            subject=subject,
            html_content=html_content,
        )

    def send_24h_reminder(
        self,
        recipient_email: str,
        recipient_name: str,
        doctor_name: str,
        appointment_date: str,
        appointment_time: str,
    ) -> Dict[str, Any]:
        """Dispatch 24-hour appointment reminder."""
        subject = f"Reminder: Your OrthoBite Appointment is Tomorrow with {doctor_name}"
        html_content = render_24h_reminder_template(
            recipient_name=recipient_name,
            doctor_name=doctor_name,
            appointment_date=appointment_date,
            appointment_time=appointment_time,
        )
        return self.send_email(
            recipient_email=recipient_email,
            recipient_name=recipient_name,
            subject=subject,
            html_content=html_content,
        )

    def send_2h_reminder(
        self,
        recipient_email: str,
        recipient_name: str,
        doctor_name: str,
        appointment_time: str,
    ) -> Dict[str, Any]:
        """Dispatch 2-hour appointment reminder."""
        subject = f"Reminder: Your OrthoBite Appointment is in 2 Hours with {doctor_name}"
        html_content = render_2h_reminder_template(
            recipient_name=recipient_name,
            doctor_name=doctor_name,
            appointment_time=appointment_time,
        )
        return self.send_email(
            recipient_email=recipient_email,
            recipient_name=recipient_name,
            subject=subject,
            html_content=html_content,
        )


# Global Singleton Instance
brevo_service = BrevoEmailService()
