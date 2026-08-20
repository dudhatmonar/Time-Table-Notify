import React, { useState, useEffect, useMemo } from 'react';
import { 
  Plus, Bell, BellOff, Settings, Calendar, List, 
  Download, Moon, Sun, Loader2, AlertCircle, MapPin, 
  Clock, User, Trash2, RefreshCw, X, Play
} from 'lucide-react';

const API_BASE_URL = import.meta.env.VITE_API_URL || (
  window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
    ? 'http://localhost:8000/api'
    : `http://${window.location.hostname}:8000/api`
);
const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

// Utility to convert VAPID public key
function urlBase64ToUint8Array(base64String) {
  const padding = '='.repeat((4 - base64String.length % 4) % 4);
  const base64 = (base64String + padding)
    .replace(/\-/g, '+')
    .replace(/_/g, '/');

  const rawData = window.atob(base64);
  const outputArray = new Uint8Array(rawData.length);

  for (let i = 0; i < rawData.length; ++i) {
    outputArray[i] = rawData.charCodeAt(i);
  }
  return outputArray;
}

export default function App() {
  // State variables
  const [lectures, setLectures] = useState([]);
  const [loading, setLoading] = useState(true);
  const [importing, setImporting] = useState(false);
  const [testingPush, setTestingPush] = useState(false);
  
  // UI states
  const [isDark, setIsDark] = useState(true);
  const [viewType, setViewType] = useState('grid'); // 'grid' or 'list'
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [selectedLecture, setSelectedLecture] = useState(null);
  
  // Notification states
  const [permission, setPermission] = useState('default');
  const [isSubscribed, setIsSubscribed] = useState(false);
  const [swRegistration, setSwRegistration] = useState(null);
  const [subscribing, setSubscribing] = useState(false);
  const [pushSupported, setPushSupported] = useState(
    () => ('serviceWorker' in navigator) && ('PushManager' in window)
  );
  
  // Active / Countdown calculations state
  const [currentTime, setCurrentTime] = useState(new Date());
  
  // Form state
  const [formLecture, setFormLecture] = useState({
    subject_code: '',
    subject_name: '',
    type: 'Lec',
    day_of_week: 'Monday',
    start_time: '09:00',
    end_time: '11:00',
    room: '',
    teacher: '',
    color_scheme: 'blue'
  });

  // --- 1. BOOTSTRAP DATA AND NOTIFICATIONS ---
  useEffect(() => {
    fetchLectures();
    setupServiceWorkerAndNotifications();
    
    // Timer to drive live dashboard clock
    const clockTimer = setInterval(() => {
      setCurrentTime(new Date());
    }, 1000);
    
    return () => clearInterval(clockTimer);
  }, []);

  const fetchLectures = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/lectures`);
      if (res.ok) {
        const data = await res.json();
        setLectures(data);
      }
    } catch (err) {
      console.error("Failed to fetch lectures:", err);
    } finally {
      setLoading(false);
    }
  };

  const setupServiceWorkerAndNotifications = async () => {
    if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
      console.warn('Push notifications are not supported by this browser.');
      setPushSupported(false);
      return;
    }

    try {
      setPushSupported(true);
      // Check current Notification permission
      setPermission(Notification.permission);
      
      // Register service worker
      const registration = await navigator.serviceWorker.register('/sw.js');
      setSwRegistration(registration);
      
      // Check if already subscribed to push manager
      const subscription = await registration.pushManager.getSubscription();
      setIsSubscribed(!!subscription);
    } catch (err) {
      console.error("Service worker or notification setup failed:", err);
      setPushSupported(false);
    }
  };

  // --- 2. NOTIFICATIONS MANAGEMENT ---
  const toggleNotifications = async () => {
    if (!swRegistration) return;
    
    setSubscribing(true);
    
    if (isSubscribed) {
      // Unsubscribe logic
      try {
        const subscription = await swRegistration.pushManager.getSubscription();
        if (subscription) {
          await subscription.unsubscribe();
          
          // Inform backend to delete subscription
          await fetch(`${API_BASE_URL}/notifications/unsubscribe`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ endpoint: subscription.endpoint })
          });
        }
        setIsSubscribed(false);
      } catch (e) {
        console.error("Failed to unsubscribe:", e);
      } finally {
        setSubscribing(false);
      }
    } else {
      // Subscribe logic
      try {
        // Request browser permission if default
        const result = await Notification.requestPermission();
        setPermission(result);
        if (result !== 'granted') {
          alert('Notification permissions were denied.');
          setSubscribing(false);
          return;
        }

        // Fetch VAPID Public Key from backend
        const keyRes = await fetch(`${API_BASE_URL}/notifications/vapid-public-key`);
        const { publicKey } = await keyRes.json();
        const convertedKey = urlBase64ToUint8Array(publicKey);

        // Subscribe to Push Service
        const subscription = await swRegistration.pushManager.subscribe({
          userVisibleOnly: true,
          applicationServerKey: convertedKey
        });

        // Store subscription info on FastAPI backend
        await fetch(`${API_BASE_URL}/notifications/subscribe`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(subscription)
        });

        setIsSubscribed(true);
      } catch (err) {
        console.error("Failed to subscribe user to Web Push:", err);
        alert("Push subscription failed. Ensure backend is running and internet is active.");
      } finally {
        setSubscribing(false);
      }
    }
  };

  const triggerTestNotification = async () => {
    if (!isSubscribed) {
      alert("Please enable notifications in the dashboard first to subscribe this browser!");
      return;
    }
    setTestingPush(true);
    try {
      const res = await fetch(`${API_BASE_URL}/notifications/test`, { method: 'POST' });
      const data = await res.json();
      console.log("Test notification triggered:", data);
    } catch (e) {
      console.error("Test notification failed:", e);
    } finally {
      setTestingPush(false);
    }
  };

  // --- 3. SEED IMPORT TIMETABLE ---
  const importTimetable = async () => {
    setImporting(true);
    try {
      const res = await fetch(`${API_BASE_URL}/import-html`, { method: 'POST' });
      if (res.ok) {
        const result = await res.json();
        alert(`Successfully imported timetable! Sync finished: ${result.imported} lectures saved.`);
        fetchLectures();
      } else {
        const error = await res.json();
        alert(`Import error: ${error.detail}`);
      }
    } catch (e) {
      console.error(e);
      alert("Failed to connect to the backend server. Make sure FastAPI is running on port 8000.");
    } finally {
      setImporting(false);
    }
  };

  // --- 4. FORM AND DRAWERS HANDLERS ---
  const openAddDrawer = () => {
    setSelectedLecture(null);
    setFormLecture({
      subject_code: '',
      subject_name: '',
      type: 'Lec',
      day_of_week: 'Monday',
      start_time: '09:00',
      end_time: '11:00',
      room: '',
      teacher: '',
      color_scheme: 'blue'
    });
    setIsDrawerOpen(true);
  };

  const openEditDrawer = (lecture) => {
    setSelectedLecture(lecture);
    setFormLecture({ ...lecture });
    setIsDrawerOpen(true);
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormLecture(prev => ({ ...prev, [name]: value }));
  };

  const handleColorSelect = (color) => {
    setFormLecture(prev => ({ ...prev, color_scheme: color }));
  };

  const saveLecture = async (e) => {
    e.preventDefault();
    const isEdit = !!selectedLecture;
    const url = isEdit ? `${API_BASE_URL}/lectures/${selectedLecture.id}` : `${API_BASE_URL}/lectures`;
    const method = isEdit ? 'PUT' : 'POST';

    try {
      const res = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formLecture)
      });

      if (res.ok) {
        setIsDrawerOpen(false);
        fetchLectures();
      } else {
        alert("Failed to save lecture details. Check times format (HH:MM).");
      }
    } catch (err) {
      console.error("Save error:", err);
    }
  };

  const deleteLecture = async () => {
    if (!selectedLecture) return;
    if (!confirm(`Are you sure you want to delete ${selectedLecture.subject_name}?`)) return;

    try {
      const res = await fetch(`${API_BASE_URL}/lectures/${selectedLecture.id}`, {
        method: 'DELETE'
      });

      if (res.ok) {
        setIsDrawerOpen(false);
        fetchLectures();
      }
    } catch (err) {
      console.error("Delete error:", err);
    }
  };

  // --- 5. LIVE COUNTER & ACTIVE LECTURE CALCULATIONS ---
  const currentDayName = useMemo(() => currentTime.toLocaleString('en-US', { weekday: 'long' }), [currentTime]);
  
  const currentMinutes = useMemo(() => {
    return currentTime.getHours() * 60 + currentTime.getMinutes();
  }, [currentTime]);

  const activeLectureInfo = useMemo(() => {
    // Check if any lecture is running right now
    const todayLectures = lectures.filter(l => l.day_of_week === currentDayName);
    
    let active = null;
    let upcoming = [];
    
    todayLectures.forEach(l => {
      const [sh, sm] = l.start_time.split(':').map(Number);
      const [eh, em] = l.end_time.split(':').map(Number);
      const startMin = sh * 60 + sm;
      const endMin = eh * 60 + em;
      
      if (currentMinutes >= startMin && currentMinutes < endMin) {
        active = l;
      } else if (startMin > currentMinutes) {
        upcoming.push({ lecture: l, startMin });
      }
    });

    // Sort upcoming by start minutes
    upcoming.sort((a, b) => a.startMin - b.startMin);
    const nextItem = upcoming[0] || null;

    let countdownString = '';
    let countdownMinutes = 0;
    if (nextItem) {
      countdownMinutes = nextItem.startMin - currentMinutes;
      const hours = Math.floor(countdownMinutes / 60);
      const mins = countdownMinutes % 60;
      countdownString = hours > 0 ? `${hours}h ${mins}m` : `${mins}m`;
    }

    return {
      active,
      next: nextItem ? nextItem.lecture : null,
      countdown: countdownString,
      countdownMinutes,
      todayAgenda: todayLectures.sort((a, b) => a.start_time.localeCompare(b.start_time))
    };
  }, [lectures, currentDayName, currentMinutes]);

  // --- 6. GRID STRUCTURE SETUP ---
  // Extract and compile unique sorted time slots to build the calendar grid
  const timeSlots = useMemo(() => {
    const slots = lectures.map(l => `${l.start_time}–${l.end_time}`);
    const unique = Array.from(new Set(slots));
    return unique.sort((a, b) => {
      const t1 = a.split('–')[0] || a.split('-')[0];
      const t2 = b.split('–')[0] || b.split('-')[0];
      return t1.localeCompare(t2);
    });
  }, [lectures]);

  // Helper to retrieve lecture mapped to a specific Day + Time Slot
  const getLectureForSlot = (day, slot) => {
    return lectures.find(l => {
      const itemSlot = `${l.start_time}–${l.end_time}`;
      return l.day_of_week === day && itemSlot === slot;
    });
  };

  const handleThemeToggle = () => {
    setIsDark(prev => {
      const nextTheme = !prev;
      if (nextTheme) {
        document.body.classList.remove('light-theme');
      } else {
        document.body.classList.add('light-theme');
      }
      return nextTheme;
    });
  };

  return (
    <div className="app-container">
      {/* HEADER SECTION */}
      <header className="app-header">
        <div className="brand-section">
          <h1>📅 MSc (IT) Sem 3 Hub</h1>
          <p>Interactive Timetable &middot; Automatic Notification Hub</p>
        </div>
        
        <div className="header-actions">
          <button className="btn btn-secondary" onClick={handleThemeToggle} title="Toggle Dark/Light Mode">
            {isDark ? <Sun size={16} /> : <Moon size={16} />}
            Theme
          </button>
          
          <button 
            className="btn btn-secondary" 
            onClick={importTimetable} 
            disabled={importing}
            title="Import Sem 3 schedule from HTML"
          >
            {importing ? <Loader2 size={16} className="animate-spin" /> : <Download size={16} />}
            Sync HTML
          </button>
          
          <button className="btn btn-primary" onClick={openAddDrawer}>
            <Plus size={16} /> Add Class
          </button>
        </div>
      </header>

      {/* DASHBOARD GRID */}
      <div className="dashboard-grid">
        
        {/* SIDEBAR */}
        <aside className="sidebar">
          
          {/* TODAY STATUS PANEL */}
          <div className="panel-card">
            <h2>Today's Overview</h2>
            
            <div className="status-indicator">
              <span className={`status-dot ${activeLectureInfo.active ? 'active' : 'idle'}`}></span>
              <span>{activeLectureInfo.active ? 'Lecture in Progress' : 'No Current Class'}</span>
            </div>

            {activeLectureInfo.active && (
              <div className={`active-class-details lecture-card ${activeLectureInfo.active.color_scheme}`}>
                <div>
                  <span className="lecture-code">{activeLectureInfo.active.subject_code}</span>
                  <h3>{activeLectureInfo.active.subject_name}</h3>
                </div>
                <div className="lecture-meta" style={{marginTop: '10px'}}>
                  <span>📍 Room: {activeLectureInfo.active.room}</span>
                  <span>⏰ {activeLectureInfo.active.start_time} - {activeLectureInfo.active.end_time}</span>
                </div>
              </div>
            )}

            {activeLectureInfo.next ? (
              <div style={{ marginTop: '16px' }}>
                <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                  Next Class: <strong>{activeLectureInfo.next.subject_name}</strong> in
                </span>
                <span className="countdown-text">{activeLectureInfo.countdown}</span>
                {activeLectureInfo.countdownMinutes <= 10 && (
                  <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', fontSize: '11px', color: '#f87171', marginTop: '6px', fontWeight: 'bold' }}>
                    <AlertCircle size={12} /> Class starting soon!
                  </span>
                )}
              </div>
            ) : (
              <div style={{ marginTop: '16px', fontSize: '13px', color: 'var(--text-muted)' }}>
                No more classes scheduled for today.
              </div>
            )}
          </div>

          {/* ALERTS SETUP CONFIG */}
          <div className="panel-card">
            <h2>Notifications</h2>
            
            <div className="settings-list">
              <div className="setting-item">
                <div className="setting-info">
                  <h4>Push Notifications</h4>
                  <p>{isSubscribed ? 'Alerts active on this device' : 'Register phone/browser alerts'}</p>
                </div>
                <label className="switch">
                  <input 
                    type="checkbox" 
                    checked={isSubscribed} 
                    onChange={toggleNotifications}
                    disabled={subscribing || !pushSupported}
                  />
                  <span className="slider"></span>
                </label>
              </div>

              {/* Secure context warnings and permission error messaging */}
              {!pushSupported && (
                <div style={{ color: '#f87171', fontSize: '12px', marginTop: '10px', padding: '8px', background: 'rgba(248,113,113,0.1)', borderRadius: '6px', border: '1px solid rgba(248,113,113,0.2)', lineHeight: '1.4' }}>
                  ⚠️ Push Notifications are not supported in this browser context. Note: Web Push requires a secure origin (HTTPS or localhost).
                </div>
              )}
              {pushSupported && (window.location.protocol !== 'https:' && window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1') && (
                <div style={{ color: '#fb923c', fontSize: '12px', marginTop: '10px', padding: '8px', background: 'rgba(251,146,60,0.1)', borderRadius: '6px', border: '1px solid rgba(251,146,60,0.2)', lineHeight: '1.4' }}>
                  ⚠️ Insecure Connection: When accessing from a mobile device, you must configure Chrome Flags (or use a secure tunnel) to treat this IP as secure, otherwise notifications are disabled.
                </div>
              )}
              {pushSupported && permission === 'denied' && (
                <div style={{ color: '#f87171', fontSize: '12px', marginTop: '10px', padding: '8px', background: 'rgba(248,113,113,0.1)', borderRadius: '6px', border: '1px solid rgba(248,113,113,0.2)', lineHeight: '1.4' }}>
                  ⚠️ Notification permissions were denied. Please clear/reset browser permissions for this site to re-enable.
                </div>
              )}

              <div style={{ borderTop: '1px solid var(--border-color)', paddingTop: '14px', marginTop: '12px' }}>
                <button 
                  className="btn btn-secondary" 
                  onClick={triggerTestNotification}
                  disabled={testingPush || !isSubscribed || !pushSupported}
                  style={{ width: '100%' }}
                >
                  {testingPush ? <Loader2 size={14} className="animate-spin" /> : <Play size={14} />}
                  Send Test Push
                </button>
              </div>
            </div>
          </div>

          {/* AGENDA COMPACT VIEW */}
          <div className="panel-card">
            <h2>Today's Schedule ({currentDayName})</h2>
            
            {activeLectureInfo.todayAgenda.length > 0 ? (
              <div className="agenda-list">
                {activeLectureInfo.todayAgenda.map(l => (
                  <div key={l.id} className="agenda-item" onClick={() => openEditDrawer(l)} style={{ cursor: 'pointer' }}>
                    <div className="agenda-time">
                      {l.start_time} - {l.end_time}
                    </div>
                    <div className="agenda-info">
                      <div className="agenda-subject">{l.subject_code} &middot; {l.subject_name}</div>
                      <div className="agenda-meta">
                        📍 {l.room || 'N/A'} &middot; 👤 {l.teacher || 'N/A'}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div style={{ fontSize: '13px', color: 'var(--text-muted)', textAlign: 'center', padding: '10px 0' }}>
                Relax! No classes scheduled today.
              </div>
            )}
          </div>

        </aside>

        {/* TIMETABLE VIEW CONTAINER */}
        <main className="timetable-container">
          
          <div className="timetable-header-row">
            <h2 style={{ fontFamily: 'var(--font-title)', fontSize: '22px' }}>
              Weekly Timetable
            </h2>
            
            <div className="view-selector">
              <button 
                className={`view-btn ${viewType === 'grid' ? 'active' : ''}`}
                onClick={() => setViewType('grid')}
              >
                <Calendar size={14} style={{ marginRight: '4px', verticalAlign: 'middle' }} />
                Grid View
              </button>
              <button 
                className={`view-btn ${viewType === 'list' ? 'active' : ''}`}
                onClick={() => setViewType('list')}
              >
                <List size={14} style={{ marginRight: '4px', verticalAlign: 'middle' }} />
                Agenda View
              </button>
            </div>
          </div>

          {loading ? (
            <div style={{ display: 'flex', justifyContent: 'center', padding: '100px 0' }}>
              <Loader2 className="animate-spin" size={40} style={{ color: 'var(--accent)' }} />
            </div>
          ) : lectures.length === 0 ? (
            <div className="panel-card" style={{ textAlign: 'center', padding: '60px 20px' }}>
              <AlertCircle size={48} style={{ color: 'var(--text-muted)', marginBottom: '16px' }} />
              <h3 style={{ marginBottom: '8px' }}>Your Timetable is Empty</h3>
              <p style={{ color: 'var(--text-muted)', marginBottom: '20px' }}>
                Start by importing the default MSc (IT) Sem 3 timetable or adding your classes manually.
              </p>
              <div style={{ display: 'flex', justifyContent: 'center', gap: '12px' }}>
                <button className="btn btn-primary" onClick={importTimetable} disabled={importing}>
                  {importing ? <Loader2 size={16} className="animate-spin" /> : <Download size={16} />}
                  Import Default Schedule
                </button>
                <button className="btn btn-secondary" onClick={openAddDrawer}>
                  <Plus size={16} /> Add Class Manually
                </button>
              </div>
            </div>
          ) : viewType === 'grid' ? (
            
            /* GRID VIEW RENDERING */
            <div className="grid-wrapper">
              <table>
                <thead>
                  <tr>
                    <th className="time-header-cell">Time</th>
                    {DAYS.map(day => (
                      <th key={day}>{day}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {timeSlots.map(slot => (
                    <tr key={slot}>
                      <td className="time-header-cell">{slot}</td>
                      {DAYS.map(day => {
                        const lecture = getLectureForSlot(day, slot);
                        return (
                          <td key={day}>
                            {lecture ? (
                              <div 
                                className={`lecture-card ${lecture.color_scheme}`}
                                onClick={() => openEditDrawer(lecture)}
                              >
                                <div className="card-header-info">
                                  <span className="lecture-code">{lecture.subject_code}</span>
                                  <span className="lecture-type-badge">{lecture.type}</span>
                                </div>
                                <div className="lecture-name">{lecture.subject_name}</div>
                                <div className="lecture-meta">
                                  <span>📍 {lecture.room || 'N/A'}</span>
                                  <span>👤 {lecture.teacher || 'N/A'}</span>
                                </div>
                              </div>
                            ) : null}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            
            /* LIST VIEW RENDERING (FOR MOBILE OPTIMIZED OR LIST MODE) */
            <div className="timetable-list-view">
              {DAYS.map(day => {
                const dayLectures = lectures.filter(l => l.day_of_week === day);
                if (dayLectures.length === 0) return null;
                
                return (
                  <div key={day} className="agenda-day-group">
                    <div className="agenda-day-title">
                      <span>{day}</span>
                    </div>
                    <div className="mobile-cards-list">
                      {dayLectures.sort((a,b) => a.start_time.localeCompare(b.start_time)).map(lecture => (
                        <div 
                          key={lecture.id}
                          className={`lecture-card mobile-lecture-card ${lecture.color_scheme}`}
                          onClick={() => openEditDrawer(lecture)}
                        >
                          <div className="card-header-info">
                            <span className="lecture-code" style={{ fontSize: '13px' }}>
                              {lecture.subject_code} &middot; {lecture.type}
                            </span>
                            <span style={{ fontSize: '11px', fontWeight: 'bold' }}>
                              ⏰ {lecture.start_time} - {lecture.end_time}
                            </span>
                          </div>
                          <div className="lecture-name" style={{ fontSize: '14px', margin: '4px 0 8px 0' }}>
                            {lecture.subject_name}
                          </div>
                          <div className="lecture-meta">
                            <span>📍 Room: {lecture.room || 'N/A'}</span>
                            <span>👤 Teacher: {lecture.teacher || 'N/A'}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </main>
      </div>

      {/* EDIT / CREATE DRAWER DRAWER */}
      {isDrawerOpen && (
        <div className="modal-overlay" onClick={() => setIsDrawerOpen(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            
            <div className="modal-header">
              <h3>{selectedLecture ? 'Edit Lecture' : 'Add New Lecture'}</h3>
              <button className="close-btn" onClick={() => setIsDrawerOpen(false)}>
                <X size={20} />
              </button>
            </div>

            <form onSubmit={saveLecture} style={{ display: 'flex', flexDirection: 'column', flexGrow: 1 }}>
              
              <div className="form-group">
                <label>Subject Code</label>
                <input 
                  type="text" 
                  name="subject_code" 
                  className="form-control" 
                  placeholder="e.g. IT627" 
                  value={formLecture.subject_code}
                  onChange={handleInputChange}
                  required
                />
              </div>

              <div className="form-group">
                <label>Subject Name</label>
                <input 
                  type="text" 
                  name="subject_name" 
                  className="form-control" 
                  placeholder="e.g. Cloud Computing" 
                  value={formLecture.subject_name}
                  onChange={handleInputChange}
                  required
                />
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>Type</label>
                  <select 
                    name="type" 
                    className="form-control" 
                    value={formLecture.type}
                    onChange={handleInputChange}
                  >
                    <option value="Lec">Lecture</option>
                    <option value="Lab">Lab Session</option>
                    <option value="Seminar">Seminar</option>
                    <option value="Tutorial">Tutorial</option>
                  </select>
                </div>
                
                <div className="form-group">
                  <label>Day of the Week</label>
                  <select 
                    name="day_of_week" 
                    className="form-control" 
                    value={formLecture.day_of_week}
                    onChange={handleInputChange}
                  >
                    {DAYS.map(day => (
                      <option key={day} value={day}>{day}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>Start Time (24h)</label>
                  <input 
                    type="text" 
                    name="start_time" 
                    className="form-control" 
                    placeholder="e.g. 09:00" 
                    value={formLecture.start_time}
                    onChange={handleInputChange}
                    required
                  />
                </div>
                
                <div className="form-group">
                  <label>End Time (24h)</label>
                  <input 
                    type="text" 
                    name="end_time" 
                    className="form-control" 
                    placeholder="e.g. 11:00" 
                    value={formLecture.end_time}
                    onChange={handleInputChange}
                    required
                  />
                </div>
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>Room / Lab</label>
                  <input 
                    type="text" 
                    name="room" 
                    className="form-control" 
                    placeholder="e.g. LAB002" 
                    value={formLecture.room}
                    onChange={handleInputChange}
                  />
                </div>
                
                <div className="form-group">
                  <label>Instructor</label>
                  <input 
                    type="text" 
                    name="teacher" 
                    className="form-control" 
                    placeholder="e.g. AM1" 
                    value={formLecture.teacher}
                    onChange={handleInputChange}
                  />
                </div>
              </div>

              <div className="form-group">
                <label>UI Highlight Theme</label>
                <div className="color-picker">
                  {['blue', 'green', 'red', 'purple', 'orange'].map(color => (
                    <span 
                      key={color} 
                      className={`color-option ${color} ${formLecture.color_scheme === color ? 'selected' : ''}`}
                      onClick={() => handleColorSelect(color)}
                    ></span>
                  ))}
                </div>
              </div>

              <div className="modal-actions">
                {selectedLecture && (
                  <button 
                    type="button" 
                    className="btn btn-danger" 
                    onClick={deleteLecture}
                    style={{ flexGrow: 0, padding: '10px 14px' }}
                    title="Delete this lecture"
                  >
                    <Trash2 size={16} />
                  </button>
                )}
                
                <button 
                  type="button" 
                  className="btn btn-secondary" 
                  onClick={() => setIsDrawerOpen(false)}
                >
                  Cancel
                </button>
                
                <button type="submit" className="btn btn-primary">
                  Save Changes
                </button>
              </div>

            </form>
          </div>
        </div>
      )}
    </div>
  );
}
