"""
retrain_model.py
Sistema di re-training automatico del modello predittivo.

Per ogni lega (serie-a, premier-league, la-liga, bundesliga, ligue-1):
  1. Scarica i risultati piu' recenti della stagione (football-data.co.uk)
  2. Calcola l'accuratezza con i parametri attuali (baseline)
  3. Esegue grid search per trovare parametri migliori
  4. Se i nuovi parametri migliorano di almeno SOGLIA_MIGLIORAMENTO%:
     - Aggiorna LEAGUE_PARAMS in predictor.py (file I/O)
     - Salva un backup di predictor.py
  5. Logga tutto in retrain_log.json

Safeguard:
  - Non applica parametri se l'accuratezza peggiora
  - Non applica se il dataset ha meno di MIN_PARTITE partite
  - Mantiene un backup dei parametri precedenti

Uso:
    python retrain_model.py
    python retrain_model.py --lega serie-a
    python retrain_model.py --dry-run     # solo testa, non applica
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import warnings
warnings.filterwarnings("ignore")

import json
import re
import shutil
import argparse
import urllib.request
import urllib.error
from datetime import datetime

# ─────────────────────────────────────────────────────────────────────────────
# Costanti di configurazione
# ─────────────────────────────────────────────────────────────────────────────

# Miglioramento minimo richiesto per aggiornare i parametri (punti percentuali)
SOGLIA_MIGLIORAMENTO = 1.0

# Numero minimo di partite nel dataset per procedere con il re-training
MIN_PARTITE = 20

# Cartella di base del progetto
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# File di log del re-training
LOG_FILE = os.path.join(BASE_DIR, "retrain_log.json")

# File timestamp ultimo re-training (usato da auto_update.py)
LAST_RETRAIN_FILE = os.path.join(BASE_DIR, "last_retrain.txt")

# Backup predictor.py prima di ogni modifica
PREDICTOR_FILE = os.path.join(BASE_DIR, "predictor.py")
PREDICTOR_BACKUP = os.path.join(BASE_DIR, "predictor_backup.py")

# URL football-data.co.uk per stagione 2025-2026
FOOTBALL_DATA_URLS = {
    'serie-a':       "https://www.football-data.co.uk/mmz4281/2526/I1.csv",
    'premier-league':"https://www.football-data.co.uk/mmz4281/2526/E0.csv",
    'la-liga':       "https://www.football-data.co.uk/mmz4281/2526/SP1.csv",
    'bundesliga':    "https://www.football-data.co.uk/mmz4281/2526/D1.csv",
    'ligue-1':       "https://www.football-data.co.uk/mmz4281/2526/F1.csv",
}

# Cartelle dati per ciascuna lega (devono corrispondere a data_loader.py)
DATA_DIRS = {
    'serie-a':       os.path.join(BASE_DIR, "data_seriea"),
    'premier-league':os.path.join(BASE_DIR, "data_pl"),
    'la-liga':       os.path.join(BASE_DIR, "data_laliga"),
    'bundesliga':    os.path.join(BASE_DIR, "data_bundesliga"),
    'ligue-1':       os.path.join(BASE_DIR, "data_ligue1"),
}

# Nomi file CSV scaricati automaticamente per il re-training
CSV_RETRAIN_NAMES = {
    'serie-a':       "I1_2526_retrain.csv",
    'premier-league':"E0_2526_retrain.csv",
    'la-liga':       "SP1_2526_retrain.csv",
    'bundesliga':    "D1_2526_retrain.csv",
    'ligue-1':       "F1_2526_retrain.csv",
}


# ─────────────────────────────────────────────────────────────────────────────
# Funzioni di utilita'
# ─────────────────────────────────────────────────────────────────────────────

def _scarica_csv(url, dest_path):
    """
    Scarica un CSV da football-data.co.uk e lo salva in dest_path.
    Ritorna True se il download ha successo, False altrimenti.
    """
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
            if len(data) < 200:
                print(f"    [!] CSV troppo piccolo ({len(data)} bytes), skip.")
                return False
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            with open(dest_path, "wb") as f:
                f.write(data)
            print(f"    [OK] CSV scaricato: {os.path.basename(dest_path)} ({len(data)} bytes)")
            return True
    except Exception as e:
        print(f"    [!] Errore download {url}: {e}")
        return False


def _carica_log():
    """Carica il log JSON dei re-training precedenti."""
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []


def _salva_log(log):
    """Salva il log JSON dei re-training."""
    try:
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            json.dump(log, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"  [!] Errore salvataggio log: {e}")


def _aggiorna_league_params(league_id, nuovi_params):
    """
    Aggiorna LEAGUE_PARAMS in predictor.py con i nuovi parametri per una lega.
    Usa file I/O: legge il file, trova il blocco della lega, lo sostituisce.

    Strategia: cerca la sezione della lega nel dizionario LEAGUE_PARAMS
    e sostituisce i valori chiave per chiave.

    Ritorna True se l'aggiornamento ha successo, False altrimenti.
    """
    if not os.path.exists(PREDICTOR_FILE):
        print(f"  [!] predictor.py non trovato in {PREDICTOR_FILE}")
        return False

    # Leggi il file
    with open(PREDICTOR_FILE, "r", encoding="utf-8") as f:
        contenuto = f.read()

    # Crea backup prima di modificare
    shutil.copy2(PREDICTOR_FILE, PREDICTOR_BACKUP)
    print(f"  [OK] Backup creato: {os.path.basename(PREDICTOR_BACKUP)}")

    # Chiavi da aggiornare (esclude le chiavi private con prefisso _)
    chiavi_da_aggiornare = {
        "draw_boost": nuovi_params.get("draw_boost"),
        "alpha_h2h": nuovi_params.get("alpha_h2h"),
        "alpha_forma": nuovi_params.get("alpha_forma"),
        "alpha_xg": nuovi_params.get("alpha_xg"),
        "dixon_coles_rho": nuovi_params.get("dixon_coles_rho"),
        "confidence_threshold": nuovi_params.get("confidence_threshold"),
    }

    # Rimuovi chiavi con valore None
    chiavi_da_aggiornare = {k: v for k, v in chiavi_da_aggiornare.items() if v is not None}

    # Trova la sezione della lega nel file
    # Cerca il pattern: 'league-id': { ... }
    # Usiamo una regex che matcha il blocco della lega specifica
    pattern_lega = re.compile(
        r"('" + re.escape(league_id) + r"'\s*:\s*\{)([^}]+)(\})",
        re.DOTALL
    )

    match = pattern_lega.search(contenuto)
    if not match:
        print(f"  [!] Blocco '{league_id}' non trovato in predictor.py")
        return False

    blocco_originale = match.group(2)  # Contenuto tra le graffe
    blocco_aggiornato = blocco_originale

    # Aggiorna ogni chiave nel blocco
    modifiche = 0
    for chiave, valore in chiavi_da_aggiornare.items():
        # Pattern per trovare la riga: 'chiave': valore,
        # Gestisce sia float che interi, con eventuale commento dopo
        pattern_chiave = re.compile(
            r"('" + re.escape(chiave) + r"'\s*:\s*)([0-9.\-]+)",
        )
        if pattern_chiave.search(blocco_aggiornato):
            blocco_aggiornato = pattern_chiave.sub(
                r"\g<1>" + str(valore),
                blocco_aggiornato
            )
            modifiche += 1

    if modifiche == 0:
        print(f"  [!] Nessuna chiave trovata nel blocco '{league_id}'")
        return False

    # Sostituisci il blocco nel contenuto del file
    contenuto_nuovo = contenuto[:match.start(2)] + blocco_aggiornato + contenuto[match.end(2):]

    # Scrivi il file aggiornato
    with open(PREDICTOR_FILE, "w", encoding="utf-8") as f:
        f.write(contenuto_nuovo)

    print(f"  [OK] predictor.py aggiornato per '{league_id}' ({modifiche} parametri)")
    return True


def _aggiungi_voce_log(league_id, params_vecchi, params_nuovi,
                        score_vecchio, score_nuovo, n_partite, applicato):
    """
    Aggiunge una voce al log del re-training.
    Mantiene la storia completa di ogni re-training con before/after.
    """
    log = _carica_log()

    voce = {
        "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "lega": league_id,
        "n_partite": n_partite,
        "score_vecchio": round(score_vecchio, 2),
        "score_nuovo": round(score_nuovo, 2),
        "miglioramento": round(score_nuovo - score_vecchio, 2),
        "applicato": applicato,
        "params_vecchi": {
            k: v for k, v in params_vecchi.items()
            if not k.startswith("_")
        } if params_vecchi else {},
        "params_nuovi": {
            k: v for k, v in params_nuovi.items()
            if not k.startswith("_")
        } if params_nuovi else {},
    }

    log.append(voce)
    _salva_log(log)
    return voce


# ─────────────────────────────────────────────────────────────────────────────
# Funzione principale di re-training per una singola lega
# ─────────────────────────────────────────────────────────────────────────────

def retrain_lega(league_id, dry_run=False, verbose=True):
    """
    Esegue il ciclo completo di re-training per una lega:
    1. Scarica CSV piu' aggiornato
    2. Calcola accuracy baseline (parametri attuali)
    3. Ottimizza parametri con grid search
    4. Se migliora >= SOGLIA_MIGLIORAMENTO%, aggiorna predictor.py
    5. Logga tutto

    Parametri:
        league_id: id della lega (es. 'serie-a')
        dry_run: se True, non modifica predictor.py (solo mostra risultati)
        verbose: se True, stampa dettagli

    Ritorna un dict con:
        {lega, score_vecchio, score_nuovo, miglioramento, applicato, n_partite}
    """
    from optimize_weights import (
        LEGA_CONFIG, get_partite_stagione_corrente,
        testa_parametri, optimize_lega, calcola_accuracy_corrente
    )
    from data_loader import load_all_data
    from predictor import LEAGUE_PARAMS, DEFAULT_LEAGUE_PARAMS

    cfg = LEGA_CONFIG.get(league_id)
    if cfg is None:
        print(f"  [!] Lega non supportata: {league_id}")
        return None

    sep = "─" * 55
    print(f"\n{sep}")
    print(f"  RE-TRAINING: {league_id.upper()}")
    print(sep)

    # ── STEP 1: Scarica CSV aggiornato ──
    url = FOOTBALL_DATA_URLS.get(league_id)
    data_dir = DATA_DIRS.get(league_id)
    csv_name = CSV_RETRAIN_NAMES.get(league_id)

    if url and data_dir and csv_name:
        dest_path = os.path.join(data_dir, csv_name)
        if verbose:
            print(f"  Scaricamento dati aggiornati...")
        scaricato = _scarica_csv(url, dest_path)
        if not scaricato:
            print(f"  [!] Download fallito, uso dati esistenti")
    else:
        print(f"  [!] URL/cartella non configurati per {league_id}")

    # ── STEP 2: Carica dati e calcola baseline ──
    if verbose:
        print(f"  Caricamento storico CSV...")
    try:
        df = load_all_data(cfg["csv_code"])
    except Exception as e:
        print(f"  [!] Errore caricamento dati: {e}")
        return None

    partite = get_partite_stagione_corrente(df)
    n_partite = len(partite)

    if n_partite < MIN_PARTITE:
        print(f"  [!] Solo {n_partite} partite disponibili "
              f"(minimo {MIN_PARTITE}), skip re-training.")
        return {
            "lega": league_id,
            "score_vecchio": None,
            "score_nuovo": None,
            "miglioramento": None,
            "applicato": False,
            "n_partite": n_partite,
            "motivo_skip": f"Meno di {MIN_PARTITE} partite",
        }

    if verbose:
        print(f"  Partite stagione corrente: {n_partite}")
        print(f"  Calcolo accuracy baseline (parametri attuali)...")

    score_vec, a1_vec, ao_vec, ag_vec, _ = calcola_accuracy_corrente(
        league_id, df=df, partite=partite
    )
    params_vecchi = LEAGUE_PARAMS.get(league_id, DEFAULT_LEAGUE_PARAMS).copy()

    print(f"  BASELINE  => score={score_vec:.1f}%  "
          f"(1X2={a1_vec:.1f}%, O/U={ao_vec:.1f}%, Goal={ag_vec:.1f}%)")

    # ── STEP 3: Grid search ──
    if verbose:
        print(f"  Grid search in corso...")

    params_nuovi, score_nuovo, _ = optimize_lega(
        league_id, df=df, partite=partite, verbose=verbose
    )

    if params_nuovi is None:
        print(f"  [!] Ottimizzazione fallita per {league_id}")
        return None

    miglioramento = score_nuovo - score_vec
    print(f"  OTTIMIZZATO => score={score_nuovo:.1f}%  "
          f"(miglioramento: {miglioramento:+.1f}%)")

    # ── STEP 4: Decisione applicazione ──
    applicato = False
    motivo = ""

    if miglioramento < SOGLIA_MIGLIORAMENTO:
        motivo = (f"Miglioramento {miglioramento:+.1f}% < soglia {SOGLIA_MIGLIORAMENTO}%")
        print(f"  [SKIP] {motivo}. Parametri NON aggiornati.")
    elif n_partite < MIN_PARTITE:
        motivo = f"Dataset troppo piccolo ({n_partite} partite)"
        print(f"  [SKIP] {motivo}.")
    elif dry_run:
        motivo = "Dry-run: aggiornamento simulato ma non applicato"
        print(f"  [DRY-RUN] {motivo}.")
        print(f"  Parametri che sarebbero stati applicati:")
        for k, v in params_nuovi.items():
            if not k.startswith("_"):
                v_vec = params_vecchi.get(k, "N/A")
                print(f"    {k}: {v_vec} -> {v}")
    else:
        # Applica i nuovi parametri
        print(f"  Aggiornamento LEAGUE_PARAMS in predictor.py...")
        aggiornato = _aggiorna_league_params(league_id, params_nuovi)
        if aggiornato:
            applicato = True
            motivo = f"Miglioramento {miglioramento:+.1f}% >= soglia {SOGLIA_MIGLIORAMENTO}%"
            print(f"  [OK] Parametri aggiornati per '{league_id}'!")
            print(f"  Prima:  score={score_vec:.1f}%")
            print(f"  Dopo:   score={score_nuovo:.1f}%")
        else:
            motivo = "Errore aggiornamento file predictor.py"
            print(f"  [!] Aggiornamento fallito.")

    # ── STEP 5: Log ──
    _aggiungi_voce_log(
        league_id, params_vecchi, params_nuovi,
        score_vec, score_nuovo, n_partite, applicato
    )

    return {
        "lega": league_id,
        "score_vecchio": round(score_vec, 2),
        "score_nuovo": round(score_nuovo, 2),
        "miglioramento": round(miglioramento, 2),
        "applicato": applicato,
        "n_partite": n_partite,
        "motivo": motivo,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Runner multi-lega
# ─────────────────────────────────────────────────────────────────────────────

def esegui_retrain(leghe=None, dry_run=False):
    """
    Esegue il re-training per tutte le leghe (o solo quelle specificate).
    Aggiorna last_retrain.txt alla fine.

    Ritorna: lista di risultati per ogni lega
    """
    if leghe is None:
        leghe = list(FOOTBALL_DATA_URLS.keys())

    print("=" * 60)
    print(f"RE-TRAINING AUTOMATICO MODELLO PREDITTIVO")
    print(f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    if dry_run:
        print("MODALITA': DRY-RUN (nessuna modifica applicata)")
    print("=" * 60)

    risultati = []

    for league_id in leghe:
        try:
            res = retrain_lega(league_id, dry_run=dry_run)
            if res:
                risultati.append(res)
        except Exception as e:
            print(f"\n  [ERRORE] {league_id}: {e}")
            import traceback
            traceback.print_exc()

    # Riepilogo finale
    print(f"\n{'=' * 60}")
    print("RIEPILOGO RE-TRAINING")
    print("=" * 60)
    for r in risultati:
        stato = "[AGGIORNATO]" if r["applicato"] else "[INVARIATO] "
        score_info = (f"score: {r['score_vecchio']}% -> {r['score_nuovo']}%  "
                      f"({r['miglioramento']:+.1f}%)"
                      if r.get("score_vecchio") is not None else "dati insufficienti")
        print(f"  {stato} {r['lega']:<18} {score_info}")

    aggiornati = sum(1 for r in risultati if r.get("applicato"))
    print(f"\n  Leghe aggiornate: {aggiornati}/{len(risultati)}")

    # Salva timestamp ultimo re-training
    if not dry_run:
        try:
            with open(LAST_RETRAIN_FILE, "w") as f:
                f.write(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            print(f"  Timestamp salvato: {os.path.basename(LAST_RETRAIN_FILE)}")
        except Exception as e:
            print(f"  [!] Errore salvataggio timestamp: {e}")

    print("=" * 60)
    return risultati


def controlla_e_ritrain(forza=False, dry_run=False):
    """
    Controlla se e' necessario eseguire il re-training.
    Se sono passati piu' di 7 giorni dall'ultimo re-training (o non e'
    mai stato eseguito), avvia il processo.

    Parametri:
        forza: se True, esegue il re-training indipendentemente dalla data
        dry_run: se True, non modifica predictor.py

    Ritorna: True se il re-training e' stato eseguito, False altrimenti
    """
    GIORNI_INTERVALLO = 7

    if not forza and os.path.exists(LAST_RETRAIN_FILE):
        try:
            with open(LAST_RETRAIN_FILE, "r") as f:
                ultimo = f.read().strip()
            ultimo_dt = datetime.strptime(ultimo, "%Y-%m-%d %H:%M:%S")
            delta = datetime.now() - ultimo_dt
            if delta.days < GIORNI_INTERVALLO:
                giorni_rimasti = GIORNI_INTERVALLO - delta.days
                print(f"  [Re-training] Prossimo aggiornamento tra {giorni_rimasti} giorni "
                      f"(ultimo: {ultimo})")
                return False
        except Exception:
            pass  # Se non riesce a leggere, esegue il re-training

    # Esegue il re-training
    print("  [Re-training] Avvio re-training settimanale...")
    esegui_retrain(dry_run=dry_run)
    return True


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Re-training automatico del modello predittivo"
    )
    parser.add_argument(
        "--lega", type=str, default=None,
        help="Lega specifica (es. serie-a, premier-league). "
             "Default: tutte le leghe"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Simula il re-training senza modificare predictor.py"
    )
    parser.add_argument(
        "--forza", action="store_true",
        help="Forza il re-training anche se non sono passati 7 giorni"
    )
    args = parser.parse_args()

    leghe = [args.lega] if args.lega else None

    risultati = esegui_retrain(leghe=leghe, dry_run=args.dry_run)

    # Stampa log storico
    if os.path.exists(LOG_FILE):
        print(f"\n  Log completo salvato in: {LOG_FILE}")

    input("\nPremi INVIO per chiudere...")
