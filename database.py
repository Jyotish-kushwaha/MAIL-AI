import os
from datetime import datetime
from typing import Optional, List
from contextlib import contextmanager

import psycopg2
import psycopg2.extras
from psycopg2 import pool
from dotenv import load_dotenv

load_dotenv()

# ─── Connection Pool ──────────────────────────────────────────────────────────

_pool: pool.ThreadedConnectionPool = None


def _get_pool() -> pool.ThreadedConnectionPool:
    """Lazily create and return the global connection pool."""
    global _pool
    if _pool is None or _pool.closed:
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise EnvironmentError(
                "DATABASE_URL is not set. Add it to your .env file.\n"
                "Format: postgresql://user:password@host:5432/dbname"
            )
        _pool = pool.ThreadedConnectionPool(
            minconn=1,
            maxconn=10,
            dsn=database_url,
            cursor_factory=psycopg2.extras.RealDictCursor,
        )
    return _pool


@contextmanager
def _conn():
    """Yield a connection from the pool, auto-returning it when done."""
    p = _get_pool()
    conn = p.getconn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        p.putconn(conn)


# ─── EmailDatabase ────────────────────────────────────────────────────────────

class EmailDatabase:
    """Production PostgreSQL database for email history and multi-user credentials."""

    def __init__(self, db_path: str = None):
        self._init_db()

    def _init_db(self):
        """Create tables if they don't exist and run alter scripts."""
        with _conn() as conn:
            with conn.cursor() as cur:
                # 1. User Credentials Table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS user_credentials (
                        email         TEXT PRIMARY KEY,
                        token         TEXT,
                        refresh_token TEXT,
                        token_uri     TEXT,
                        client_id     TEXT,
                        client_secret TEXT,
                        scopes        TEXT,
                        created_at    TIMESTAMPTZ
                    )
                """)

                # 2. Email Records Table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS email_records (
                        id            TEXT PRIMARY KEY,
                        thread_id     TEXT,
                        from_address  TEXT,
                        to_address    TEXT,
                        subject       TEXT,
                        email_body    TEXT,
                        reply_subject TEXT,
                        reply_body    TEXT,
                        category      TEXT,
                        status        TEXT,
                        confidence    DOUBLE PRECISION DEFAULT 0.9,
                        processed_at  TIMESTAMPTZ,
                        sent_at       TIMESTAMPTZ,
                        user_email    TEXT
                    )
                """)

                # Safely add user_email if upgrading from old version without recreating
                try:
                    cur.execute("ALTER TABLE email_records ADD COLUMN user_email TEXT;")
                except psycopg2.errors.DuplicateColumn:
                    conn.rollback()  # Rollback just this statement if already exists

                # 3. Indexes
                cur.execute("CREATE INDEX IF NOT EXISTS idx_email_records_status ON email_records (status)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_email_records_category ON email_records (category)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_email_records_user_email ON email_records (user_email)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_email_records_processed_at ON email_records (processed_at DESC)")


    # ── User Tokens Management ────────────────────────────────────────────────

    def upsert_user_tokens(self, email: str, creds_dict: dict):
        """Save or update Google OAuth tokens for a user."""
        with _conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO user_credentials
                        (email, token, refresh_token, token_uri, client_id, client_secret, scopes, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (email) DO UPDATE SET
                        token         = EXCLUDED.token,
                        refresh_token = EXCLUDED.refresh_token,
                        token_uri     = EXCLUDED.token_uri,
                        client_id     = EXCLUDED.client_id,
                        client_secret = EXCLUDED.client_secret,
                        scopes        = EXCLUDED.scopes,
                        created_at    = EXCLUDED.created_at
                """, (
                    email,
                    creds_dict.get("token"),
                    creds_dict.get("refresh_token"),
                    creds_dict.get("token_uri"),
                    creds_dict.get("client_id"),
                    creds_dict.get("client_secret"),
                    ",".join(creds_dict.get("scopes", [])) if creds_dict.get("scopes") else "",
                    datetime.utcnow()
                ))

    def get_user_tokens(self, email: str) -> Optional[dict]:
        """Fetch tokens for a specific user to build Google Credentials."""
        with _conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM user_credentials WHERE email = %s", (email,))
                row = cur.fetchone()
        if row:
            row_dict = dict(row)
            row_dict["scopes"] = row_dict["scopes"].split(",") if row_dict.get("scopes") else []
            return row_dict
        return None

    def get_all_users(self) -> List[dict]:
        """Fetch all connected users to run background email processors."""
        with _conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM user_credentials")
                rows = cur.fetchall()
        result = []
        for row in rows:
            row_dict = dict(row)
            row_dict["scopes"] = row_dict["scopes"].split(",") if row_dict.get("scopes") else []
            result.append(row_dict)
        return result

    # ── Email Records Management ─────────────────────────────────────────────

    def is_already_replied(self, email_id: str, user_email: str) -> bool:
        """Check if a specific user already processed this specific email."""
        with _conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id FROM email_records WHERE id = %s AND user_email = %s AND status IN ('sent', 'draft', 'pending_review')",
                    (email_id, user_email)
                )
                return cur.fetchone() is not None

    def save_email_record(
        self,
        email_id: str,
        user_email: str,
        email_data: dict,
        reply: dict,
        category: str,
        status: str
    ):
        """Insert or replace a processed email record, tied to a user."""
        with _conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO email_records
                        (id, thread_id, from_address, to_address, subject, email_body,
                         reply_subject, reply_body, category, status, confidence, processed_at, user_email)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET
                        thread_id     = EXCLUDED.thread_id,
                        from_address  = EXCLUDED.from_address,
                        to_address    = EXCLUDED.to_address,
                        subject       = EXCLUDED.subject,
                        email_body    = EXCLUDED.email_body,
                        reply_subject = EXCLUDED.reply_subject,
                        reply_body    = EXCLUDED.reply_body,
                        category      = EXCLUDED.category,
                        status        = EXCLUDED.status,
                        confidence    = EXCLUDED.confidence,
                        processed_at  = EXCLUDED.processed_at,
                        user_email    = EXCLUDED.user_email
                """, (
                    email_id,
                    email_data.get("thread_id", ""),
                    email_data.get("from", ""),
                    email_data.get("to", ""),
                    email_data.get("subject", ""),
                    email_data.get("body", ""),
                    reply.get("subject", ""),
                    reply.get("body", ""),
                    category,
                    status,
                    reply.get("confidence", 0.9),
                    datetime.utcnow(),
                    user_email
                ))

    def update_status(self, email_id: str, status: str):
        """Update the status (and sent_at if sending) of an email record."""
        with _conn() as conn:
            with conn.cursor() as cur:
                sent_at = datetime.utcnow() if status == "sent" else None
                cur.execute(
                    "UPDATE email_records SET status = %s, sent_at = %s WHERE id = %s",
                    (status, sent_at, email_id)
                )

    def get_email_record(self, email_id: str) -> Optional[dict]:
        """Fetch a single email record by ID."""
        with _conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM email_records WHERE id = %s", (email_id,))
                row = cur.fetchone()
        return dict(row) if row else None

    def get_history(
        self,
        user_email: str = None,
        limit: int = 50,
        status: str = None,
        category: str = None
    ) -> List[dict]:
        """Get email history with filters."""
        query = "SELECT * FROM email_records WHERE TRUE"
        params: list = []

        if user_email:
            query += " AND user_email = %s"
            params.append(user_email)
        if status:
            query += " AND status = %s"
            params.append(status)
        if category:
            query += " AND category = %s"
            params.append(category)

        query += " ORDER BY processed_at DESC LIMIT %s"
        params.append(limit)

        with _conn() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                rows = cur.fetchall()
        return [dict(r) for r in rows]

    def get_stats(self, user_email: str = None) -> dict:
        """Return aggregate statistics across email records."""
        base_where = "WHERE user_email = %s" if user_email else ""
        params = (user_email,) if user_email else ()
        
        with _conn() as conn:
            with conn.cursor() as cur:
                cur.execute(f"SELECT COUNT(*) AS cnt FROM email_records {base_where}", params)
                total = cur.fetchone()["cnt"]

                cur.execute(f"SELECT COUNT(*) AS cnt FROM email_records WHERE status = 'sent' {'AND user_email = %s' if user_email else ''}", params)
                sent = cur.fetchone()["cnt"]

                cur.execute(f"SELECT COUNT(*) AS cnt FROM email_records WHERE status = 'pending_review' {'AND user_email = %s' if user_email else ''}", params)
                pending = cur.fetchone()["cnt"]

                cur.execute(f"SELECT COUNT(*) AS cnt FROM email_records WHERE status = 'draft' {'AND user_email = %s' if user_email else ''}", params)
                drafts = cur.fetchone()["cnt"]

                cur.execute(f"SELECT COUNT(*) AS cnt FROM email_records WHERE status = 'error' {'AND user_email = %s' if user_email else ''}", params)
                errors = cur.fetchone()["cnt"]

                cur.execute(f"SELECT category, COUNT(*) AS cnt FROM email_records {base_where} GROUP BY category", params)
                categories = {r["category"]: r["cnt"] for r in cur.fetchall()}

                cur.execute(f"SELECT AVG(confidence) AS avg FROM email_records WHERE status = 'sent' {'AND user_email = %s' if user_email else ''}", params)
                avg_conf = cur.fetchone()["avg"] or 0.0

        return {
            "total_processed": total,
            "sent": sent,
            "pending_review": pending,
            "drafts": drafts,
            "errors": errors,
            "avg_confidence": round(float(avg_conf), 3),
            "categories": categories,
        }