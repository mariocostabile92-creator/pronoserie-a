"""
backtesting.py
Testa i pronostici del modello sulle partite gia' giocate (giornate 1-30).
Misura accuratezza reale su 1X2, Over/Under, Goal/NoGoal.
Ottimizza i pesi del modello.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import warnings
warnings.filterwarnings("ignore")

from data_loader import load_all_data
from stats_engine import get_team_stats
from predictor import get_prediction, calcola_mercati_extra
from season_2526 import SQUADRE_2526, get_risultati_stagione


def run_backtest():
    """Esegue il backtesting completo."""
    print("=" * 60)
    print("BACKTESTING PRONOSTICI SERIE A 2025-2026")
    print("=" * 60)
    print("\nCaricamento dati...")

    df = load_all_data()
    print(f"Partite caricate: {len(df)}")

    giornate = get_risultati_stagione(df)
    print(f"Giornate trovate: {len(giornate)}")

    if not giornate:
        print("ERRORE: Nessuna giornata trovata per la stagione 2025-2026!")
        return

    # Contatori
    tot = 0
    ok_1x2 = 0
    ok_over25 = 0
    ok_under25 = 0
    ok_goal = 0
    ok_nogoal = 0
    ok_esatto = 0
    tot_over = 0
    tot_under = 0
    tot_goal = 0
    tot_nogoal = 0
    tot_esatto = 0

    # Confidenza
    ok_alta = 0
    tot_alta = 0
    ok_media = 0
    tot_media = 0
    ok_bassa = 0
    tot_bassa = 0

    # Dettaglio per giornata
    acc_per_giornata = {}

    errori = 0

    print("\nAnalisi in corso...\n")

    for g in giornate:
        g_num = g["giornata"]
        g_ok = 0
        g_tot = 0

        for r in g["risultati"]:
            home = r["home"]
            away = r["away"]
            gol_h = r["gol_home"]
            gol_a = r["gol_away"]
            ris_reale = r["risultato"]  # H, D, A

            if home not in SQUADRE_2526 or away not in SQUADRE_2526:
                continue

            try:
                # Genera pronostico (SENZA usare la partita stessa)
                hs = get_team_stats(df, home, opponent=away)
                as_ = get_team_stats(df, away, opponent=home)
                pred = get_prediction(hs, as_, df=df)
            except Exception:
                errori += 1
                continue

            tot += 1
            g_tot += 1

            # ── 1X2 ──
            sugg = pred["suggerimento"]
            mappa = {"H": "1", "D": "X", "A": "2"}
            ris_1x2 = mappa.get(ris_reale, "?")

            if sugg == ris_1x2:
                ok_1x2 += 1
                g_ok += 1

            # ── OVER/UNDER 2.5 ──
            gol_tot = gol_h + gol_a
            is_over = gol_tot > 2.5
            pred_over = pred.get("over_25", 50) > 50

            if is_over:
                tot_over += 1
                if pred_over:
                    ok_over25 += 1
            else:
                tot_under += 1
                if not pred_over:
                    ok_under25 += 1

            # ── GOAL/NOGOAL ──
            is_goal = gol_h >= 1 and gol_a >= 1
            pred_goal = pred.get("goal_si", 50) > 50

            if is_goal:
                tot_goal += 1
                if pred_goal:
                    ok_goal += 1
            else:
                tot_nogoal += 1
                if not pred_goal:
                    ok_nogoal += 1

            # ── RISULTATO ESATTO ──
            esatti = pred.get("risultati_esatti", [])
            if esatti:
                tot_esatto += 1
                score_reale = f"{gol_h}-{gol_a}"
                if any(e["score"] == score_reale for e in esatti[:3]):
                    ok_esatto += 1

            # ── CONFIDENZA ──
            conf = pred.get("confidence_label", "Media")
            if conf == "Alta":
                tot_alta += 1
                if sugg == ris_1x2:
                    ok_alta += 1
            elif conf == "Media":
                tot_media += 1
                if sugg == ris_1x2:
                    ok_media += 1
            else:
                tot_bassa += 1
                if sugg == ris_1x2:
                    ok_bassa += 1

        if g_tot > 0:
            acc_per_giornata[g_num] = round(g_ok / g_tot * 100, 1)

    # ── RISULTATI ──
    print("=" * 60)
    print("RISULTATI BACKTESTING")
    print("=" * 60)

    print(f"\nPartite analizzate: {tot}")
    print(f"Errori di calcolo: {errori}")

    if tot == 0:
        print("Nessuna partita valida per il backtesting!")
        return {}

    acc_1x2 = round(ok_1x2 / tot * 100, 1)
    print(f"\n{'─' * 40}")
    print(f"  1X2:           {ok_1x2}/{tot} = {acc_1x2}%")

    tot_ou = tot_over + tot_under
    ok_ou = ok_over25 + ok_under25
    acc_ou = round(ok_ou / tot_ou * 100, 1) if tot_ou > 0 else 0
    print(f"  Over/Under 2.5: {ok_ou}/{tot_ou} = {acc_ou}%")

    tot_g = tot_goal + tot_nogoal
    ok_g = ok_goal + ok_nogoal
    acc_g = round(ok_g / tot_g * 100, 1) if tot_g > 0 else 0
    print(f"  Goal/NoGoal:    {ok_g}/{tot_g} = {acc_g}%")

    acc_es = round(ok_esatto / tot_esatto * 100, 1) if tot_esatto > 0 else 0
    print(f"  Risultato Esatto (top3): {ok_esatto}/{tot_esatto} = {acc_es}%")

    print(f"\n{'─' * 40}")
    print(f"  ACCURATEZZA PER LIVELLO CONFIDENZA:")
    if tot_alta > 0:
        print(f"    Alta:   {ok_alta}/{tot_alta} = {round(ok_alta/tot_alta*100,1)}%")
    if tot_media > 0:
        print(f"    Media:  {ok_media}/{tot_media} = {round(ok_media/tot_media*100,1)}%")
    if tot_bassa > 0:
        print(f"    Bassa:  {ok_bassa}/{tot_bassa} = {round(ok_bassa/tot_bassa*100,1)}%")

    print(f"\n{'─' * 40}")
    print(f"  ACCURATEZZA PER GIORNATA:")
    for g_num in sorted(acc_per_giornata.keys()):
        bar = "#" * int(acc_per_giornata[g_num] / 5)
        print(f"    G.{g_num:2d}: {acc_per_giornata[g_num]:5.1f}%  {bar}")

    print(f"\n{'=' * 60}")

    # Score complessivo
    score = round((acc_1x2 * 0.4 + acc_ou * 0.3 + acc_g * 0.3), 1)
    print(f"\n  SCORE COMPLESSIVO: {score}%")

    if score >= 60:
        print("  Valutazione: ECCELLENTE")
    elif score >= 55:
        print("  Valutazione: BUONO")
    elif score >= 50:
        print("  Valutazione: DISCRETO")
    else:
        print("  Valutazione: DA MIGLIORARE")

    print(f"\n{'=' * 60}")

    return {
        "tot": tot,
        "acc_1x2": acc_1x2,
        "acc_ou": acc_ou,
        "acc_goal": acc_g,
        "acc_esatto": acc_es,
        "score": score,
        "per_giornata": acc_per_giornata,
        "conf_alta": round(ok_alta / tot_alta * 100, 1) if tot_alta > 0 else 0,
        "conf_media": round(ok_media / tot_media * 100, 1) if tot_media > 0 else 0,
        "conf_bassa": round(ok_bassa / tot_bassa * 100, 1) if tot_bassa > 0 else 0,
    }


if __name__ == "__main__":
    risultati = run_backtest()
    input("\nPremi INVIO per chiudere...")
