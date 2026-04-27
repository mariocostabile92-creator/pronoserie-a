"""
database.py - PostgreSQL (Railway)
Database persistente con connection pooling, transazioni sicure,
migrazioni leggere e vincoli database.
"""

import os
import logging
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta

from dotenv import load_dotenv
import psycopg2
import psycopg2.extras
import psycopg2.pool

# Carica variabili da file .env se presente
load_dotenv()

logger = logging.getLogger(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL non configurata nelle variabili d'ambiente!")

# Connection pool: min 1, max 10 connessioni
_pool = None
_pool_connections = set()


# ─────────────────────────────────────────────
# CONNESSIONI / POOL
# ─────────────────────────────────────────────

def _init_pool():
    """Inizializza il pool PostgreSQL se non esiste."""
    global _pool
    if _pool is None:
        try:
            _pool = psycopg2.pool.SimpleConnectionPool(
                minconn=1,
                maxconn=10,
                dsn=DATABASE_URL,
            )
            logger.info("Pool PostgreSQL inizializzato")
        except Exception as e:
            logger.error(f"Errore inizializzazione pool DB: {e}")
            _pool = None


def _get_conn():
    """Prende una connessione dal pool. Se il pool fallisce, usa una standalone."""
    global _pool

    if _pool is None:
        _init_pool()

    if _pool:
        try:
            conn = _pool.getconn()
            conn.autocommit = False
            _pool_connections.add(id(conn))
            return conn
        except Exception as e:
            logger.error(f"Errore _get_conn dal pool: {e}")
            _pool = None

    logger.warning("Pool non disponibile, uso connessione standalone")
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = False
    return conn


def _put_conn(conn):
    """Restituisce la connessione al pool o chiude la standalone."""
    global _pool

    if conn is None:
        return

    conn_id = id(conn)

    if _pool and conn_id in _pool_connections:
        try:
            _pool_connections.discard(conn_id)
            _pool.putconn(conn)
        except Exception as e:
            logger.error(f"Errore _put_conn pool: {e}")
            try:
                conn.close()
            except Exception:
                pass
    else:
        try:
            conn.close()
        except Exception as e:
            logger.error(f"Errore chiusura connessione standalone: {e}")


@contextmanager
def db_transaction():
    """Context manager per commit/rollback automatico."""
    conn = _get_conn()
    try:
        yield conn
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception as rb_err:
            logger.error(f"Errore rollback in db_transaction: {rb_err}")
        raise
    finally:
        _put_conn(conn)


# ─────────────────────────────────────────────
# INIT DATABASE
# ─────────────────────────────────────────────

def init_db():
    """Crea tabelle, colonne, indici e poi applica migrazioni/vincoli."""
    conn = _get_conn()
    cur = conn.cursor()

    try:
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
                prob_1 REAL,
                prob_x REAL,
                prob_2 REAL,
                suggerimento TEXT,
                confidence REAL,
                confidence_label TEXT,
                over_25 REAL,
                goal_si REAL,
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

        cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS referral_code TEXT")
        cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS referred_by INTEGER")

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

        # Indici principali
        cur.execute("CREATE INDEX IF NOT EXISTS idx_api_usage_user_time ON api_usage(user_id, timestamp)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_predictions_verificato ON predictions_tracking(verificato)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_user_predictions_user_id ON user_predictions(user_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_referrals_referrer_id ON referrals(referrer_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_user_predictions_match_date ON user_predictions(match_date)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_predictions_data_partita ON predictions_tracking(data_partita)")

        conn.commit()
        logger.info("DB PostgreSQL OK")
        print("DB PostgreSQL OK")

    except Exception as e:
        conn.rollback()
        logger.error(f"Errore init_db: {e}")
        raise

    finally:
        try:
            cur.close()
        except Exception:
            pass
        _put_conn(conn)

    # Migrazioni/vincoli dopo la creazione base
    _migrate_column_types()
    _add_fk_constraints()
    _add_unique_predictions_tracking()
    _add_check_constraints()


# ─────────────────────────────────────────────
# MIGRAZIONI TIPI COLONNE
# ─────────────────────────────────────────────

def _get_column_type(cur, table, column):
    cur.execute("""
        SELECT data_type
        FROM information_schema.columns
        WHERE table_name = %s
          AND column_name = %s
    """, (table, column))
    row = cur.fetchone()
    return row[0].lower() if row else None


def _migrate_column_types():
    """
    Migra colonne TEXT verso TIMESTAMPTZ o DATE.
    Se una migrazione fallisce, logga e continua con le altre.
    """
    migrations = [
        ("users", "created_at", "TIMESTAMPTZ", "NULLIF(created_at, '')::TIMESTAMPTZ"),
        ("api_usage", "timestamp", "TIMESTAMPTZ", "NULLIF(timestamp, '')::TIMESTAMPTZ"),
        ("predictions_tracking", "data_partita", "DATE", "NULLIF(data_partita, '')::DATE"),
        ("predictions_tracking", "created_at", "TIMESTAMPTZ", "NULLIF(created_at, '')::TIMESTAMPTZ"),
        ("referrals", "created_at", "TIMESTAMPTZ", "NULLIF(created_at, '')::TIMESTAMPTZ"),
        ("referrals", "completed_at", "TIMESTAMPTZ", "NULLIF(completed_at, '')::TIMESTAMPTZ"),
        ("user_predictions", "created_at", "TIMESTAMPTZ", "NULLIF(created_at, '')::TIMESTAMPTZ"),
        ("user_predictions", "match_date", "DATE", "NULLIF(match_date, '')::DATE"),
    ]

    conn = _get_conn()

    try:
        for table, col, new_type, cast_expr in migrations:
            cur = None
            try:
                cur = conn.cursor()
                current_type = _get_column_type(cur, table, col)

                if current_type is None:
                    logger.warning(f"Colonna {table}.{col} non trovata, salto migrazione")
                    cur.close()
                    continue

                if new_type == "TIMESTAMPTZ" and current_type == "timestamp with time zone":
                    cur.close()
                    continue

                if new_type == "DATE" and current_type == "date":
                    cur.close()
                    continue

                cur.execute(
                    f"ALTER TABLE {table} "
                    f"ALTER COLUMN {col} TYPE {new_type} "
                    f"USING {cast_expr}"
                )
                conn.commit()
                cur.close()
                logger.info(f"Migrazione OK: {table}.{col} -> {new_type}")

            except Exception as e:
                logger.error(f"Migrazione fallita {table}.{col} -> {new_type}: {e}")
                try:
                    conn.rollback()
                except Exception:
                    pass
                if cur:
                    try:
                        cur.close()
                    except Exception:
                        pass

    finally:
        _put_conn(conn)


# ─────────────────────────────────────────────
# VINCOLI FOREIGN KEY
# ─────────────────────────────────────────────

def _constraint_exists(cur, table, constraint_name):
    cur.execute("""
        SELECT 1
        FROM information_schema.table_constraints
        WHERE table_name = %s
          AND constraint_name = %s
    """, (table, constraint_name))
    return cur.fetchone() is not None


def _add_fk_constraints():
    """
    Aggiunge FK solo se non ci sono righe orfane.
    Se trova dati sporchi, non blocca l'app: logga e continua.
    """
    fk_specs = [
        (
            "fk_api_usage_user_id",
            "api_usage", "user_id",
            "users", "id",
            "SELECT COUNT(*) FROM api_usage a WHERE NOT EXISTS (SELECT 1 FROM users u WHERE u.id = a.user_id)",
        ),
        (
            "fk_referrals_referrer_id",
            "referrals", "referrer_id",
            "users", "id",
            "SELECT COUNT(*) FROM referrals r WHERE NOT EXISTS (SELECT 1 FROM users u WHERE u.id = r.referrer_id)",
        ),
        (
            "fk_referrals_referred_id",
            "referrals", "referred_id",
            "users", "id",
            "SELECT COUNT(*) FROM referrals r WHERE r.referred_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM users u WHERE u.id = r.referred_id)",
        ),
        (
            "fk_users_referred_by",
            "users", "referred_by",
            "users", "id",
            "SELECT COUNT(*) FROM users u WHERE u.referred_by IS NOT NULL AND NOT EXISTS (SELECT 1 FROM users p WHERE p.id = u.referred_by)",
        ),
        (
            "fk_user_predictions_user_id",
            "user_predictions", "user_id",
            "users", "id",
            "SELECT COUNT(*) FROM user_predictions up WHERE NOT EXISTS (SELECT 1 FROM users u WHERE u.id = up.user_id)",
        ),
    ]

    conn = _get_conn()

    try:
        for fk_name, child_table, child_col, parent_table, parent_col, orphan_query in fk_specs:
            cur = None
            try:
                cur = conn.cursor()

                if _constraint_exists(cur, child_table, fk_name):
                    cur.close()
                    continue

                cur.execute(orphan_query)
                orphan_count = cur.fetchone()[0]

                if orphan_count > 0:
                    logger.error(
                        f"FK {fk_name}: trovati {orphan_count} orfani in "
                        f"{child_table}.{child_col}. FK non aggiunta."
                    )
                    cur.close()
                    continue

                cur.execute(
                    f"ALTER TABLE {child_table} "
                    f"ADD CONSTRAINT {fk_name} "
                    f"FOREIGN KEY ({child_col}) REFERENCES {parent_table}({parent_col})"
                )
                conn.commit()
                cur.close()
                logger.info(f"FK aggiunta: {fk_name}")

            except Exception as e:
                logger.error(f"Errore aggiunta FK {fk_name}: {e}")
                try:
                    conn.rollback()
                except Exception:
                    pass
                if cur:
                    try:
                        cur.close()
                    except Exception:
                        pass

    finally:
        _put_conn(conn)


# ─────────────────────────────────────────────
# UNIQUE PREDICTIONS
# ─────────────────────────────────────────────

def _add_unique_predictions_tracking():
    """
    Aggiunge UNIQUE(home, away, data_partita) su predictions_tracking.
    Se trova duplicati, non aggiunge il vincolo e logga l'errore.
    """
    conn = _get_conn()
    cur = None

    try:
        cur = conn.cursor()

        if _constraint_exists(cur, "predictions_tracking", "uq_predictions_home_away_data"):
            return

        cur.execute("""
            SELECT home, away, data_partita, COUNT(*) AS cnt
            FROM predictions_tracking
            GROUP BY home, away, data_partita
            HAVING COUNT(*) > 1
        """)
        duplicates = cur.fetchall()

        if duplicates:
            logger.error(
                f"UNIQUE predictions_tracking non aggiunto: trovati {len(duplicates)} gruppi duplicati. "
                f"Esempio: {duplicates[0]}"
            )
            return

        cur.execute("""
            ALTER TABLE predictions_tracking
            ADD CONSTRAINT uq_predictions_home_away_data
            UNIQUE (home, away, data_partita)
        """)
        conn.commit()
        logger.info("UNIQUE uq_predictions_home_away_data aggiunto")

    except Exception as e:
        logger.error(f"Errore aggiunta UNIQUE predictions_tracking: {e}")
        try:
            conn.rollback()
        except Exception:
            pass

    finally:
        if cur:
            try:
                cur.close()
            except Exception:
                pass
        _put_conn(conn)


# ─────────────────────────────────────────────
# CHECK CONSTRAINTS
# ─────────────────────────────────────────────

def _add_check_constraints():
    """
    Aggiunge CHECK constraints controllando prima se esistono.
    Evita ADD CONSTRAINT IF NOT EXISTS, che può non essere supportato.
    """
    constraints = [
        ("chk_users_piano", "users", "piano IN ('free', 'pro')"),
        ("chk_predictions_confidence_label", "predictions_tracking", "confidence_label IS NULL OR confidence_label IN ('Bassa', 'Media', 'Alta')"),
        ("chk_referrals_status", "referrals", "status IN ('pending', 'completed', 'expired')"),
    ]

    conn = _get_conn()

    try:
        for name, table, expr in constraints:
            cur = None
            try:
                cur = conn.cursor()

                if _constraint_exists(cur, table, name):
                    cur.close()
                    continue

                cur.execute(
                    f"ALTER TABLE {table} "
                    f"ADD CONSTRAINT {name} CHECK ({expr})"
                )
                conn.commit()
                cur.close()
                logger.info(f"CHECK constraint applicato: {name}")

            except Exception as e:
                logger.warning(f"CHECK constraint {name} non applicato: {e}")
                try:
                    conn.rollback()
                except Exception:
                    pass
                if cur:
                    try:
                        cur.close()
                    except Exception:
                        pass

    finally:
        _put_conn(conn)


# ─────────────────────────────────────────────
# CRUD UTENTI
# ─────────────────────────────────────────────

def create_user(email, password_hash):
    with db_transaction() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            cur.execute("""
                INSERT INTO users (email, password_hash, piano, created_at)
                VALUES (%s, %s, 'free', %s)
                RETURNING *
            """, (
                email.lower().strip(),
                password_hash,
                datetime.now(timezone.utc),
            ))
            row = cur.fetchone()
            return dict(row) if row else None
        finally:
            cur.close()


def get_user_by_email(email):
    conn = _get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("SELECT * FROM users WHERE email = %s", (email.lower().strip(),))
        row = cur.fetchone()
        return dict(row) if row else None
    finally:
        cur.close()
        _put_conn(conn)


def get_user_by_id(user_id):
    conn = _get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        row = cur.fetchone()
        return dict(row) if row else None
    finally:
        cur.close()
        _put_conn(conn)


def update_plan(user_id, plan):
    with db_transaction() as conn:
        cur = conn.cursor()
        try:
            cur.execute(
                "UPDATE users SET piano = %s WHERE id = %s",
                (plan, user_id),
            )
            return cur.rowcount > 0
        finally:
            cur.close()


def update_stripe_customer(user_id, stripe_customer_id):
    with db_transaction() as conn:
        cur = conn.cursor()
        try:
            cur.execute(
                "UPDATE users SET stripe_customer_id = %s WHERE id = %s",
                (stripe_customer_id, user_id),
            )
            return cur.rowcount > 0
        finally:
            cur.close()


# ─────────────────────────────────────────────
# USAGE API
# ─────────────────────────────────────────────

def log_api_call(user_id, endpoint):
    with db_transaction() as conn:
        cur = conn.cursor()
        try:
            cur.execute("""
                INSERT INTO api_usage (user_id, endpoint, timestamp)
                VALUES (%s, %s, %s)
            """, (
                user_id,
                endpoint,
                datetime.now(timezone.utc),
            ))
        finally:
            cur.close()


def count_daily_calls(user_id):
    """Conta le chiamate API di oggi usando range TIMESTAMPTZ."""
    conn = _get_conn()
    cur = conn.cursor()

    try:
        now_utc = datetime.now(timezone.utc)
        start_of_day = now_utc.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)

        cur.execute("""
            SELECT COUNT(*)
            FROM api_usage
            WHERE user_id = %s
              AND timestamp >= %s
              AND timestamp < %s
        """, (user_id, start_of_day, end_of_day))

        row = cur.fetchone()
        return row[0] if row else 0

    finally:
        cur.close()
        _put_conn(conn)


