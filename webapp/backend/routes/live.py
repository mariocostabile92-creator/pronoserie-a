"""
routes/live.py - Risultati live, fixture, notizie
"""
from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["live"])

@router.get("/risultati")
async def risultati():
    """Ritorna risultati: live + storico completo da API Football."""
    from api_server import LIVE_RESULTS_CACHE, RISULTATI_STAGIONE_CACHE, LIVE_RESULTS_TIME, RISULTATI_STAGIONE_TIME
    from collections import defaultdict
    
    giornate = []
    
    # 1. Partite LIVE (in corso adesso)
    live_partite = []
    if LIVE_RESULTS_CACHE:
        for p in LIVE_RESULTS_CACHE:
            if p.get("live"):
                live_partite.append({
                    "home": p["home"], "away": p["away"],
                    "gol_h": p["gol_h"], "gol_a": p["gol_a"],
                    "marcatori": p["marcatori"],
                    "marcatori_home": p.get("marcatori_home", []),
                    "marcatori_away": p.get("marcatori_away", []),
                    "status": p["status"],
                    "status_it": p.get("status_it", p["status"]),
                    "minuto": p["minuto"], "live": True,
                    "data": p["data"], "ora": p.get("ora", ""),
                    "rossi_home": p.get("rossi_home", []),
                    "rossi_away": p.get("rossi_away", []),
                    "fixture_id": p.get("fixture_id"),
                })
    if live_partite:
        giornate.append({
            "giornata": "Live",
            "data": live_partite[0]["data"],
            "partite": live_partite,
            "live": True,
        })
    
    # 2. Storico completo da API Football
    if RISULTATI_STAGIONE_CACHE:
        per_round = defaultdict(list)
        for p in RISULTATI_STAGIONE_CACHE:
            rd = p.get("round", "")
            per_round[rd].append(p)
        
        rounds_sorted = sorted(per_round.keys(), key=lambda r: int(r.split(" - ")[-1]) if " - " in r and r.split(" - ")[-1].isdigit() else 0, reverse=True)
        
        for rd in rounds_sorted:
            partite = per_round[rd]
            g_num = rd.split(" - ")[-1] if " - " in rd else rd
            data_str = partite[0]["data"] if partite else ""
            giornate.append({
                "giornata": g_num,
                "data": data_str,
                "partite": partite,
                "live": False,
            })
    elif LIVE_RESULTS_CACHE:
        # Fallback: usa le ultime 30 partite raggruppate per data
        per_data = defaultdict(list)
        for p in LIVE_RESULTS_CACHE:
            if not p.get("live"):
                per_data[p["data"]].append({
                    "home": p["home"], "away": p["away"],
                    "gol_h": p["gol_h"], "gol_a": p["gol_a"],
                    "marcatori": p.get("marcatori", []),
                    "marcatori_home": p.get("marcatori_home", []),
                    "marcatori_away": p.get("marcatori_away", []),
                    "status": "FT", "status_it": "Terminata",
                    "live": False, "data": p["data"],
                    "ora": p.get("ora", ""),
                    "fixture_id": p.get("fixture_id"),
                })
        for data_str in sorted(per_data.keys(), reverse=True):
            giornate.append({
                "giornata": data_str,
                "data": data_str,
                "partite": per_data[data_str],
                "live": False,
            })
    
    return {
        "giornate": giornate,
        "live": any(g.get("live") for g in giornate),
        "aggiornamento": RISULTATI_STAGIONE_TIME or LIVE_RESULTS_TIME or "In caricamento...",
    }

