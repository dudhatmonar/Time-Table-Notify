from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from database import Base

class Lecture(Base):
    __tablename__ = "lectures"

    id = Column(Integer, primary_key=True, index=True)
    subject_code = Column(String, nullable=False)
    subject_name = Column(String, nullable=False)
    type = Column(String, default="Lec")  # e.g., Lec, Lab, Seminar
    day_of_week = Column(String, nullable=False)  # Monday, Tuesday, etc.
    start_time = Column(String, nullable=False)  # HH:MM (24h format)
    end_time = Column(String, nullable=False)  # HH:MM (24h format)
    room = Column(String, nullable=True)
    teacher = Column(String, nullable=True)
    color_scheme = Column(String, default="blue")  # green, red, blue, etc.

class PushSubscription(Base):
    __tablename__ = "push_subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    endpoint = Column(String, nullable=False, unique=True)
    p256dh = Column(String, nullable=False)
    auth = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class NotificationLog(Base):
    __tablename__ = "notification_logs"

    id = Column(Integer, primary_key=True, index=True)
    lecture_id = Column(Integer, ForeignKey("lectures.id", ondelete="CASCADE"), nullable=False)
    event_type = Column(String, nullable=False)  # "10_min_before", "started"
    sent_date = Column(String, nullable=False)  # YYYY-MM-DD format
