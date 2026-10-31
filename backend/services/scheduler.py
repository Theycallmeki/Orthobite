import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session

from config.database import SessionLocal
from config.settings import settings
from models.appointment import Appointment, AppointmentStatus
from models.notification import NotificationLog, NotificationStatus, NotificationType
from services.brevo import brevo_service

logger = logging.getLogger("orthobite.scheduler")

# Background scheduler instance
scheduler = BackgroundScheduler(timezone=settings.CLINIC_TIMEZONE)


# ---------------------------------------------------------------------------
# Reminder Scanning & Deduplication Logic
# ---------------------------------------------------------------------------

def scan_and_send_reminders(db: Optional[Session] = None) -> Dict[str, Any]:
    """
    Scans for upcoming appointments within:
    - 24 hours (±15 min window)
    - 2 hours (±10 min window)
    Deduplicates against NotificationLog to ensure reminders are dispatched strictly once.
    """
    should_close_db = False
    if db is None:
        db = SessionLocal()
        should_close_db = True

    summary = {
        "timestamp": datetime.now().isoformat(),
        "reminders_24h_sent": 0,
        "reminders_2h_sent": 0,
        "skipped_deduplicated": 0,
        "failed": 0,
    }

    try:
        now = datetime.now()

        # -------------------------------------------------------------------
        # 1. Scan for 24-Hour Reminders (±15 min window)
        # -------------------------------------------------------------------
        target_24h = now + timedelta(hours=24)
        win_24h_start = target_24h - timedelta(minutes=15)
        win_24h_end = target_24h + timedelta(minutes=15)

        appts_24h = (
            db.query(Appointment)
            .filter(
                Appointment.status.in_([AppointmentStatus.PENDING, AppointmentStatus.CONFIRMED]),
                Appointment.start_time >= win_24h_start,
                Appointment.start_time <= win_24h_end,
            )
            .all()
        )

        for appt in appts_24h:
            # Check deduplication log
            existing_log = (
                db.query(NotificationLog)
                .filter(
                    NotificationLog.appointment_id == appt.id,
                    NotificationLog.type == NotificationType.REMINDER_24H,
                    NotificationLog.status.in_([NotificationStatus.SENT, NotificationStatus.SIMULATED]),
                )
                .first()
            )

            if existing_log:
                summary["skipped_deduplicated"] += 1
                continue

            recipient_email = appt.patient.email if appt.patient else None
            recipient_name = appt.patient.full_name if appt.patient else "Valued Patient"
            doc_name = appt.doctor.user.full_name if (appt.doctor and appt.doctor.user) else "Doctor"

            if not recipient_email:
                continue

            # Send 24h reminder
            res = brevo_service.send_24h_reminder(
                recipient_email=recipient_email,
                recipient_name=recipient_name,
                doctor_name=doc_name,
                appointment_date=appt.start_time.strftime("%A, %B %d, %Y"),
                appointment_time=appt.start_time.strftime("%I:%M %p"),
            )

            status_val = (
                NotificationStatus.SENT
                if res["status"] == "sent"
                else (NotificationStatus.SIMULATED if res["status"] == "simulated" else NotificationStatus.FAILED)
            )

            log_entry = NotificationLog(
                appointment_id=appt.id,
                recipient=recipient_email,
                type=NotificationType.REMINDER_24H,
                status=status_val,
                subject=f"Reminder: Your OrthoBite Appointment is Tomorrow with {doc_name}",
                brevo_message_id=res.get("message_id"),
                error_message=res.get("detail") if not res["success"] else None,
                scheduled_for=appt.start_time,
                sent_at=datetime.now(),
            )
            db.add(log_entry)
            db.commit()

            if res["success"]:
                summary["reminders_24h_sent"] += 1
            else:
                summary["failed"] += 1

        # -------------------------------------------------------------------
        # 2. Scan for 2-Hour Reminders (±10 min window)
        # -------------------------------------------------------------------
        target_2h = now + timedelta(hours=2)
        win_2h_start = target_2h - timedelta(minutes=10)
        win_2h_end = target_2h + timedelta(minutes=10)

        appts_2h = (
            db.query(Appointment)
            .filter(
                Appointment.status.in_([AppointmentStatus.PENDING, AppointmentStatus.CONFIRMED]),
                Appointment.start_time >= win_2h_start,
                Appointment.start_time <= win_2h_end,
            )
            .all()
        )

        for appt in appts_2h:
            # Check deduplication log
            existing_log = (
                db.query(NotificationLog)
                .filter(
                    NotificationLog.appointment_id == appt.id,
                    NotificationLog.type == NotificationType.REMINDER_2H,
                    NotificationLog.status.in_([NotificationStatus.SENT, NotificationStatus.SIMULATED]),
                )
                .first()
            )

            if existing_log:
                summary["skipped_deduplicated"] += 1
                continue

            recipient_email = appt.patient.email if appt.patient else None
            recipient_name = appt.patient.full_name if appt.patient else "Valued Patient"
            doc_name = appt.doctor.user.full_name if (appt.doctor and appt.doctor.user) else "Doctor"

            if not recipient_email:
                continue

            # Send 2h reminder
            res = brevo_service.send_2h_reminder(
                recipient_email=recipient_email,
                recipient_name=recipient_name,
                doctor_name=doc_name,
                appointment_time=appt.start_time.strftime("%I:%M %p"),
            )

            status_val = (
                NotificationStatus.SENT
                if res["status"] == "sent"
                else (NotificationStatus.SIMULATED if res["status"] == "simulated" else NotificationStatus.FAILED)
            )

            log_entry = NotificationLog(
                appointment_id=appt.id,
                recipient=recipient_email,
                type=NotificationType.REMINDER_2H,
                status=status_val,
                subject=f"Reminder: Your OrthoBite Appointment is in 2 Hours with {doc_name}",
                brevo_message_id=res.get("message_id"),
                error_message=res.get("detail") if not res["success"] else None,
                scheduled_for=appt.start_time,
                sent_at=datetime.now(),
            )
            db.add(log_entry)
            db.commit()

            if res["success"]:
                summary["reminders_2h_sent"] += 1
            else:
                summary["failed"] += 1

    except Exception as e:
        logger.error(f"Error during reminder scan job: {e}")
        summary["error"] = str(e)
    finally:
        if should_close_db:
            db.close()

    return summary


