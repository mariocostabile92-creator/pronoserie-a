"""
auto_update.py
Aggiornamento automatico dei dati Serie A 2025-2026.
Scarica classifica, marcatori e xG aggiornati dal web.
Esegui prima di aprire l'app per avere dati freschi.
"""

import os
import json
import re
from datetime import datetime

try:
    import urllib.request
    import urllib.error
    HAS_URLLIB = True
except ImportError:
    HAS_URLLIB = False

DATA_DIR = os.path.dirname(__file__)
LOG_FILE = os.path.join(DATA_DIR, "ultimo_aggiornamento.txt")


def _fetch_url(url: str) -> str | None:
    """Scarica il contenuto di un URL."""
    if not HAS_URLLIB:
        return None
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"  Errore download {url}: {e}")
        return None


def aggiorna_classifica() -> list | None:
    """Scarica la classifica aggiornata da Sky Sport."""
    print("  Scarico classifica...")
    html = _fetch_url("https://sport.sky.it/calcio/serie-a/classifica")
    if not html:
        return None

    # Cerca pattern classifica nel HTML
    # Nota: parsing molto semplificato, potrebbe non funzionare se Sky cambia struttura
    print("  Classifica scaricata (parsing manuale necessario per aggiornamenti futuri)")
    return None  # Ritorna None = usa dati hardcoded


def aggiorna_marcatori() -> list | None:
    """Scarica i marcatori aggiornati da Tuttosport."""
    print("  Scarico marcatori...")
    html = _fetch_url("https://www.tuttosport.com/live/classifica-marcatori-serie-a")
    if not html:
        return None
    print("  Marcatori scaricati (parsing manuale necessario per aggiornamenti futuri)")
    return None


def scarica_csv_risultati() -> bool:
    """
    Scarica i CSV aggiornati dei risultati Serie A da football-data.co.uk.
    Questo e' il metodo piu' affidabile per aggiornare i dati storici.
    """
    print("  Scarico CSV risultati aggiornati...")

    # Football-data.co.uk fornisce CSV aggiornati della stagione corrente
    url = "https://www.football-data.co.uk/mmz4281/2526/I1.csv"
    cartella_csv = r"C:\Users\Mario\Desktop\Mariocalcio"

    if not os.path.exists(cartella_csv):
        print(f"  Cartella {cartella_csv} non trovata!")
        return False

    dest = os.path.join(cartella_csv, "I1_2526_auto.csv")

    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        })
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
            if len(data) < 100:
                print("  CSV troppo piccolo, potrebbe essere un errore")
                return False
            with open(dest, "wb") as f:
                f.write(data)
            print(f"  CSV salvato: {dest} ({len(data)} bytes)")
            return True
    except Exception as e:
        print(f"  Errore download CSV: {e}")
        return False


def esegui_aggiornamento():
    """Esegue l'aggiornamento completo."""
    print("=" * 50)
    print(f"AGGIORNAMENTO DATI SERIE A")
    print(f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print("=" * 50)

    successo = False

    # 1. Scarica CSV risultati (fonte piu' importante)
    if scarica_csv_risultati():
        successo = True
        print("  [OK] CSV risultati aggiornato!")
    else:
        print("  [!] CSV non aggiornato (usa dati esistenti)")

    # 2. Prova ad aggiornare classifica e marcatori
    aggiorna_classifica()
    aggiorna_marcatori()

    # 3. Salva timestamp
    try:
        with open(LOG_FILE, "w") as f:
            f.write(datetime.now().strftime("%d/%m/%Y %H:%M"))
        print(f"\n  Timestamp salvato in: {LOG_FILE}")
    except Exception:
        pass

    if successo:
        print("\n  AGGIORNAMENTO COMPLETATO!")
        print("  I nuovi risultati saranno caricati al prossimo avvio dell'app.")
    else:
        print("\n  Aggiornamento parziale. L'app usera' i dati esistenti.")

    print("=" * 50)
    return successo


def get_ultimo_aggiornamento() -> str:
    """Ritorna la data dell'ultimo aggiornamento."""
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, "r") as f:
                return f.read().strip()
        except Exception:
            pass
    return "Mai aggiornato"


if __name__ == "__main__":
    esegui_aggiornamento()
    input("\nPremi INVIO per chiudere...")
