"""
database.py
Gestione del database SQLite per la webapp pronostici Serie A.
Tabelle: users (profili utenti) e api_usage (log chiamate API).
"""

import sqlite3
import os
from datetime import datetime, timezone

# Percorso del database nella cartella backend
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "webapp_users.db")


def _get_conn() -> sqlite3.Connection:
    """Apre e ritorna una connessione al database SQLite."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Risultati come dizionari
    return conn


def init_db() -> None:
    """
    Inizializza il database creando le tabelle se non esistono.
    Chiamare all'avvio del server.
    """
    conn = _get_conn()
    try:
        cursor = conn.cursor()

        # Tabella utenti
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                email             TEXT    UNIQUE NOT NULL,
                password_hash     TEXT    NOT NULL,
                piano             TEXT    DEFAULT 'free',
                stripe_customer_id TEXT,
                created_at        TEXT    NOT NULL
            )
        """)

        # Tabella log chiamate API
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS api_usage (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id   INTEGER NOT NULL,
                endpoint  TEXT    NOT NULL,
                timestamp TEXT    NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        conn.commit()
    finally:
        conn.close()


def create_user(email: str, password_hash: str) -> dict | None:
    """
    Crea un nuovo utente con piano 'free'.
    Ritorna il dict dell'utente creato, o None se l'email esiste già.
    """
    conn = _get_conn()
    try:
        created_at = datetime.now(timezone.utc).isoformat()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (email, password_hash, piano, created_at) VALUES (?, ?, 'free', ?)",
            (email.lower().strip(), password_hash, created_at)
        )
        conn.commit()
        user_id = cursor.lastrowid
        return get_user_by_id(user_id)
    except sqlite3.IntegrityError:
        # Email già registrata
        return None
    finally:
        conn.close()


def get_user_by_email(email: str) -> dict | None:
    """
    Recupera un utente dal database tramite email.
    Ritorna dict con tutti i campi, o None se non trovato.
    """
    conn = _get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM users WHERE email = ?",
            (email.lower().strip(),)
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return dict(row)
    finally:
        conn.close()


def get_user_by_id(user_id: int) -> dict | None:
    """
    Recupera un utente dal database tramite ID.
    Ritorna dict con tutti i campi, o None se non trovato.
    """
    conn = _get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        if row is None:
            return None
        return dict(row)
    finally:
        conn.close()


def update_plan(user_id: int, plan: str) -> bool:
    """
    Aggiorna il piano di un utente ('free' o 'pro').
    Ritorna True se l'aggiornamento ha avuto successo.
    """
    conn = _get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET piano = ? WHERE id = ?",
            (plan, user_id)
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def update_stripe_customer(user_id: int, stripe_customer_id: str) -> bool:
    """
    Salva lo stripe_customer_id per un utente.
    Ritorna True se l'aggiornamento ha avuto successo.
    """
    conn = _get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET stripe_customer_id = ? WHERE id = ?",
            (stripe_customer_id, user_id)
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def log_api_call(user_id: int, endpoint: str) -> None:
    """
    Registra una chiamata API nel log.
    Usato per il rate limiting degli utenti Free.
    """
    conn = _get_conn()
    try:
        timestamp = datetime.now(timezone.utc).isoformat()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO api_usage (user_id, endpoint, timestamp) VALUES (?, ?, ?)",
            (user_id, endpoint, timestamp)
        )
        conn.commit()
    finally:
        conn.close()


def count_daily_calls(user_id: int) -> int:
    """
    Conta le chiamate API effettuate dall'utente oggi (UTC).
    Usato per il limite giornaliero degli utenti Free (max 5).
    """
    conn = _get_conn()
    try:
        oggi = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT COUNT(*) FROM api_usage
            WHERE user_id = ?
              AND timestamp LIKE ?
            """,
            (user_id, f"{oggi}%")
        )
        row = cursor.fetchone()
        return row[0] if row else 0
    finally:
        conn.close()
