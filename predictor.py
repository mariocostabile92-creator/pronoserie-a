"""
predictor.py
Calcola le probabilità 1X2 usando Dixon-Coles (Poisson corretto),
con integrazione H2H, forma pesata, confronto bookmaker e indice di confidence.
"""

import numpy as np
import pandas as pd
from scipy.stats import poisson
from stats_engine import get_h2h_stats
from season_2526 import get_xg, get_xg_media_campionato, CLASSIFICA_REALE_30G, get_team_ou_tendency, get_season_avg_goals
from live_data import get_impatto_infortunati, get_n_indisponibili

# Import statistiche API Football (opzionale, non blocca se non disponibili)
try:
    from api_football_stats import get_team_real_stats
    _HAS_API_STATS = True
except ImportError:
    _HAS_API_STATS = False
    def get_team_real_stats(name):
        return None

# Costanti del modello (ottimizzate da backtesting su 299 partite)
MAX_GOL = 10
ALPHA_H2H = 0.12         # H2H contributo moderato
ALPHA_FORMA = 0.18        # Forma recente pesata (ottimizzato)
ALPHA_XG = 0.45           # xG stagione attuale - peso alto (ottimizzato)
ALPHA_CLASSIFICA = 0.08   # Classifica reale
DIXON_COLES_RHO = -0.10   # Correzione Dixon-Coles (ottimizzato)
DRAW_BOOST = 1.12         # Boost pareggio
MARGINE_BK = 1.05
ALPHA_BK_BLEND = 0.35     # Blend con quote bookmaker

# Coppie bookmaker (Home, Draw, Away)
BOOKMAKER_COLS = [
    ("WHH", "WHD", "WHA"),
    ("GBH", "GBD", "GBA"),
    ("IWH", "IWD", "IWA"),
    ("LBH", "LBD", "LBA"),
    ("SBH", "SBD", "SBA"),
]

# Mappa classifica reale -> punti (per correzione forza)
_CLASSIFICA_PTS = {}
for _r in CLASSIFICA_REALE_30G:
    _CLASSIFICA_PTS[_r["Squadra"]] = _r["Punti"]
_MEDIA_PTS = sum(_CLASSIFICA_PTS.values()) / len(_CLASSIFICA_PTS) if _CLASSIFICA_PTS else 40


def _get_classifica_factor(home: str, away: str) -> float:
    """
    Ritorna un fattore di correzione basato sulla differenza in classifica.
    Positivo = casa piu' forte, negativo = ospite piu' forte.
    Range circa [-0.15, +0.15].
    """
    pts_h = _CLASSIFICA_PTS.get(home, _MEDIA_PTS)
    pts_a = _CLASSIFICA_PTS.get(away, _MEDIA_PTS)
    diff = (pts_h - pts_a) / 100.0  # Normalizzato [-0.5, +0.5]
    return diff


def _get_h2h_gol_media(df: pd.DataFrame, home: str, away: str) -> tuple:
    """
    Ritorna la media gol negli scontri diretti recenti (ultimi 10).
    Usata per calibrare Over/Under.
    Ritorna (media_gol_totali, n_partite) oppure (None, 0).
    """
    if df is None:
        return None, 0
    mask = (
        ((df["HomeTeam"] == home) & (df["AwayTeam"] == away)) |
        ((df["HomeTeam"] == away) & (df["AwayTeam"] == home))
    )
    h2h = df[mask].sort_values("Date", ascending=False).head(10)
    if len(h2h) < 3:
        return None, 0
    gol_totali = (h2h["FTHG"] + h2h["FTAG"]).mean()
    return round(gol_totali, 2), len(h2h)


def _dixon_coles_tau(i: int, j: int, lh: float, la: float, rho: float) -> float:
    """Correzione Dixon-Coles per risultati a basso punteggio."""
    if i == 0 and j == 0:
        return 1.0 - lh * la * rho
    elif i == 1 and j == 0:
        return 1.0 + la * rho
    elif i == 0 and j == 1:
        return 1.0 + lh * rho
    elif i == 1 and j == 1:
        return 1.0 - rho
    return 1.0


