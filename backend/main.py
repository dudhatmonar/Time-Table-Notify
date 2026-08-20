import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List
from bs4 import BeautifulSoup

from database import Base, engine, get_db
import models
import schemas
import scheduler
from scheduler import scheduler_loop
from vapid import get_vapid_keys

# Order of days to sort schedule response
DAYS_ORDER = {
    "Monday": 0,
    "Tuesday": 1,
    "Wednesday": 2,
    "Thursday": 3,
    "Friday": 4,
    "Saturday": 5,
    "Sunday": 6
}

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Create tables if they don't exist
    Base.metadata.create_all(bind=engine)
    
    # Initialize VAPID keys
    get_vapid_keys()
    
    # Seed default sample data if database is empty
    db = next(get_db())
    try:
        count = db.query(models.Lecture).count()
        if count == 0:
            # Seed a default Thursday Cloud Computing lecture in LAB002 as requested
            sample_lecture = models.Lecture(
                subject_code="IT627",
                subject_name="Cloud Computing",
                type="Lec",
                day_of_week="Thursday",
                start_time="09:00",
                end_time="11:00",
                room="LAB002",
                teacher="AM1",
                color_scheme="blue"
            )
            db.add(sample_lecture)
            db.commit()
            print("Database seeded with sample Thursday Cloud Computing lecture.")
    finally:
        db.close()

    # Start background timetable notification checker
    scheduler.scheduler_running = True
    asyncio_task = asyncio.create_task(scheduler_loop())
    
    yield
    
    # Shutdown: Stop scheduler loop
    scheduler.scheduler_running = False
    await asyncio_task

app = FastAPI(
    title="Weekly Timetable Notification API",
    description="Backend for timetable schedule management and automatic push alerts.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for local development and testing
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

import asyncio

# --- REST ENDPOINTS ---

@app.get("/api/lectures", response_model=List[schemas.LectureResponse])
def get_lectures(db: Session = Depends(get_db)):
    """
    Get all lectures sorted by day of the week, then by start time.
    """
    lectures = db.query(models.Lecture).all()
    # Sort helper: day index first, then start_time string
    lectures.sort(key=lambda x: (DAYS_ORDER.get(x.day_of_week, 7), x.start_time))
    return lectures

@app.post("/api/lectures", response_model=schemas.LectureResponse, status_code=status.HTTP_201_CREATED)
def create_lecture(lecture: schemas.LectureCreate, db: Session = Depends(get_db)):
    """
    Add a new lecture.
    """
    db_lecture = models.Lecture(**lecture.model_dump())
    db.add(db_lecture)
    db.commit()
    db.refresh(db_lecture)
    return db_lecture

@app.put("/api/lectures/{lecture_id}", response_model=schemas.LectureResponse)
def update_lecture(lecture_id: int, lecture_update: schemas.LectureUpdate, db: Session = Depends(get_db)):
    """
    Update an existing lecture's details.
    """
    db_lecture = db.query(models.Lecture).filter(models.Lecture.id == lecture_id).first()
    if not db_lecture:
        raise HTTPException(status_code=404, detail="Lecture not found")
        
    update_data = lecture_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_lecture, key, value)
        
    db.commit()
    db.refresh(db_lecture)
    return db_lecture

