"""
routes/tracking.py - Tracking accuratezza predizioni e pronostici utente
Endpoint: /api/accuratezza, /api/user/save-prediction,
          /api/user/my-predictions, /api/user/verify-predictions
"""
import json
from collections import defaultdict
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from api_auth import get_optional_user

router = APIRouter(prefix="/api", tags=["tracking"])
limiter = Limiter(key_func=get_remote_address)


# ─────────────────────────────
# ACCURATEZZA GLOBALE SISTEMA
# ─────────────────────────────

@router.get("/accuratezza")
@limiter.limit("10/minute")
async def accuratezza(request: Request):
    """Calcola l'accuratezza del motore di pronostici per ogni giornata e campionato."""
    from api_server import (LEAGUES, RISULTATI_STAGIONE_CACHE_ML,
                             _get_nome_map, genera_pronostico,
                             _df, _df_pl, _df_ll, _df_bl, _df_l1,
                             get_team_stats, get_prediction)

    risultati = []

    for league_key in ["serie-a", "premier-league", "la-liga", "bundesliga", "ligue-1"]:
        league = LEAGUES.get(league_key)
        if not league:
            continue

        # Seleziona il DataFrame CSV corretto per ogni campionato
        csv_df_map = {
            "serie-a": _df,
            "premier-league": _df_pl,
            "la-liga": _df_ll,
            "bundesliga": _df_bl,
            "ligue-1": _df_l1,
        }
        csv_df = csv_df_map.get(league_key)

        storico = RISULTATI_STAGIONE_CACHE_ML.get(league_key) or []
        if not storico:
            continue

        per_round = defaultdict(list)
        for p in storico:
            per_round[p.get("round", "")].append(p)

        rounds_sorted = sorted(
            per_round.keys(),
            key=lambda r: int(r.split(" - ")[-1]) if " - " in r and r.split(" - ")[-1].isdigit() else 0,
            reverse=True
        )

        for rd in rounds_sorted[:5]:
            partite = per_round[rd]
            if len(partite) < 5:
                continue

            g_num = rd.split(" - ")[-1] if " - " in rd else rd
            ok_1x2 = ok_ou = ok_goal = tot = ok_alta = tot_alta = 0
            dettagli = []

            for p in partite:
                h, a = p["home"], p["away"]
                gol_h, gol_a = p["gol_h"], p["gol_a"]
                if gol_h is None:
                    continue

                try:
                    if csv_df is not None and len(csv_df) > 100:
                        try:
                            hs = get_team_stats(csv_df, h, opponent=a)
                            aws = get_team_stats(csv_df, a, opponent=h)
                        except Exception:
                            hs = get_team_stats(csv_df, h)
                            aws = get_team_stats(csv_df, a)
                        pred = get_prediction(hs, aws, df=csv_df)
                    else:
                        pred = genera_pronostico(h, a)
                except Exception:
                    continue

                # Calcola risultato reale 1/X/2
                ris = "1" if gol_h > gol_a else ("X" if gol_h == gol_a else "2")
                sugg = pred.get("suggerimento", "")
                corretto = sugg == ris
                if corretto:
                    ok_1x2 += 1

                # Over/Under 2.5
                gol_tot = gol_h + gol_a
                pred_over = pred.get("over_25", 50) > 50
                ou_ok = (gol_tot > 2.5) == pred_over
                if ou_ok:
                    ok_ou += 1

                # Goal/NoGoal
                is_goal = gol_h >= 1 and gol_a >= 1
                pred_goal = pred.get("goal_si", 50) > 50
                goal_ok = is_goal == pred_goal
                if goal_ok:
                    ok_goal += 1

                # Confidenza Alta
                conf = pred.get("confidence_label", "")
                if conf == "Alta":
                    tot_alta += 1
                    if corretto:
                        ok_alta += 1

                tot += 1
                dettagli.append({
                    "home": h, "away": a,
                    "gol_h": gol_h, "gol_a": gol_a,
                    "pronostico": sugg, "risultato": ris,
                    "corretto": corretto, "confidenza": conf,
                })

            if tot >= 5:
                risultati.append({
                    "campionato": league["name"],
                    "league_key": league_key,
                    "giornata": g_num,
                    "totale": tot,
                    "ok_1x2": ok_1x2,
                    "acc_1x2": round(ok_1x2 / tot * 100, 0),
                    "ok_ou": ok_ou,
                    "acc_ou": round(ok_ou / tot * 100, 0),
                    "ok_goal": ok_goal,
                    "acc_goal": round(ok_goal / tot * 100, 0),
                    "ok_alta": ok_alta,
                    "tot_alta": tot_alta,
                    "acc_alta": round(ok_alta / tot_alta * 100, 0) if tot_alta > 0 else 0,
                    "dettagli": dettagli,
                })

    # Totali aggregati su tutti i campionati
    tot_all = sum(r["totale"] for r in risultati)
    ok_all = sum(r["ok_1x2"] for r in risultati)
    ok_ou_all = sum(r["ok_ou"] for r in risultati)
    ok_g_all = sum(r["ok_goal"] for r in risultati)
    ok_alta_all = sum(r["ok_alta"] for r in risultati)
    tot_alta_all = sum(r["tot_alta"] for r in risultati)

    return {
        "giornate": risultati,
        "totale": {
            "partite": tot_all,
            "acc_1x2": round(ok_all / tot_all * 100, 1) if tot_all > 0 else 0,
            "acc_ou": round(ok_ou_all / tot_all * 100, 1) if tot_all > 0 else 0,
            "acc_goal": round(ok_g_all / tot_all * 100, 1) if tot_all > 0 else 0,
            "acc_alta": round(ok_alta_all / tot_alta_all * 100, 1) if tot_alta_all > 0 else 0,
            "tot_alta": tot_alta_all,
        },
    }


