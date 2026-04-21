"""
routes/leghe.py - Endpoint classifiche, marcatori, calendario, squadre, mondiali
Gestisce: /api/classifica, /api/marcatori, /api/squadra/{nome},
          /api/{league}/classifica, /api/{league}/calendario,
          /api/{league}/squadre-attive, /api/mondiali-2026/*
"""
import json
import os
import urllib.request
import threading
from collections import defaultdict
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from api_auth import get_optional_user

router = APIRouter(prefix="/api", tags=["leghe"])

# Limiter condiviso (viene registrato su app in api_server.py)
limiter = Limiter(key_func=get_remote_address)


# ─────────────────────────────
# SERIE A: classifica e marcatori
# ─────────────────────────────

@router.get("/classifica")
@limiter.limit("30/minute")
async def classifica(request: Request):
    """Classifica Serie A con statistiche squadre."""
    from api_server import (CLASSIFICA_CACHE, MARCATORI_CACHE, CLASSIFICA_LAST_UPDATE,
                             CLASS_FALLBACK, MARC_FALLBACK, _compute_best_stats)
    cl = CLASSIFICA_CACHE.get("serie-a") or CLASS_FALLBACK
    mc = MARCATORI_CACHE.get("serie-a") or MARC_FALLBACK
    return {
        "classifica": cl,
        "marcatori": mc,
        "aggiornamento": CLASSIFICA_LAST_UPDATE.get("serie-a", "") or "Dati base",
        "live": CLASSIFICA_CACHE.get("serie-a") is not None,
        "stats_squadre": _compute_best_stats("serie-a"),
    }


@router.get("/marcatori")
@limiter.limit("30/minute")
async def marcatori(request: Request):
    """Marcatori Serie A."""
    try:
        from season_2526 import get_marcatori as _get_marc
        return _get_marc()
    except Exception as e:
        print("❌ ERRORE MARCATORI:", e)
        return []


# ─────────────────────────────
# SQUADRA (rose, formazioni, infortunati)
# ─────────────────────────────

@router.get("/squadra/{nome}")
@limiter.limit("20/minute")
async def squadra(nome: str, request: Request):
    """Dati completi di una squadra: formazione, rosa, infortunati, allenatore."""
    from api_server import (LIVE_FORMAZIONI, FORMAZIONI, LIVE_INFORTUNATI, INFORTUNATI,
                             INFORTUNATI_LIVE, ALLENATORI, ALLENATORI_LIVE, ROSE, ROSE_LIVE,
                             PL_TEAM_IDS, ROSE_LAST_UPDATE, LIVE_LAST_UPDATE,
                             _get_last_lineup, _get_injuries_ondemand,
                             _get_coach_ondemand, _get_squad_ondemand)
    n = nome.strip().title()

    # Formazione: live > hardcoded > on-demand
    form = LIVE_FORMAZIONI.get(n) or FORMAZIONI.get(n)
    if not form:
        form = _get_last_lineup(n)

    # Infortunati: live cache > hardcoded > on-demand
    inj = (INFORTUNATI_LIVE.get(n) if INFORTUNATI_LIVE.get(n)
           else (LIVE_INFORTUNATI.get(n) if LIVE_INFORTUNATI.get(n) is not None
                 else INFORTUNATI.get(n, [])))
    if not inj and (n in PL_TEAM_IDS or not INFORTUNATI.get(n)):
        inj = _get_injuries_ondemand(n)

    # Allenatore: live > hardcoded > on-demand API
    allenatore = ALLENATORI_LIVE.get(n) or ALLENATORI.get(n)
    if not allenatore or allenatore == "N/D":
        allenatore = _get_coach_ondemand(n) or "N/D"

    # Rosa: live cache > hardcoded > on-demand
    if ROSE_LIVE.get(n):
        rosa = ROSE_LIVE[n]
    elif ROSE.get(n):
        rosa = [{"nome": g[0], "ruolo": g[1], "numero": g[2]} for g in ROSE[n]]
    else:
        rosa = _get_squad_ondemand(n)

    return {
        "nome": n,
        "allenatore": allenatore,
        "formazione": form,
        "infortunati": inj,
        "rosa": rosa,
        "ultimo_aggiornamento": ROSE_LAST_UPDATE or LIVE_LAST_UPDATE or "Dati base",
    }


# ─────────────────────────────
# MULTI-LEAGUE: classifica, calendario, squadre attive
# ─────────────────────────────