@app.delete("/api/lectures/{lecture_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_lecture(lecture_id: int, db: Session = Depends(get_db)):
    """
    Delete a lecture.
    """
    db_lecture = db.query(models.Lecture).filter(models.Lecture.id == lecture_id).first()
    if not db_lecture:
        raise HTTPException(status_code=404, detail="Lecture not found")
    db.delete(db_lecture)
    db.commit()
    return None

# --- WEB PUSH ENDPOINTS ---

@app.get("/api/notifications/vapid-public-key")
def get_vapid_public_key():
    """
    Exposes the VAPID Public Key for service worker registration.
    """
    _, public_key = get_vapid_keys()
    return {"publicKey": public_key}

@app.post("/api/notifications/subscribe", status_code=status.HTTP_201_CREATED)
def subscribe_notifications(subscription: schemas.PushSubscriptionCreate, db: Session = Depends(get_db)):
    """
    Subscribe browser/phone client for notifications.
    """
    # Check if subscription already exists
    existing = db.query(models.PushSubscription).filter(
        models.PushSubscription.endpoint == subscription.endpoint
    ).first()
    
    if existing:
        # Update credentials just in case
        existing.p256dh = subscription.keys.p256dh
        existing.auth = subscription.keys.auth
        db.commit()
        db.refresh(existing)
        return {"message": "Subscription updated successfully", "id": existing.id}
        
    db_sub = models.PushSubscription(
        endpoint=subscription.endpoint,
        p256dh=subscription.keys.p256dh,
        auth=subscription.keys.auth
    )
    db.add(db_sub)
    db.commit()
    db.refresh(db_sub)
    return {"message": "Subscribed successfully", "id": db_sub.id}

@app.post("/api/notifications/unsubscribe")
def unsubscribe_notifications(payload: dict, db: Session = Depends(get_db)):
    """
    Remove browser/phone client subscription.
    """
    endpoint = payload.get("endpoint")
    if not endpoint:
        raise HTTPException(status_code=400, detail="Endpoint parameter is required")
        
    db_sub = db.query(models.PushSubscription).filter(models.PushSubscription.endpoint == endpoint).first()
    if not db_sub:
        return {"message": "Subscription not found, nothing to remove"}
        
    db.delete(db_sub)
    db.commit()
    return {"message": "Unsubscribed successfully"}

@app.post("/api/notifications/test")
def test_notification(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    Immediately send a test push notification to all subscribers with live timetable updates.
    """
    subscriptions = db.query(models.PushSubscription).all()
    if not subscriptions:
        raise HTTPException(status_code=400, detail="No push subscriptions found. Please subscribe from the frontend first.")
        
    private_key, _ = get_vapid_keys()
    
    # Dynamically build a detailed push payload showing current and next class details
    payload = scheduler.build_dynamic_notification_payload(db)
    
    # Broadcast asynchronously
    for sub in subscriptions:
        background_tasks.add_task(
            scheduler.send_push_to_subscription,
            db, sub, payload, private_key
        )
        
    return {"message": f"Test push queued for {len(subscriptions)} subscriber(s)", "payload": payload}

# --- TIMETABLE IMPORT ENDPOINT ---

@app.post("/api/import-html")
def import_timetable_html(db: Session = Depends(get_db)):
    """
    Reads local index.html from C:/Users/monar/.gemini/antigravity-ide/scratch/timetable-pdf/index.html,
    parses the grid, and seeds the SQLite database.
    """
    html_path = "C:\\Users\\monar\\.gemini\\antigravity-ide\\scratch\\timetable-pdf\\index.html"
    if not os.path.exists(html_path):
        raise HTTPException(
            status_code=404, 
            detail=f"MSc (IT) Sem 3 index.html file not found at: {html_path}"
        )
        
    try:
        with open(html_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        soup = BeautifulSoup(content, "html.parser")
        table = soup.find("table", id="timetable")
        if not table:
            table = soup.find("table")
            
        if not table:
            raise HTTPException(status_code=400, detail="Could not find timetable table in index.html")
            
        tbody = table.find("tbody")
        rows = tbody.find_all("tr") if tbody else table.find_all("tr")
        
        imported_count = 0
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
        
        # Clear existing lectures to perform a fresh sync
        db.query(models.Lecture).delete()
        db.commit()
        
        def clean_split(text: str) -> list:
            for sep in ["·", "•", "•", "\xb7", "&middot;"]:
                text = text.replace(sep, "|")
            return [p.strip() for p in text.split("|") if p.strip()]
            
        for row in rows:
            cols = row.find_all("td")
            if not cols:
                continue
                
            first_col = cols[0]
            if "time-col" not in first_col.get("class", []):
                continue
                
            time_range = first_col.get_text(strip=True)
            time_parts = time_range.split("–")
            if len(time_parts) != 2:
                time_parts = time_range.split("-")
                
            if len(time_parts) != 2:
                continue
                
            start_time = time_parts[0].strip()
            end_time = time_parts[1].strip()
            
            # Skip lunch break row
            if len(cols) == 2 and ("lunch-break" in cols[1].get("class", []) or "Break" in cols[1].get_text()):
                continue
                
            # Iterate through day columns
            for idx in range(1, len(cols)):
                cell = cols[idx]
                if idx - 1 >= len(days):
                    continue  # Safety boundary
                day_name = days[idx - 1]
                
                card = cell.find("div", class_="card")
                if not card:
                    continue
                    
                # Color scheme
                card_classes = card.get("class", [])
                color_scheme = "blue"
                for c in card_classes:
                    if c in ["green", "red", "blue"]:
                        color_scheme = c
                        break
                        
                # Extract text elements
                code_span = card.find("span", class_="subject-code")
                name_span = card.find("span", class_="subject-name")
                meta_span = card.find("span", class_="subject-meta")
                
                subject_code_raw = code_span.get_text(strip=True) if code_span else ""
                subject_name = name_span.get_text(strip=True) if name_span else ""
                subject_meta_raw = meta_span.get_text(strip=True) if meta_span else ""
                
                # Split subject code and lecture type
                code_parts = clean_split(subject_code_raw)
                subject_code = code_parts[0] if code_parts else "N/A"
                lecture_type = code_parts[1] if len(code_parts) > 1 else "Lec"
                
                # Room and Teacher
                meta_parts = clean_split(subject_meta_raw)
                room = meta_parts[0] if meta_parts else ""
                teacher = meta_parts[1] if len(meta_parts) > 1 else ""
                
                # Custom sample mapping override: Thursday Cloud Computing to LAB002 if matched
                if day_name == "Thursday" and "Cloud" in subject_name:
                    room = "LAB002"
                
                db_lecture = models.Lecture(
                    subject_code=subject_code,
                    subject_name=subject_name,
                    type=lecture_type,
                    day_of_week=day_name,
                    start_time=start_time,
                    end_time=end_time,
                    room=room,
                    teacher=teacher,
                    color_scheme=color_scheme
                )
                db.add(db_lecture)
                imported_count += 1
                
        db.commit()
        return {"status": "success", "imported": imported_count}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to import HTML timetable: {str(e)}")

# CLI running support
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
