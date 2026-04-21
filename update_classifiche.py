"""
update_classifiche.py
Scarica le classifiche REALI correnti per tutte le 5 leghe top europee
da football-data.co.uk, calcola punti medi per partita e forma recente
pesata (ultime 5 partite con decay factor).

Salva i risultati in classifiche_reali.json, importabile da predictor.py.

Utilizzo:
    python update_classifiche.py           # Aggiorna tutte le leghe
    python update_classifiche.py --lega serie-a   # Solo una lega

Frequenza consigliata: settimanale (integrato in auto_update.py --classifiche).
"""

import os
import json
import csv
import io
import sys
from datetime import datetime

try:
    import urllib.request
    HAS_URLLIB = True
except ImportError:
    HAS_URLLIB = False

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(DATA_DIR, "classifiche_reali.json")

# URL CSV stagione 2025-2026 da football-data.co.uk
# Aggiornati automaticamente durante la stagione
LEGHE_URL = {
    "serie-a":        "https://www.football-data.co.uk/mmz4281/2526/I1.csv",
    "premier-league": "https://www.football-data.co.uk/mmz4281/2526/E0.csv",
    "la-liga":        "https://www.football-data.co.uk/mmz4281/2526/SP1.csv",
    "bundesliga":     "https://www.football-data.co.uk/mmz4281/2526/D1.csv",
    "ligue-1":        "https://www.football-data.co.uk/mmz4281/2526/F1.csv",
}

# Pesi forma recente: dalla partita piu' recente alla meno recente (5 partite)
# Somma = 1.0, la piu' recente pesa il 35%
PESI_FORMA = [0.35, 0.25, 0.20, 0.12, 0.08]


def _fetch_csv(url: str) -> str | None:
    """Scarica il contenuto di un CSV da URL. Gestisce UTF-8 e Latin-1."""
    if not HAS_URLLIB:
        print("  urllib non disponibile!")
        return None
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read()
            # Prova prima UTF-8, poi Latin-1 come fallback
            try:
                return raw.decode("utf-8")
            except UnicodeDecodeError:
                return raw.decode("latin-1")
    except Exception as e:
        print(f"  Errore download {url}: {e}")
        return None


