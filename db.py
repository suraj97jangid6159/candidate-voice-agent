import sqlite3
import os
import yaml
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.yaml")

def get_db_path():
    """Get database path from config or environment, ensuring absolute path."""
    # First check environment variable
    env_db_path = os.getenv("APP_DB_PATH")
    if env_db_path:
        if os.path.isabs(env_db_path):
            return env_db_path
        return os.path.join(BASE_DIR, env_db_path)
    
    # Then check config file
    try:
        with open(CONFIG_PATH, "r") as f:
            config = yaml.safe_load(f)
            db_path = config.get("app", {}).get("db_path", "database.db")
            if os.path.isabs(db_path):
                return db_path
            return os.path.join(BASE_DIR, db_path)
    except Exception:
        return os.path.join(BASE_DIR, "database.db")

def init_db():
    """Initialize database with all required tables and indexes."""
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Create candidates table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS candidates (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        phone TEXT NOT NULL,
        current_ctc TEXT,
        expected_ctc TEXT,
        notice_period TEXT,
        skills TEXT,
        resume_text TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    
    # Create jobs table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS jobs (
        id TEXT PRIMARY KEY,
        candidate_id TEXT,
        company_name TEXT NOT NULL,
        job_title TEXT NOT NULL,
        jd_url TEXT,
        jd_text TEXT NOT NULL,
        hr_phone TEXT,
        hr_email TEXT,
        fit_score REAL,
        status TEXT DEFAULT 'PENDING',
        FOREIGN KEY(candidate_id) REFERENCES candidates(id)
    );
    """)
    
    # Create calls table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS calls (
        id TEXT PRIMARY KEY,
        job_id TEXT,
        status TEXT NOT NULL,
        transcript TEXT,
        recording_url TEXT,
        scheduled_callback TIMESTAMP,
        call_duration_seconds INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(job_id) REFERENCES jobs(id)
    );
    """)
    
    # Create security_logs table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS security_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        call_id TEXT,
        violation_type TEXT NOT NULL,
        flagged_text TEXT,
        action_taken TEXT NOT NULL,
        severity TEXT DEFAULT 'MEDIUM',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(call_id) REFERENCES calls(id)
    );
    """)
    
    # Create scheduled_callbacks table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS scheduled_callbacks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        call_id TEXT NOT NULL,
        scheduled_time TIMESTAMP NOT NULL,
        status TEXT DEFAULT 'PENDING',
        attempts INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(call_id) REFERENCES calls(id)
    );
    """)
    
    # Create indexes for performance
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_calls_job_id ON calls(job_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_calls_status ON calls(status);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_security_logs_call_id ON security_logs(call_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_scheduled_callbacks_status ON scheduled_callbacks(status);")
    
    conn.commit()
    
    # Migrate existing databases that predate newer columns
    _migrate_schema(cursor)
    conn.commit()
    conn.close()
    return db_path

def _migrate_schema(cursor):
    """Add columns introduced after initial schema without breaking existing DBs."""
    cursor.execute("PRAGMA table_info(calls)")
    call_columns = {row[1] for row in cursor.fetchall()}
    if "call_duration_seconds" not in call_columns:
        cursor.execute("ALTER TABLE calls ADD COLUMN call_duration_seconds INTEGER DEFAULT 0")
    if "updated_at" not in call_columns:
        cursor.execute("ALTER TABLE calls ADD COLUMN updated_at TIMESTAMP")

    cursor.execute("PRAGMA table_info(security_logs)")
    log_columns = {row[1] for row in cursor.fetchall()}
    if "severity" not in log_columns:
        cursor.execute("ALTER TABLE security_logs ADD COLUMN severity TEXT DEFAULT 'MEDIUM'")

def get_db_connection():
    """Get a database connection with row factory."""
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

# Helper Functions for Candidates
def save_candidate(candidate_id, name, phone, current_ctc, expected_ctc, notice_period, skills, resume_text):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT OR REPLACE INTO candidates (id, name, phone, current_ctc, expected_ctc, notice_period, skills, resume_text)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (candidate_id, name, phone, current_ctc, expected_ctc, notice_period, skills, resume_text))
    conn.commit()
    conn.close()

def get_candidate(candidate_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM candidates WHERE id = ?", (candidate_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_latest_candidate():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM candidates ORDER BY created_at DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

# Helper Functions for Jobs
def save_job(job_id, candidate_id, company_name, job_title, jd_url, jd_text, hr_phone, hr_email, fit_score, status="PENDING"):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT OR REPLACE INTO jobs (id, candidate_id, company_name, job_title, jd_url, jd_text, hr_phone, hr_email, fit_score, status)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (job_id, candidate_id, company_name, job_title, jd_url, jd_text, hr_phone, hr_email, fit_score, status))
    conn.commit()
    conn.close()

def get_job(job_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_jobs_for_candidate(candidate_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM jobs WHERE candidate_id = ?", (candidate_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

# Helper Functions for Calls
def save_call(call_id, job_id, status, transcript="", recording_url=None, scheduled_callback=None, call_duration_seconds=0):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT OR REPLACE INTO calls (id, job_id, status, transcript, recording_url, scheduled_callback, call_duration_seconds)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (call_id, job_id, status, transcript, recording_url, scheduled_callback, call_duration_seconds))
    conn.commit()
    conn.close()

def update_call_transcript(call_id, transcript):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE calls SET transcript = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (transcript, call_id))
    conn.commit()
    conn.close()

def update_call_status(call_id, status, scheduled_callback=None, call_duration_seconds=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    if scheduled_callback and call_duration_seconds is not None:
        cursor.execute("UPDATE calls SET status = ?, scheduled_callback = ?, call_duration_seconds = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", 
                      (status, scheduled_callback, call_duration_seconds, call_id))
    elif scheduled_callback:
        cursor.execute("UPDATE calls SET status = ?, scheduled_callback = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", 
                      (status, scheduled_callback, call_id))
    elif call_duration_seconds is not None:
        cursor.execute("UPDATE calls SET status = ?, call_duration_seconds = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", 
                      (status, call_duration_seconds, call_id))
    else:
        cursor.execute("UPDATE calls SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (status, call_id))
    conn.commit()
    conn.close()

def get_call(call_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM calls WHERE id = ?", (call_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_all_calls_with_details():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT c.*, j.company_name, j.job_title, j.hr_phone, cand.name as candidate_name
    FROM calls c
    JOIN jobs j ON c.job_id = j.id
    JOIN candidates cand ON j.candidate_id = cand.id
    ORDER BY c.created_at DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

# Security Log Functions
def save_security_log(call_id, violation_type, flagged_text, action_taken, severity="MEDIUM"):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO security_logs (call_id, violation_type, flagged_text, action_taken, severity)
    VALUES (?, ?, ?, ?, ?)
    """, (call_id, violation_type, flagged_text, action_taken, severity))
    conn.commit()
    conn.close()

def get_security_logs_for_call(call_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM security_logs WHERE call_id = ? ORDER BY created_at DESC", (call_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_all_security_logs(limit=100):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT sl.*, c.status as call_status, j.company_name
    FROM security_logs sl
    LEFT JOIN calls c ON sl.call_id = c.id
    LEFT JOIN jobs j ON c.job_id = j.id
    ORDER BY sl.created_at DESC
    LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

# Scheduled Callback Functions
def save_scheduled_callback(call_id, scheduled_time):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO scheduled_callbacks (call_id, scheduled_time, status)
    VALUES (?, ?, 'PENDING')
    """, (call_id, scheduled_time))
    conn.commit()
    conn.close()
    return cursor.lastrowid

def get_pending_callbacks():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT sc.*, c.job_id, j.candidate_id, j.hr_phone, cand.name as candidate_name
    FROM scheduled_callbacks sc
    JOIN calls c ON sc.call_id = c.id
    JOIN jobs j ON c.job_id = j.id
    JOIN candidates cand ON j.candidate_id = cand.id
    WHERE sc.status = 'PENDING' AND sc.scheduled_time <= datetime('now', '+5 minutes')
    ORDER BY sc.scheduled_time ASC
    """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def mark_callback_completed(callback_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE scheduled_callbacks SET status = 'COMPLETED' WHERE id = ?", (callback_id,))
    conn.commit()
    conn.close()

# Run initialization if main
if __name__ == "__main__":
    db_path = init_db()
    print(f"Database initialized successfully at: {db_path}")
