"""
database.py - PostgreSQL (Neon.tech)
Database persistente che non si cancella mai.
"""

import os
import psycopg2
import psycopg2.extras
from datetime import datetime, timezone

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://neondb_owner:npg_MH8IvDSTg3mq@ep-soft-voice-aga6gbd9-pooler.c-2.eu-central-1.aws.neon.tech/neondb?sslmode=require"
)


def _get_conn():
    conn = psycopg2.connect(DATABASE_URL)
    return conn


def init_db():
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            piano TEXT DEFAULT 'free',
            stripe_customer_id TEXT,
            created_at TEXT NOT NULL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS api_usage (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            endpoint TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
    """)
    conn.commit()
    cur.close()
    conn.close()
    print("DB PostgreSQL OK")


def create_user(email, password_hash):
    conn = _get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute(
            "INSERT INTO users (email, password_hash, piano, created_at) VALUES (%s, %s, 'free', %s) RETURNING *",
            (email.lower().strip(), password_hash, datetime.now(timezone.utc).isoformat())
        )
        user = dict(cur.fetchone())
        conn.commit()
        return user
    except psycopg2.IntegrityError:
        conn.rollback()
        return None
    finally:
        cur.close()
        conn.close()


def get_user_by_email(email):
    conn = _get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM users WHERE email = %s", (email.lower().strip(),))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return dict(row) if row else None


def get_user_by_id(user_id):
    conn = _get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return dict(row) if row else None


def update_plan(user_id, plan):
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE users SET piano = %s WHERE id = %s", (plan, user_id))
    conn.commit()
    ok = cur.rowcount > 0
    cur.close()
    conn.close()
    return ok


def update_stripe_customer(user_id, stripe_customer_id):
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE users SET stripe_customer_id = %s WHERE id = %s", (stripe_customer_id, user_id))
    conn.commit()
    cur.close()
    conn.close()


def log_api_call(user_id, endpoint):
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO api_usage (user_id, endpoint, timestamp) VALUES (%s, %s, %s)",
        (user_id, endpoint, datetime.now(timezone.utc).isoformat())
    )
    conn.commit()
    cur.close()
    conn.close()


def count_daily_calls(user_id):
    conn = _get_conn()
    cur = conn.cursor()
    oggi = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    cur.execute(
        "SELECT COUNT(*) FROM api_usage WHERE user_id = %s AND timestamp LIKE %s",
        (user_id, f"{oggi}%")
    )
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row[0] if row else 0
