"""
simulator.py
Motore di simulazione partita usando la distribuzione di Poisson.
"""

import numpy as np
from scipy.stats import poisson

ALPHA_H2H = 0.08
ALPHA_FORMA = 0.06


def simulate_match(home_stats: dict, away_stats: dict, seed: int = None) -> dict:
    """
    Simula una partita di calcio usando il modello di Dixon-Coles (Poisson).
    Integra fattori H2H e forma pesata se disponibili.
    """
    if seed is not None:
        np.random.seed(seed)

    # Lambda attesi per i gol
    lambda_home = (
        home_stats["forza_att_casa"]
        * away_stats["forza_dif_trasf"]
        * home_stats["media_gol_casa_campionato"]
    )
    lambda_away = (
        away_stats["forza_att_trasf"]
        * home_stats["forza_dif_casa"]
        * home_stats["media_gol_trasf_campionato"]
    )

    # Correzione H2H (se disponibile)
    h2h = home_stats.get("h2h")
    if h2h is not None:
        adv = h2h.get("h2h_advantage", 0)
        lambda_home *= (1.0 + ALPHA_H2H * adv)
        lambda_away *= (1.0 - ALPHA_H2H * adv)

    # Correzione forma pesata (se disponibile)
    if "forma_casa_pesata" in home_stats and "forma_trasf_pesata" in away_stats:
        forma_diff = home_stats["forma_casa_pesata"] - away_stats["forma_trasf_pesata"]
        forma_factor = 1.0 + ALPHA_FORMA * forma_diff
        lambda_home *= forma_factor
        lambda_away *= (2.0 - forma_factor)

    # Clamp per evitare valori anomali
    lambda_home = max(0.3, min(lambda_home, 5.0))
    lambda_away = max(0.3, min(lambda_away, 5.0))

    # Simula gol totali
    gol_home = int(np.random.poisson(lambda_home))
    gol_away = int(np.random.poisson(lambda_away))

    # Simula primo tempo (circa 40% dei gol, min 0)
    ht_home = int(np.random.binomial(gol_home, 0.45)) if gol_home > 0 else 0
    ht_away = int(np.random.binomial(gol_away, 0.45)) if gol_away > 0 else 0

    # Possesso palla (proporzionale alla forza di attacco)
    forza_h = home_stats["forza_att_casa"] + home_stats.get("forza_att_trasf", 1.0)
    forza_a = away_stats["forza_att_trasf"] + away_stats.get("forza_att_casa", 1.0)
    totale_forza = forza_h + forza_a
    possesso_home = round((forza_h / totale_forza) * 100) if totale_forza > 0 else 50
    possesso_away = 100 - possesso_home

    # Tiri (stimati: gol attesi * fattore casuale 6-9)
    fattore_tiri_h = np.random.uniform(6, 9)
    fattore_tiri_a = np.random.uniform(5, 8)
    tiri_home = max(1, int(lambda_home * fattore_tiri_h))
    tiri_away = max(1, int(lambda_away * fattore_tiri_a))

    # Risultato finale
    if gol_home > gol_away:
        risultato = "1"
        esito = "Vittoria Casa"
    elif gol_home < gol_away:
        risultato = "2"
        esito = "Vittoria Ospite"
    else:
        risultato = "X"
        esito = "Pareggio"

    return {
        "home_goals": gol_home,
        "away_goals": gol_away,
        "ht_home": ht_home,
        "ht_away": ht_away,
        "possesso_home": possesso_home,
        "possesso_away": possesso_away,
        "tiri_home": tiri_home,
        "tiri_away": tiri_away,
        "risultato": risultato,
        "esito": esito,
        "lambda_home": round(lambda_home, 3),
        "lambda_away": round(lambda_away, 3),
    }
