"""
league.py
Simula una stagione Serie A completa e calcola la classifica.
Supporta simulazione delle giornate rimanenti a partire dalla classifica reale.
"""

import pandas as pd
import itertools
from simulator import simulate_match
from season_2526 import CLASSIFICA_REALE_30G, genera_partite_rimanenti


PUNTI_VITTORIA = 3
PUNTI_PAREGGIO = 1
PUNTI_SCONFITTA = 0


def crea_classifica_vuota(squadre: list) -> dict:
    """Crea dizionario classifica con tutti i valori a zero."""
    return {
        sq: {"G": 0, "V": 0, "P": 0, "S": 0, "GF": 0, "GS": 0, "DR": 0, "Punti": 0}
        for sq in squadre
    }


def aggiorna_classifica(classifica: dict, home: str, away: str, gol_home: int, gol_away: int):
    """Aggiorna la classifica con il risultato di una partita."""
    classifica[home]["G"] += 1
    classifica[away]["G"] += 1
    classifica[home]["GF"] += gol_home
    classifica[home]["GS"] += gol_away
    classifica[away]["GF"] += gol_away
    classifica[away]["GS"] += gol_home
    classifica[home]["DR"] = classifica[home]["GF"] - classifica[home]["GS"]
    classifica[away]["DR"] = classifica[away]["GF"] - classifica[away]["GS"]

    if gol_home > gol_away:
        classifica[home]["V"] += 1
        classifica[home]["Punti"] += PUNTI_VITTORIA
        classifica[away]["S"] += 1
    elif gol_home < gol_away:
        classifica[away]["V"] += 1
        classifica[away]["Punti"] += PUNTI_VITTORIA
        classifica[home]["S"] += 1
    else:
        classifica[home]["P"] += 1
        classifica[away]["P"] += 1
        classifica[home]["Punti"] += PUNTI_PAREGGIO
        classifica[away]["Punti"] += PUNTI_PAREGGIO


def simulate_season(squadre: list, get_stats_fn, df) -> pd.DataFrame:
    """
    Simula una stagione completa (andata + ritorno).
    squadre: lista delle 20 squadre
    get_stats_fn: funzione get_team_stats(df, nome) -> dict
    df: DataFrame con i dati storici
    Ritorna DataFrame classifica ordinata.
    """
    classifica = crea_classifica_vuota(squadre)
    risultati = []

    # Genera tutte le partite (andata e ritorno)
    partite_andata = list(itertools.permutations(squadre, 2))

    for home, away in partite_andata:
        try:
            hs = get_stats_fn(df, home)
            as_ = get_stats_fn(df, away)
            sim = simulate_match(hs, as_)
            aggiorna_classifica(classifica, home, away, sim["home_goals"], sim["away_goals"])
            risultati.append({
                "Casa": home,
                "Ospite": away,
                "Gol Casa": sim["home_goals"],
                "Gol Ospite": sim["away_goals"],
                "Risultato": sim["risultato"]
            })
        except Exception:
            continue

    # Converti in DataFrame e ordina
    df_class = pd.DataFrame([
        {"Squadra": sq, **vals}
        for sq, vals in classifica.items()
    ])
    df_class = df_class.sort_values(
        ["Punti", "DR", "GF"], ascending=False
    ).reset_index(drop=True)
    df_class.index += 1
    df_class.index.name = "Pos"

    return df_class, risultati


def simulate_remaining_season(get_stats_fn, df) -> pd.DataFrame:
    """
    Simula le giornate rimanenti (31a-38a) partendo dalla classifica REALE
    della stagione 2025-2026 (30 giornate gia' giocate).
    Ritorna DataFrame con la classifica finale proiettata.
    """
    # Parte dalla classifica reale
    classifica = {
        row["Squadra"]: {
            "G": row["G"], "V": row["V"], "P": row["N"],
            "S": row["P"], "GF": row["GF"], "GS": row["GS"],
            "DR": row["DR"], "Punti": row["Punti"]
        }
        for row in CLASSIFICA_REALE_30G
    }

    # Simula le partite rimanenti
    partite_rim = genera_partite_rimanenti()
    for home, away in partite_rim:
        if home not in classifica or away not in classifica:
            continue
        try:
            hs = get_stats_fn(df, home)
            as_ = get_stats_fn(df, away)
            sim = simulate_match(hs, as_)
            aggiorna_classifica(classifica, home, away, sim["home_goals"], sim["away_goals"])
        except Exception:
            continue

    df_class = pd.DataFrame([
        {"Squadra": sq, **vals}
        for sq, vals in classifica.items()
    ])
    df_class = df_class.sort_values(
        ["Punti", "DR", "GF"], ascending=False
    ).reset_index(drop=True)
    df_class.index += 1
    df_class.index.name = "Pos"
    return df_class


def simulate_matchday(partite: list, get_stats_fn, df) -> list:
    """
    Simula una singola giornata.
    partite: lista di tuple (home, away)
    Ritorna lista di dizionari con i risultati.
    """
    risultati = []
    for home, away in partite:
        try:
            hs = get_stats_fn(df, home)
            as_ = get_stats_fn(df, away)
            sim = simulate_match(hs, as_)
            risultati.append({
                "Casa": home,
                "Ospite": away,
                "Gol Casa": sim["home_goals"],
                "Gol Ospite": sim["away_goals"],
                "Risultato": sim["risultato"],
                "Esito": sim["esito"]
            })
        except Exception as e:
            risultati.append({
                "Casa": home,
                "Ospite": away,
                "Gol Casa": "-",
                "Gol Ospite": "-",
                "Risultato": "?",
                "Esito": f"Errore: {e}"
            })
    return risultati