def _calcola_classifica_da_csv(contenuto_csv: str) -> tuple:
    """
    Calcola classifica e forma recente da un CSV football-data.co.uk.

    Formato atteso colonne: HomeTeam, AwayTeam, FTHG (gol home), FTAG (gol away), Date.

    Ritorna:
        classifica: {squadra: {"punti": int, "giocate": int, "gf": int,
                               "gs": int, "dr": int, "pts_pg": float}}
        forma:      {squadra: {"forma_5": float, "ultimi_risultati": list}}
    """
    classifica = {}
    partite_squadra = {}  # {squadra: [(data_str, pts_ottenuti, risultato), ...]}

    try:
        reader = csv.DictReader(io.StringIO(contenuto_csv))
        righe = []

        for riga in reader:
            # Salta righe vuote o senza dati essenziali
            home = (riga.get("HomeTeam") or "").strip()
            away = (riga.get("AwayTeam") or "").strip()
            if not home or not away:
                continue
            try:
                gf = int(riga.get("FTHG", "").strip())
                ga = int(riga.get("FTAG", "").strip())
            except (ValueError, TypeError):
                continue

            data = (riga.get("Date") or "").strip()
            righe.append((data, home, away, gf, ga))

        # Ordina per data (partite piu' vecchie prima)
        righe.sort(key=lambda x: x[0])

        for data, home, away, gf, ga in righe:
            # Inizializza squadre se non presenti
            for sq in [home, away]:
                if sq not in classifica:
                    classifica[sq] = {"punti": 0, "giocate": 0, "gf": 0, "gs": 0, "dr": 0}
                    partite_squadra[sq] = []

            # Calcola risultato e punti
            if gf > ga:
                # Vittoria casalinga
                classifica[home]["punti"] += 3
                pts_home, pts_away = 3, 0
                ris_home, ris_away = "V", "P"
            elif gf == ga:
                # Pareggio
                classifica[home]["punti"] += 1
                classifica[away]["punti"] += 1
                pts_home, pts_away = 1, 1
                ris_home, ris_away = "X", "X"
            else:
                # Vittoria ospite
                classifica[away]["punti"] += 3
                pts_home, pts_away = 0, 3
                ris_home, ris_away = "P", "V"

            # Aggiorna gol e statistiche
            classifica[home]["giocate"] += 1
            classifica[away]["giocate"] += 1
            classifica[home]["gf"] += gf
            classifica[home]["gs"] += ga
            classifica[home]["dr"] += (gf - ga)
            classifica[away]["gf"] += ga
            classifica[away]["gs"] += gf
            classifica[away]["dr"] += (ga - gf)

            # Registra nella storia delle partite
            partite_squadra[home].append((data, pts_home, ris_home))
            partite_squadra[away].append((data, pts_away, ris_away))

        # Calcola punti per partita (metrica normalizzata per confronto)
        for sq in classifica:
            g = classifica[sq]["giocate"]
            classifica[sq]["pts_pg"] = round(classifica[sq]["punti"] / g, 3) if g > 0 else 0.0

        # Calcola forma recente con decay factor (ultime 5 partite)
        forma = {}
        for sq, partite in partite_squadra.items():
            # Le partite sono ordinate dalla piu' vecchia; prendiamo le ultime 5
            ultime = partite[-5:]
            ultime.reverse()  # Dalla piu' recente alla meno recente

            forma_score = 0.0
            risultati = []

            for i, (_, pts, ris) in enumerate(ultime):
                if i >= len(PESI_FORMA):
                    break
                peso = PESI_FORMA[i]
                # Converte risultato in score normalizzato [0, 1]
                if pts == 3:
                    score = 1.0    # Vittoria
                elif pts == 1:
                    score = 0.5    # Pareggio
                else:
                    score = 0.0    # Sconfitta
                forma_score += peso * score
                risultati.append(ris)

            forma[sq] = {
                "forma_5": round(forma_score, 3),
                # Es: ["V", "X", "P", "V", "V"] dalla piu' recente
                "ultimi_risultati": risultati,
            }

        return classifica, forma

    except Exception as e:
        print(f"  Errore parsing CSV: {e}")
        return {}, {}


