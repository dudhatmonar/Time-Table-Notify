import asyncio
import json
import logging
from datetime import datetime
from sqlalchemy.orm import Session
from pywebpush import webpush, WebPushException

from database import SessionLocal
from models import Lecture, PushSubscription, NotificationLog
from vapid import get_vapid_keys

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Scheduler")

# Global stop flag for the loop
scheduler_running = True
last_morning_summary_date = ""

def get_time_difference_minutes(t1_str: str, t2_str: str) -> int:
    """
    Calculates t1_str - t2_str in minutes.
    t1_str and t2_str are in "HH:MM" 24h format.
    """
    try:
        h1, m1 = map(int, t1_str.split(":"))
        h2, m2 = map(int, t2_str.split(":"))
        return (h1 * 60 + m1) - (h2 * 60 + m2)
    except Exception as e:
        logger.error(f"Error parsing time strings: {t1_str}, {t2_str} - {e}")
        return -9999

def send_push_to_subscription(db: Session, subscription: PushSubscription, payload: dict, private_key: str):
    """
    Sends a push notification to a single subscriber. Deletes subscription if endpoint is invalid (404/410).
    """
    subscription_info = {
        "endpoint": subscription.endpoint,
        "keys": {
            "p256dh": subscription.p256dh,
            "auth": subscription.auth
        }
    }
    
    try:
        webpush(
            subscription_info=subscription_info,
            data=json.dumps(payload),
            vapid_private_key=private_key,
            vapid_claims={"sub": "mailto:admin@example.com"}
        )
        logger.info(f"Successfully sent push to subscription ID {subscription.id}")
    except WebPushException as ex:
        # Check if the subscription is gone or expired
        if ex.response is not None and ex.response.status_code in [404, 410]:
            logger.warning(f"Subscription ID {subscription.id} is invalid (status {ex.response.status_code}). Pruning from DB.")
            try:
                db.delete(subscription)
                db.commit()
            except Exception as delete_error:
                db.rollback()
                logger.error(f"Failed to delete expired subscription {subscription.id}: {delete_error}")
        else:
            logger.error(f"WebPushException for subscription ID {subscription.id}: {ex}")
    except Exception as e:
        logger.error(f"Unexpected error sending push notification to {subscription.id}: {e}")

