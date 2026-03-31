"""
optimize_weights.py
Ottimizza i pesi del modello usando grid search sul backtesting.
Testa varie combinazioni di ALPHA_H2H, ALPHA_FORMA, ALPHA_XG e rho.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import warnings
warnings.filterwarnings("ignore")

import itertools
from data_loader import load_all_data
from stats_engine import get_team_stats
from season_2526 import SQUADRE_2526, get_risultati_stagione
from predictor import calcola_probabilita, calcola_mercati_extra
from season_2526 import get_xg, get_xg_media_campionato
from live_data import get_impatto_infortunati


def test_weights(df, giornate, alpha_h2h, alpha_forma, alpha_xg, rho):
    """Testa una combinazione di pesi e ritorna l'accuratezza."""
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

                # Lambda base
                lh = hs["forza_att_casa"] * as_["forza_dif_trasf"] * hs["media_gol_casa_campionato"]
                la = as_["forza_att_trasf"] * hs["forza_dif_casa"] * hs["media_gol_trasf_campionato"]

                # xG blending
                xg_h = get_xg(home)
                xg_a = get_xg(away)
                if xg_h and xg_a:
                    medie = get_xg_media_campionato()
                    lh_xg = xg_h["xG_pg"] * (xg_a["xGA_pg"] / medie["xGA_pg_medio"])
                    la_xg = xg_a["xG_pg"] * (xg_h["xGA_pg"] / medie["xGA_pg_medio"])
                    lh = (1 - alpha_xg) * lh + alpha_xg * lh_xg
                    la = (1 - alpha_xg) * la + alpha_xg * la_xg

                # H2H
                h2h = hs.get("h2h")
                if h2h:
                    adv = h2h["h2h_advantage"]
                    lh *= (1.0 + alpha_h2h * adv)
                    la *= (1.0 - alpha_h2h * adv)

                # Forma
                fh = hs.get("forma_casa_pesata", 1.5)
                fa = as_.get("forma_trasf_pesata", 1.5)
                fd = fh - fa
                ff = 1.0 + alpha_forma * fd
                lh *= ff
                la *= (2.0 - ff)

                # Infortunati
                lh *= get_impatto_infortunati(home)
                la *= get_impatto_infortunati(away)

                # Clamp
                lh = max(0.3, min(lh, 5.0))
                la = max(0.3, min(la, 5.0))

                # Probabilita'
                probs = calcola_probabilita(lh, la, rho)
                extra = calcola_mercati_extra(lh, la, rho)

                # Suggerimento
                max_p = max(probs["prob_1"], probs["prob_x"], probs["prob_2"])
                if max_p == probs["prob_1"]:
                    sugg = "1"
                elif max_p == probs["prob_x"]:
                    sugg = "X"
                else:
                    sugg = "2"

                tot += 1

                # 1X2
                mappa = {"H": "1", "D": "X", "A": "2"}
                if sugg == mappa.get(r["risultato"], "?"):
                    ok_1x2 += 1

                # O/U
                gol = r["gol_home"] + r["gol_away"]
                pred_over = extra["over_25"] > 50
                if (gol > 2.5) == pred_over:
                    ok_ou += 1

                # Goal
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
    print("=" * 60)
    print("OTTIMIZZAZIONE PESI MODELLO")
    print("=" * 60)

    print("\nCaricamento dati...")
    df = load_all_data()
    giornate = get_risultati_stagione(df)
    print(f"Partite disponibili: {sum(len(g['risultati']) for g in giornate)}")

    # Grid search
    h2h_vals = [0.04, 0.08, 0.12, 0.16, 0.20]
    forma_vals = [0.03, 0.06, 0.10, 0.15]
    xg_vals = [0.15, 0.25, 0.35, 0.45]
    rho_vals = [-0.08, -0.13, -0.18]

    total_combos = len(h2h_vals) * len(forma_vals) * len(xg_vals) * len(rho_vals)
    print(f"Combinazioni da testare: {total_combos}")
    print("\nOttimizzazione in corso (potrebbe richiedere qualche minuto)...\n")

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

    # Top 5
    results.sort(key=lambda x: -x[0])
    print(f"\n  TOP 5 COMBINAZIONI:")
    for j, (sc, ah, af, ax, rh, a1, ao, ag) in enumerate(results[:5], 1):
        print(f"    {j}. Score={sc:.1f}%  H2H={ah} Forma={af} xG={ax} rho={rh}")

    print(f"\n{'=' * 60}")

    return best_params, best_score


if __name__ == "__main__":
    best, score = optimize()
    print(f"\nVuoi applicare questi pesi al modello? (i valori sono sopra)")
    input("\nPremi INVIO per chiudere...")