# ---------------------------------------------------------------------------
# Immediate Transactional Dispatch Helpers
# ---------------------------------------------------------------------------

def dispatch_booking_confirmation(db: Session, appointment_id: int) -> Optional[NotificationLog]:
    """Sends immediate booking confirmation email and creates NotificationLog."""
    try:
        appt = db.query(Appointment).filter(Appointment.id == appointment_id).first()
        if not appt or not appt.patient or not appt.patient.email:
            return None

        doc_name = appt.doctor.user.full_name if (appt.doctor and appt.doctor.user) else "Doctor"
        specialty = appt.doctor.specialty if appt.doctor else "Orthodontics"
        fee_str = str(appt.doctor.consultation_fee) if (appt.doctor and appt.doctor.consultation_fee) else None

        res = brevo_service.send_booking_confirmation(
            recipient_email=appt.patient.email,
            recipient_name=appt.patient.full_name,
            doctor_name=doc_name,
            specialty=specialty,
            appointment_date=appt.start_time.strftime("%A, %B %d, %Y"),
            appointment_time=f"{appt.start_time.strftime('%I:%M %p')} - {appt.end_time.strftime('%I:%M %p')}",
            consultation_fee=fee_str,
            reason=appt.reason_for_visit,
        )

        status_val = (
            NotificationStatus.SENT
            if res["status"] == "sent"
            else (NotificationStatus.SIMULATED if res["status"] == "simulated" else NotificationStatus.FAILED)
        )

        log = NotificationLog(
            appointment_id=appt.id,
            recipient=appt.patient.email,
            type=NotificationType.BOOKING_CONFIRMATION,
            status=status_val,
            subject=f"Appointment Confirmed: OrthoBite Consultation with {doc_name}",
            brevo_message_id=res.get("message_id"),
            error_message=res.get("detail") if not res["success"] else None,
            sent_at=datetime.now(),
        )
        db.add(log)
        db.commit()
        db.refresh(log)
        return log
    except Exception as e:
        logger.error(f"Failed to dispatch booking confirmation for appointment {appointment_id}: {e}")
        return None


def dispatch_cancellation_notice(
    db: Session,
    appointment_id: int,
    cancellation_reason: Optional[str] = None,
) -> Optional[NotificationLog]:
    """Sends cancellation notice email and creates NotificationLog."""
    try:
        appt = db.query(Appointment).filter(Appointment.id == appointment_id).first()
        if not appt or not appt.patient or not appt.patient.email:
            return None

        doc_name = appt.doctor.user.full_name if (appt.doctor and appt.doctor.user) else "Doctor"

        res = brevo_service.send_cancellation_notice(
            recipient_email=appt.patient.email,
            recipient_name=appt.patient.full_name,
            doctor_name=doc_name,
            appointment_date=appt.start_time.strftime("%A, %B %d, %Y"),
            appointment_time=appt.start_time.strftime("%I:%M %p"),
            cancellation_reason=cancellation_reason or appt.cancellation_reason,
        )

        status_val = (
            NotificationStatus.SENT
            if res["status"] == "sent"
            else (NotificationStatus.SIMULATED if res["status"] == "simulated" else NotificationStatus.FAILED)
        )

        log = NotificationLog(
            appointment_id=appt.id,
            recipient=appt.patient.email,
            type=NotificationType.CANCELLATION_NOTICE,
            status=status_val,
            subject=f"Appointment Cancelled: OrthoBite Consultation with {doc_name}",
            brevo_message_id=res.get("message_id"),
            error_message=res.get("detail") if not res["success"] else None,
            sent_at=datetime.now(),
        )
        db.add(log)
        db.commit()
        db.refresh(log)
        return log
    except Exception as e:
        logger.error(f"Failed to dispatch cancellation notice for appointment {appointment_id}: {e}")
        return None


# ---------------------------------------------------------------------------
# Scheduler Lifecycle Management
# ---------------------------------------------------------------------------

def start_scheduler():
    """Initializes and starts the background reminder daemon."""
    if not scheduler.running:
        # Schedule reminder scan to run every 5 minutes
        scheduler.add_job(
            scan_and_send_reminders,
            trigger="interval",
            minutes=5,
            id="appointment_reminder_scanner",
            replace_existing=True,
            misfire_grace_time=60,
        )
        scheduler.start()
        logger.info("APScheduler reminder daemon started successfully (every 5 minutes).")


def shutdown_scheduler():
    """Shuts down the background scheduler cleanly."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("APScheduler reminder daemon stopped.")
