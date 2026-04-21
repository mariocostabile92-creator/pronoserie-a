"""
auto_update.py
Aggiornamento automatico dei dati Serie A 2025-2026 + xG multi-lega da Understat.

Esegui prima di aprire l'app per avere dati freschi.
Per aggiornare i dati xG di tutte le leghe (settimanale):
    python auto_update.py --xg

Per schedulare l'aggiornamento automatico settimanale:
    Windows Task Scheduler:
        Azione: python C:\\...\\auto_update.py --xg
        Trigger: Ogni settimana (es. lunedi' mattina)

    Linux/macOS cron (ogni lunedi' alle 7:00):
        0 7 * * 1 cd /path/to/project && python auto_update.py --xg

Per aggiornamento completo (CSV + xG):
    python auto_update.py --all
"""

import os
import json
import re
import sys
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


def aggiorna_xg_understat() -> bool:
    """
    Aggiorna i dati xG REALI per tutte le 5 leghe top europee
    scaricando da Understat.com (endpoint getLeagueData).

    Delega a scrape_understat.py che aggiorna automaticamente season_2526.py.

    Ritorna True se almeno una lega e' stata aggiornata, False in caso di errore totale.
    """
    print("\n  [xG] Avvio aggiornamento xG da Understat...")

    # Importa il modulo scrape_understat dalla stessa cartella
    script_dir = os.path.dirname(os.path.abspath(__file__))
    scrape_module = os.path.join(script_dir, "scrape_understat.py")

    if not os.path.exists(scrape_module):
        print(f"  [xG] ERRORE: {scrape_module} non trovato!")
        print("  [xG] Esegui prima: python scrape_understat.py")
        return False

    try:
        # Importa ed esegui il modulo
        import importlib.util
        spec = importlib.util.spec_from_file_location("scrape_understat", scrape_module)
        scrape_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(scrape_mod)

        # Esegui lo scraping
        ok = scrape_mod.main()
        if ok:
            print("  [xG] Aggiornamento xG completato!")
        else:
            print("  [xG] Aggiornamento xG parziale (alcune leghe con errori)")
        return ok

    except Exception as e:
        print(f"  [xG] ERRORE durante lo scraping: {e}")
        return False


def controlla_retrain(forza=False, dry_run=False) -> bool:
    """
    Controlla se e' necessario eseguire il re-training settimanale del modello.
    Se sono passati piu' di 7 giorni dall'ultimo re-training (o non e' mai stato
    eseguito), importa retrain_model e avvia il processo.

    Il re-training:
      - Scarica i risultati piu' recenti per ogni lega
      - Ottimizza i parametri del modello (LEAGUE_PARAMS in predictor.py)
      - Logga tutto in retrain_log.json

    Parametri:
        forza: se True, esegue il re-training anche se non sono passati 7 giorni
        dry_run: se True, simula senza modificare predictor.py

    Ritorna True se il re-training e' stato eseguito.
    """
    GIORNI_INTERVALLO = 7
    LAST_RETRAIN_FILE = os.path.join(DATA_DIR, "last_retrain.txt")

    # Controlla se sono passati abbastanza giorni dall'ultimo re-training
    if not forza and os.path.exists(LAST_RETRAIN_FILE):
        try:
            with open(LAST_RETRAIN_FILE, "r") as f:
                ultimo = f.read().strip()
            ultimo_dt = datetime.strptime(ultimo, "%Y-%m-%d %H:%M:%S")
            delta = datetime.now() - ultimo_dt
            if delta.days < GIORNI_INTERVALLO:
                giorni_rimasti = GIORNI_INTERVALLO - delta.days
                print(f"  [Re-training] Prossimo in {giorni_rimasti} giorni "
                      f"(ultimo: {ultimo_dt.strftime('%d/%m/%Y')}). Skip.")
                return False
        except Exception:
            pass  # Se non riesce a leggere il timestamp, esegue il re-training

    # Importa e avvia il re-training
    print("  [Re-training] Avvio re-training settimanale del modello...")
    try:
        import importlib.util
        script_dir = os.path.dirname(os.path.abspath(__file__))
        retrain_path = os.path.join(script_dir, "retrain_model.py")

        if not os.path.exists(retrain_path):
            print(f"  [Re-training] ERRORE: retrain_model.py non trovato in {script_dir}")
            return False

        spec = importlib.util.spec_from_file_location("retrain_model", retrain_path)
        retrain_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(retrain_mod)

        # Esegui il re-training per tutte le leghe
        risultati = retrain_mod.esegui_retrain(dry_run=dry_run)

        aggiornati = sum(1 for r in risultati if r.get("applicato"))
        print(f"  [Re-training] Completato. Leghe aggiornate: {aggiornati}/{len(risultati)}")
        return True

    except Exception as e:
        print(f"  [Re-training] ERRORE: {e}")
        return False


def esegui_aggiornamento(include_retrain=True) -> bool:
    """
    Esegue l'aggiornamento completo:
    1. Scarica CSV risultati (football-data.co.uk)
    2. Aggiorna classifica e marcatori
    3. (Settimanale) Re-training automatico del modello predittivo

    Parametri:
        include_retrain: se True, controlla e avvia il re-training settimanale
    """
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

    # 3. Re-training settimanale del modello (se attivo)
    if include_retrain:
        print("\n  Controllo re-training automatico...")
        controlla_retrain()

    # 4. Salva timestamp
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
    args = sys.argv[1:]

    if "--xg" in args:
        # Modalita': aggiorna solo i dati xG da Understat
        print("=" * 60)
        print("AGGIORNAMENTO xG DA UNDERSTAT")
        print(f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        print("=" * 60)
        ok = aggiorna_xg_understat()
        print("\n" + ("OK - xG aggiornati con dati reali Understat" if ok else "ERRORE - aggiornamento parziale"))
        sys.exit(0 if ok else 1)

    elif "--all" in args:
        # Modalita': aggiornamento completo (CSV + xG + re-training)
        print("=" * 60)
        print("AGGIORNAMENTO COMPLETO (CSV + xG Understat + Re-training)")
        print(f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        print("=" * 60)
        ok_csv = esegui_aggiornamento(include_retrain=True)
        ok_xg = aggiorna_xg_understat()
        print("\n" + "=" * 60)
        print(f"CSV risultati: {'OK' if ok_csv else 'SKIP'}")
        print(f"xG Understat:  {'OK' if ok_xg else 'ERRORE'}")
        print("=" * 60)
        sys.exit(0 if ok_xg else 1)

    elif "--retrain" in args:
        # Modalita': re-training manuale del modello (ignora il check 7 giorni)
        dry_run = "--dry-run" in args
        print("=" * 60)
        print("RE-TRAINING MANUALE DEL MODELLO PREDITTIVO")
        print(f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        if dry_run:
            print("MODALITA' DRY-RUN")
        print("=" * 60)
        ok = controlla_retrain(forza=True, dry_run=dry_run)
        sys.exit(0 if ok else 1)

    else:
        # Modalita' default: aggiornamento CSV Serie A + controllo re-training settimanale
        esegui_aggiornamento(include_retrain=True)
        input("\nPremi INVIO per chiudere...")