# ─────────────────────────────────────────────
# TRACKING PREDIZIONI
# ─────────────────────────────────────────────

def save_prediction(home, away, data_partita, pred, bk_live=False):
    """Salva un pronostico nel DB per verifica futura."""
    try:
        with db_transaction() as conn:
            cur = conn.cursor()
            try:
                cur.execute("""
                    INSERT INTO predictions_tracking
                    (home, away, data_partita, prob_1, prob_x, prob_2, suggerimento,
                     confidence, confidence_label, over_25, goal_si, gol_attesi,
                     bookmaker_live, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT ON CONSTRAINT uq_predictions_home_away_data DO NOTHING
                """, (
                    home,
                    away,
                    data_partita,
                    pred.get("prob_1"),
                    pred.get("prob_x"),
                    pred.get("prob_2"),
                    pred.get("suggerimento"),
                    pred.get("confidence"),
                    pred.get("confidence_label"),
                    pred.get("over_25"),
                    pred.get("goal_si"),
                    pred.get("gol_attesi"),
                    bk_live,
                    datetime.now(timezone.utc),
                ))
            except psycopg2.errors.UndefinedObject:
                # Se il vincolo UNIQUE non esiste ancora, fallback sicuro
                conn.rollback()
                cur.close()
                cur = conn.cursor()
                cur.execute("""
                    INSERT INTO predictions_tracking
                    (home, away, data_partita, prob_1, prob_x, prob_2, suggerimento,
                     confidence, confidence_label, over_25, goal_si, gol_attesi,
                     bookmaker_live, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT DO NOTHING
                """, (
                    home,
                    away,
                    data_partita,
                    pred.get("prob_1"),
                    pred.get("prob_x"),
                    pred.get("prob_2"),
                    pred.get("suggerimento"),
                    pred.get("confidence"),
                    pred.get("confidence_label"),
                    pred.get("over_25"),
                    pred.get("goal_si"),
                    pred.get("gol_attesi"),
                    bk_live,
                    datetime.now(timezone.utc),
                ))
            finally:
                cur.close()

    except Exception as e:
        logger.error(f"Errore save_prediction ({home} vs {away}): {e}")


