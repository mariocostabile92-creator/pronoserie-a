"""
stats_engine.py
Calcola statistiche storiche per ogni squadra dai dati CSV.
Include: H2H, forma pesata con decadimento, indici forza attacco/difesa.
"""

import pandas as pd
import numpy as np

DECAY_ALPHA = 0.15  # Decadimento piu' rapido: partite recenti contano molto di piu'
FORM_N = 20  # Ultime 20 partite (circa 1 stagione)
SEASON_DECAY = 0.25  # Decadimento per stagione: ogni stagione passata pesa il 25% in meno


def _weighted_mean(series, dates, ref_year=2026):
    """Media pesata per anno: stagioni recenti contano di piu'."""
    if len(series) == 0:
        return None
    weights = []
    for d in dates:
        try:
            year = d.year if hasattr(d, 'year') else int(str(d)[:4])
            years_ago = max(0, ref_year - year)
            w = np.exp(-SEASON_DECAY * years_ago)
        except Exception:
            w = 0.1
        weights.append(w)
    weights = np.array(weights)
    if weights.sum() == 0:
        return series.mean()
    return np.average(series, weights=weights)


def get_league_averages(df: pd.DataFrame) -> dict:
    """Calcola le medie del campionato (usate come base per gli indici)."""
    media_gol_casa = df["FTHG"].mean()
    media_gol_trasferta = df["FTAG"].mean()
    if pd.isna(media_gol_casa) or media_gol_casa == 0:
        media_gol_casa = 1.5
    if pd.isna(media_gol_trasferta) or media_gol_trasferta == 0:
        media_gol_trasferta = 1.1
    return {
        "media_gol_casa": media_gol_casa,
        "media_gol_trasferta": media_gol_trasferta
    }


def get_h2h_stats(df: pd.DataFrame, home: str, away: str) -> dict | None:
    """
    Calcola statistiche testa a testa tra due squadre.
    Ritorna None se < 3 scontri diretti.
    """
    mask = (
        ((df["HomeTeam"] == home) & (df["AwayTeam"] == away)) |
        ((df["HomeTeam"] == away) & (df["AwayTeam"] == home))
    )
    h2h = df[mask].copy()
    n = len(h2h)

    if n < 3:
        return None

    vittorie_home = 0
    vittorie_away = 0
    pareggi = 0
    gol_home_tot = 0
    gol_away_tot = 0

    for _, row in h2h.iterrows():
        if row["HomeTeam"] == home:
            gh = int(row["FTHG"])
            ga = int(row["FTAG"])
        else:
            gh = int(row["FTAG"])
            ga = int(row["FTHG"])
        gol_home_tot += gh
        gol_away_tot += ga
        if gh > ga:
            vittorie_home += 1
        elif gh < ga:
            vittorie_away += 1
        else:
            pareggi += 1

    h2h_advantage = (vittorie_home - vittorie_away) / n

    # Ultimi 5 scontri diretti (dal piu' recente)
    ultimi = h2h.sort_values("Date", ascending=False).head(5)
    ultimi_5 = []
    for _, row in ultimi.iterrows():
        ht = row["HomeTeam"]
        at = row["AwayTeam"]
        gh = int(row["FTHG"])
        ga = int(row["FTAG"])
        ultimi_5.append(f"{ht} {gh}-{ga} {at}")

    return {
        "n_partite": n,
        "vittorie_home": vittorie_home,
        "pareggi": pareggi,
        "vittorie_away": vittorie_away,
        "media_gol_home": round(gol_home_tot / n, 2),
        "media_gol_away": round(gol_away_tot / n, 2),
        "h2h_advantage": round(h2h_advantage, 3),
        "ultimi_5_h2h": ultimi_5,
    }


def get_weighted_form(df: pd.DataFrame, team: str, n: int = FORM_N) -> dict:
    """
    Calcola la forma pesata con decadimento esponenziale.
    w_i = exp(-alpha * i) dove i=0 e' la partita piu' recente.
    Ritorna forma globale, casa e trasferta, normalizzata in [0, 3].
    """
    tutti = df[(df["HomeTeam"] == team) | (df["AwayTeam"] == team)].copy()
    tutti = tutti.sort_values("Date", ascending=False).head(n)

    if len(tutti) == 0:
        return {"forma_pesata": 1.5, "forma_casa_pesata": 1.5, "forma_trasf_pesata": 1.5}

    # Calcolo forma globale
    punti = []
    for _, row in tutti.iterrows():
        if row["HomeTeam"] == team:
            ftr = row["FTR"]
            p = 3 if ftr == "H" else (1 if ftr == "D" else 0)
        else:
            ftr = row["FTR"]
            p = 3 if ftr == "A" else (1 if ftr == "D" else 0)
        punti.append(p)

    pesi = [np.exp(-DECAY_ALPHA * i) for i in range(len(punti))]
    somma_pesi = sum(pesi)
    forma_pesata = sum(p * w for p, w in zip(punti, pesi)) / somma_pesi if somma_pesi > 0 else 1.5

    # Forma solo casa
    casa = tutti[tutti["HomeTeam"] == team]
    if len(casa) >= 3:
        punti_c = [3 if r["FTR"] == "H" else (1 if r["FTR"] == "D" else 0) for _, r in casa.iterrows()]
        pesi_c = [np.exp(-DECAY_ALPHA * i) for i in range(len(punti_c))]
        sc = sum(pesi_c)
        forma_casa = sum(p * w for p, w in zip(punti_c, pesi_c)) / sc if sc > 0 else 1.5
    else:
        forma_casa = forma_pesata

    # Forma solo trasferta
    trasf = tutti[tutti["AwayTeam"] == team]
    if len(trasf) >= 3:
        punti_t = [3 if r["FTR"] == "A" else (1 if r["FTR"] == "D" else 0) for _, r in trasf.iterrows()]
        pesi_t = [np.exp(-DECAY_ALPHA * i) for i in range(len(punti_t))]
        st = sum(pesi_t)
        forma_trasf = sum(p * w for p, w in zip(punti_t, pesi_t)) / st if st > 0 else 1.5
    else:
        forma_trasf = forma_pesata

    return {
        "forma_pesata": round(forma_pesata, 3),
        "forma_casa_pesata": round(forma_casa, 3),
        "forma_trasf_pesata": round(forma_trasf, 3),
    }