@router.get("/fixture/{fixture_id}")
async def fixture_detail(fixture_id: int):
    """Scarica dettagli completi di una partita: eventi, statistiche, formazioni."""
    import urllib.request
    import json
    import os
    
    FOOTBALL_API_KEY = os.environ.get("FOOTBALL_API_KEY", "")
    FOOTBALL_API_HOST = "v3.football.api-sports.io"
    from api_server import FOOTBALL_NOME_MAP, _utc_to_rome
    
    result = {"fixture_id": fixture_id}
    
    # 1. Fixture base + eventi
    try:
        req = urllib.request.Request(
            f"https://{FOOTBALL_API_HOST}/fixtures?id={fixture_id}",
            headers={"x-apisports-key": FOOTBALL_API_KEY, "User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode())
        
        if data.get("response") and len(data["response"]) > 0:
            fix = data["response"][0]
            teams = fix.get("teams", {})
            goals = fix.get("goals", {})
            fixture = fix.get("fixture", {})
            status = fixture.get("status", {})
            events = fix.get("events", [])
            score = fix.get("score", {})
            
            home_name = FOOTBALL_NOME_MAP.get(teams.get("home", {}).get("name", "?"), teams.get("home", {}).get("name", "?"))
            away_name = FOOTBALL_NOME_MAP.get(teams.get("away", {}).get("name", "?"), teams.get("away", {}).get("name", "?"))
            home_id = teams.get("home", {}).get("id")
            
            status_map = {"FT":"Terminata","1H":"1T","2H":"2T","HT":"Intervallo","NS":"Non iniziata","ET":"Supplementari","P":"Rigori"}
            
            result["home"] = home_name
            result["away"] = away_name
            result["gol_h"] = goals.get("home", 0) or 0
            result["gol_a"] = goals.get("away", 0) or 0
            result["status"] = status.get("short", "")
            result["status_it"] = status_map.get(status.get("short", ""), status.get("short", ""))
            result["minuto"] = status.get("elapsed")
            result["live"] = status.get("short", "") in ("1H", "2H", "HT", "ET", "P")
            result["data"] = fixture.get("date", "")[:10]
            result["ora"] = _utc_to_rome(fixture.get("date", ""))
            result["arbitro"] = fixture.get("referee", "")
            result["stadio"] = fixture.get("venue", {}).get("name", "")
            result["citta"] = fixture.get("venue", {}).get("city", "")
            
            # Eventi dettagliati
            eventi = []
            for ev in events:
                nome = ev.get("player", {}).get("name", "?")
                assist = ev.get("assist", {}).get("name", "")
                minuto = ev.get("time", {}).get("elapsed", "?")
                extra = ev.get("time", {}).get("extra")
                min_str = f"{minuto}'+{extra}" if extra else f"{minuto}'"
                tipo = ev.get("type", "")
                detail = ev.get("detail", "")
                team_id = ev.get("team", {}).get("id")
                is_home = team_id == home_id
                
                evento = {
                    "minuto": min_str,
                    "tipo": tipo,
                    "dettaglio": detail,
                    "giocatore": nome,
                    "assist": assist,
                    "squadra": "home" if is_home else "away",
                }
                eventi.append(evento)
            result["eventi"] = eventi
    except Exception as e:
        result["errore_fixture"] = str(e)
    
    return result

@router.get("/notizie")
async def notizie():
    """Ritorna le ultime notizie Serie A."""
    from api_server import NOTIZIE_CACHE, NOTIZIE_LAST_UPDATE
    
    if not NOTIZIE_CACHE or len(NOTIZIE_CACHE) < 4:
        return {"notizie":[
            {"titolo":"Probabili formazioni Serie A Giornata 31: le scelte dei tecnici","fonte":"Fantacalcio.it","url":"https://www.fantacalcio.it/probabili-formazioni-serie-a"},
            {"titolo":"Calciomercato Serie A: tutti i trasferimenti di gennaio 2026","fonte":"Sky Sport","url":"https://sport.sky.it/calciomercato/serie-a"},
            {"titolo":"Serie A Giornata 31: Inter-Roma, Napoli-Milan - pronostici e analisi","fonte":"Sky Sport","url":"https://sport.sky.it/calcio/serie-a/calendario-risultati"},
        ],"aggiornamento":"Aggiornamento automatico ogni 30 min"}
    return {"notizie":NOTIZIE_CACHE,"aggiornamento":NOTIZIE_LAST_UPDATE}

@router.get("/{league}/risultati")
async def risultati_league(league: str):
    """Risultati per qualsiasi campionato."""
    from api_server import LEAGUES, LIVE_RESULTS_CACHE_ML, RISULTATI_STAGIONE_CACHE_ML, LIVE_IN_CORSO_ML, CLASSIFICA_LAST_UPDATE
    from fastapi import HTTPException
    from collections import defaultdict
    
    if league not in LEAGUES:
        raise HTTPException(404, "Campionato non trovato")
    giornate = []
    # Live
    live_p = LIVE_RESULTS_CACHE_ML.get(league) or []
    live_now = [p for p in live_p if p.get("live")]
    if live_now:
        giornate.append({"giornata":"Live","data":live_now[0]["data"],"partite":live_now,"live":True})
    # Storico
    storico = RISULTATI_STAGIONE_CACHE_ML.get(league) or []
    if storico:
        per_round = defaultdict(list)
        for p in storico:
            per_round[p.get("round","")].append(p)
        for rd in sorted(per_round.keys(), key=lambda r: int(r.split(" - ")[-1]) if " - " in r and r.split(" - ")[-1].isdigit() else 0, reverse=True):
            g_num = rd.split(" - ")[-1] if " - " in rd else rd
            giornate.append({"giornata":g_num,"data":per_round[rd][0]["data"],"partite":per_round[rd],"live":False})
    return {"giornate":giornate,"live":LIVE_IN_CORSO_ML.get(league,False),"aggiornamento":CLASSIFICA_LAST_UPDATE.get(league,"")}