def calcola_probabilita(lambda_home: float, lambda_away: float,
                         rho: float = DIXON_COLES_RHO) -> dict:
    """
    Calcola P(1), P(X), P(2) con correzione Dixon-Coles.
    """
    prob_1 = 0.0
    prob_x = 0.0
    prob_2 = 0.0

    for i in range(MAX_GOL + 1):
        for j in range(MAX_GOL + 1):
            p_base = poisson.pmf(i, lambda_home) * poisson.pmf(j, lambda_away)
            tau = _dixon_coles_tau(i, j, lambda_home, lambda_away, rho)
            p = max(0.0, p_base * tau)  # Clamp per evitare negativi

            if i > j:
                prob_1 += p
            elif i == j:
                prob_x += p
            else:
                prob_2 += p

    # Normalizza con boost pareggio (Serie A ha piu' pareggi del modello Poisson)
    prob_x *= DRAW_BOOST
    totale = prob_1 + prob_x + prob_2
    if totale > 0:
        prob_1 /= totale
        prob_x /= totale
        prob_2 /= totale

    return {"prob_1": prob_1, "prob_x": prob_x, "prob_2": prob_2}


def calcola_mercati_extra(lambda_home: float, lambda_away: float,
                           rho: float = DIXON_COLES_RHO) -> dict:
    """
    Calcola probabilita' per mercati extra:
    - Over/Under 1.5, 2.5, 3.5
    - Goal/NoGoal (entrambe segnano si/no)
    - Risultato esatto piu' probabile
    """
    # Matrice probabilita' (i gol home, j gol away)
    matrice = {}
    for i in range(MAX_GOL + 1):
        for j in range(MAX_GOL + 1):
            p_base = poisson.pmf(i, lambda_home) * poisson.pmf(j, lambda_away)
            tau = _dixon_coles_tau(i, j, lambda_home, lambda_away, rho)
            matrice[(i, j)] = max(0.0, p_base * tau)

    # Normalizza
    tot = sum(matrice.values())
    if tot > 0:
        matrice = {k: v / tot for k, v in matrice.items()}

    # Over/Under
    over_15 = sum(p for (i, j), p in matrice.items() if i + j > 1.5)
    over_25 = sum(p for (i, j), p in matrice.items() if i + j > 2.5)
    over_35 = sum(p for (i, j), p in matrice.items() if i + j > 3.5)

    # Goal/NoGoal (entrambe segnano almeno 1)
    goal_si = sum(p for (i, j), p in matrice.items() if i >= 1 and j >= 1)

    # Risultato esatto piu' probabile (top 5, max 4 gol per squadra)
    esatti_realistici = {k: v for k, v in matrice.items() if k[0] <= 4 and k[1] <= 4}
    top_esatti = sorted(esatti_realistici.items(), key=lambda x: -x[1])[:5]
    risultati_esatti = [
        {"score": f"{i}-{j}", "prob": round(p * 100, 1)}
        for (i, j), p in top_esatti
    ]

    # Gol totali attesi
    gol_attesi = lambda_home + lambda_away

    # Suggerimenti
    tips = []
    if over_25 > 0.50:
        tips.append(("Over 2.5", round(over_25 * 100, 1), "#2ecc71"))
    else:
        tips.append(("Under 2.5", round((1 - over_25) * 100, 1), "#3498db"))

    if goal_si > 0.50:
        tips.append(("Goal Si", round(goal_si * 100, 1), "#2ecc71"))
    else:
        tips.append(("Goal No", round((1 - goal_si) * 100, 1), "#3498db"))

    return {
        "over_15": round(over_15 * 100, 1),
        "under_15": round((1 - over_15) * 100, 1),
        "over_25": round(over_25 * 100, 1),
        "under_25": round((1 - over_25) * 100, 1),
        "over_35": round(over_35 * 100, 1),
        "under_35": round((1 - over_35) * 100, 1),
        "goal_si": round(goal_si * 100, 1),
        "goal_no": round((1 - goal_si) * 100, 1),
        "gol_attesi": round(gol_attesi, 2),
        "risultati_esatti": risultati_esatti,
        "tips_extra": tips,
    }