# ─────────────────────────────
# PRONOSTICI PERSONALI UTENTE
# ─────────────────────────────

@router.post("/user/save-prediction")
@limiter.limit("30/minute")
async def save_user_prediction(data: dict, request: Request, user: Optional[dict] = Depends(get_optional_user)):
    """Salva un pronostico personale dell'utente nel database."""
    if not user:
        raise HTTPException(401, "Devi essere loggato")

    from database import _get_conn
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO user_predictions (user_id, league, home, away, pronostico, prob, confidence,
                                      over_under, goal, created_at, match_date)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        user["id"],
        data.get("league", ""),
        data.get("home", ""),
        data.get("away", ""),
        data.get("pronostico", ""),
        data.get("prob", 0),
        data.get("confidence", ""),
        data.get("over_under", ""),
        data.get("goal", ""),
        datetime.now(timezone.utc).isoformat(),
        data.get("match_date", ""),
    ))
    conn.commit()
    cur.close()
    conn.close()
    return {"status": "ok"}


@router.get("/user/my-predictions")
@limiter.limit("30/minute")
async def get_user_predictions(request: Request, user: Optional[dict] = Depends(get_optional_user)):
    """Restituisce i pronostici salvati dell'utente con statistiche di accuratezza."""
    if not user:
        raise HTTPException(401, "Devi essere loggato")

    import psycopg2.extras
    from database import _get_conn
    conn = _get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Ultimi 50 pronostici
    cur.execute("""
        SELECT * FROM user_predictions WHERE user_id = %s ORDER BY id DESC LIMIT 50
    """, (user["id"],))
    preds = cur.fetchall()

    # Statistiche aggregate
    cur.execute("""
        SELECT
            COUNT(*)                                          AS totale,
            SUM(CASE WHEN corretto      THEN 1 ELSE 0 END)   AS ok_1x2,
            SUM(CASE WHEN ou_corretto   THEN 1 ELSE 0 END)   AS ok_ou,
            SUM(CASE WHEN goal_corretto THEN 1 ELSE 0 END)   AS ok_goal,
            SUM(CASE WHEN verificato    THEN 1 ELSE 0 END)   AS verificati
        FROM user_predictions WHERE user_id = %s
    """, (user["id"],))
    stats = cur.fetchone()

    cur.close()
    conn.close()

    v = stats["verificati"] or 0
    return {
        "predictions": [dict(p) for p in preds],
        "stats": {
            "totale": stats["totale"] or 0,
            "verificati": v,
            "ok_1x2": stats["ok_1x2"] or 0,
            "ok_ou": stats["ok_ou"] or 0,
            "ok_goal": stats["ok_goal"] or 0,
            "acc_1x2": round((stats["ok_1x2"] or 0) / v * 100, 1) if v > 0 else 0,
            "acc_ou": round((stats["ok_ou"] or 0) / v * 100, 1) if v > 0 else 0,
            "acc_goal": round((stats["ok_goal"] or 0) / v * 100, 1) if v > 0 else 0,
        },
    }