@router.get("/{league}/classifica")
@limiter.limit("30/minute")
async def classifica_league(league: str, request: Request):
    """Classifica per qualsiasi campionato con statistiche squadre."""
    from api_server import (LEAGUES, CLASSIFICA_CACHE, MARCATORI_CACHE,
                             CLASSIFICA_LAST_UPDATE, _compute_best_stats,
                             _fetch_team_stats_league)
    if league not in LEAGUES:
        raise HTTPException(404, "Campionato non trovato")
    cl = CLASSIFICA_CACHE.get(league)
    mc = MARCATORI_CACHE.get(league)

    # Statistiche squadre (solo campionati domestici)
    stats_squadre = None
    if league in ["serie-a", "premier-league", "la-liga", "bundesliga", "ligue-1"]:
        stats_squadre = _compute_best_stats(league)
        if not stats_squadre:
            # Avvia fetch in background senza bloccare la risposta
            threading.Thread(target=_fetch_team_stats_league, args=(league,), daemon=True).start()

    return {
        "classifica": cl or [],
        "marcatori": mc or [],
        "aggiornamento": CLASSIFICA_LAST_UPDATE.get(league, ""),
        "live": cl is not None,
        "stats_squadre": stats_squadre,
    }


@router.get("/{league}/calendario")
@limiter.limit("20/minute")
async def calendario_league(league: str, request: Request):
    """Calendario completo per qualsiasi campionato (giocate + da giocare)."""
    from api_server import (LEAGUES, FOOTBALL_API_KEY, FOOTBALL_API_HOST,
                             _get_nome_map, _utc_to_rome)
    if league not in LEAGUES:
        raise HTTPException(404, "Campionato non trovato")

    lg = LEAGUES[league]
    lid = lg["id"]
    season = lg["season"]
    nome_map = _get_nome_map(league)

    giornate = []
    giornata_corrente = None

    try:
        req = urllib.request.Request(
            f"https://{FOOTBALL_API_HOST}/fixtures?league={lid}&season={season}",
            headers={"x-apisports-key": FOOTBALL_API_KEY, "User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.loads(r.read().decode())

        if data.get("response"):
            per_round = defaultdict(list)

            for fix in data["response"]:
                teams = fix.get("teams", {})
                goals = fix.get("goals", {})
                fixture = fix.get("fixture", {})
                status = fixture.get("status", {})
                lg_data = fix.get("league", {})
                events = fix.get("events", [])

                home_name = nome_map.get(teams.get("home", {}).get("name", "?"), teams.get("home", {}).get("name", "?"))
                away_name = nome_map.get(teams.get("away", {}).get("name", "?"), teams.get("away", {}).get("name", "?"))

                ss = status.get("short", "NS")
                is_live = ss in ("1H", "2H", "HT", "ET", "P")
                has_result = ss in ("FT", "AET", "PEN", "1H", "2H", "HT")

                marc_list = []
                for ev in events:
                    if ev.get("type") == "Goal":
                        nome = ev.get("player", {}).get("name", "?")
                        minuto = ev.get("time", {}).get("elapsed", "?")
                        detail = ev.get("detail", "")
                        marc_list.append(f"{nome} {minuto}'" + (" (R)" if detail == "Penalty" else " (aut.)" if detail == "Own Goal" else ""))

                match_data = {
                    "home": home_name, "away": away_name,
                    "gol_h": goals.get("home") if has_result else None,
                    "gol_a": goals.get("away") if has_result else None,
                    "status": ss,
                    "status_it": {"FT": "Terminata", "NS": "Da giocare", "1H": "1T", "2H": "2T", "HT": "Intervallo"}.get(ss, ss),
                    "minuto": status.get("elapsed"),
                    "live": is_live,
                    "fixture_id": fixture.get("id"),
                    "ora": _utc_to_rome(fixture.get("date", "")),
                    "data": fixture.get("date", "")[:10],
                    "marcatori": marc_list,
                }
                per_round[lg_data.get("round", "")].append(match_data)

            def round_num(r):
                try:
                    return int(r.split(" - ")[-1])
                except Exception:
                    return 0

            for rd in sorted(per_round.keys(), key=round_num):
                partite = per_round[rd]
                g_num = rd.split(" - ")[-1] if " - " in rd else rd

                total = len(partite)
                ft_count = sum(1 for p in partite if p["status"] in ("FT", "AET", "PEN"))
                ns_count = sum(1 for p in partite if p["status"] in ("NS", "TBD"))
                ha_live = any(p["live"] for p in partite)
                # Una giornata è "completata" SOLO se non ci sono partite da giocare (NS/TBD)
                # e nessuna partita è live. La soglia 70% era troppo aggressiva e causava
                # giornate con 3 partite ancora NS di essere marchiate come completate,
                # spostando erroneamente la giornata_corrente alla successiva.
                tutte_finite = ns_count == 0 and not ha_live and ft_count > 0
                ha_da_giocare = ns_count > 0

                if tutte_finite:
                    stato = "completata"
                elif ha_live:
                    stato = "live"
                    giornata_corrente = g_num
                else:
                    stato = "prossima"
                    if giornata_corrente is None and ha_da_giocare:
                        giornata_corrente = g_num

                giornate.append({
                    "giornata": g_num,
                    "data": partite[0]["data"] if partite else "",
                    "partite": partite,
                    "stato": stato,
                    "live": ha_live,
                })

    except Exception as e:
        print(f"⚠️ Calendario {league}: {e}")

    if giornata_corrente is None and giornate:
        for g in giornate:
            if g["stato"] != "completata":
                giornata_corrente = g["giornata"]
                break

    return {
        "giornate": giornate,
        "giornata_corrente": giornata_corrente or (giornate[-1]["giornata"] if giornate else "1"),
        "live": any(g.get("live") for g in giornate),
    }


@router.get("/{league}/squadre-attive")
@limiter.limit("20/minute")
async def squadre_attive(league: str, request: Request):
    """Squadre ancora attive in una competizione (da prossime fixtures)."""
    from api_server import LEAGUES, FOOTBALL_API_KEY, FOOTBALL_API_HOST, _get_nome_map
    if league not in LEAGUES:
        raise HTTPException(404, "Competizione non trovata")
    lg = LEAGUES[league]
    nome_map = _get_nome_map(league)
    try:
        req = urllib.request.Request(
            f"https://{FOOTBALL_API_HOST}/fixtures?league={lg['id']}&season={lg['season']}&next=20",
            headers={"x-apisports-key": FOOTBALL_API_KEY, "User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode())
        teams = set()
        for fix in data.get("response", []):
            h = fix.get("teams", {}).get("home", {}).get("name", "")
            a = fix.get("teams", {}).get("away", {}).get("name", "")
            h_mapped = nome_map.get(h, h)
            a_mapped = nome_map.get(a, a)
            if h_mapped:
                teams.add(h_mapped)
            if a_mapped:
                teams.add(a_mapped)
        return {"squadre": sorted(teams)}
    except Exception:
        return {"squadre": []}


# ─────────────────────────────
# MONDIALI 2026
# ─────────────────────────────

@router.get("/mondiali-2026/gironi")
@limiter.limit("20/minute")
async def worldcup_gironi(request: Request):
    """Restituisce gironi e partite del Mondiale 2026."""
    from api_server import WC_GIRONI_CACHE, WC_FIXTURES_CACHE, _fetch_worldcup_data
    if not WC_GIRONI_CACHE:
        _fetch_worldcup_data()

    # Raggruppa fixtures per girone
    fixtures_per_girone = {}
    for f in WC_FIXTURES_CACHE:
        rd = f.get("round", "")
        if "Group" in rd:
            for g_letter, squadre in WC_GIRONI_CACHE.items():
                nomi_girone = [s["squadra"] for s in squadre]
                if f["home"] in nomi_girone or f["away"] in nomi_girone:
                    if g_letter not in fixtures_per_girone:
                        fixtures_per_girone[g_letter] = []
                    fixtures_per_girone[g_letter].append(f)
                    break

    # Fixtures fasi finali (non girone)
    fasi = {}
    for f in WC_FIXTURES_CACHE:
        rd = f.get("round", "")
        if "Group" not in rd and rd:
            if rd not in fasi:
                fasi[rd] = []
            fasi[rd].append(f)

    return {
        "gironi": WC_GIRONI_CACHE,
        "partite_gironi": fixtures_per_girone,
        "fasi_finale": fasi,
        "totale_partite": len(WC_FIXTURES_CACHE),
    }


@router.get("/mondiali-2026/standings/{girone}")
@limiter.limit("20/minute")
async def worldcup_standings(girone: str, request: Request):
    """Classifica di un girone del Mondiale 2026."""
    from api_server import WC_GIRONI_CACHE, _fetch_worldcup_data
    if not WC_GIRONI_CACHE:
        _fetch_worldcup_data()
    g = girone.upper()
    standings = WC_GIRONI_CACHE.get(g, [])
    return {"girone": g, "classifica": standings}