def build_dynamic_notification_payload(db: Session) -> dict:
    """
    Constructs a detailed live notification showing the currently active class (if any)
    and the next upcoming class with exact remaining time or day description.
    """
    now = datetime.now()
    current_day = now.strftime("%A")
    current_time_str = now.strftime("%H:%M")
    
    # 1. Check if there is an active class right now
    lectures_today = db.query(Lecture).filter(Lecture.day_of_week == current_day).all()
    active_lecture = None
    
    for lec in lectures_today:
        try:
            if lec.start_time <= current_time_str < lec.end_time:
                active_lecture = lec
                break
        except Exception:
            continue
            
    # 2. Find the next upcoming class today or later in the week
    next_lecture = None
    time_diff_min = 0
    day_desc = ""
    
    # Sort today's classes by start_time
    lectures_today.sort(key=lambda x: x.start_time)
    for lec in lectures_today:
        if lec.start_time > current_time_str:
            next_lecture = lec
            time_diff_min = get_time_difference_minutes(lec.start_time, current_time_str)
            day_desc = "today"
            break
            
    if not next_lecture:
        # Check upcoming days
        days_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        current_day_idx = days_order.index(current_day)
        
        all_lectures = db.query(Lecture).all()
        if all_lectures:
            # Sort by day order, then start_time
            all_lectures.sort(key=lambda x: (days_order.index(x.day_of_week), x.start_time))
            
            # Find the next class chronologically
            for lec in all_lectures:
                lec_day_idx = days_order.index(lec.day_of_week)
                if lec_day_idx > current_day_idx:
                    days_diff = lec_day_idx - current_day_idx
                    next_lecture = lec
                    # Calculate minutes
                    h_now, m_now = map(int, current_time_str.split(":"))
                    h_start, m_start = map(int, lec.start_time.split(":"))
                    time_diff_min = (days_diff * 24 * 60) + (h_start * 60 + m_start) - (h_now * 60 + m_now)
                    day_desc = lec.day_of_week
                    break
            
            # Wrap around to start of week
            if not next_lecture:
                first_lec = all_lectures[0]
                lec_day_idx = days_order.index(first_lec.day_of_week)
                days_diff = (lec_day_idx + 7) - current_day_idx
                next_lecture = first_lec
                h_now, m_now = map(int, current_time_str.split(":"))
                h_start, m_start = map(int, first_lec.start_time.split(":"))
                time_diff_min = (days_diff * 24 * 60) + (h_start * 60 + m_start) - (h_now * 60 + m_now)
                day_desc = first_lec.day_of_week

    # Format the notification text
    title = "🔔 Timetable Notification Test"
    body_parts = []
    
    if active_lecture:
        rem_min = get_time_difference_minutes(active_lecture.end_time, current_time_str)
        body_parts.append(
            f"🟢 Active Class Now:\n"
            f"{active_lecture.subject_code} - {active_lecture.subject_name}\n"
            f"Room: {active_lecture.room or 'N/A'}\n"
            f"Instructor: {active_lecture.teacher or 'N/A'}\n"
            f"Ends in: {rem_min} mins (at {active_lecture.end_time})"
        )
    
    if next_lecture:
        if time_diff_min < 60:
            time_str = f"{time_diff_min} mins"
        else:
            hours = time_diff_min // 60
            mins = time_diff_min % 60
            if hours < 24:
                time_str = f"{hours}h {mins}m"
            else:
                days = hours // 24
                remaining_hours = hours % 24
                time_str = f"{days}d {remaining_hours}h"
                
        when_str = f"in {time_str}" if day_desc == "today" else f"on {day_desc} at {next_lecture.start_time} ({time_str})"
        
        body_parts.append(
            f"⏰ Next Class:\n"
            f"{next_lecture.subject_code} - {next_lecture.subject_name}\n"
            f"Room: {next_lecture.room or 'N/A'}\n"
            f"Instructor: {next_lecture.teacher or 'N/A'}\n"
            f"Starts: {when_str}"
        )
        
    if not body_parts:
        body_parts.append("No classes scheduled in your database. Add classes first!")
        
    return {
        "title": title,
        "body": "\n\n".join(body_parts),
        "room": next_lecture.room if next_lecture else "N/A",
        "subject_code": next_lecture.subject_code if next_lecture else "TEST",
        "subject_name": next_lecture.subject_name if next_lecture else "Test Push",
        "event_type": "test"
    }

def send_morning_summary(db: Session, today_date_str: str):
    """
    Broadcasts a summary of today's schedule to all subscribers.
    Triggers once per day at 08:00 AM.
    """
    global last_morning_summary_date
    current_day = datetime.now().strftime("%A")
    
    # Fetch lectures scheduled for today
    lectures = db.query(Lecture).filter(Lecture.day_of_week == current_day).all()
    
    if not lectures:
        body = "Relax! You have no classes scheduled for today."
    else:
        # Sort classes by start time
        lectures.sort(key=lambda x: x.start_time)
        body_lines = ["Here is your schedule for today:"]
        for lec in lectures:
            body_lines.append(f"• {lec.start_time} - {lec.end_time}: {lec.subject_code} ({lec.subject_name}) in {lec.room or 'N/A'}")
        body = "\n".join(body_lines)
        
    subscriptions = db.query(PushSubscription).all()
    if not subscriptions:
        logger.info("Morning summary skipped: No subscribers found.")
        # Mark as sent anyway so we don't spam checks if someone subscribes later in that 5m window
        last_morning_summary_date = today_date_str
        return
        
    private_key, _ = get_vapid_keys()
    payload = {
        "title": "📅 Today's Schedule Overview",
        "body": body,
        "room": "N/A",
        "subject_code": "DAILY",
        "subject_name": "Daily Summary",
        "event_type": "morning_summary"
    }
    
    logger.info(f"Sending morning summary notification to {len(subscriptions)} subscriber(s)...")
    for sub in subscriptions:
        send_push_to_subscription(db, sub, payload, private_key)
        
    last_morning_summary_date = today_date_str
    logger.info(f"Morning summary successfully sent for {today_date_str}.")