@router.post("/user/verify-predictions")
@limiter.limit("10/minute")
async def verify_user_predictions(request: Request, user: Optional[dict] = Depends(get_optional_user)):
    """Verifica i pronostici salvati dell'utente confrontandoli con i risultati reali."""
    if not user:
        raise HTTPException(401, "Devi essere loggato")

    import psycopg2.extras
    from database import _get_conn
    from api_server import (LEAGUES, RISULTATI_STAGIONE_CACHE_ML,
                             LIVE_RESULTS_CACHE_ML, LIVE_RESULTS_CACHE)

    conn = _get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM user_predictions WHERE user_id = %s AND verificato = FALSE", (user["id"],))
    preds = cur.fetchall()

    # Raccoglie tutti i risultati disponibili da tutte le cache
    all_results = []
    for lk in LEAGUES:
        for p in (RISULTATI_STAGIONE_CACHE_ML.get(lk) or []):
            all_results.append(p)
        for p in (LIVE_RESULTS_CACHE_ML.get(lk) or []):
            if p.get("status") in ("FT", "AET", "PEN"):
                all_results.append(p)
    if LIVE_RESULTS_CACHE:
        for p in LIVE_RESULTS_CACHE:
            if p.get("status") in ("FT", "AET", "PEN"):
                all_results.append(p)

    verificati = 0
    for pred in preds:
        for ris in all_results:
            if (ris.get("home") == pred["home"] and ris.get("away") == pred["away"]
                    and ris.get("status") in ("FT", "AET", "PEN")):
                gol_h = ris["gol_h"]
                gol_a = ris["gol_a"]

                # Risultato 1X2
                if gol_h > gol_a:
                    ris_1x2 = "1"
                elif gol_h == gol_a:
                    ris_1x2 = "X"
                else:
                    ris_1x2 = "2"

                corretto = pred["pronostico"] == ris_1x2

                # Over/Under
                gol_tot = gol_h + gol_a
                ou_pred = "Over" in (pred.get("over_under") or "")
                ou_ok = (gol_tot > 2.5) == ou_pred

                # Goal/NoGoal
                goal_pred = "Si" in (pred.get("goal") or "")
                is_goal = gol_h >= 1 and gol_a >= 1
                goal_ok = is_goal == goal_pred

                cur.execute("""
                    UPDATE user_predictions
                    SET gol_h_reale=%s, gol_a_reale=%s, risultato_reale=%s,
                        corretto=%s, ou_corretto=%s, goal_corretto=%s, verificato=TRUE
                    WHERE id=%s
                """, (gol_h, gol_a, ris_1x2, corretto, ou_ok, goal_ok, pred["id"]))
                verificati += 1
                break

    conn.commit()
    cur.close()
    conn.close()
    return {"verificati": verificati}
