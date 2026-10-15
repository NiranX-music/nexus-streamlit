"""
core/db.py - Sovereign High-Speed SQLite Cache for PW Hub v2.
Uses WAL mode, in-memory temp stores, and indexed tables for sub-millisecond
lookups, offline test banks, and persistent PDF cache.
"""
import os
import sqlite3
import json
import time
from typing import List, Dict, Any, Optional

DB_PATH = os.path.join("data", "nexus_vault.db")
if not os.path.exists(DB_PATH) and os.path.exists(os.path.join("data", "pw_vault.db")):
    import shutil
    try:
        shutil.copyfile(os.path.join("data", "pw_vault.db"), DB_PATH)
    except Exception:
        pass

def get_connection() -> sqlite3.Connection:
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    # Ultra-fast SQLite pragmas
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA temp_store = MEMORY;")
    conn.execute("PRAGMA cache_size = -64000;") # 64MB cache
    return conn

def init_db():
    """Initializes tables and indexes."""
    conn = get_connection()
    with conn:
        # 1. Batches table
        conn.execute("""
        CREATE TABLE IF NOT EXISTS batches (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            slug TEXT,
            is_free INTEGER DEFAULT 0,
            is_starred INTEGER DEFAULT 0,
            raw_json TEXT,
            updated_at REAL
        );
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_batches_starred ON batches(is_starred);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_batches_free ON batches(is_free);")

        # 2. Tests table
        conn.execute("""
        CREATE TABLE IF NOT EXISTS tests (
            test_id TEXT PRIMARY KEY,
            batch_id TEXT,
            batch_name TEXT,
            mapping_id TEXT,
            name TEXT NOT NULL,
            timeline TEXT,
            attempted INTEGER DEFAULT 0,
            is_free INTEGER DEFAULT 0,
            total_questions INTEGER DEFAULT 0,
            total_marks REAL DEFAULT 0,
            max_duration INTEGER DEFAULT 0,
            start_time TEXT,
            end_time TEXT,
            formatted_start_date TEXT,
            formatted_end_date TEXT,
            timeline_desc TEXT,
            raw_json TEXT,
            updated_at REAL
        );
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tests_batch ON tests(batch_id);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tests_timeline ON tests(timeline);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tests_name ON tests(name);")

        # 3. Test Questions Cache
        conn.execute("""
        CREATE TABLE IF NOT EXISTS questions (
            test_id TEXT PRIMARY KEY,
            questions_json TEXT NOT NULL,
            question_count INTEGER DEFAULT 0,
            updated_at REAL
        );
        """)

        # 4. Curated PDF Binary Store (Zero Re-render on download)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS test_pdfs (
            test_id TEXT PRIMARY KEY,
            booklet_pdf BLOB,
            solutions_pdf BLOB,
            omr_pdf BLOB,
            zip_pack BLOB,
            qna_pdf BLOB,
            updated_at REAL
        );
        """)
        try:
            conn.execute("ALTER TABLE test_pdfs ADD COLUMN qna_pdf BLOB;")
        except Exception:
            pass
    conn.close()

# --- BATCH OPERATIONS ---
def save_batches(batches: List[Dict[str, Any]]):
    if not batches:
        return
    now = time.time()
    conn = get_connection()
    with conn:
        conn.executemany("""
        INSERT INTO batches (id, name, slug, is_free, is_starred, raw_json, updated_at)
        VALUES (:id, :name, :slug, :is_free, :is_starred, :raw_json, :updated_at)
        ON CONFLICT(id) DO UPDATE SET
            name = excluded.name,
            slug = excluded.slug,
            is_free = excluded.is_free,
            is_starred = excluded.is_starred,
            raw_json = excluded.raw_json,
            updated_at = excluded.updated_at
        """, [
            {
                "id": b["_id"],
                "name": b.get("name", "Unnamed Batch"),
                "slug": b.get("slug", ""),
                "is_free": 1 if b.get("is_free") else 0,
                "is_starred": 1 if b.get("is_starred") else 0,
                "raw_json": json.dumps(b),
                "updated_at": now
            }
            for b in batches
        ])
    conn.close()

def get_cached_batches(starred_only: bool = False, paid_only: bool = False, free_only: bool = False) -> List[Dict[str, Any]]:
    conn = get_connection()
    query = "SELECT raw_json FROM batches WHERE 1=1"
    params = []
    if starred_only:
        query += " AND is_starred = 1"
    elif paid_only:
        query += " AND is_free = 0"
    elif free_only:
        query += " AND is_free = 1"
    query += " ORDER BY is_starred DESC, name ASC"
    
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [json.loads(r["raw_json"]) for r in rows]

# --- TEST OPERATIONS ---
def save_tests(tests: List[Dict[str, Any]], batch_id: str, batch_name: str = ""):
    if not tests:
        return
    now = time.time()
    conn = get_connection()
    with conn:
        conn.executemany("""
        INSERT INTO tests (
            test_id, batch_id, batch_name, mapping_id, name, timeline, attempted, is_free,
            total_questions, total_marks, max_duration, start_time, end_time,
            formatted_start_date, formatted_end_date, timeline_desc, raw_json, updated_at
        ) VALUES (
            :test_id, :batch_id, :batch_name, :mapping_id, :name, :timeline, :attempted, :is_free,
            :total_questions, :total_marks, :max_duration, :start_time, :end_time,
            :formatted_start_date, :formatted_end_date, :timeline_desc, :raw_json, :updated_at
        )
        ON CONFLICT(test_id) DO UPDATE SET
            batch_id = excluded.batch_id,
            batch_name = excluded.batch_name,
            mapping_id = excluded.mapping_id,
            name = excluded.name,
            timeline = excluded.timeline,
            attempted = excluded.attempted,
            is_free = excluded.is_free,
            total_questions = excluded.total_questions,
            total_marks = excluded.total_marks,
            max_duration = excluded.max_duration,
            start_time = excluded.start_time,
            end_time = excluded.end_time,
            formatted_start_date = excluded.formatted_start_date,
            formatted_end_date = excluded.formatted_end_date,
            timeline_desc = excluded.timeline_desc,
            raw_json = excluded.raw_json,
            updated_at = excluded.updated_at
        """, [
            {
                "test_id": t["test_id"],
                "batch_id": batch_id,
                "batch_name": batch_name or t.get("batch_name", ""),
                "mapping_id": t.get("mapping_id"),
                "name": t.get("name", "PW Test"),
                "timeline": t.get("timeline", "past"),
                "attempted": 1 if t.get("attempted") else 0,
                "is_free": 1 if t.get("is_free") else 0,
                "total_questions": t.get("total_questions", 0),
                "total_marks": t.get("total_marks", 0),
                "max_duration": t.get("max_duration", 0),
                "start_time": t.get("start_time", ""),
                "end_time": t.get("end_time", ""),
                "formatted_start_date": t.get("formatted_start_date", ""),
                "formatted_end_date": t.get("formatted_end_date", ""),
                "timeline_desc": t.get("timeline_desc", ""),
                "raw_json": json.dumps(t),
                "updated_at": now
            }
            for t in tests
        ])
    conn.close()

def get_tests_by_batch(batch_id: str) -> List[Dict[str, Any]]:
    conn = get_connection()
    rows = conn.execute("SELECT raw_json FROM tests WHERE batch_id = ? ORDER BY start_time DESC", (batch_id,)).fetchall()
    conn.close()
    return [json.loads(r["raw_json"]) for r in rows]

def search_tests_db(query_text: str = "", timeline_filter: str = "", limit: int = 200, offset: int = 0) -> List[Dict[str, Any]]:
    conn = get_connection()
    q = "SELECT raw_json FROM tests WHERE 1=1"
    params = []
    if query_text:
        q += " AND (name LIKE ? OR batch_name LIKE ?)"
        like_p = f"%{query_text}%"
        params.extend([like_p, like_p])
    if timeline_filter and timeline_filter != "all":
        q += " AND timeline = ?"
        params.append(timeline_filter)
    q += " ORDER BY start_time DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    rows = conn.execute(q, params).fetchall()
    conn.close()
    return [json.loads(r["raw_json"]) for r in rows]

def get_total_tests_count() -> int:
    conn = get_connection()
    cnt = conn.execute("SELECT COUNT(*) FROM tests").fetchone()[0]
    conn.close()
    return cnt

# --- QUESTION CACHE ---
def save_questions(test_id: str, questions: List[Dict[str, Any]]):
    now = time.time()
    conn = get_connection()
    with conn:
        conn.execute("""
        INSERT INTO questions (test_id, questions_json, question_count, updated_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(test_id) DO UPDATE SET
            questions_json = excluded.questions_json,
            question_count = excluded.question_count,
            updated_at = excluded.updated_at
        """, (test_id, json.dumps(questions), len(questions), now))
    conn.close()

def get_cached_questions(test_id: str) -> Optional[List[Dict[str, Any]]]:
    conn = get_connection()
    row = conn.execute("SELECT questions_json FROM questions WHERE test_id = ?", (test_id,)).fetchone()
    conn.close()
    if row and row["questions_json"]:
        return json.loads(row["questions_json"])
    return None

# --- CURATED PDF BINARY STORE ---
def save_curated_pdfs(test_id: str, booklet_pdf: bytes, solutions_pdf: bytes, omr_pdf: bytes, zip_pack_bytes: bytes, qna_pdf: bytes = None):
    now = time.time()
    conn = get_connection()
    with conn:
        conn.execute("""
        INSERT INTO test_pdfs (test_id, booklet_pdf, solutions_pdf, omr_pdf, zip_pack, qna_pdf, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(test_id) DO UPDATE SET
            booklet_pdf = excluded.booklet_pdf,
            solutions_pdf = excluded.solutions_pdf,
            omr_pdf = excluded.omr_pdf,
            zip_pack = excluded.zip_pack,
            qna_pdf = excluded.qna_pdf,
            updated_at = excluded.updated_at
        """, (test_id, booklet_pdf, solutions_pdf, omr_pdf, zip_pack_bytes, qna_pdf, now))
    conn.close()

def get_cached_curated_pdfs(test_id: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    row = conn.execute("SELECT booklet_pdf, solutions_pdf, omr_pdf, zip_pack, qna_pdf FROM test_pdfs WHERE test_id = ?", (test_id,)).fetchone()
    conn.close()
    if row and row["booklet_pdf"]:
        import io
        zip_io = io.BytesIO(row["zip_pack"]) if row["zip_pack"] else None
        return {
            "booklet_pdf": row["booklet_pdf"],
            "solutions_pdf": row["solutions_pdf"],
            "omr_pdf": row["omr_pdf"],
            "qna_pdf": row["qna_pdf"] if "qna_pdf" in row.keys() else None,
            "zip_pack": zip_io
        }
    return None

# Auto-initialize database on import
init_db()