def get_team_stats(df: pd.DataFrame, team_name: str, opponent: str = None) -> dict:
    """
    Calcola statistiche complete per una squadra.
    Se opponent e' specificato, include anche le statistiche H2H.
    """
    medie = get_league_averages(df)

    casa = df[df["HomeTeam"] == team_name].copy()
    trasf = df[df["AwayTeam"] == team_name].copy()
    n_casa = len(casa)
    n_trasf = len(trasf)
    n_tot = n_casa + n_trasf

    if n_casa < 5:
        mgf_casa = medie["media_gol_casa"]
        mgs_casa = medie["media_gol_trasferta"]
    else:
        # Media pesata: partite recenti contano di piu'
        mgf_casa = _weighted_mean(casa["FTHG"], casa["Date"])
        mgs_casa = _weighted_mean(casa["FTAG"], casa["Date"])
        if mgf_casa is None:
            mgf_casa = casa["FTHG"].mean()
        if mgs_casa is None:
            mgs_casa = casa["FTAG"].mean()

    if n_trasf < 5:
        mgf_trasf = medie["media_gol_trasferta"]
        mgs_trasf = medie["media_gol_casa"]
    else:
        mgf_trasf = _weighted_mean(trasf["FTAG"], trasf["Date"])
        mgs_trasf = _weighted_mean(trasf["FTHG"], trasf["Date"])
        if mgf_trasf is None:
            mgf_trasf = trasf["FTAG"].mean()
        if mgs_trasf is None:
            mgs_trasf = trasf["FTHG"].mean()

    forza_att_casa = mgf_casa / medie["media_gol_casa"] if medie["media_gol_casa"] > 0 else 1.0
    forza_dif_casa = mgs_casa / medie["media_gol_trasferta"] if medie["media_gol_trasferta"] > 0 else 1.0
    forza_att_trasf = mgf_trasf / medie["media_gol_trasferta"] if medie["media_gol_trasferta"] > 0 else 1.0
    forza_dif_trasf = mgs_trasf / medie["media_gol_casa"] if medie["media_gol_casa"] > 0 else 1.0

    # Percentuali
    if n_tot > 0:
        vittorie = len(casa[casa["FTR"] == "H"]) + len(trasf[trasf["FTR"] == "A"])
        pareggi = len(df[((df["HomeTeam"] == team_name) | (df["AwayTeam"] == team_name)) & (df["FTR"] == "D")])
        sconfitte = n_tot - vittorie - pareggi
        perc_v = vittorie / n_tot * 100
        perc_p = pareggi / n_tot * 100
        perc_s = sconfitte / n_tot * 100
    else:
        perc_v = perc_p = perc_s = 33.3

    # Forma recente classica (ultimi 5) per retrocompatibilita' UI
    tutti_match = df[(df["HomeTeam"] == team_name) | (df["AwayTeam"] == team_name)].copy()
    tutti_match = tutti_match.sort_values("Date", ascending=False)
    forma_recente = []
    for _, row in tutti_match.head(5).iterrows():
        if row["HomeTeam"] == team_name:
            if row["FTR"] == "H":
                forma_recente.append("V")
            elif row["FTR"] == "D":
                forma_recente.append("P")
            else:
                forma_recente.append("S")
        else:
            if row["FTR"] == "A":
                forma_recente.append("V")
            elif row["FTR"] == "D":
                forma_recente.append("P")
            else:
                forma_recente.append("S")
    while len(forma_recente) < 5:
        forma_recente.append("-")

    # Forma pesata con decadimento
    forma = get_weighted_form(df, team_name)

    result = {
        "nome": team_name,
        "n_partite": n_tot,
        "mgf_casa": round(mgf_casa, 3),
        "mgs_casa": round(mgs_casa, 3),
        "mgf_trasf": round(mgf_trasf, 3),
        "mgs_trasf": round(mgs_trasf, 3),
        "forza_att_casa": round(forza_att_casa, 3),
        "forza_dif_casa": round(forza_dif_casa, 3),
        "forza_att_trasf": round(forza_att_trasf, 3),
        "forza_dif_trasf": round(forza_dif_trasf, 3),
        "perc_vittorie": round(perc_v, 1),
        "perc_pareggi": round(perc_p, 1),
        "perc_sconfitte": round(perc_s, 1),
        "forma_recente": forma_recente,
        "forma_pesata": forma["forma_pesata"],
        "forma_casa_pesata": forma["forma_casa_pesata"],
        "forma_trasf_pesata": forma["forma_trasf_pesata"],
        "media_gol_casa_campionato": medie["media_gol_casa"],
        "media_gol_trasf_campionato": medie["media_gol_trasferta"],
    }

    # H2H se richiesto
    if opponent is not None:
        result["h2h"] = get_h2h_stats(df, team_name, opponent)
    else:
        result["h2h"] = None

    return result