def _get_bookmaker_reference(df: pd.DataFrame, home: str, away: str) -> dict | None:
    """
    Recupera le quote bookmaker storiche e le converte in probabilita' implicite.
    1. Prima cerca le quote H2H dirette (piu' precise)
    2. Se non trovate, stima dalle quote recenti di ciascuna squadra
    """
    if df is None:
        return None

    def _extract_quotes(row):
        """Estrae le quote medie da una riga."""
        qh, qd, qa = [], [], []
        for col_h, col_d, col_a in BOOKMAKER_COLS:
            h = row.get(col_h, np.nan)
            d = row.get(col_d, np.nan)
            a = row.get(col_a, np.nan)
            if pd.notna(h) and pd.notna(d) and pd.notna(a) and h > 1 and d > 1 and a > 1:
                qh.append(h)
                qd.append(d)
                qa.append(a)
        return qh, qd, qa

    # 1. Cerca H2H diretto (piu' preciso)
    mask = (
        ((df["HomeTeam"] == home) & (df["AwayTeam"] == away)) |
        ((df["HomeTeam"] == away) & (df["AwayTeam"] == home))
    )
    h2h = df[mask].sort_values("Date", ascending=False)

    for _, row in h2h.iterrows():
        qh, qd, qa = _extract_quotes(row)
        if len(qh) > 0:
            avg_h, avg_d, avg_a = np.mean(qh), np.mean(qd), np.mean(qa)
            p_h, p_d, p_a = 1.0/avg_h, 1.0/avg_d, 1.0/avg_a
            overround = p_h + p_d + p_a
            if overround > 0:
                is_inverted = (row["HomeTeam"] == away)
                if is_inverted:
                    p_h, p_a = p_a, p_h
                return {
                    "book_prob_1": round(p_h / overround * 100, 1),
                    "book_prob_x": round(p_d / overround * 100, 1),
                    "book_prob_2": round(p_a / overround * 100, 1),
                    "n_bookmakers": len(qh),
                }

    # 2. Fallback: stima dalle quote recenti di ciascuna squadra separatamente
    # Calcola la forza implicita da quote recenti come casa e come ospite
    home_as_home = df[df["HomeTeam"] == home].sort_values("Date", ascending=False).head(5)
    away_as_away = df[df["AwayTeam"] == away].sort_values("Date", ascending=False).head(5)

    home_win_probs = []
    away_win_probs = []

    for _, row in home_as_home.iterrows():
        qh, qd, qa = _extract_quotes(row)
        if qh:
            tot = 1/np.mean(qh) + 1/np.mean(qd) + 1/np.mean(qa)
            if tot > 0:
                home_win_probs.append((1/np.mean(qh)) / tot)

    for _, row in away_as_away.iterrows():
        qh, qd, qa = _extract_quotes(row)
        if qh:
            tot = 1/np.mean(qh) + 1/np.mean(qd) + 1/np.mean(qa)
            if tot > 0:
                away_win_probs.append((1/np.mean(qa)) / tot)

    if len(home_win_probs) >= 2 and len(away_win_probs) >= 2:
        avg_home_win = np.mean(home_win_probs)
        avg_away_win = np.mean(away_win_probs)
        # Stima pareggio come complemento
        est_draw = max(0.15, 1.0 - avg_home_win - avg_away_win)
        # Normalizza
        tot = avg_home_win + est_draw + avg_away_win
        return {
            "book_prob_1": round(avg_home_win / tot * 100, 1),
            "book_prob_x": round(est_draw / tot * 100, 1),
            "book_prob_2": round(avg_away_win / tot * 100, 1),
            "n_bookmakers": min(len(home_win_probs), len(away_win_probs)),
        }

    return None


def _calcola_confidence(probs: dict, n_home: int, n_away: int,
                         h2h: dict | None, bk: dict | None) -> dict:
    """
    Calcola indice di affidabilita' composito [0, 1].
    4 componenti pesate: separazione, volume dati, H2H, convergenza.
    """
    # 1. Separazione probabilita' (40%)
    vals = sorted([probs["prob_1"], probs["prob_x"], probs["prob_2"]], reverse=True)
    spread = vals[0] - vals[1]  # Distanza tra prima e seconda prob
    sep_score = min(spread / 0.40, 1.0)  # Max se spread >= 40%

    # 2. Volume dati (25%)
    n_min = min(n_home, n_away)
    data_score = min(n_min / 200, 1.0)

    # 3. H2H (20%)
    if h2h is not None:
        h2h_score = min(h2h["n_partite"] / 15, 1.0)
    else:
        h2h_score = 0.3  # Valore base quando non ci sono abbastanza scontri diretti

    # 4. Convergenza forma / bookmaker (15%)
    if bk is not None:
        # Quanto il modello concorda col mercato
        delta_1 = abs(probs["prob_1"] * 100 - bk["book_prob_1"])
        delta_x = abs(probs["prob_x"] * 100 - bk["book_prob_x"])
        delta_2 = abs(probs["prob_2"] * 100 - bk["book_prob_2"])
        avg_delta = (delta_1 + delta_x + delta_2) / 3
        conv_score = max(0, 1.0 - avg_delta / 20)  # 0% delta = 1.0, 20%+ delta = 0
    else:
        conv_score = 0.5

    confidence = 0.40 * sep_score + 0.25 * data_score + 0.20 * h2h_score + 0.15 * conv_score
    confidence = round(min(max(confidence, 0), 1.0), 3)

    if confidence >= 0.82:
        label = "Alta"
        color = "#2ecc71"
    elif confidence >= 0.50:
        label = "Media"
        color = "#f39c12"
    else:
        label = "Bassa"
        color = "#e74c3c"

    return {
        "confidence": confidence,
        "confidence_label": label,
        "confidence_color": color,
    }


