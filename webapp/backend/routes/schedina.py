"""
routes/schedina.py - Endpoint schedine del giorno per tutti i campionati
Endpoint: /api/schedina, /api/schedina-pl, /api/schedina-ll,
          /api/schedina-bl, /api/schedina-l1
"""
import json
import urllib.request
from typing import Optional

from fastapi import APIRouter, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

router = APIRouter(prefix="/api", tags=["schedina"])
limiter = Limiter(key_func=get_remote_address)


def _build_schedina(giocate_raw, giornata_num="", data_str=""):
    """Helper condiviso: ordina, limita a 5, calcola quota totale."""
    giocate_raw.sort(key=lambda x: -x["confidence"])
    top = giocate_raw[:5]
    quota_tot = 1.0
    for g in top:
        q = g.get("quota", 1.5)
        if q > 1:
            quota_tot *= q
    return {
        "giornata": giornata_num,
        "data": data_str,
        "giocate": top,
        "n_giocate": len(top),
        "quota_totale": round(quota_tot, 2),
        "tipo": "Pronostici ad alta confidenza selezionati dall'IA",
    }


# ─────────────────────────────
# SERIE A
# ─────────────────────────────

@router.get("/schedina")
@limiter.limit("10/minute")
async def schedina_del_giorno(request: Request):
    """L'IA seleziona le 3-5 giocate piu' sicure della prossima giornata Serie A."""
    from api_server import CAL_HARDCODED, LIVE_RESULTS_CACHE, genera_pronostico

    # Trova la prossima giornata da giocare automaticamente
    prossima_g = None
    for g_num in range(31, 39):
        cal = CAL_HARDCODED.get(g_num)
        if not cal:
            continue
        tutte_giocate = True
        if LIVE_RESULTS_CACHE:
            for h, a in cal["partite"]:
                trovata = False
                for p in LIVE_RESULTS_CACHE:
                    if (p["home"] == h and p["away"] == a) or (p["home"] == a and p["away"] == h):
                        if p.get("status") in ("FT", "AET", "PEN"):
                            trovata = True
                            break
                if not trovata:
                    tutte_giocate = False
                    break
        else:
            tutte_giocate = False
        if not tutte_giocate:
            prossima_g = g_num
            break

    if prossima_g is None:
        prossima_g = 38

    cal = CAL_HARDCODED.get(prossima_g, {})
    partite = cal.get("partite", [])
    giocate = []

    for home, away in partite:
        try:
            raw = genera_pronostico(home, away)
            if raw.get("sicura"):
                giocate.append({
                    "home": home, "away": away,
                    "tip": raw["suggerimento"],
                    "tip_label": raw["sugg_label"],
                    "prob": max(raw["prob_1"], raw["prob_x"], raw["prob_2"]),
                    "quota": raw.get(f"quota_{raw['suggerimento'].lower()}", 0),
                    "confidence": raw["confidence"],
                    "over_under": ("Over 2.5 " + str(raw.get("over_25", 50)) + "%") if raw.get("over_25", 0) > 50 else ("Under 2.5 " + str(raw.get("under_25", 50)) + "%"),
                    "goal": ("Goal Si " + str(raw.get("goal_si", 50)) + "%") if raw.get("goal_si", 0) > 50 else ("Goal No " + str(raw.get("goal_no", 50)) + "%"),
                })
        except Exception:
            continue

    return _build_schedina(giocate, prossima_g, cal.get("data", ""))


# ─────────────────────────────
# PREMIER LEAGUE
# ─────────────────────────────

