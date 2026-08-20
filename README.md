# MSc (IT) Sem 3 Interactive Timetable App

A responsive, high-performance weekly timetable and scheduling application. Built using a **React + Vite** frontend and **FastAPI** backend, featuring automated Web Push notification warnings (starts in 10 minutes, class started) on desktops and mobile devices.

---

## Folder Structure
```
timetable-app/
├── backend/
│   ├── main.py            # FastAPI entrypoint, CRUD routes, VAPID controller, HTML Parser
│   ├── database.py        # SQLAlchemy SQLite / Supabase PostgreSQL adapter
│   ├── models.py          # SQLAlchemy tables (Lectures, Subscriptions, Logs)
│   ├── schemas.py         # Pydantic schemas for verification
│   ├── vapid.py           # Auto-generates VAPID keys locally if missing
│   ├── scheduler.py       # Async background loop checks starting times and triggers push broadcasts
│   └── requirements.txt   # Python dependencies
├── frontend/
│   ├── package.json       # React & Vite packages config
│   ├── vite.config.js     # Vite dev port and host configuration
│   ├── index.html         # HTML root and web typography import
│   ├── public/
│   │   └── sw.js          # Service worker listening for push events
│   └── src/
│       ├── main.jsx       # React mounting entrypoint
│       ├── App.jsx        # Main Dashboard UI & Notification subscription logic
│       └── index.css      # Custom dark/light mode glassmorphic UI stylesheet
└── README.md              # Startup, Supabase structure, and deployment instructions
```

---

## 🚀 Local Installation & Running

### Step 1: Start the Backend (FastAPI)
1. Open a terminal, navigate to the `backend/` directory:
   ```bash
   cd backend
   ```
2. Create and activate a Python virtual environment:
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   ```
3. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Start the Uvicorn server:
   ```bash
   python main.py
   # Or directly:
   uvicorn main:app --reload --port 8000
   ```
   *Note: On first startup, the backend automatically generates a secure set of VAPID keys in `backend/vapid_keys/` and seeds a default Thursday Cloud Computing lecture in `LAB002`.*

---

### Step 2: Start the Frontend (Vite + React)
1. Open a new terminal, navigate to the `frontend/` directory:
   ```bash
   cd frontend
   ```
2. Install npm packages:
   ```bash
   npm install
   ```
3. Run the development server:
   ```bash
   npm run dev
   ```
4. Open the application in your browser at `http://localhost:5173`.
5. Click **"Sync HTML"** at the top right. This queries the backend parser, reads the existing `timetable-pdf/index.html` timetable file, clears the database, and imports all MSc (IT) Sem 3 subjects into the interactive grid.

---

## 📱 Testing Push Notifications on Mobile (Physical Device)

Because the Vite configuration sets `server.host: true`, the dev server is exposed to your local network.
1. Find your computer's local IP address (e.g. `192.168.1.15`).
2. Open the browser on your phone and go to `http://192.168.1.15:5173`.
3. Toggle the **"Push Notifications"** switch in the Notifications panel.
4. When prompted, **Allow notifications** on your browser.
5. Tap **"Send Test Push"** to receive an immediate demonstration alert!

---

## ⚡ Supabase Setup (PostgreSQL)

To shift the application storage from SQLite to a live production database on **Supabase**:

### Step 1: Run the Database Schema
In the Supabase Dashboard, open your project, go to the **SQL Editor**, and run the following script to create the required tables:

```sql
-- 1. Create lectures table
CREATE TABLE lectures (
    id SERIAL PRIMARY KEY,
    subject_code VARCHAR(255) NOT NULL,
    subject_name VARCHAR(255) NOT NULL,
    type VARCHAR(50) DEFAULT 'Lec',
    day_of_week VARCHAR(50) NOT NULL,
    start_time VARCHAR(5) NOT NULL, -- HH:MM
    end_time VARCHAR(5) NOT NULL,   -- HH:MM
    room VARCHAR(255),
    teacher VARCHAR(255),
    color_scheme VARCHAR(50) DEFAULT 'blue'
);

-- 2. Create push subscriptions table
CREATE TABLE push_subscriptions (
    id SERIAL PRIMARY KEY,
    endpoint TEXT NOT NULL UNIQUE,
    p256dh TEXT NOT NULL,
    auth TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 3. Create notification logs table
CREATE TABLE notification_logs (
    id SERIAL PRIMARY KEY,
    lecture_id INTEGER REFERENCES lectures(id) ON DELETE CASCADE,
    event_type VARCHAR(50) NOT NULL, -- '10_min_before', 'started'
    sent_date VARCHAR(10) NOT NULL  -- YYYY-MM-DD
);

-- Indexing for performance
CREATE INDEX idx_lectures_day ON lectures(day_of_week);
CREATE INDEX idx_logs_date_event ON notification_logs(sent_date, event_type);
```

### Step 2: Configure Environment Variables
1. Copy your Supabase PostgreSQL Connection String (located in *Project Settings > Database > Connection string > URI*). Make sure to replace the password placeholder with your actual database password.
2. In your `backend/` directory, create a `.env` file:
   ```env
   DATABASE_URL=postgresql://postgres.yourprojectid:yourpassword@aws-0-us-east-1.pooler.supabase.com:6543/postgres
   ```
3. Restart your FastAPI backend. SQLAlchemy will automatically connect to Supabase PostgreSQL, read the schema, and configure migrations!

---

## 🌐 Deploying Continuously

### 1. Backend Deployment (e.g. Render / Heroku)
- Deploy the `backend` folder as a Python web service.
- Configure the environment variable `DATABASE_URL` in the service settings pointing to Supabase.
- Add VAPID environment overrides or upload the persistent key files to ensure subscriptions persist across server restarts.

### 2. Frontend Deployment (e.g. Vercel / Netlify)
- Set up a build override for the `frontend` folder using command `npm run build` and publish directory `dist`.
- Update the `API_BASE_URL` in `frontend/src/App.jsx` to point to your live backend endpoint.
- HTTPS is forced by modern browsers for Web Push subscriptions. All standard frontend deployment hosts (Vercel, Netlify, Cloudflare Pages) provide SSL certificates automatically.
