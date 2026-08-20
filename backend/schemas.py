from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

# Lecture Schemas
class LectureBase(BaseModel):
    subject_code: str
    subject_name: str
    type: str = "Lec"
    day_of_week: str
    start_time: str = Field(..., description="Format: HH:MM (24h)")
    end_time: str = Field(..., description="Format: HH:MM (24h)")
    room: Optional[str] = None
    teacher: Optional[str] = None
    color_scheme: Optional[str] = "blue"

class LectureCreate(LectureBase):
    pass

class LectureUpdate(BaseModel):
    subject_code: Optional[str] = None
    subject_name: Optional[str] = None
    type: Optional[str] = None
    day_of_week: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    room: Optional[str] = None
    teacher: Optional[str] = None
    color_scheme: Optional[str] = None

class LectureResponse(LectureBase):
    id: int

    class Config:
        from_attributes = True

# Push Notification Subscription Schemas
class SubscriptionKeys(BaseModel):
    p256dh: str
    auth: str

class PushSubscriptionCreate(BaseModel):
    endpoint: str
    keys: SubscriptionKeys

class PushSubscriptionResponse(BaseModel):
    id: int
    endpoint: str
    created_at: datetime

    class Config:
        from_attributes = True
