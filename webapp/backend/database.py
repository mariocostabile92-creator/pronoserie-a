"""
database.py - PostgreSQL (Neon.tech)
Database persistente con connection pooling.
"""

import os
import psycopg2
import psycopg2.extras
import psycopg2.pool
from datetime import datetime, timezone

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL non configurata nelle variabili d'ambiente!")

# Connection pool: min 1, max 10 connessioni
_pool = None

def _init_pool():
    global _pool
    if _pool is None:
        try:
            _pool = psycopg2.pool.SimpleConnectionPool(1, 10, DATABASE_URL)
        except Exception as e:
            print(f"Errore pool DB: {e}")
            _pool = None

def _get_conn():
    global _pool
    if _pool is None:
        _init_pool()
    if _pool:
        try:
            conn = _pool.getconn()
            conn.autocommit = False
            return conn
        except Exception:
            _pool = None
    # Fallback senza pool
    conn = psycopg2.connect(DATABASE_URL)
    return conn

def _put_conn(conn):
    global _pool
    if _pool and conn:
        try:
            _pool.putconn(conn)
        except Exception:
            try:
                _put_conn(conn)
            except Exception:
                pass


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
    cur.execute("""
        CREATE TABLE IF NOT EXISTS predictions_tracking (
            id SERIAL PRIMARY KEY,
            home TEXT NOT NULL,
            away TEXT NOT NULL,
            data_partita TEXT,
            prob_1 REAL, prob_x REAL, prob_2 REAL,
            suggerimento TEXT,
            confidence REAL,
            confidence_label TEXT,
            over_25 REAL, goal_si REAL,
            gol_attesi REAL,
            bookmaker_live BOOLEAN DEFAULT FALSE,
            risultato_reale TEXT,
            gol_home_reale INTEGER,
            gol_away_reale INTEGER,
            corretto_1x2 BOOLEAN,
            corretto_ou BOOLEAN,
            corretto_goal BOOLEAN,
            created_at TEXT NOT NULL,
            verificato BOOLEAN DEFAULT FALSE
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS referrals (
            id SERIAL PRIMARY KEY,
            referrer_id INTEGER NOT NULL,
            referrer_email TEXT NOT NULL,
            referral_code TEXT UNIQUE NOT NULL,
            referred_email TEXT,
            referred_id INTEGER,
            status TEXT DEFAULT 'pending',
            reward_applied BOOLEAN DEFAULT FALSE,
            created_at TEXT NOT NULL,
            completed_at TEXT
        )
    """)
    # Aggiungi colonna referral_code a users se non esiste
    try:
        cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS referral_code TEXT")
        cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS referred_by INTEGER")
    except Exception:
        pass
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_predictions (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            league TEXT,
            home TEXT NOT NULL,
            away TEXT NOT NULL,
            pronostico TEXT NOT NULL,
            prob REAL,
            confidence TEXT,
            over_under TEXT,
            goal TEXT,
            gol_h_reale INTEGER,
            gol_a_reale INTEGER,
            risultato_reale TEXT,
            corretto BOOLEAN,
            ou_corretto BOOLEAN,
            goal_corretto BOOLEAN,
            verificato BOOLEAN DEFAULT FALSE,
            created_at TEXT NOT NULL,
            match_date TEXT
        )
    """)
    conn.commit()
    cur.close()
    _put_conn(conn)
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
        _put_conn(conn)


def get_user_by_email(email):
    conn = _get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM users WHERE email = %s", (email.lower().strip(),))
    row = cur.fetchone()
    cur.close()
    _put_conn(conn)
    return dict(row) if row else None


def get_user_by_id(user_id):
    conn = _get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    row = cur.fetchone()
    cur.close()
    _put_conn(conn)
    return dict(row) if row else None


def update_plan(user_id, plan):
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE users SET piano = %s WHERE id = %s", (plan, user_id))
    conn.commit()
    ok = cur.rowcount > 0
    cur.close()
    _put_conn(conn)
    return ok


def update_stripe_customer(user_id, stripe_customer_id):
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE users SET stripe_customer_id = %s WHERE id = %s", (stripe_customer_id, user_id))
    conn.commit()
    cur.close()
    _put_conn(conn)


def log_api_call(user_id, endpoint):
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO api_usage (user_id, endpoint, timestamp) VALUES (%s, %s, %s)",
        (user_id, endpoint, datetime.now(timezone.utc).isoformat())
    )
    conn.commit()
    cur.close()
    _put_conn(conn)


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
    _put_conn(conn)
    return row[0] if row else 0


# â”€â”€ TRACKING PREDIZIONI â”€â”€

def save_prediction(home, away, data_partita, pred, bk_live=False):
    """Salva un pronostico nel DB per verifica futura."""
    try:
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO predictions_tracking
            (home, away, data_partita, prob_1, prob_x, prob_2, suggerimento,
             confidence, confidence_label, over_25, goal_si, gol_attesi,
             bookmaker_live, created_at)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT DO NOTHING
        """, (
            home, away, data_partita,
            pred.get("prob_1"), pred.get("prob_x"), pred.get("prob_2"),
            pred.get("suggerimento"), pred.get("confidence"),
            pred.get("confidence_label"),
            pred.get("over_25"), pred.get("goal_si"),
            pred.get("gol_attesi"), bk_live,
            datetime.now(timezone.utc).isoformat()
        ))
        conn.commit()
        cur.close()
        _put_conn(conn)
    except Exception:
        pass


