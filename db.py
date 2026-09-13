"""SQLite persistence layer for discovered jobs and application tracking."""
import sqlite3
import os
import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "jobs.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    source_id TEXT,
    title TEXT NOT NULL,
    company TEXT NOT NULL,
    location TEXT,
    remote_ok INTEGER DEFAULT 0,
    us_remote INTEGER DEFAULT 0,
    employment_type TEXT DEFAULT 'unknown',
    url TEXT UNIQUE NOT NULL,
    description TEXT,
    posted_date TEXT,
    fetched_at TEXT,
    score REAL DEFAULT 0,
    score_breakdown TEXT,
    visa_flag TEXT DEFAULT 'ok',
    visa_flag_reason TEXT,
    status TEXT DEFAULT 'new',
    notes TEXT DEFAULT '',
    applied_date TEXT,
    tailored_resume_filename TEXT,
    created_at TEXT,
    updated_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_jobs_score ON jobs(score DESC);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
"""


def get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _migrate(conn):
    """Add columns introduced after a user's local DB was first created, so pulling app
    updates never requires deleting existing job/tracking data."""
    existing = {row["name"] for row in conn.execute("PRAGMA table_info(jobs)")}
    additions = {
        "employment_type": "TEXT DEFAULT 'unknown'",
        "tailored_resume_filename": "TEXT",
    }
    for col, decl in additions.items():
        if col not in existing:
            conn.execute(f"ALTER TABLE jobs ADD COLUMN {col} {decl}")


def init_db():
    conn = get_conn()
    conn.executescript(SCHEMA)
    _migrate(conn)
    conn.commit()
    conn.close()


def upsert_job(job):
    """Insert a new job, or refresh scoring fields on an existing one (by URL) without
    touching user-owned fields like status/notes/applied_date."""
    now = job["fetched_at"]
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id FROM jobs WHERE url = ?", (job["url"],))
    existing = cur.fetchone()
    if existing:
        cur.execute(
            """UPDATE jobs SET score=?, score_breakdown=?, visa_flag=?, visa_flag_reason=?,
               remote_ok=?, us_remote=?, employment_type=?, description=?, fetched_at=?, updated_at=?
               WHERE id=?""",
            (
                job["score"], job["score_breakdown"], job["visa_flag"], job["visa_flag_reason"],
                job["remote_ok"], job["us_remote"], job.get("employment_type", "unknown"),
                job["description"], now, now, existing["id"],
            ),
        )
        is_new = False
    else:
        cur.execute(
            """INSERT INTO jobs (source, source_id, title, company, location, remote_ok, us_remote,
               employment_type, url, description, posted_date, fetched_at, score, score_breakdown,
               visa_flag, visa_flag_reason, status, notes, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'new', '', ?, ?)""",
            (
                job["source"], job.get("source_id"), job["title"], job["company"], job["location"],
                job["remote_ok"], job["us_remote"], job.get("employment_type", "unknown"),
                job["url"], job["description"], job["posted_date"],
                now, job["score"], job["score_breakdown"], job["visa_flag"], job["visa_flag_reason"],
                now, now,
            ),
        )
        is_new = True
    conn.commit()
    conn.close()
    return is_new


def _parse_posted_date(value):
    """Best-effort parse of the varied ISO-ish date strings sources provide. Returns a
    timezone-aware datetime, or None if missing/unparseable."""
    if not value:
        return None
    try:
        dt = datetime.datetime.fromisoformat(value)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    return dt


def list_jobs(status=None, min_score=None, search=None, source=None, max_age_days=None):
    conn = get_conn()
    query = "SELECT * FROM jobs WHERE 1=1"
    params = []
    if status:
        query += " AND status = ?"
        params.append(status)
    if min_score is not None:
        query += " AND score >= ?"
        params.append(min_score)
    if source:
        query += " AND source = ?"
        params.append(source)
    if search:
        query += " AND (title LIKE ? OR company LIKE ? OR description LIKE ?)"
        like = f"%{search}%"
        params.extend([like, like, like])
    query += " ORDER BY score DESC, posted_date DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    jobs = [dict(r) for r in rows]

    if max_age_days is not None:
        cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=max_age_days)
        jobs = [j for j in jobs if (_parse_posted_date(j["posted_date"]) or cutoff - datetime.timedelta(seconds=1)) >= cutoff]

    return jobs


def get_job(job_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def update_job_tracking(job_id, status=None, notes=None, applied_date=None):
    conn = get_conn()
    fields, params = [], []
    if status is not None:
        fields.append("status = ?")
        params.append(status)
    if notes is not None:
        fields.append("notes = ?")
        params.append(notes)
    if applied_date is not None:
        fields.append("applied_date = ?")
        params.append(applied_date)
    fields.append("updated_at = ?")
    params.append(datetime.datetime.now().isoformat())
    params.append(job_id)
    conn.execute(f"UPDATE jobs SET {', '.join(fields)} WHERE id = ?", params)
    conn.commit()
    conn.close()


def set_tailored_resume(job_id, filename):
    conn = get_conn()
    conn.execute(
        "UPDATE jobs SET tailored_resume_filename = ?, updated_at = ? WHERE id = ?",
        (filename, datetime.datetime.now().isoformat(), job_id),
    )
    conn.commit()
    conn.close()


def list_applied_jobs():
    """Every job ever marked Applied, regardless of score or posting age — this is a
    historical record, not a discovery feed, so none of the usual filters apply."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM jobs WHERE status = 'applied' ORDER BY applied_date DESC, updated_at DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def stats():
    conn = get_conn()
    total = conn.execute("SELECT COUNT(*) c FROM jobs").fetchone()["c"]
    today = datetime.date.today().isoformat()
    new_today = conn.execute(
        "SELECT COUNT(*) c FROM jobs WHERE substr(fetched_at,1,10) = ?", (today,)
    ).fetchone()["c"]
    by_status = conn.execute("SELECT status, COUNT(*) c FROM jobs GROUP BY status").fetchall()
    conn.close()
    return {
        "total": total,
        "new_today": new_today,
        "by_status": {r["status"]: r["c"] for r in by_status},
    }
