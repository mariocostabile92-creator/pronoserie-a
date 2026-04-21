"""
data_loader.py
Carica e unifica tutti i CSV storici.
Supporta Serie A (I1) e Premier League (E0).
"""

import os
import glob
import warnings
import pandas as pd

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)

CARTELLA_CSV = os.environ.get("CARTELLA_CSV", os.path.join(os.path.dirname(os.path.abspath(__file__)), "data_seriea"))
CARTELLA_PL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data_pl")
CARTELLA_LL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data_laliga")
CARTELLA_UCL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data_ucl")
CARTELLA_UEL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data_uel")
CARTELLA_UECL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data_uecl")
CARTELLA_BL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data_bundesliga")
CARTELLA_L1 = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data_ligue1")

COLONNE_NECESSARIE = [
    "Div", "Date", "HomeTeam", "AwayTeam",
    "FTHG", "FTAG", "FTR",
    "HTHG", "HTAG", "HTR"
]

COLONNE_QUOTE = [
    "WHH", "WHD", "WHA",
    "GBH", "GBD", "GBA",
    "IWH", "IWD", "IWA",
    "LBH", "LBD", "LBA",
    "SBH", "SBD", "SBA",
]


def load_all_data(league="I1") -> pd.DataFrame:
    """
    Carica CSV storici.
    league="I1" per Serie A, league="E0" per Premier League.
    """
    # Determina cartella e divisione
    if league == "E0":
        cartella = CARTELLA_PL
    elif league == "SP1":
        cartella = CARTELLA_LL
    elif league == "UCL":
        cartella = CARTELLA_UCL
    elif league == "UEL":
        cartella = CARTELLA_UEL
    elif league == "UECL":
        cartella = CARTELLA_UECL
    elif league == "D1":
        cartella = CARTELLA_BL
    elif league == "F1":
        cartella = CARTELLA_L1
    else:
        cartella = CARTELLA_CSV

    if not os.path.exists(cartella):
        if league == "E0":
            raise FileNotFoundError(f"Cartella PL non trovata: {cartella}")
        raise FileNotFoundError(
            f"Cartella non trovata: {cartella}\n"
            "Controlla che la cartella 'Mariocalcio' sia sul Desktop."
        )

    pattern = os.path.join(cartella, "**", "*.csv")
    files = glob.glob(pattern, recursive=True)
    # Rimuovi duplicati (normalizza i path)
    files = list(set(os.path.normpath(f) for f in files))

    if not files:
        raise FileNotFoundError(
            f"Nessun file CSV trovato in: {CARTELLA_CSV}"
        )

    frames = []
    for f in files:
        try:
            df = pd.read_csv(f, encoding="utf-8", on_bad_lines="skip", low_memory=False)
        except Exception:
            try:
                df = pd.read_csv(f, encoding="latin-1", on_bad_lines="skip", low_memory=False)
            except Exception as e:
                print(f"  Errore lettura {f}: {e}")
                continue

        # Normalizza nomi colonne
        df.columns = [c.strip() for c in df.columns]

        # Aggiunge colonne mancanti con NaN
        for col in COLONNE_NECESSARIE + COLONNE_QUOTE:
            if col not in df.columns:
                df[col] = None

        frames.append(df)

    if not frames:
        raise ValueError("Nessun file CSV leggibile trovato.")

    # Filtra frame vuoti prima del concat
    frames = [f for f in frames if len(f) > 0]
    dati = pd.concat(frames, ignore_index=True, sort=False)

    # Filtra per campionato
    if "Div" in dati.columns:
        dati = dati[dati["Div"] == league].copy()

    # Pulisce colonne numeriche
    for col in ["FTHG", "FTAG", "HTHG", "HTAG"]:
        dati[col] = pd.to_numeric(dati[col], errors="coerce")

    # Pulisce colonne quote bookmaker
    for col in COLONNE_QUOTE:
        if col in dati.columns:
            dati[col] = pd.to_numeric(dati[col], errors="coerce")

    # Rimuove righe senza squadre o gol
    dati = dati.dropna(subset=["HomeTeam", "AwayTeam", "FTHG", "FTAG"])

    # Rimuove duplicati (stessa partita nello stesso giorno)
    dati = dati.drop_duplicates(subset=["Date", "HomeTeam", "AwayTeam"], keep="first")
    dati = dati.reset_index(drop=True)

    # Normalizza nomi squadre
    dati["HomeTeam"] = dati["HomeTeam"].str.strip()
    dati["AwayTeam"] = dati["AwayTeam"].str.strip()

    # Ordina per data (per forma pesata e H2H)
    dati["Date"] = pd.to_datetime(dati["Date"], dayfirst=True, format="mixed", errors="coerce")
    dati = dati.sort_values("Date", ascending=True).reset_index(drop=True)

    # Filtra ultimi 15 anni (dal 2011) - dati piu' recenti sono piu' rilevanti
    cutoff = pd.Timestamp("2011-01-01")
    dati_recenti = dati[dati["Date"] >= cutoff].copy()
    if len(dati_recenti) >= 500:
        dati = dati_recenti.reset_index(drop=True)

    return dati


def get_teams(df: pd.DataFrame) -> list:
    """Ritorna la lista ordinata di tutte le squadre presenti nei dati."""
    home = set(df["HomeTeam"].dropna().unique())
    away = set(df["AwayTeam"].dropna().unique())
    tutte = sorted(home | away)
    return tutte