def aggiorna_classifiche(solo_lega: str = None) -> bool:
    """
    Scarica e aggiorna le classifiche per tutte le 5 leghe top (o solo una).
    Salva i risultati in classifiche_reali.json.

    Parametri:
        solo_lega: se specificato (es. 'serie-a'), aggiorna solo quella lega.

    Ritorna True se almeno una lega e' stata aggiornata.
    """
    print(f"\n{'='*60}")
    print(f"AGGIORNAMENTO CLASSIFICHE - {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print(f"{'='*60}")

    # Carica dati esistenti (per aggiornamento parziale)
    dati_esistenti = {}
    if os.path.exists(OUTPUT_FILE):
        try:
            with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
                dati_esistenti = json.load(f)
        except Exception:
            pass

    risultato = {
        "ultimo_aggiornamento": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "leghe": dati_esistenti.get("leghe", {}),
    }

    leghe_da_aggiornare = LEGHE_URL if solo_lega is None else {
        solo_lega: LEGHE_URL[solo_lega]
    } if solo_lega in LEGHE_URL else {}

    ok_count = 0

    for lega, url in leghe_da_aggiornare.items():
        print(f"\n  [{lega.upper()}] Scarico da: {url}")
        contenuto = _fetch_csv(url)

        if not contenuto or len(contenuto) < 200:
            print(f"  [{lega.upper()}] ERRORE: CSV vuoto o non scaricato - mantengo dati precedenti")
            continue

        classifica, forma = _calcola_classifica_da_csv(contenuto)

        if not classifica:
            print(f"  [{lega.upper()}] ERRORE: Nessuna squadra trovata nel CSV")
            continue

        n_squadre = len(classifica)
        # Squadra con piu' punti (leader)
        leader = max(classifica.items(), key=lambda x: x[1]["punti"])
        leader_pts = leader[1]["punti"]
        leader_g = leader[1]["giocate"]

        print(f"  [{lega.upper()}] OK: {n_squadre} squadre | "
              f"Leader: {leader[0]} ({leader_pts} pts in {leader_g} partite)")

        risultato["leghe"][lega] = {
            "classifica": classifica,
            "forma": forma,
            "aggiornato": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        ok_count += 1

    if ok_count > 0:
        try:
            with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                json.dump(risultato, f, ensure_ascii=False, indent=2)
            print(f"\n  Risultati salvati in: {OUTPUT_FILE}")
            print(f"  Leghe aggiornate: {ok_count}/{len(leghe_da_aggiornare)}")
        except Exception as e:
            print(f"\n  ERRORE salvataggio JSON: {e}")
            return False
    else:
        print("\n  Nessuna lega aggiornata. Dati precedenti mantenuti.")

    print(f"{'='*60}")
    return ok_count > 0


def carica_classifiche() -> dict:
    """
    Carica le classifiche salvate da classifiche_reali.json.
    Ritorna il dizionario completo o {} se non disponibile.
    Usata da predictor.py al momento del caricamento del modulo.
    """
    if not os.path.exists(OUTPUT_FILE):
        return {}
    try:
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def stampa_classifica(lega: str = "serie-a"):
    """Stampa la classifica di una lega dal file JSON salvato."""
    dati = carica_classifiche()
    lega_dati = dati.get("leghe", {}).get(lega)
    if not lega_dati:
        print(f"Nessun dato disponibile per {lega}. Esegui prima: python update_classifiche.py")
        return

    classifica = lega_dati.get("classifica", {})
    forma = lega_dati.get("forma", {})

    # Ordina per punti decrescenti
    classifica_ord = sorted(classifica.items(), key=lambda x: (-x[1]["punti"], -x[1]["dr"], -x[1]["gf"]))

    print(f"\n{'='*70}")
    print(f"CLASSIFICA {lega.upper()} (aggiornata: {lega_dati.get('aggiornato', 'N/D')})")
    print(f"{'='*70}")
    print(f"{'#':<3} {'Squadra':<25} {'Pts':>4} {'G':>4} {'GF':>4} {'GS':>4} {'DR':>5} {'Pts/G':>6} {'Forma':>6}")
    print("-" * 70)

    for i, (sq, dati_sq) in enumerate(classifica_ord, 1):
        f = forma.get(sq, {})
        forma_str = " ".join(f.get("ultimi_risultati", []))
        print(f"{i:<3} {sq:<25} {dati_sq['punti']:>4} {dati_sq['giocate']:>4} "
              f"{dati_sq['gf']:>4} {dati_sq['gs']:>4} {dati_sq['dr']:>5} "
              f"{dati_sq['pts_pg']:>6.2f} {forma_str:>6}")


if __name__ == "__main__":
    args = sys.argv[1:]

    if "--stampa" in args:
        # Stampa classifica di una lega
        lega = next((a for a in args if a != "--stampa"), "serie-a")
        for lega_target in LEGHE_URL:
            if lega_target in lega or lega in lega_target:
                stampa_classifica(lega_target)
                break
        else:
            stampa_classifica(lega)
    elif "--lega" in args:
        # Aggiorna solo una lega specifica
        idx = args.index("--lega")
        if idx + 1 < len(args):
            lega_target = args[idx + 1]
            ok = aggiorna_classifiche(solo_lega=lega_target)
            sys.exit(0 if ok else 1)
        else:
            print("Uso: python update_classifiche.py --lega <nome-lega>")
            print(f"Leghe disponibili: {', '.join(LEGHE_URL.keys())}")
            sys.exit(1)
    else:
        # Aggiorna tutte le leghe
        ok = aggiorna_classifiche()
        if ok:
            print("\nAggiornamento classifiche completato!")
            # Mostra anteprima
            for lega in LEGHE_URL:
                dati = carica_classifiche()
                lega_dati = dati.get("leghe", {}).get(lega, {})
                if lega_dati:
                    cl = lega_dati.get("classifica", {})
                    if cl:
                        leader = max(cl.items(), key=lambda x: x[1]["punti"])
                        print(f"  {lega:<18}: leader {leader[0]} ({leader[1]['punti']} pts)")
        else:
            print("\nErrore: nessuna lega aggiornata.")
            sys.exit(1)