def verify_predictions(risultati_live):
    """Verifica le predizioni passate con i risultati reali."""
    conn = _get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        cur.execute("SELECT * FROM predictions_tracking WHERE verificato = FALSE")
        rows = cur.fetchall()

        verificate = 0

        for row in rows:
            home = row["home"]
            away = row["away"]

            for ris in risultati_live:
                if (
                    ris.get("home") == home
                    and ris.get("away") == away
                    and ris.get("status") == "FT"
                ):
                    gol_h = ris.get("gol_h")
                    gol_a = ris.get("gol_a")

                    if gol_h is None or gol_a is None:
                        continue

                    if gol_h > gol_a:
                        ris_reale = "1"
                    elif gol_h == gol_a:
                        ris_reale = "X"
                    else:
                        ris_reale = "2"

                    corretto_1x2 = row["suggerimento"] == ris_reale

                    gol_tot = gol_h + gol_a
                    pred_over = (row["over_25"] or 50) > 50
                    corretto_ou = (gol_tot > 2.5) == pred_over

                    pred_goal = (row["goal_si"] or 50) > 50
                    corretto_goal = (gol_h >= 1 and gol_a >= 1) == pred_goal

                    cur.execute("""
                        UPDATE predictions_tracking
                        SET risultato_reale = %s,
                            gol_home_reale = %s,
                            gol_away_reale = %s,
                            corretto_1x2 = %s,
                            corretto_ou = %s,
                            corretto_goal = %s,
                            verificato = TRUE
                        WHERE id = %s
                    """, (
                        ris_reale,
                        gol_h,
                        gol_a,
                        corretto_1x2,
                        corretto_ou,
                        corretto_goal,
                        row["id"],
                    ))

                    verificate += 1
                    break

        conn.commit()

        if verificate > 0:
            print(f"TRACKING: {verificate} predizioni verificate")

    except Exception as e:
        conn.rollback()
        logger.error(f"Errore verify_predictions: {e}")

    finally:
        cur.close()
        _put_conn(conn)