@router.get("/schedina-pl")
@limiter.limit("10/minute")
async def schedina_pl(request: Request):
    """Schedina del giorno Premier League - prossima giornata."""
    from api_server import (CLASSIFICA_CACHE, FOOTBALL_API_KEY, FOOTBALL_API_HOST,
                             _fetch_league_data, _get_nome_map, genera_pronostico)
    try:
        if not CLASSIFICA_CACHE.get("premier-league"):
            _fetch_league_data("premier-league")

        req = urllib.request.Request(
            f"https://{FOOTBALL_API_HOST}/fixtures?league=39&season=2025&next=10",
            headers={"x-apisports-key": FOOTBALL_API_KEY, "User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode())

        if not data.get("response"):
            return {"giornata": "?", "giocate": [], "n_giocate": 0, "quota_totale": 0, "tipo": "Nessuna partita disponibile"}

        nome_map = _get_nome_map("premier-league")
        giornata_num = ""
        giocate = []

        for fix in data["response"][:10]:
            teams = fix.get("teams", {})
            lg = fix.get("league", {})
            home = nome_map.get(teams.get("home", {}).get("name", "?"), teams.get("home", {}).get("name", "?"))
            away = nome_map.get(teams.get("away", {}).get("name", "?"), teams.get("away", {}).get("name", "?"))
            if not giornata_num:
                giornata_num = lg.get("round", "").split(" - ")[-1] if " - " in lg.get("round", "") else "?"
            try:
                raw = genera_pronostico(home, away)
                mp = max(raw.get("prob_1", 0), raw.get("prob_x", 0), raw.get("prob_2", 0))
                conf = raw.get("confidence", 0)
                if conf >= 0.30 or mp > 35:
                    giocate.append({
                        "home": home, "away": away,
                        "tip": raw.get("suggerimento", "?"),
                        "tip_label": raw.get("sugg_label", ""),
                        "prob": mp,
                        "quota": raw.get(f"quota_{raw.get('suggerimento','1').lower()}", 1.5),
                        "confidence": conf,
                        "over_under": ("Over 2.5 " + str(raw.get("over_25", 50)) + "%") if raw.get("over_25", 0) > 50 else ("Under 2.5 " + str(raw.get("under_25", 50)) + "%"),
                        "goal": ("Goal Si " + str(raw.get("goal_si", 50)) + "%") if raw.get("goal_si", 0) > 50 else ("Goal No " + str(raw.get("goal_no", 50)) + "%"),
                    })
            except Exception:
                continue

        return _build_schedina(giocate, giornata_num)
    except Exception as e:
        return {"giornata": "?", "giocate": [], "n_giocate": 0, "quota_totale": 0, "tipo": f"Errore: {e}"}


# ─────────────────────────────
# LA LIGA
# ─────────────────────────────

@router.get("/schedina-ll")
@limiter.limit("10/minute")
async def schedina_ll(request: Request):
    """Schedina del giorno La Liga - prossima giornata."""
    from api_server import (CLASSIFICA_CACHE, FOOTBALL_API_KEY, FOOTBALL_API_HOST,
                             _fetch_league_data, _get_nome_map, genera_pronostico)
    try:
        if not CLASSIFICA_CACHE.get("la-liga"):
            _fetch_league_data("la-liga")

        req = urllib.request.Request(
            f"https://{FOOTBALL_API_HOST}/fixtures?league=140&season=2025&next=10",
            headers={"x-apisports-key": FOOTBALL_API_KEY, "User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode())

        if not data.get("response"):
            return {"giornata": "?", "giocate": [], "n_giocate": 0, "quota_totale": 0, "tipo": "Nessuna partita"}

        nome_map = _get_nome_map("la-liga")
        giornata_num = ""
        giocate = []

        for fix in data["response"][:10]:
            teams = fix.get("teams", {})
            lg = fix.get("league", {})
            home = nome_map.get(teams.get("home", {}).get("name", "?"), teams.get("home", {}).get("name", "?"))
            away = nome_map.get(teams.get("away", {}).get("name", "?"), teams.get("away", {}).get("name", "?"))
            if not giornata_num:
                giornata_num = lg.get("round", "").split(" - ")[-1] if " - " in lg.get("round", "") else "?"
            try:
                raw = genera_pronostico(home, away)
                mp = max(raw.get("prob_1", 0), raw.get("prob_x", 0), raw.get("prob_2", 0))
                conf = raw.get("confidence", 0)
                if conf >= 0.30 or mp > 35:
                    giocate.append({
                        "home": home, "away": away,
                        "tip": raw.get("suggerimento", "?"),
                        "prob": mp,
                        "quota": raw.get(f"quota_{raw.get('suggerimento','1').lower()}", 1.5),
                        "confidence": conf,
                        "over_under": ("Over 2.5 " + str(raw.get("over_25", 50)) + "%") if raw.get("over_25", 0) > 50 else ("Under 2.5 " + str(raw.get("under_25", 50)) + "%"),
                        "goal": ("Goal Si " + str(raw.get("goal_si", 50)) + "%") if raw.get("goal_si", 0) > 50 else ("Goal No " + str(raw.get("goal_no", 50)) + "%"),
                    })
            except Exception:
                continue

        return _build_schedina(giocate, giornata_num)
    except Exception as e:
        return {"giornata": "?", "giocate": [], "n_giocate": 0, "quota_totale": 0, "tipo": f"Errore: {e}"}


# ─────────────────────────────
# BUNDESLIGA
# ─────────────────────────────

@router.get("/schedina-bl")
@limiter.limit("10/minute")
async def schedina_bl(request: Request):
    """Schedina del giorno Bundesliga."""
    from api_server import (CLASSIFICA_CACHE, FOOTBALL_API_KEY, FOOTBALL_API_HOST,
                             _fetch_league_data, _get_nome_map, genera_pronostico,
                             _df_bl, get_team_stats, get_prediction)
    try:
        if not CLASSIFICA_CACHE.get("bundesliga"):
            _fetch_league_data("bundesliga")

        req = urllib.request.Request(
            f"https://{FOOTBALL_API_HOST}/fixtures?league=78&season=2025&next=10",
            headers={"x-apisports-key": FOOTBALL_API_KEY, "User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode())

        if not data.get("response"):
            return {"giornata": "?", "giocate": [], "n_giocate": 0, "quota_totale": 0, "tipo": "Nessuna partita"}

        nome_map = _get_nome_map("bundesliga")
        giornata_num = ""
        giocate = []

        for fix in data["response"][:10]:
            teams = fix.get("teams", {})
            lg = fix.get("league", {})
            home_api = teams.get("home", {}).get("name", "?")
            away_api = teams.get("away", {}).get("name", "?")
            home = nome_map.get(home_api, home_api)
            away = nome_map.get(away_api, away_api)
            if not giornata_num:
                giornata_num = lg.get("round", "").split(" - ")[-1] if " - " in lg.get("round", "") else "?"
            try:
                # Usa CSV Bundesliga se disponibile, altrimenti fallback generale
                if _df_bl is not None and len(_df_bl) > 100:
                    try:
                        hs = get_team_stats(_df_bl, home, opponent=away)
                        aws = get_team_stats(_df_bl, away, opponent=home)
                    except Exception:
                        hs = get_team_stats(_df_bl, home_api, opponent=away_api)
                        aws = get_team_stats(_df_bl, away_api, opponent=home_api)
                    raw = get_prediction(hs, aws, df=_df_bl, league="bundesliga")
                else:
                    raw = genera_pronostico(home, away)
                mp = max(raw.get("prob_1", 0), raw.get("prob_x", 0), raw.get("prob_2", 0))
                conf = raw.get("confidence", 0)
                if conf >= 0.30 or mp > 35:
                    giocate.append({
                        "home": home, "away": away,
                        "tip": raw.get("suggerimento", "?"),
                        "prob": mp,
                        "quota": raw.get(f"quota_{raw.get('suggerimento','1').lower()}", 1.5),
                        "confidence": conf,
                        "over_under": ("Over 2.5 " + str(raw.get("over_25", 50)) + "%") if raw.get("over_25", 0) > 50 else ("Under 2.5 " + str(raw.get("under_25", 50)) + "%"),
                        "goal": ("Goal Si " + str(raw.get("goal_si", 50)) + "%") if raw.get("goal_si", 0) > 50 else ("Goal No " + str(raw.get("goal_no", 50)) + "%"),
                    })
            except Exception:
                continue

        return _build_schedina(giocate, giornata_num)
    except Exception as e:
        return {"giornata": "?", "giocate": [], "n_giocate": 0, "quota_totale": 0, "tipo": f"Errore: {e}"}


# ─────────────────────────────
# LIGUE 1
# ─────────────────────────────

@router.get("/schedina-l1")
@limiter.limit("10/minute")
async def schedina_l1(request: Request):
    """Schedina del giorno Ligue 1."""
    from api_server import (CLASSIFICA_CACHE, FOOTBALL_API_KEY, FOOTBALL_API_HOST,
                             _fetch_league_data, _get_nome_map, genera_pronostico,
                             _df_l1, get_team_stats, get_prediction)
    try:
        if not CLASSIFICA_CACHE.get("ligue-1"):
            _fetch_league_data("ligue-1")

        req = urllib.request.Request(
            f"https://{FOOTBALL_API_HOST}/fixtures?league=61&season=2025&next=10",
            headers={"x-apisports-key": FOOTBALL_API_KEY, "User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode())

        if not data.get("response"):
            return {"giornata": "?", "giocate": [], "n_giocate": 0, "quota_totale": 0, "tipo": "Nessuna partita"}

        nome_map = _get_nome_map("ligue-1")
        giornata_num = ""
        giocate = []

        for fix in data["response"][:10]:
            teams = fix.get("teams", {})
            lg = fix.get("league", {})
            home_api = teams.get("home", {}).get("name", "?")
            away_api = teams.get("away", {}).get("name", "?")
            home = nome_map.get(home_api, home_api)
            away = nome_map.get(away_api, away_api)
            if not giornata_num:
                giornata_num = lg.get("round", "").split(" - ")[-1] if " - " in lg.get("round", "") else "?"
            try:
                # Usa CSV Ligue 1 se disponibile
                if _df_l1 is not None and len(_df_l1) > 100:
                    try:
                        hs = get_team_stats(_df_l1, home, opponent=away)
                        aws = get_team_stats(_df_l1, away, opponent=home)
                    except Exception:
                        hs = get_team_stats(_df_l1, home_api, opponent=away_api)
                        aws = get_team_stats(_df_l1, away_api, opponent=home_api)
                    raw = get_prediction(hs, aws, df=_df_l1, league="ligue-1")
                else:
                    raw = genera_pronostico(home, away)
                mp = max(raw.get("prob_1", 0), raw.get("prob_x", 0), raw.get("prob_2", 0))
                conf = raw.get("confidence", 0)
                if conf >= 0.30 or mp > 35:
                    giocate.append({
                        "home": home, "away": away,
                        "tip": raw.get("suggerimento", "?"),
                        "prob": mp,
                        "quota": raw.get(f"quota_{raw.get('suggerimento','1').lower()}", 1.5),
                        "confidence": conf,
                        "over_under": ("Over 2.5 " + str(raw.get("over_25", 50)) + "%") if raw.get("over_25", 0) > 50 else ("Under 2.5 " + str(raw.get("under_25", 50)) + "%"),
                        "goal": ("Goal Si " + str(raw.get("goal_si", 50)) + "%") if raw.get("goal_si", 0) > 50 else ("Goal No " + str(raw.get("goal_no", 50)) + "%"),
                    })
            except Exception:
                continue

        return _build_schedina(giocate, giornata_num)
    except Exception as e:
        return {"giornata": "?", "giocate": [], "n_giocate": 0, "quota_totale": 0, "tipo": f"Errore: {e}"}
