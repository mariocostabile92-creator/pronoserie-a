"""
database.py - Versione Ottimizzata
Gestione SQLite con migrazioni automatiche per Stripe e Piani Pro.
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
    Inizializza il database e applica migrazioni se le colonne mancano.
    Questa funzione evita l'errore 500 dovuto a tabelle non aggiornate.
    """
    conn = _get_conn()
    try:
        cursor = conn.cursor()

        # 1. Creazione tabella users (se non esiste)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                piano TEXT DEFAULT 'free',
                stripe_customer_id TEXT,
                created_at TEXT NOT NULL
            )
        """)

        # 2. MIGRAZIONE: Aggiunta colonne a tabelle esistenti
        # Se il DB esiste già ma è vecchio, aggiungiamo le colonne mancanti
        colonne_da_controllare = [
            ("piano", "TEXT DEFAULT 'free'"),
            ("stripe_customer_id", "TEXT")
        ]

        for nome_colonna, tipo_colonna in colonne_da_controllare:
            try:
                cursor.execute(f"ALTER TABLE users ADD COLUMN {nome_colonna} {tipo_colonna}")
                print(f"Migrazione: Colonna '{nome_colonna}' aggiunta con successo.")
            except sqlite3.OperationalError:
                # Se la colonna esiste già, SQLite lancia questo errore: lo ignoriamo.
                pass

        # 3. Tabella log chiamate API
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS api_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                endpoint TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        conn.commit()
    except Exception as e:
        print(f"Errore durante init_db: {e}")
    finally:
        conn.close()


def create_user(email: str, password_hash: str) -> dict | None:
    """Crea un nuovo utente. Ritorna il dict o None se l'email esiste."""
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
        return None
    finally:
        conn.close()


def get_user_by_email(email: str) -> dict | None:
    """Recupera utente tramite email."""
    conn = _get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (email.lower().strip(),))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_user_by_id(user_id: int) -> dict | None:
    """Recupera utente tramite ID."""
    conn = _get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def update_plan(user_id: int, plan: str) -> bool:
    """Aggiorna il piano (es. da 'free' a 'pro')."""
    conn = _get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET piano = ? WHERE id = ?", (plan, user_id))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def update_stripe_customer(user_id: int, stripe_customer_id: str) -> bool:
    """Salva l'ID cliente Stripe."""
    conn = _get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET stripe_customer_id = ? WHERE id = ?", (stripe_customer_id, user_id))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def log_api_call(user_id: int, endpoint: str) -> None:
    """Registra l'utilizzo API."""
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
    """Conta chiamate odierne per rate limiting."""
    conn = _get_conn()
    try:
        oggi = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM api_usage WHERE user_id = ? AND timestamp LIKE ?",
            (user_id, f"{oggi}%")
        )
        row = cursor.fetchone()
        return row[0] if row else 0
    finally:
        conn.close()