def get_tracking_stats():
    """Ritorna le statistiche di accuratezza delle predizioni tracciate."""
    conn = _get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        cur.execute("""
            SELECT
                COUNT(*) AS totale,
                COALESCE(SUM(CASE WHEN corretto_1x2 THEN 1 ELSE 0 END), 0) AS ok_1x2,
                COALESCE(SUM(CASE WHEN corretto_ou THEN 1 ELSE 0 END), 0) AS ok_ou,
                COALESCE(SUM(CASE WHEN corretto_goal THEN 1 ELSE 0 END), 0) AS ok_goal,
                COALESCE(SUM(CASE WHEN corretto_1x2 AND confidence_label = 'Alta' THEN 1 ELSE 0 END), 0) AS ok_alta,
                COALESCE(SUM(CASE WHEN confidence_label = 'Alta' THEN 1 ELSE 0 END), 0) AS tot_alta
            FROM predictions_tracking
            WHERE verificato = TRUE
        """)

        row = cur.fetchone()

        if row and row["totale"] > 0:
            totale = row["totale"]
            tot_alta = row["tot_alta"] or 0

            return {
                "totale": totale,
                "acc_1x2": round((row["ok_1x2"] or 0) / totale * 100, 1),
                "acc_ou": round((row["ok_ou"] or 0) / totale * 100, 1),
                "acc_goal": round((row["ok_goal"] or 0) / totale * 100, 1),
                "acc_alta": round((row["ok_alta"] or 0) / tot_alta * 100, 1) if tot_alta > 0 else 0,
                "tot_alta": tot_alta,
            }

    except Exception as e:
        logger.error(f"Errore get_tracking_stats: {e}")

    finally:
        cur.close()
        _put_conn(conn)

    return None
