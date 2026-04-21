"""
optimize_weights.py
Ottimizza i pesi del modello usando grid search sul backtesting.
Supporta tutte le leghe: Serie A, Premier League, La Liga, Bundesliga, Ligue 1.
Per ogni lega fa grid search su draw_boost, alpha_h2h, alpha_forma, alpha_xg,
confidence_threshold e rho.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import warnings
warnings.filterwarnings("ignore")

import itertools
import pandas as pd
from data_loader import load_all_data
from stats_engine import get_team_stats
from season_2526 import (
    SQUADRE_2526, get_risultati_stagione,
    get_xg, get_xg_media_campionato,
    get_xg_pl, get_xg_media_pl,
    get_xg_laliga, get_xg_media_laliga,
    get_xg_bl, get_xg_media_bl,
    get_xg_l1, get_xg_media_l1,
)
from predictor import calcola_probabilita, calcola_mercati_extra
from live_data import get_impatto_infortunati

# ─────────────────────────────────────────────────────────────────────────────
# Configurazione per ciascuna lega
# csv_code: codice usato da data_loader / football-data.co.uk
# fn_xg: funzione per ottenere xG della squadra (da season_2526)
# fn_xg_media: funzione per ottenere medie xG del campionato
# ─────────────────────────────────────────────────────────────────────────────
LEGA_CONFIG = {
    'serie-a': {
        'csv_code': 'I1',
        'fn_xg': get_xg,
        'fn_xg_media': get_xg_media_campionato,
    },
    'premier-league': {
        'csv_code': 'E0',
        'fn_xg': get_xg_pl,
        'fn_xg_media': get_xg_media_pl,
    },
    'la-liga': {
        'csv_code': 'SP1',
        'fn_xg': get_xg_laliga,
        'fn_xg_media': get_xg_media_laliga,
    },
    'bundesliga': {
        'csv_code': 'D1',
        'fn_xg': get_xg_bl,
        'fn_xg_media': get_xg_media_bl,
    },
    'ligue-1': {
        'csv_code': 'F1',
        'fn_xg': get_xg_l1,
        'fn_xg_media': get_xg_media_l1,
    },
}


def get_partite_stagione_corrente(df,
                                   stagione_start="2025-08-01",
                                   stagione_end="2026-06-30",
                                   min_partite_squadra=3):
    """
    Estrae le partite della stagione corrente da un dataframe storico.
    Ritorna una lista di dict con home, away, gol_home, gol_away, risultato.
    Non dipende da SQUADRE_2526 (funziona per qualsiasi lega).

    Parametri:
        df: dataframe storico della lega
        stagione_start: data inizio stagione corrente
        stagione_end: data fine stagione corrente
        min_partite_squadra: numero minimo di partite perche' una squadra
                             sia considerata "in" la stagione corrente
    """
    if df is None or len(df) == 0:
        return []

    # Filtra per stagione corrente
    mask = (df["Date"] >= stagione_start) & (df["Date"] <= stagione_end)
    stagione = df[mask].dropna(subset=["HomeTeam", "AwayTeam", "FTHG", "FTAG", "FTR"])
    stagione = stagione[stagione["FTR"].isin(["H", "D", "A"])].copy()

    if len(stagione) == 0:
        return []

    # Conta partite per squadra per escludere squadre con troppo poche partite
    conteggio = pd.concat([
        stagione["HomeTeam"],
        stagione["AwayTeam"]
    ]).value_counts()
    squadre_valide = set(conteggio[conteggio >= min_partite_squadra].index)

    # Filtra solo partite tra squadre valide
    mask_sq = (
        stagione["HomeTeam"].isin(squadre_valide) &
        stagione["AwayTeam"].isin(squadre_valide)
    )
    stagione = stagione[mask_sq]

    partite = []
    for _, m in stagione.iterrows():
        partite.append({
            "home": str(m["HomeTeam"]),
            "away": str(m["AwayTeam"]),
            "gol_home": int(m["FTHG"]),
            "gol_away": int(m["FTAG"]),
            "risultato": str(m["FTR"]),  # H, D, A
        })

    return partite


def testa_parametri(df, partite, alpha_h2h, alpha_forma, alpha_xg, rho,
                    draw_boost, fn_xg, fn_xg_media):
    """
    Testa una combinazione di parametri su una lista di partite.
    Ritorna (score_composito, acc_1x2, acc_ou, acc_goal, n_partite).

    Versione generica: non dipende da SQUADRE_2526, funziona per qualsiasi lega.
    """
    ok_1x2 = 0
    ok_ou = 0
    ok_goal = 0
    tot = 0

    for r in partite:
        home = r["home"]
        away = r["away"]

        try:
            hs = get_team_stats(df, home, opponent=away)
            as_ = get_team_stats(df, away, opponent=home)

            # Lambda base (forza attacco/difesa storica)
            lh = hs["forza_att_casa"] * as_["forza_dif_trasf"] * hs["media_gol_casa_campionato"]
            la = as_["forza_att_trasf"] * hs["forza_dif_casa"] * hs["media_gol_trasf_campionato"]

            # Blending xG stagione corrente
            xg_h = fn_xg(home)
            xg_a = fn_xg(away)
            if xg_h and xg_a and alpha_xg > 0:
                medie = fn_xg_media()
                lh_xg = xg_h["xG_pg"] * (xg_a["xGA_pg"] / medie["xGA_pg_medio"])
                la_xg = xg_a["xG_pg"] * (xg_h["xGA_pg"] / medie["xGA_pg_medio"])
                lh = (1 - alpha_xg) * lh + alpha_xg * lh_xg
                la = (1 - alpha_xg) * la + alpha_xg * la_xg

            # Correzione H2H
            h2h = hs.get("h2h")
            if h2h:
                adv = h2h["h2h_advantage"]
                lh *= (1.0 + alpha_h2h * adv)
                la *= (1.0 - alpha_h2h * adv)

            # Correzione forma pesata
            fh = hs.get("forma_casa_pesata", 1.5)
            fa = as_.get("forma_trasf_pesata", 1.5)
            fd = fh - fa
            ff = 1.0 + alpha_forma * fd
            lh *= ff
            la *= (2.0 - ff)

            # Impatto infortunati
            lh *= get_impatto_infortunati(home)
            la *= get_impatto_infortunati(away)

            # Clamp
            lh = max(0.3, min(lh, 5.0))
            la = max(0.3, min(la, 5.0))

            # Probabilita' con parametri testati
            probs = calcola_probabilita(lh, la, rho, draw_boost)
            extra = calcola_mercati_extra(lh, la, rho)

            # Suggerimento 1X2
            max_p = max(probs["prob_1"], probs["prob_x"], probs["prob_2"])
            if max_p == probs["prob_1"]:
                sugg = "1"
            elif max_p == probs["prob_x"]:
                sugg = "X"
            else:
                sugg = "2"

            tot += 1

            # Verifica 1X2
            mappa = {"H": "1", "D": "X", "A": "2"}
            if sugg == mappa.get(r["risultato"], "?"):
                ok_1x2 += 1

            # Verifica Over/Under 2.5
            gol = r["gol_home"] + r["gol_away"]
            pred_over = extra["over_25"] > 50
            if (gol > 2.5) == pred_over:
                ok_ou += 1

            # Verifica Goal/NoGoal
            is_goal = r["gol_home"] >= 1 and r["gol_away"] >= 1
            pred_goal = extra["goal_si"] > 50
            if is_goal == pred_goal:
                ok_goal += 1

        except Exception:
            continue

    if tot == 0:
        return 0, 0, 0, 0, 0

    acc_1x2 = ok_1x2 / tot * 100
    acc_ou = ok_ou / tot * 100
    acc_goal = ok_goal / tot * 100
    # Score composito pesato (stesso schema del backtesting)
    score = acc_1x2 * 0.4 + acc_ou * 0.3 + acc_goal * 0.3
    return score, acc_1x2, acc_ou, acc_goal, tot


def optimize_lega(league_id, df=None, partite=None, verbose=True):
    """
    Esegue grid search sui parametri del modello per una specifica lega.
    Se df/partite non vengono forniti, li carica in autonomia.

    Ritorna:
        (best_params, best_score, n_partite)
        best_params include: draw_boost, alpha_h2h, alpha_forma, alpha_xg,
                             dixon_coles_rho, confidence_threshold
    """
    cfg = LEGA_CONFIG.get(league_id)
    if cfg is None:
        raise ValueError(f"Lega non supportata: {league_id}. "
                         f"Disponibili: {list(LEGA_CONFIG.keys())}")

    fn_xg = cfg["fn_xg"]
    fn_xg_media = cfg["fn_xg_media"]

    # Carica dati se non forniti
    if df is None:
        if verbose:
            print(f"  Caricamento dati per {league_id}...")
        df = load_all_data(cfg["csv_code"])

    if partite is None:
        partite = get_partite_stagione_corrente(df)

    if verbose:
        print(f"  Partite stagione corrente disponibili: {len(partite)}")

    if len(partite) < 20:
        if verbose:
            print(f"  ATTENZIONE: meno di 20 partite disponibili, skip ottimizzazione.")
        return None, 0, len(partite)

    # Grid search
    draw_boost_vals      = [0.95, 1.00, 1.05, 1.08, 1.10, 1.12, 1.15]
    h2h_vals             = [0.04, 0.08, 0.12, 0.16, 0.20]
    forma_vals           = [0.06, 0.10, 0.15, 0.20, 0.25]
    xg_vals              = [0.15, 0.25, 0.35, 0.45, 0.50]
    rho_vals             = [-0.05, -0.08, -0.10, -0.13, -0.18]
    # confidence_threshold non impatta l'accuracy grezza ma vogliamo ottimizzarla comunque
    # la includiamo come parametro separato (non influisce sul grid search ma viene salvata)
    confidence_vals      = [0.75, 0.78, 0.80, 0.82, 0.85]

    total_combos = (len(draw_boost_vals) * len(h2h_vals) *
                    len(forma_vals) * len(xg_vals) * len(rho_vals))
    if verbose:
        print(f"  Combinazioni da testare: {total_combos}")

    best_score = -1
    best_params = {}
    i = 0

    for db in draw_boost_vals:
        for ah in h2h_vals:
            for af in forma_vals:
                for ax in xg_vals:
                    for rh in rho_vals:
                        i += 1
                        score, a1, ao, ag, n = testa_parametri(
                            df, partite, ah, af, ax, rh, db, fn_xg, fn_xg_media
                        )

                        if score > best_score:
                            best_score = score
                            best_params = {
                                "draw_boost": db,
                                "alpha_h2h": ah,
                                "alpha_forma": af,
                                "alpha_xg": ax,
                                "dixon_coles_rho": rh,
                                # confidence_threshold: usa il valore mid-range per ora
                                # (non influisce su score composito, ottimizzata separatamente)
                                "confidence_threshold": 0.80,
                                "alpha_bk_blend": 0.35,  # mantieni invariato
                                # accuratezze di riferimento
                                "_acc_1x2": round(a1, 1),
                                "_acc_ou": round(ao, 1),
                                "_acc_goal": round(ag, 1),
                                "_n_partite": n,
                            }
                            if verbose:
                                print(f"    [{i}/{total_combos}] Nuovo best {league_id}: "
                                      f"score={score:.1f}% "
                                      f"(DB={db}, H2H={ah}, Forma={af}, xG={ax}, rho={rh})")

    # Ottimizza confidence_threshold separatamente (non impatta accuracy)
    # Usa il valore che massimizza il rapporto between "Alta" predictions corrette
    # Per ora lasciamo il valore di default (0.80) e lo segnaliamo

    if verbose:
        print(f"\n  MIGLIORI PARAMETRI per {league_id}:")
        print(f"    draw_boost      = {best_params.get('draw_boost')}")
        print(f"    alpha_h2h       = {best_params.get('alpha_h2h')}")
        print(f"    alpha_forma     = {best_params.get('alpha_forma')}")
        print(f"    alpha_xg        = {best_params.get('alpha_xg')}")
        print(f"    dixon_coles_rho = {best_params.get('dixon_coles_rho')}")
        print(f"    Score: {best_score:.1f}%  "
              f"(1X2={best_params.get('_acc_1x2')}%, "
              f"O/U={best_params.get('_acc_ou')}%, "
              f"Goal={best_params.get('_acc_goal')}%)")

    return best_params, best_score, len(partite)


def calcola_accuracy_corrente(league_id, df=None, partite=None):
    """
    Calcola l'accuratezza del modello con i parametri ATTUALI per una lega.
    Usata come baseline prima dell'ottimizzazione.

    Ritorna: (score, acc_1x2, acc_ou, acc_goal, n_partite)
    """
    from predictor import LEAGUE_PARAMS, DEFAULT_LEAGUE_PARAMS

    cfg = LEGA_CONFIG.get(league_id)
    if cfg is None:
        raise ValueError(f"Lega non supportata: {league_id}")

    if df is None:
        df = load_all_data(cfg["csv_code"])

    if partite is None:
        partite = get_partite_stagione_corrente(df)

    # Parametri attuali per questa lega
    p = LEAGUE_PARAMS.get(league_id, DEFAULT_LEAGUE_PARAMS)

    score, a1, ao, ag, n = testa_parametri(
        df, partite,
        p["alpha_h2h"], p["alpha_forma"], p["alpha_xg"],
        p["dixon_coles_rho"], p["draw_boost"],
        cfg["fn_xg"], cfg["fn_xg_media"]
    )

    return score, a1, ao, ag, n


# ─────────────────────────────────────────────────────────────────────────────
# FUNZIONI LEGACY - mantenute per compatibilita' con codice esistente
# ─────────────────────────────────────────────────────────────────────────────

def test_weights(df, giornate, alpha_h2h, alpha_forma, alpha_xg, rho):
    """
    [LEGACY] Testa pesi solo su Serie A (usa SQUADRE_2526).
    Mantenuta per compatibilita' con vecchi script.
    Per il multi-lega usa testa_parametri().
    """
    ok_1x2 = 0
    ok_ou = 0
    ok_goal = 0
    tot = 0

    for g in giornate:
        for r in g["risultati"]:
            home = r["home"]
            away = r["away"]
            if home not in SQUADRE_2526 or away not in SQUADRE_2526:
                continue

            try:
                hs = get_team_stats(df, home, opponent=away)
                as_ = get_team_stats(df, away, opponent=home)

                lh = hs["forza_att_casa"] * as_["forza_dif_trasf"] * hs["media_gol_casa_campionato"]
                la = as_["forza_att_trasf"] * hs["forza_dif_casa"] * hs["media_gol_trasf_campionato"]

                xg_h = get_xg(home)
                xg_a = get_xg(away)
                if xg_h and xg_a:
                    medie = get_xg_media_campionato()
                    lh_xg = xg_h["xG_pg"] * (xg_a["xGA_pg"] / medie["xGA_pg_medio"])
                    la_xg = xg_a["xG_pg"] * (xg_h["xGA_pg"] / medie["xGA_pg_medio"])
                    lh = (1 - alpha_xg) * lh + alpha_xg * lh_xg
                    la = (1 - alpha_xg) * la + alpha_xg * la_xg

                h2h = hs.get("h2h")
                if h2h:
                    adv = h2h["h2h_advantage"]
                    lh *= (1.0 + alpha_h2h * adv)
                    la *= (1.0 - alpha_h2h * adv)

                fh = hs.get("forma_casa_pesata", 1.5)
                fa = as_.get("forma_trasf_pesata", 1.5)
                fd = fh - fa
                ff = 1.0 + alpha_forma * fd
                lh *= ff
                la *= (2.0 - ff)

                lh *= get_impatto_infortunati(home)
                la *= get_impatto_infortunati(away)

                lh = max(0.3, min(lh, 5.0))
                la = max(0.3, min(la, 5.0))

                probs = calcola_probabilita(lh, la, rho)
                extra = calcola_mercati_extra(lh, la, rho)

                max_p = max(probs["prob_1"], probs["prob_x"], probs["prob_2"])
                if max_p == probs["prob_1"]:
                    sugg = "1"
                elif max_p == probs["prob_x"]:
                    sugg = "X"
                else:
                    sugg = "2"

                tot += 1

                mappa = {"H": "1", "D": "X", "A": "2"}
                if sugg == mappa.get(r["risultato"], "?"):
                    ok_1x2 += 1

                gol = r["gol_home"] + r["gol_away"]
                pred_over = extra["over_25"] > 50
                if (gol > 2.5) == pred_over:
                    ok_ou += 1

                is_goal = r["gol_home"] >= 1 and r["gol_away"] >= 1
                pred_goal = extra["goal_si"] > 50
                if is_goal == pred_goal:
                    ok_goal += 1

            except Exception:
                continue

    if tot == 0:
        return 0, 0, 0, 0, 0

    acc_1x2 = ok_1x2 / tot * 100
    acc_ou = ok_ou / tot * 100
    acc_goal = ok_goal / tot * 100
    score = acc_1x2 * 0.4 + acc_ou * 0.3 + acc_goal * 0.3
    return score, acc_1x2, acc_ou, acc_goal, tot


def optimize():
    """[LEGACY] Ottimizza pesi solo per Serie A (per compatibilita')."""
    print("=" * 60)
    print("OTTIMIZZAZIONE PESI MODELLO - SERIE A")
    print("=" * 60)

    print("\nCaricamento dati...")
    df = load_all_data()
    giornate = get_risultati_stagione(df)
    print(f"Partite disponibili: {sum(len(g['risultati']) for g in giornate)}")

    h2h_vals  = [0.04, 0.08, 0.12, 0.16, 0.20]
    forma_vals = [0.03, 0.06, 0.10, 0.15]
    xg_vals   = [0.15, 0.25, 0.35, 0.45]
    rho_vals  = [-0.08, -0.13, -0.18]

    total_combos = len(h2h_vals) * len(forma_vals) * len(xg_vals) * len(rho_vals)
    print(f"Combinazioni da testare: {total_combos}")
    print("\nOttimizzazione in corso...\n")

    best_score = 0
    best_params = {}
    results = []
    i = 0

    for ah in h2h_vals:
        for af in forma_vals:
            for ax in xg_vals:
                for rh in rho_vals:
                    i += 1
                    score, a1, ao, ag, n = test_weights(df, giornate, ah, af, ax, rh)
                    results.append((score, ah, af, ax, rh, a1, ao, ag))

                    if score > best_score:
                        best_score = score
                        best_params = {"h2h": ah, "forma": af, "xg": ax, "rho": rh,
                                       "1x2": a1, "ou": ao, "goal": ag}
                        print(f"  [{i}/{total_combos}] Nuovo best: {score:.1f}% "
                              f"(H2H={ah}, Forma={af}, xG={ax}, rho={rh})")

    print(f"\n{'=' * 60}")
    print(f"RISULTATI OTTIMIZZAZIONE")
    print(f"{'=' * 60}")
    print(f"\n  MIGLIORI PESI TROVATI:")
    print(f"    ALPHA_H2H  = {best_params['h2h']}")
    print(f"    ALPHA_FORMA = {best_params['forma']}")
    print(f"    ALPHA_XG   = {best_params['xg']}")
    print(f"    DIXON_COLES_RHO = {best_params['rho']}")
    print(f"\n  ACCURATEZZA CON PESI OTTIMALI:")
    print(f"    1X2:           {best_params['1x2']:.1f}%")
    print(f"    Over/Under 2.5: {best_params['ou']:.1f}%")
    print(f"    Goal/NoGoal:    {best_params['goal']:.1f}%")
    print(f"    SCORE TOTALE:   {best_score:.1f}%")

    results.sort(key=lambda x: -x[0])
    print(f"\n  TOP 5 COMBINAZIONI:")
    for j, (sc, ah, af, ax, rh, a1, ao, ag) in enumerate(results[:5], 1):
        print(f"    {j}. Score={sc:.1f}%  H2H={ah} Forma={af} xG={ax} rho={rh}")

    print(f"\n{'=' * 60}")
    return best_params, best_score


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Ottimizza i pesi del modello predittivo")
    parser.add_argument("--lega", type=str, default="serie-a",
                        choices=list(LEGA_CONFIG.keys()) + ["tutte"],
                        help="Lega da ottimizzare (default: serie-a, usa 'tutte' per tutte le leghe)")
    args = parser.parse_args()

    if args.lega == "tutte":
        for league_id in LEGA_CONFIG.keys():
            print(f"\n{'=' * 60}")
            print(f"OTTIMIZZAZIONE: {league_id.upper()}")
            print(f"{'=' * 60}")
            try:
                best_p, best_s, n_p = optimize_lega(league_id, verbose=True)
                if best_p:
                    print(f"\n  Risultato finale: score={best_s:.1f}% su {n_p} partite")
            except Exception as e:
                print(f"  ERRORE per {league_id}: {e}")
    else:
        if args.lega == "serie-a":
            # Per Serie A usa la funzione legacy che usa SQUADRE_2526
            best, score = optimize()
        else:
            print(f"\n{'=' * 60}")
            print(f"OTTIMIZZAZIONE: {args.lega.upper()}")
            print(f"{'=' * 60}")
            best, score, n_p = optimize_lega(args.lega, verbose=True)
            if best:
                print(f"\nParametri ottimali trovati su {n_p} partite (score={score:.1f}%)")

    input("\nPremi INVIO per chiudere...")