def check_and_send_notifications():
    """
    Checks active lectures for today and triggers notifications if they start in 10 minutes or start now.
    """
    db = SessionLocal()
    try:
        # Get current date details in server local time
        now = datetime.now()
        current_day = now.strftime("%A")  # Monday, Tuesday, ...
        current_time_str = now.strftime("%H:%M")  # HH:MM
        today_date_str = now.strftime("%Y-%m-%d")  # YYYY-MM-DD
        
        logger.debug(f"Checking timetable at {current_time_str} on {current_day}")

        # Check and send daily morning summary between 08:00 AM and 08:05 AM
        global last_morning_summary_date
        if "08:00" <= current_time_str <= "08:05" and last_morning_summary_date != today_date_str:
            try:
                send_morning_summary(db, today_date_str)
            except Exception as e:
                logger.error(f"Failed to send morning summary: {e}")

        # Fetch lectures scheduled for today
        lectures = db.query(Lecture).filter(Lecture.day_of_week == current_day).all()
        if not lectures:
            return

        # Fetch all active push subscriptions
        subscriptions = db.query(PushSubscription).all()
        if not subscriptions:
            return

        private_key, _ = get_vapid_keys()

        for lecture in lectures:
            diff_min = get_time_difference_minutes(lecture.start_time, current_time_str)

            event_type = None
            if diff_min == 10:
                event_type = "10_min_before"
            elif diff_min == 0:
                event_type = "started"

            if not event_type:
                continue

            # Check if this notification event has already been sent today
            already_sent = db.query(NotificationLog).filter(
                NotificationLog.lecture_id == lecture.id,
                NotificationLog.event_type == event_type,
                NotificationLog.sent_date == today_date_str
            ).first()

            if already_sent:
                continue

            logger.info(f"Triggering {event_type} notification for {lecture.subject_code} ({lecture.start_time})")

            # Record in logs first to prevent double sends in case of slow API calls
            log_entry = NotificationLog(
                lecture_id=lecture.id,
                event_type=event_type,
                sent_date=today_date_str
            )
            db.add(log_entry)
            db.commit()

            # Compile push payload
            if event_type == "10_min_before":
                title = f"🔔 {lecture.subject_code} starts in 10m"
                body = f"{lecture.subject_name}\nTime: {lecture.start_time} - {lecture.end_time}\nRoom: {lecture.room or 'N/A'}\nInstructor: {lecture.teacher or 'N/A'}"
            else:
                title = f"🚀 {lecture.subject_code} Started Now!"
                body = f"{lecture.subject_name}\nTime: {lecture.start_time} - {lecture.end_time}\nRoom: {lecture.room or 'N/A'}\nInstructor: {lecture.teacher or 'N/A'}"

            payload = {
                "title": title,
                "body": body,
                "room": lecture.room,
                "subject_code": lecture.subject_code,
                "subject_name": lecture.subject_name,
                "event_type": event_type
            }

            # Broadcast push to all subscribers
            for sub in subscriptions:
                send_push_to_subscription(db, sub, payload, private_key)

    except Exception as e:
        logger.error(f"Error in scheduler notification check: {e}")
    finally:
        db.close()

async def scheduler_loop():
    """
    Asynchronous loop that runs checking cycle every 30 seconds.
    """
    logger.info("Background Timetable Checker started.")
    while scheduler_running:
        try:
            check_and_send_notifications()
        except Exception as e:
            logger.error(f"Error in check_and_send_notifications: {e}")
        await asyncio.sleep(30)
    logger.info("Background Timetable Checker stopped.")
