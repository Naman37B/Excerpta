import sqlite3
from pathlib import Path
from contextlib import closing

DB_PATH = Path("./tracker.db")

# `with sqlite3.connect(...) as conn:` only commits or rolls back the
# transaction on exit — it does NOT close the connection (this is documented
# Python behavior, not a bug in sqlite3, but it's a very common surprise).
# Wrapping with contextlib.closing() so every connection actually closes.

def init_db():
    with closing(sqlite3.connect(DB_PATH)) as conn:
        with conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS jobs (
                    job_id TEXT PRIMARY KEY,
                    document_id TEXT,
                    filename TEXT,
                    status TEXT
                )
            ''')

def create_job(job_id: str, document_id: str, filename: str, status: str):
    init_db()
    with closing(sqlite3.connect(DB_PATH)) as conn:
        with conn:
            conn.execute(
                "INSERT INTO jobs (job_id, document_id, filename, status) VALUES (?, ?, ?, ?)",
                (job_id, document_id, filename, status)
            )

def update_job_status(job_id: str, status: str):
    with closing(sqlite3.connect(DB_PATH)) as conn:
        with conn:
            conn.execute("UPDATE jobs SET status = ? WHERE job_id = ?", (status, job_id))

def get_job(job_id: str) -> dict:
    init_db()
    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

def list_completed_documents() -> list[dict]:
    """Distinct successfully-ingested documents, most recent first —
    what the frontend's document-scoping picker actually lists."""
    init_db()
    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT document_id, filename, MAX(rowid) as latest "
            "FROM jobs WHERE status = 'Complete' "
            "GROUP BY document_id ORDER BY latest DESC"
        ).fetchall()
        return [{"document_id": r["document_id"], "filename": r["filename"]} for r in rows]