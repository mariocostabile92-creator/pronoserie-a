"""
history_db.py
Gestione del database SQLite per lo storico delle simulazioni.
"""

import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "simulazioni.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Crea la tabella se non esiste."""
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS simulazioni (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data_sim TEXT,
                home TEXT,
                away TEXT,
                gol_home INTEGER,
                gol_away INTEGER,
                risultato TEXT,
                pronostico TEXT,
                quota_pronostico REAL
            )
        """)
        conn.commit()


def save_simulation(home: str, away: str, sim_result: dict, prediction: dict):
    """Salva una simulazione nel database."""
    init_db()
    data_sim = datetime.now().strftime("%d/%m/%Y %H:%M")
    risultato = f"{sim_result['home_goals']}-{sim_result['away_goals']}"
    pronostico = prediction.get("suggerimento", "?")
    quota = prediction.get(f"quota_{pronostico.lower()}", 0.0) if pronostico != "?" else 0.0

    with get_connection() as conn:
        conn.execute("""
            INSERT INTO simulazioni
            (data_sim, home, away, gol_home, gol_away, risultato, pronostico, quota_pronostico)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data_sim, home, away,
            sim_result["home_goals"], sim_result["away_goals"],
            risultato, pronostico, quota
        ))
        conn.commit()


def get_history() -> list:
    """Ritorna tutto lo storico come lista di dizionari."""
    init_db()
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM simulazioni ORDER BY id DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def clear_history():
    """Cancella tutto lo storico."""
    init_db()
    with get_connection() as conn:
        conn.execute("DELETE FROM simulazioni")
        conn.commit()