def get_prediction(home_stats: dict, away_stats: dict, df: pd.DataFrame = None) -> dict:
    """
    Genera il pronostico 1X2 SUPER INTEGRATO:
    - Lambda base da storico CSV (26 anni)
    - Blending con xG stagione 2025-2026 (30%)
    - Correzione H2H
    - Correzione forma pesata
    - Dixon-Coles per risultati bassi
    - Confronto quote bookmaker (5 bookmaker)
    - Indice di confidence multi-fattore
    """
    home_name = home_stats.get("nome", "")
    away_name = away_stats.get("nome", "")

    # ── LAMBDA BASE (storico CSV con peso recenza) ──
    lambda_home_hist = (
        home_stats["forza_att_casa"]
        * away_stats["forza_dif_trasf"]
        * home_stats["media_gol_casa_campionato"]
    )
    lambda_away_hist = (
        away_stats["forza_att_trasf"]
        * home_stats["forza_dif_casa"]
        * home_stats["media_gol_trasf_campionato"]
    )

    # ── MIGLIORIA 3: USA MEDIA GOL STAGIONE CORRENTE ──
    # Solo per calibrare i mercati extra (O/U, Goal), NON per 1X2
    # (evita di alterare i lambda base che peggiorano l'1X2)

    # ── LAMBDA DA xG 2025-2026 (MIGLIORIA 4: differenziato) ──
    xg_home = get_xg(home_name)
    xg_away = get_xg(away_name)
    xg_applied = False
    xg_home_val = None
    xg_away_val = None

    if xg_home is not None and xg_away is not None:
        xg_applied = True
        medie_xg = get_xg_media_campionato()
        # xG attacco casa vs xGA difesa ospite, rapportati alla media
        lambda_home_xg = xg_home["xG_pg"] * (xg_away["xGA_pg"] / medie_xg["xGA_pg_medio"])
        lambda_away_xg = xg_away["xG_pg"] * (xg_home["xGA_pg"] / medie_xg["xGA_pg_medio"])
        xg_home_val = round(xg_home["xG_pg"], 2)
        xg_away_val = round(xg_away["xG_pg"], 2)

        # Blending: 70% storico + 30% xG stagione attuale
        lambda_home = (1 - ALPHA_XG) * lambda_home_hist + ALPHA_XG * lambda_home_xg
        lambda_away = (1 - ALPHA_XG) * lambda_away_hist + ALPHA_XG * lambda_away_xg
    else:
        lambda_home = lambda_home_hist
        lambda_away = lambda_away_hist

    # ── STATISTICHE REALI API FOOTBALL (gol casa/trasferta specifici) ──
    try:
        api_home = get_team_real_stats(home_name) if _HAS_API_STATS else None
        api_away = get_team_real_stats(away_name) if _HAS_API_STATS else None
    except Exception:
        api_home = None
        api_away = None
    if api_home and api_away and api_home.get("played", 0) >= 10 and api_away.get("played", 0) >= 10:
        lambda_api_h = api_home["gf_home_pg"] * (api_away["gs_away_pg"] / max(0.5, (api_home["gs_home_pg"] + api_away["gs_away_pg"]) / 2))
        lambda_api_a = api_away["gf_away_pg"] * (api_home["gs_home_pg"] / max(0.5, (api_home["gs_home_pg"] + api_away["gs_away_pg"]) / 2))
        lambda_api_h = max(0.4, min(lambda_api_h, 3.5))
        lambda_api_a = max(0.2, min(lambda_api_a, 2.5))
        ALPHA_API = 0.15
        lambda_home = (1 - ALPHA_API) * lambda_home + ALPHA_API * lambda_api_h
        lambda_away = (1 - ALPHA_API) * lambda_away + ALPHA_API * lambda_api_a

    # ── CORREZIONE H2H ──
    h2h = home_stats.get("h2h")
    h2h_applied = False
    h2h_n = 0
    if h2h is not None:
        h2h_applied = True
        h2h_n = h2h["n_partite"]
        adv = h2h["h2h_advantage"]
        lambda_home *= (1.0 + ALPHA_H2H * adv)
        lambda_away *= (1.0 - ALPHA_H2H * adv)

    # Correzione forma pesata
    forma_home = home_stats.get("forma_casa_pesata", 1.5)
    forma_away = away_stats.get("forma_trasf_pesata", 1.5)
    forma_diff = forma_home - forma_away
    forma_factor = 1.0 + ALPHA_FORMA * forma_diff
    lambda_home *= forma_factor
    lambda_away *= (2.0 - forma_factor)  # Inverso

    # ── MIGLIORIA 3: CORREZIONE CLASSIFICA REALE ──
    class_diff = _get_classifica_factor(home_name, away_name)
    lambda_home *= (1.0 + ALPHA_CLASSIFICA * class_diff * 5)
    lambda_away *= (1.0 - ALPHA_CLASSIFICA * class_diff * 5)

    # ── IMPATTO INFORTUNATI ──
    imp_home = get_impatto_infortunati(home_name)
    imp_away = get_impatto_infortunati(away_name)
    lambda_home *= imp_home
    lambda_away *= imp_away
    inj_home = get_n_indisponibili(home_name)
    inj_away = get_n_indisponibili(away_name)

    # Clamp
    lambda_home = max(0.3, min(lambda_home, 5.0))
    lambda_away = max(0.3, min(lambda_away, 5.0))

    # Probabilita' con Dixon-Coles + boost pareggio
    probs = calcola_probabilita(lambda_home, lambda_away)

    # Extra boost X: se le squadre sono equilibrate (lambda simili), il pareggio e' piu' probabile
    ratio = min(lambda_home, lambda_away) / max(lambda_home, lambda_away) if max(lambda_home, lambda_away) > 0 else 0
    if ratio > 0.85:  # Squadre molto equilibrate
        extra_draw = 1.0 + (ratio - 0.85) * 0.5  # Fino a +7.5% extra
        probs["prob_x"] *= extra_draw
        # Rinormalizza
        tot = probs["prob_1"] + probs["prob_x"] + probs["prob_2"]
        probs = {k: v / tot for k, v in probs.items()}

    # Quote con margine
    def quota(p):
        if p <= 0:
            return 99.0
        return round(MARGINE_BK / p, 2)

    # Suggerimento (calcolo provvisorio, ricalcolato dopo blend)
    max_prob = max(probs["prob_1"], probs["prob_x"], probs["prob_2"])
    if max_prob == probs["prob_1"]:
        suggerimento = "1"
        sugg_label = "Vittoria Casa"
    elif max_prob == probs["prob_x"]:
        suggerimento = "X"
        sugg_label = "Pareggio"
    else:
        suggerimento = "2"
        sugg_label = "Vittoria Ospite"

    # Confronto bookmaker
    bk = None
    if df is not None:
        bk = _get_bookmaker_reference(df, home_stats["nome"], away_stats["nome"])

    # ── MIGLIORIA 4: BLENDING CON QUOTE BOOKMAKER ──
    if bk is not None:
        bk_p1 = bk["book_prob_1"] / 100.0
        bk_px = bk["book_prob_x"] / 100.0
        bk_p2 = bk["book_prob_2"] / 100.0
        # Blend: (1-alpha) modello + alpha bookmaker
        probs["prob_1"] = (1 - ALPHA_BK_BLEND) * probs["prob_1"] + ALPHA_BK_BLEND * bk_p1
        probs["prob_x"] = (1 - ALPHA_BK_BLEND) * probs["prob_x"] + ALPHA_BK_BLEND * bk_px
        probs["prob_2"] = (1 - ALPHA_BK_BLEND) * probs["prob_2"] + ALPHA_BK_BLEND * bk_p2
        # Rinormalizza
        tot_bk = probs["prob_1"] + probs["prob_x"] + probs["prob_2"]
        if tot_bk > 0:
            probs = {k: v / tot_bk for k, v in probs.items()}
        # Ricalcola suggerimento dopo blend
        max_prob = max(probs["prob_1"], probs["prob_x"], probs["prob_2"])
        if max_prob == probs["prob_1"]:
            suggerimento = "1"
            sugg_label = "Vittoria Casa"
        elif max_prob == probs["prob_x"]:
            suggerimento = "X"
            sugg_label = "Pareggio"
        else:
            suggerimento = "2"
            sugg_label = "Vittoria Ospite"

    # Quote finali (dopo blend)
    q1 = quota(probs["prob_1"])
    qx = quota(probs["prob_x"])
    q2 = quota(probs["prob_2"])

    # Confidence
    conf = _calcola_confidence(
        probs,
        home_stats.get("n_partite", 0),
        away_stats.get("n_partite", 0),
        h2h,
        bk
    )

    result = {
        "prob_1": round(probs["prob_1"] * 100, 1),
        "prob_x": round(probs["prob_x"] * 100, 1),
        "prob_2": round(probs["prob_2"] * 100, 1),
        "quota_1": q1,
        "quota_x": qx,
        "quota_2": q2,
        "suggerimento": suggerimento,
        "sugg_label": sugg_label,
        "lambda_home": round(lambda_home, 3),
        "lambda_away": round(lambda_away, 3),
        "h2h_applied": h2h_applied,
        "h2h_n": h2h_n,
        "xg_applied": xg_applied,
        "xg_home": xg_home_val,
        "xg_away": xg_away_val,
        "inj_home": inj_home,
        "inj_away": inj_away,
        "confidence": conf["confidence"],
        "confidence_label": conf["confidence_label"],
        "confidence_color": conf["confidence_color"],
    }

    # Mercati extra: Over/Under, Goal/NoGoal, Risultato Esatto
    extra = calcola_mercati_extra(lambda_home, lambda_away)

    # ── MIGLIORIA 1: CALIBRAZIONE O/U CON MEDIA GOL H2H ──
    h2h_gol_media, h2h_gol_n = _get_h2h_gol_media(df, home_name, away_name)
    if h2h_gol_media is not None and h2h_gol_n >= 5:
        # Se la media gol H2H e' molto diversa da quella del modello, correggi
        gol_modello = lambda_home + lambda_away
        # Se H2H dice piu' gol del modello, alza Over
        if h2h_gol_media > gol_modello + 0.3:
            boost_over = min(1.15, 1.0 + (h2h_gol_media - gol_modello) * 0.08)
            extra["over_25"] = round(min(85, extra["over_25"] * boost_over), 1)
            extra["under_25"] = round(100 - extra["over_25"], 1)
            extra["over_15"] = round(min(95, extra["over_15"] * boost_over), 1)
            extra["under_15"] = round(100 - extra["over_15"], 1)
        elif h2h_gol_media < gol_modello - 0.3:
            boost_under = min(1.15, 1.0 + (gol_modello - h2h_gol_media) * 0.08)
            extra["under_25"] = round(min(85, extra["under_25"] * boost_under), 1)
            extra["over_25"] = round(100 - extra["under_25"], 1)

    # ── MIGLIORIA 2: TENDENZA O/U SPECIFICA PER SQUADRA ──
    ou_home = get_team_ou_tendency(home_name)
    ou_away = get_team_ou_tendency(away_name)
    avg_gol_coppia = (ou_home["gol_pg"] + ou_away["gol_pg"]) / 2
    if avg_gol_coppia > 3.0:
        ou_boost = min(1.10, 1.0 + (avg_gol_coppia - 3.0) * 0.06)
        extra["over_25"] = round(min(85, extra["over_25"] * ou_boost), 1)
        extra["under_25"] = round(100 - extra["over_25"], 1)
    elif avg_gol_coppia < 2.2:
        ou_boost = min(1.10, 1.0 + (2.2 - avg_gol_coppia) * 0.06)
        extra["under_25"] = round(min(85, extra["under_25"] * ou_boost), 1)
        extra["over_25"] = round(100 - extra["under_25"], 1)

    result.update(extra)

    # Aggiungi confronto bookmaker se disponibile
    if bk is not None:
        result["book_prob_1"] = bk["book_prob_1"]
        result["book_prob_x"] = bk["book_prob_x"]
        result["book_prob_2"] = bk["book_prob_2"]
        result["delta_bk_1"] = round(result["prob_1"] - bk["book_prob_1"], 1)
        result["delta_bk_x"] = round(result["prob_x"] - bk["book_prob_x"], 1)
        result["delta_bk_2"] = round(result["prob_2"] - bk["book_prob_2"], 1)
        result["n_bookmakers"] = bk["n_bookmakers"]
    else:
        result["book_prob_1"] = None
        result["book_prob_x"] = None
        result["book_prob_2"] = None
        result["delta_bk_1"] = None
        result["delta_bk_x"] = None
        result["delta_bk_2"] = None
        result["n_bookmakers"] = 0

    return result