def verify_predictions(risultati_live):
    """Verifica le predizioni passate con i risultati reali."""
    try:
        conn = _get_conn()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        # Prendi predizioni non ancora verificate
        cur.execute("SELECT * FROM predictions_tracking WHERE verificato = FALSE")
        rows = cur.fetchall()

        verificate = 0
        for row in rows:
            home, away = row["home"], row["away"]
            # Cerca il risultato reale
            for ris in risultati_live:
                if ris["home"] == home and ris["away"] == away and ris.get("status") == "FT":
                    gol_h = ris["gol_h"]
                    gol_a = ris["gol_a"]
                    # Determina risultato
                    if gol_h > gol_a:
                        ris_reale = "1"
                    elif gol_h == gol_a:
                        ris_reale = "X"
                    else:
                        ris_reale = "2"
                    # Verifica
                    corretto_1x2 = row["suggerimento"] == ris_reale
                    gol_tot = gol_h + gol_a
                    pred_over = (row["over_25"] or 50) > 50
                    corretto_ou = (gol_tot > 2.5) == pred_over
                    pred_goal = (row["goal_si"] or 50) > 50
                    corretto_goal = (gol_h >= 1 and gol_a >= 1) == pred_goal

                    cur.execute("""
                        UPDATE predictions_tracking SET
                            risultato_reale=%s, gol_home_reale=%s, gol_away_reale=%s,
                            corretto_1x2=%s, corretto_ou=%s, corretto_goal=%s,
                            verificato=TRUE
                        WHERE id=%s
                    """, (ris_reale, gol_h, gol_a, corretto_1x2, corretto_ou, corretto_goal, row["id"]))
                    verificate += 1
                    break

        conn.commit()
        cur.close()
        _put_conn(conn)
        if verificate > 0:
            print(f"âœ… TRACKING: {verificate} predizioni verificate")
    except Exception as e:
        print(f"âš ï¸ Errore tracking: {e}")


def get_tracking_stats():
    """Ritorna le statistiche di accuratezza delle predizioni tracciate."""
    try:
        conn = _get_conn()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT
                COUNT(*) as totale,
                SUM(CASE WHEN corretto_1x2 THEN 1 ELSE 0 END) as ok_1x2,
                SUM(CASE WHEN corretto_ou THEN 1 ELSE 0 END) as ok_ou,
                SUM(CASE WHEN corretto_goal THEN 1 ELSE 0 END) as ok_goal,
                SUM(CASE WHEN corretto_1x2 AND confidence_label='Alta' THEN 1 ELSE 0 END) as ok_alta,
                SUM(CASE WHEN confidence_label='Alta' THEN 1 ELSE 0 END) as tot_alta
            FROM predictions_tracking WHERE verificato = TRUE
        """)
        row = cur.fetchone()
        cur.close()
        _put_conn(conn)
        if row and row["totale"] > 0:
            return {
                "totale": row["totale"],
                "acc_1x2": round(row["ok_1x2"] / row["totale"] * 100, 1),
                "acc_ou": round(row["ok_ou"] / row["totale"] * 100, 1),
                "acc_goal": round(row["ok_goal"] / row["totale"] * 100, 1),
                "acc_alta": round(row["ok_alta"] / row["tot_alta"] * 100, 1) if row["tot_alta"] > 0 else 0,
                "tot_alta": row["tot_alta"],
            }
    except Exception:
        pass
    return None
