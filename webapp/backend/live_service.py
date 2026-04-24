"""
live_service.py - Servizio di aggiornamento live per MatchIQ
Gestisce: fetch risultati live, classifica, marcatori, rose, infortunati,
          statistiche giocatori, dati Mondiali 2026, multi-league data.
Loop aggiornamento: 2 min durante live, 30 min altrimenti.
"""

import os
import json
import time
import logging
import threading
import urllib.request
from datetime import datetime, timezone

_logger = logging.getLogger(__name__)

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

# ─────────────────────────────
# API Football config
# ─────────────────────────────
FOOTBALL_API_KEY = os.environ.get("FOOTBALL_API_KEY", "")
FOOTBALL_API_HOST = "v3.football.api-sports.io"

# ─────────────────────────────
# LEAGUES config (import circolare-safe: definita qui, usata anche in api_server)
# ─────────────────────────────
LEAGUES = {
    "serie-a":          {"id": 135, "season": 2025, "name": "Serie A",          "country": "Italy"},
    "premier-league":   {"id": 39,  "season": 2025, "name": "Premier League",   "country": "England"},
    "la-liga":          {"id": 140, "season": 2025, "name": "La Liga",           "country": "Spain"},
    "champions-league": {"id": 2,   "season": 2025, "name": "Champions League", "country": "Europe"},
    "europa-league":    {"id": 3,   "season": 2025, "name": "Europa League",     "country": "Europe"},
    "conference-league":{"id": 848, "season": 2025, "name": "Conference League","country": "Europe"},
    "bundesliga":       {"id": 78,  "season": 2025, "name": "Bundesliga",        "country": "Germany"},
    "ligue-1":          {"id": 61,  "season": 2025, "name": "Ligue 1",           "country": "France"},
    "mondiali-2026":    {"id": 1,   "season": 2026, "name": "FIFA World Cup 2026","country": "World", "type": "tournament"},
}

_LEAGUE_KEYS = ["serie-a", "premier-league", "la-liga", "champions-league",
                "europa-league", "conference-league", "bundesliga", "ligue-1"]

# ─────────────────────────────
# CACHE GLOBALI
# ─────────────────────────────
LIVE_RESULTS_CACHE = None
LIVE_RESULTS_TIME = ""
LIVE_IN_CORSO = False

CLASSIFICA_CACHE       = {k: None for k in _LEAGUE_KEYS}
CLASSIFICA_LAST_UPDATE = {k: ""   for k in _LEAGUE_KEYS}
MARCATORI_CACHE        = {k: None for k in _LEAGUE_KEYS}
LIVE_RESULTS_CACHE_ML  = {k: None for k in _LEAGUE_KEYS}
RISULTATI_STAGIONE_CACHE_ML = {k: None for k in _LEAGUE_KEYS}
LIVE_IN_CORSO_ML       = {k: False for k in _LEAGUE_KEYS}

RISULTATI_STAGIONE_CACHE = None
RISULTATI_STAGIONE_TIME  = ""

ROSE_LIVE          = {}
ALLENATORI_LIVE    = {}
INFORTUNATI_LIVE   = {}
ROSE_LAST_UPDATE   = ""

PLAYER_STATS_CACHE = {}
PLAYER_STATS_LAST  = 0
FANTACALCIO_LEAGUES = ["serie-a", "premier-league", "la-liga", "bundesliga", "ligue-1"]
MATCHDAY_CACHE     = {}
TEAM_STATS_CACHE   = {}

WC_GIRONI_CACHE    = {}
WC_FIXTURES_CACHE  = []
WC_LAST_UPDATE     = 0

_updater_count = 0

# ─────────────────────────────
# HELPER
# ─────────────────────────────
def _utc_to_rome(utc_str):
    """Converte orario UTC dall'API in ora italiana (CET/CEST) usando zoneinfo."""
    try:
        if not utc_str or len(utc_str) < 16:
            return ""
        from zoneinfo import ZoneInfo
        orario_utc = datetime.fromisoformat(utc_str.replace('Z', '+00:00'))
        ora_locale = orario_utc.astimezone(ZoneInfo("Europe/Rome"))
        return ora_locale.strftime("%H:%M")
    except Exception:
        return utc_str[11:16] if len(utc_str) > 15 else ""


def _get_nome_map(league_key):
    from league_mappings import (
        PL_NOME_MAP, LL_NOME_MAP, BL_NOME_MAP, L1_NOME_MAP,
        WC_NOME_MAP, FOOTBALL_NOME_MAP,
    )
    if league_key == "premier-league":
        return PL_NOME_MAP
    if league_key == "la-liga":
        return LL_NOME_MAP
    if league_key == "bundesliga":
        return BL_NOME_MAP
    if league_key == "ligue-1":
        return L1_NOME_MAP
    if league_key == "mondiali-2026":
        return WC_NOME_MAP
    return FOOTBALL_NOME_MAP


# ─────────────────────────────
# FETCH LIVE RESULTS (Serie A)
# ─────────────────────────────
def _fetch_live_results():
    """Scarica risultati live dalla API Football (ultimi 30 + oggi)."""
    global LIVE_RESULTS_CACHE, LIVE_RESULTS_TIME, LIVE_IN_CORSO
    from league_mappings import FOOTBALL_NOME_MAP
    try:
        req = urllib.request.Request(
            f"https://{FOOTBALL_API_HOST}/fixtures?league=135&season=2025&last=30",
            headers={"x-apisports-key": FOOTBALL_API_KEY, "User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode())

        partite = []
        has_live = False
        status_map = {
            "FT": "Terminata", "AET": "Dopo supplementari",
            "PEN": "Dopo rigori", "1H": "1° Tempo",
            "2H": "2° Tempo", "HT": "Intervallo",
            "ET": "Supplementari", "P": "Rigori",
            "NS": "Non iniziata", "TBD": "Da definire",
            "CANC": "Cancellata", "PST": "Posticipata",
            "SUSP": "Sospesa", "INT": "Interrotta",
            "ABD": "Abbandonata", "AWD": "Vittoria a tavolino",
            "WO": "Walkover", "BT": "Pausa",
        }

        if data.get("response"):
            for fix in data["response"]:
                teams   = fix.get("teams", {})
                goals   = fix.get("goals", {})
                fixture = fix.get("fixture", {})
                status  = fixture.get("status", {})
                events  = fix.get("events", [])

                marcatori, marcatori_home, marcatori_away = [], [], []
                home_id = teams.get("home", {}).get("id")
                away_id = teams.get("away", {}).get("id")
                for ev in events:
                    if ev.get("type") == "Goal":
                        nome   = ev.get("player", {}).get("name", "?")
                        minuto = ev.get("time", {}).get("elapsed", "?")
                        detail = ev.get("detail", "")
                        team_id = ev.get("team", {}).get("id")
                        if detail == "Penalty":
                            gol_str = f"{nome} {minuto}' (R)"
                        elif detail == "Own Goal":
                            gol_str = f"{nome} {minuto}' (aut.)"
                        else:
                            gol_str = f"{nome} {minuto}'"
                        marcatori.append(gol_str)
                        if team_id == home_id:
                            marcatori_home.append(gol_str)
                        else:
                            marcatori_away.append(gol_str)

                cartellini_gialli, rossi_home, rossi_away = [], [], []
                for ev in events:
                    if ev.get("type") == "Card":
                        nome   = ev.get("player", {}).get("name", "?")
                        minuto = ev.get("time", {}).get("elapsed", "?")
                        team_id = ev.get("team", {}).get("id")
                        if ev.get("detail") == "Red Card":
                            if team_id == home_id:
                                rossi_home.append(f"{nome} {minuto}'")
                            else:
                                rossi_away.append(f"{nome} {minuto}'")
                        elif ev.get("detail") == "Yellow Card":
                            cartellini_gialli.append(f"{nome} {minuto}'")

                stats_list = fix.get("statistics", [])
                stats = {}
                if stats_list and len(stats_list) >= 2:
                    for idx, side in enumerate(["home", "away"]):
                        for s in (stats_list[idx] or {}).get("statistics", []):
                            tipo = s.get("type", "")
                            val  = s.get("value")
                            mapping = {
                                "Ball Possession": f"possesso_{side}",
                                "Total Shots":     f"tiri_{side}",
                                "Shots on Goal":   f"tiri_porta_{side}",
                                "Corner Kicks":    f"corner_{side}",
                                "Fouls":           f"falli_{side}",
                                "Offsides":        f"fuorigioco_{side}",
                            }
                            if tipo in mapping:
                                stats[mapping[tipo]] = val

                status_short = status.get("short", "FT")
                is_live = status_short in ("1H", "2H", "HT", "ET", "P", "BT", "INT")
                if is_live:
                    has_live = True

                home_name = FOOTBALL_NOME_MAP.get(
                    teams.get("home", {}).get("name", "?"),
                    teams.get("home", {}).get("name", "?")
                )
                away_name = FOOTBALL_NOME_MAP.get(
                    teams.get("away", {}).get("name", "?"),
                    teams.get("away", {}).get("name", "?")
                )

                partite.append({
                    "home": home_name, "away": away_name,
                    "gol_h": goals.get("home", 0) or 0,
                    "gol_a": goals.get("away", 0) or 0,
                    "status": status_short,
                    "status_it": status_map.get(status_short, status_short),
                    "minuto": status.get("elapsed"),
                    "live": is_live,
                    "marcatori": marcatori,
                    "marcatori_home": marcatori_home,
                    "marcatori_away": marcatori_away,
                    "rossi_home": rossi_home,
                    "rossi_away": rossi_away,
                    "gialli": cartellini_gialli,
                    "stats": stats,
                    "fixture_id": fixture.get("id"),
                    "data": fixture.get("date", "")[:10],
                    "ora": _utc_to_rome(fixture.get("date", "")),
                })

        # Partite di oggi (potrebbero non essere nelle ultime 30)
        try:
            oggi = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            req2 = urllib.request.Request(
                f"https://{FOOTBALL_API_HOST}/fixtures?league=135&season=2025&date={oggi}",
                headers={"x-apisports-key": FOOTBALL_API_KEY, "User-Agent": "Mozilla/5.0"}
            )
            with urllib.request.urlopen(req2, timeout=15) as r2:
                data2 = json.loads(r2.read().decode())
            if data2.get("response"):
                existing_ids = {fix.get("fixture", {}).get("id") for fix in data.get("response", [])}
                for fix in data2["response"]:
                    if fix.get("fixture", {}).get("id") in existing_ids:
                        continue
                    teams   = fix.get("teams", {})
                    goals   = fix.get("goals", {})
                    fixture = fix.get("fixture", {})
                    status  = fixture.get("status", {})
                    events  = fix.get("events", [])
                    marcatori = []
                    for ev in events:
                        if ev.get("type") == "Goal":
                            nome   = ev.get("player", {}).get("name", "?")
                            minuto = ev.get("time", {}).get("elapsed", "?")
                            detail = ev.get("detail", "")
                            if detail == "Penalty":
                                marcatori.append(f"{nome} {minuto}' (R)")
                            elif detail == "Own Goal":
                                marcatori.append(f"{nome} {minuto}' (aut.)")
                            else:
                                marcatori.append(f"{nome} {minuto}'")
                    status_short = status.get("short", "NS")
                    is_live = status_short in ("1H", "2H", "HT", "ET", "P", "BT", "INT")
                    if is_live:
                        has_live = True
                    home_name = FOOTBALL_NOME_MAP.get(teams.get("home",{}).get("name","?"), teams.get("home",{}).get("name","?"))
                    away_name = FOOTBALL_NOME_MAP.get(teams.get("away",{}).get("name","?"), teams.get("away",{}).get("name","?"))
                    partite.append({
                        "home": home_name, "away": away_name,
                        "gol_h": goals.get("home", 0) or 0,
                        "gol_a": goals.get("away", 0) or 0,
                        "status": status_short,
                        "status_it": {"FT":"Terminata","NS":"Non iniziata","1H":"1° Tempo","2H":"2° Tempo","HT":"Intervallo"}.get(status_short, status_short),
                        "minuto": status.get("elapsed"),
                        "live": is_live,
                        "marcatori": marcatori,
                        "rossi_home": [], "rossi_away": [],
                        "data": fixture.get("date", "")[:10],
                        "ora": _utc_to_rome(fixture.get("date", "")),
                    })
        except Exception as e:
            print(f"⚠️ Fetch partite oggi: {e}")

        if partite:
            LIVE_RESULTS_CACHE = partite
            LIVE_RESULTS_TIME  = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")
            LIVE_IN_CORSO      = has_live
            print(f"⚽ RISULTATI LIVE: {len(partite)} partite {'(LIVE IN CORSO!)' if has_live else ''}")
    except Exception as e:
        print(f"❌ Errore API Football: {e}")


# ─────────────────────────────
# CLASSIFICA SERIE A
# ─────────────────────────────
def _fetch_classifica_live():
    """Scarica classifica Serie A aggiornata da API Football."""
    from league_mappings import FOOTBALL_NOME_MAP
    try:
        req = urllib.request.Request(
            f"https://{FOOTBALL_API_HOST}/standings?league=135&season=2025",
            headers={"x-apisports-key": FOOTBALL_API_KEY, "User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode())

        if data.get("response") and len(data["response"]) > 0:
            standings = data["response"][0].get("league", {}).get("standings", [])
            if standings and len(standings) > 0:
                classifica = []
                for team in standings[0]:
                    nome_api = team.get("team", {}).get("name", "?")
                    nome  = FOOTBALL_NOME_MAP.get(nome_api, nome_api)
                    stats = team.get("all", {})
                    gf = stats.get("goals", {}).get("for", 0)
                    gs = stats.get("goals", {}).get("against", 0)
                    classifica.append({
                        "Squadra": nome,
                        "Punti": team.get("points", 0),
                        "G": stats.get("played", 0),
                        "V": stats.get("win", 0),
                        "N": stats.get("draw", 0),
                        "P": stats.get("lose", 0),
                        "GF": gf, "GS": gs, "DR": gf - gs,
                    })
                classifica.sort(key=lambda x: (-x["Punti"], -x["DR"], -x["GF"]))
                if len(classifica) >= 10:
                    CLASSIFICA_CACHE["serie-a"] = classifica
                    CLASSIFICA_LAST_UPDATE["serie-a"] = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")
                    print(f"🏆 CLASSIFICA LIVE: {len(classifica)} squadre aggiornate")
                    return True
    except Exception as e:
        print(f"❌ Errore fetch classifica: {e}")
    return False


# ─────────────────────────────
# MARCATORI SERIE A
# ─────────────────────────────
def _fetch_marcatori_live():
    """Scarica classifica marcatori Serie A da API Football."""
    from league_mappings import FOOTBALL_NOME_MAP
    try:
        req = urllib.request.Request(
            f"https://{FOOTBALL_API_HOST}/players/topscorers?league=135&season=2025",
            headers={"x-apisports-key": FOOTBALL_API_KEY, "User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode())

        if data.get("response") and len(data["response"]) > 0:
            marcatori = []
            for i, player in enumerate(data["response"][:20], 1):
                info  = player.get("player", {})
                gol   = 0
                squadra_api = ""
                for s in player.get("statistics", []):
                    if s.get("league", {}).get("id") == 135:
                        gol = s.get("goals", {}).get("total", 0) or 0
                        squadra_api = s.get("team", {}).get("name", "")
                        break
                if gol == 0 and player.get("statistics"):
                    gol = player["statistics"][0].get("goals", {}).get("total", 0) or 0
                    squadra_api = player["statistics"][0].get("team", {}).get("name", "")
                squadra = FOOTBALL_NOME_MAP.get(squadra_api, squadra_api)
                marcatori.append({"pos": i, "giocatore": info.get("name", "?"), "squadra": squadra, "gol": gol})
            if len(marcatori) >= 5:
                MARCATORI_CACHE["serie-a"] = marcatori
                print(f"⚽ MARCATORI LIVE: {len(marcatori)} giocatori aggiornati")
                return True
    except Exception as e:
        print(f"❌ Errore fetch marcatori: {e}")
    return False


# ─────────────────────────────
# INFORTUNATI
# ─────────────────────────────
def _fetch_infortunati_live():
    """Scarica infortunati ATTUALI da API Football (solo quelli non recuperati)."""
    global INFORTUNATI_LIVE
    from league_mappings import FOOTBALL_NOME_MAP
    try:
        req = urllib.request.Request(
            f"https://{FOOTBALL_API_HOST}/injuries?league=135&season=2025",
            headers={"x-apisports-key": FOOTBALL_API_KEY, "User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode())

        if data.get("response"):
            inj_per_team = {}
            seen_players = {}
            for item in data["response"]:
                team_name = FOOTBALL_NOME_MAP.get(
                    item.get("team", {}).get("name", ""),
                    item.get("team", {}).get("name", "")
                )
                player      = item.get("player", {})
                player_name = player.get("name", "?")
                reason      = player.get("reason", "") or ""
                ptype       = player.get("type", "") or ""
                fixture_date = item.get("fixture", {}).get("date", "")

                if not team_name or not player_name:
                    continue

                key = f"{team_name}_{player_name}"
                if key in seen_players:
                    if fixture_date <= seen_players[key]["date"]:
                        continue
                seen_players[key] = {
                    "date": fixture_date,
                    "team": team_name,
                    "nome": player_name,
                    "tipo": "squalifica" if "Suspended" in reason or "Red" in reason else "infortunio",
                    "dettaglio": reason or ptype or "Indisponibile",
                }

            for key, inj in seen_players.items():
                team = inj["team"]
                if team not in inj_per_team:
                    inj_per_team[team] = []
                if len(inj_per_team[team]) < 8:
                    inj_per_team[team].append({
                        "nome": inj["nome"],
                        "tipo": inj["tipo"],
                        "dettaglio": inj["dettaglio"],
                    })

            if inj_per_team:
                INFORTUNATI_LIVE = inj_per_team
                tot = sum(len(v) for v in inj_per_team.values())
                print(f"🏥 INFORTUNATI LIVE: {tot} giocatori in {len(inj_per_team)} squadre")
    except Exception as e:
        print(f"❌ Errore fetch infortunati: {e}")


# ─────────────────────────────
# ROSE + ALLENATORI
# ─────────────────────────────
def _fetch_rose_live(team_ids=None):
    """Scarica rose complete di tutte le squadre da API Football."""
    global ROSE_LIVE, ALLENATORI_LIVE, ROSE_LAST_UPDATE
    from league_mappings import _TEAM_IDS, _RUOLO_MAP
    if team_ids is None:
        team_ids = _TEAM_IDS
    try:
        for nome, team_id in team_ids.items():
            try:
                req = urllib.request.Request(
                    f"https://{FOOTBALL_API_HOST}/players/squads?team={team_id}",
                    headers={"x-apisports-key": FOOTBALL_API_KEY, "User-Agent": "Mozilla/5.0"}
                )
                with urllib.request.urlopen(req, timeout=15) as r:
                    data = json.loads(r.read().decode())
                if data.get("response") and len(data["response"]) > 0:
                    players = data["response"][0].get("players", [])
                    rosa = []
                    for p in players:
                        ruolo = _RUOLO_MAP.get(p.get("position", ""), "C")
                        rosa.append({
                            "nome": p.get("name", "?"),
                            "ruolo": ruolo,
                            "numero": p.get("number", 0) or 0,
                            "foto": p.get("photo", ""),
                        })
                    if rosa:
                        ROSE_LIVE[nome] = rosa

                req2 = urllib.request.Request(
                    f"https://{FOOTBALL_API_HOST}/coachs?team={team_id}",
                    headers={"x-apisports-key": FOOTBALL_API_KEY, "User-Agent": "Mozilla/5.0"}
                )
                with urllib.request.urlopen(req2, timeout=15) as r:
                    data2 = json.loads(r.read().decode())
                if data2.get("response") and len(data2["response"]) > 0:
                    for coach in data2["response"]:
                        career = coach.get("career", [])
                        for c in career:
                            if c.get("team", {}).get("id") == team_id and c.get("end") is None:
                                ALLENATORI_LIVE[nome] = coach.get("name", "N/D")
                                break

                time.sleep(0.5)
            except Exception:
                _logger.warning("Eccezione silenziata", exc_info=True)

        if ROSE_LIVE:
            ROSE_LAST_UPDATE = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")
            print(f"👕 ROSE LIVE: {len(ROSE_LIVE)} squadre aggiornate")
    except Exception as e:
        print(f"❌ Errore fetch rose: {e}")


# ─────────────────────────────
# STORICO STAGIONE
# ─────────────────────────────
def _fetch_risultati_stagione():
    """Scarica TUTTI i risultati della stagione da API Football."""
    global RISULTATI_STAGIONE_CACHE, RISULTATI_STAGIONE_TIME
    from league_mappings import FOOTBALL_NOME_MAP
    try:
        req = urllib.request.Request(
            f"https://{FOOTBALL_API_HOST}/fixtures?league=135&season=2025&status=FT-AET-PEN",
            headers={"x-apisports-key": FOOTBALL_API_KEY, "User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.loads(r.read().decode())

        if data.get("response"):
            partite = []
            for fix in data["response"]:
                teams   = fix.get("teams", {})
                goals   = fix.get("goals", {})
                fixture = fix.get("fixture", {})
                events  = fix.get("events", [])
                league  = fix.get("league", {})

                home_name = FOOTBALL_NOME_MAP.get(teams.get("home",{}).get("name","?"), teams.get("home",{}).get("name","?"))
                away_name = FOOTBALL_NOME_MAP.get(teams.get("away",{}).get("name","?"), teams.get("away",{}).get("name","?"))

                marcatori, marcatori_home, marcatori_away = [], [], []
                home_id = teams.get("home", {}).get("id")
                for ev in events:
                    if ev.get("type") == "Goal":
                        nome   = ev.get("player",{}).get("name","?")
                        minuto = ev.get("time",{}).get("elapsed","?")
                        detail = ev.get("detail","")
                        if detail == "Penalty":
                            gol_str = f"{nome} {minuto}' (R)"
                        elif detail == "Own Goal":
                            gol_str = f"{nome} {minuto}' (aut.)"
                        else:
                            gol_str = f"{nome} {minuto}'"
                        marcatori.append(gol_str)
                        if ev.get("team",{}).get("id") == home_id:
                            marcatori_home.append(gol_str)
                        else:
                            marcatori_away.append(gol_str)

                partite.append({
                    "home": home_name, "away": away_name,
                    "gol_h": goals.get("home", 0) or 0,
                    "gol_a": goals.get("away", 0) or 0,
                    "status": "FT", "status_it": "Terminata", "live": False,
                    "marcatori": marcatori,
                    "marcatori_home": marcatori_home,
                    "marcatori_away": marcatori_away,
                    "fixture_id": fixture.get("id"),
                    "data": fixture.get("date", "")[:10],
                    "ora": _utc_to_rome(fixture.get("date", "")),
                    "round": league.get("round", ""),
                })

            if partite:
                partite.sort(key=lambda x: x["data"], reverse=True)
                RISULTATI_STAGIONE_CACHE = partite
                RISULTATI_STAGIONE_CACHE_ML["serie-a"] = partite
                RISULTATI_STAGIONE_TIME = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")
                print(f"📊 STORICO STAGIONE: {len(partite)} partite caricate")
    except Exception as e:
        print(f"❌ Errore fetch storico stagione: {e}")


# ─────────────────────────────
# STATISTICHE GIOCATORI (Fantacalcio)
# ─────────────────────────────
def _fetch_player_stats(league_key):
    """Fetch statistiche giocatori da API Football per il fantacalcio."""
    global PLAYER_STATS_CACHE, PLAYER_STATS_LAST
    lid = LEAGUES.get(league_key, {}).get("id")
    if not lid:
        return
    stats = {}
    pos_map = {"Goalkeeper": "P", "Defender": "D", "Midfielder": "C", "Attacker": "A"}

    for endpoint in ["topscorers", "topassists"]:
        try:
            req = urllib.request.Request(
                f"https://{FOOTBALL_API_HOST}/players/{endpoint}?league={lid}&season=2025",
                headers={"x-apisports-key": FOOTBALL_API_KEY, "User-Agent": "Mozilla/5.0"}
            )
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read().decode())
            for p in data.get("response", []):
                pname = p.get("player", {}).get("name", "")
                if not pname:
                    continue
                s = p.get("statistics", [{}])[0]
                key = pname.lower()
                existing = stats.get(key, {})
                goals_data   = s.get("goals", {})
                games_data   = s.get("games", {})
                cards_data   = s.get("cards", {})
                penalty_data = s.get("penalty", {})
                stats[key] = {
                    "nome": pname,
                    "gol":    max(existing.get("gol", 0),    goals_data.get("total") or 0),
                    "assist": max(existing.get("assist", 0), goals_data.get("assists") or 0),
                    "media":  float(games_data.get("rating") or existing.get("media", 0) or 0),
                    "minuti": max(existing.get("minuti", 0), games_data.get("minutes") or 0),
                    "presenze": max(existing.get("presenze", 0), games_data.get("appearences") or 0),
                    "gialli": max(existing.get("gialli", 0), cards_data.get("yellow") or 0),
                    "rossi":  max(existing.get("rossi", 0),  cards_data.get("red") or 0),
                    "rigori_segnati": max(existing.get("rigori_segnati", 0), penalty_data.get("scored") or 0),
                    "posizione": pos_map.get(games_data.get("position", ""), existing.get("posizione", "A")),
                    "squadra": s.get("team", {}).get("name", existing.get("squadra", "")),
                }
        except Exception as e:
            print(f"⚠️ Fetch player stats {league_key}/{endpoint}: {e}")

    marc = MARCATORI_CACHE.get(league_key) or []
    marc_nomi = set(m.get("giocatore", "").split()[-1] for m in marc if m.get("gol", 0) >= 3)
    for key, ps in stats.items():
        cognome = ps["nome"].split()[-1].lower()
        if cognome in marc_nomi:
            ps["forma"] = 1.15
            ps["forma_trend"] = "crescita"
        elif ps.get("media", 0) >= 7.0:
            ps["forma"] = 1.05
            ps["forma_trend"] = "stabile"
        else:
            ps["forma"] = 0.95
            ps["forma_trend"] = "calo"

    PLAYER_STATS_CACHE[league_key] = stats
    PLAYER_STATS_LAST = time.time()
    print(f"📊 Player stats {league_key}: {len(stats)} giocatori")


# ─────────────────────────────
# MONDIALI 2026
# ─────────────────────────────
def _fetch_worldcup_data():
    """Fetch gironi e partite Mondiali 2026 da API Football."""
    global WC_GIRONI_CACHE, WC_FIXTURES_CACHE, WC_LAST_UPDATE
    from league_mappings import WC_NOME_MAP
    if time.time() - WC_LAST_UPDATE < 1800:
        return

    try:
        req = urllib.request.Request(
            f"https://{FOOTBALL_API_HOST}/standings?league=1&season=2026",
            headers={"x-apisports-key": FOOTBALL_API_KEY, "User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.loads(r.read().decode())

        gironi = {}
        for resp in data.get("response", []):
            for grp_list in resp.get("league", {}).get("standings", []):
                if not grp_list:
                    continue
                g_name   = grp_list[0].get("group", "")
                g_letter = g_name.replace("Group ", "").strip()
                if g_letter.startswith("Ranking"):
                    continue
                squadre = []
                for team in grp_list:
                    t_name  = team.get("team", {}).get("name", "")
                    display = WC_NOME_MAP.get(t_name, t_name)
                    squadre.append({
                        "pos": team.get("rank", 0),
                        "squadra": display, "squadra_api": t_name,
                        "team_id": team.get("team", {}).get("id", 0),
                        "punti": team.get("points", 0),
                        "g": team.get("all", {}).get("played", 0),
                        "v": team.get("all", {}).get("win", 0),
                        "p": team.get("all", {}).get("draw", 0),
                        "s": team.get("all", {}).get("lose", 0),
                        "gf": team.get("all", {}).get("goals", {}).get("for", 0),
                        "gs": team.get("all", {}).get("goals", {}).get("against", 0),
                        "diff": team.get("goalsDiff", 0),
                    })
                if g_letter:
                    gironi[g_letter] = squadre

        WC_GIRONI_CACHE = gironi

        req = urllib.request.Request(
            f"https://{FOOTBALL_API_HOST}/fixtures?league=1&season=2026",
            headers={"x-apisports-key": FOOTBALL_API_KEY, "User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.loads(r.read().decode())

        fixtures = []
        for fix in data.get("response", []):
            home_api = fix.get("teams", {}).get("home", {}).get("name", "")
            away_api = fix.get("teams", {}).get("away", {}).get("name", "")
            fix_date = fix.get("fixture", {}).get("date", "")
            fixtures.append({
                "home": WC_NOME_MAP.get(home_api, home_api),
                "away": WC_NOME_MAP.get(away_api, away_api),
                "home_api": home_api, "away_api": away_api,
                "home_id": fix.get("teams", {}).get("home", {}).get("id", 0),
                "away_id": fix.get("teams", {}).get("away", {}).get("id", 0),
                "data": fix_date[:10],
                "ora": fix_date[11:16] if "T" in fix_date else "",
                "round": fix.get("league", {}).get("round", ""),
                "status": fix.get("fixture", {}).get("status", {}).get("short", "NS"),
                "gol_h": fix.get("goals", {}).get("home"),
                "gol_a": fix.get("goals", {}).get("away"),
            })

        WC_FIXTURES_CACHE = sorted(fixtures, key=lambda x: x.get("data", ""))
        WC_LAST_UPDATE = time.time()
        print(f"🏆 Mondiali 2026: {len(gironi)} gironi, {len(fixtures)} partite")
    except Exception as e:
        print(f"⚠️ Fetch WC data: {e}")


# ─────────────────────────────
# MULTI-LEAGUE DATA
# ─────────────────────────────
def _fetch_league_data(league_key):
    """Scarica classifica, marcatori, risultati per un campionato da API Football."""
    league = LEAGUES.get(league_key)
    if not league:
        return
    lid    = league["id"]
    season = league["season"]
    nome_map = _get_nome_map(league_key)
    print(f"📡 Fetch {league['name']} (league={lid}, season={season})...")

    # Classifica
    try:
        req = urllib.request.Request(
            f"https://{FOOTBALL_API_HOST}/standings?league={lid}&season={season}",
            headers={"x-apisports-key": FOOTBALL_API_KEY, "User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode())
        if data.get("response") and len(data["response"]) > 0:
            standings = data["response"][0].get("league", {}).get("standings", [])
            if standings and len(standings) > 0:
                classifica = []
                for team in standings[0]:
                    nome_api = team.get("team", {}).get("name", "?")
                    nome  = nome_map.get(nome_api, nome_api)
                    stats = team.get("all", {})
                    gf = stats.get("goals", {}).get("for", 0)
                    gs = stats.get("goals", {}).get("against", 0)
                    classifica.append({
                        "Squadra": nome, "Punti": team.get("points", 0),
                        "G": stats.get("played", 0), "V": stats.get("win", 0),
                        "N": stats.get("draw", 0),   "P": stats.get("lose", 0),
                        "GF": gf, "GS": gs, "DR": gf - gs,
                    })
                classifica.sort(key=lambda x: (-x["Punti"], -x["DR"]))
                if len(classifica) >= 10:
                    CLASSIFICA_CACHE[league_key] = classifica
                    CLASSIFICA_LAST_UPDATE[league_key] = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")
    except Exception as e:
        print(f"⚠️ Classifica {league_key}: {e}")

    # Marcatori
    try:
        req = urllib.request.Request(
            f"https://{FOOTBALL_API_HOST}/players/topscorers?league={lid}&season={season}",
            headers={"x-apisports-key": FOOTBALL_API_KEY, "User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode())
        if data.get("response"):
            marcatori = []
            for i, player in enumerate(data["response"][:20], 1):
                info = player.get("player", {})
                gol  = 0
                squadra_api = ""
                for s in player.get("statistics", []):
                    if s.get("league", {}).get("id") == lid:
                        gol = s.get("goals", {}).get("total", 0) or 0
                        squadra_api = s.get("team", {}).get("name", "")
                        break
                squadra = nome_map.get(squadra_api, squadra_api)
                marcatori.append({"pos": i, "giocatore": info.get("name", "?"), "squadra": squadra, "gol": gol})
            if marcatori:
                MARCATORI_CACHE[league_key] = marcatori
    except Exception as e:
        print(f"⚠️ Marcatori {league_key}: {e}")

    # Risultati stagione
    try:
        req = urllib.request.Request(
            f"https://{FOOTBALL_API_HOST}/fixtures?league={lid}&season={season}&status=FT-AET-PEN",
            headers={"x-apisports-key": FOOTBALL_API_KEY, "User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.loads(r.read().decode())
        if data.get("response"):
            partite = []
            for fix in data["response"]:
                teams   = fix.get("teams", {})
                goals   = fix.get("goals", {})
                fixture = fix.get("fixture", {})
                events  = fix.get("events", [])
                lg      = fix.get("league", {})
                home_name = nome_map.get(teams.get("home",{}).get("name","?"), teams.get("home",{}).get("name","?"))
                away_name = nome_map.get(teams.get("away",{}).get("name","?"), teams.get("away",{}).get("name","?"))
                marcatori, marcatori_home, marcatori_away = [], [], []
                home_id = teams.get("home",{}).get("id")
                for ev in events:
                    if ev.get("type") == "Goal":
                        nome   = ev.get("player",{}).get("name","?")
                        minuto = ev.get("time",{}).get("elapsed","?")
                        detail = ev.get("detail","")
                        gol_str = f"{nome} {minuto}'" + (" (R)" if detail=="Penalty" else " (aut.)" if detail=="Own Goal" else "")
                        marcatori.append(gol_str)
                        if ev.get("team",{}).get("id") == home_id:
                            marcatori_home.append(gol_str)
                        else:
                            marcatori_away.append(gol_str)
                partite.append({
                    "home": home_name, "away": away_name,
                    "gol_h": goals.get("home", 0) or 0,
                    "gol_a": goals.get("away", 0) or 0,
                    "status": "FT", "status_it": "Terminata", "live": False,
                    "marcatori": marcatori,
                    "marcatori_home": marcatori_home,
                    "marcatori_away": marcatori_away,
                    "fixture_id": fixture.get("id"),
                    "data": fixture.get("date","")[:10],
                    "ora": _utc_to_rome(fixture.get("date","")),
                    "round": lg.get("round",""),
                })
            if partite:
                partite.sort(key=lambda x: x["data"], reverse=True)
                RISULTATI_STAGIONE_CACHE_ML[league_key] = partite
    except Exception as e:
        print(f"⚠️ Risultati {league_key}: {e}")

    # Live results
    try:
        req = urllib.request.Request(
            f"https://{FOOTBALL_API_HOST}/fixtures?league={lid}&season={season}&last=15",
            headers={"x-apisports-key": FOOTBALL_API_KEY, "User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode())
        if data.get("response"):
            live_p   = []
            has_live = False
            for fix in data["response"]:
                teams   = fix.get("teams",{})
                goals   = fix.get("goals",{})
                fixture = fix.get("fixture",{})
                status  = fixture.get("status",{})
                events  = fix.get("events",[])
                home_name = nome_map.get(teams.get("home",{}).get("name","?"), teams.get("home",{}).get("name","?"))
                away_name = nome_map.get(teams.get("away",{}).get("name","?"), teams.get("away",{}).get("name","?"))
                marcatori = []
                for ev in events:
                    if ev.get("type") == "Goal":
                        nome   = ev.get("player",{}).get("name","?")
                        minuto = ev.get("time",{}).get("elapsed","?")
                        detail = ev.get("detail","")
                        marcatori.append(f"{nome} {minuto}'" + (" (R)" if detail=="Penalty" else " (aut.)" if detail=="Own Goal" else ""))
                ss      = status.get("short","FT")
                is_live = ss in ("1H","2H","HT","ET","P")
                if is_live:
                    has_live = True
                live_p.append({
                    "home": home_name, "away": away_name,
                    "gol_h": goals.get("home",0) or 0,
                    "gol_a": goals.get("away",0) or 0,
                    "status": ss, "minuto": status.get("elapsed"),
                    "live": is_live, "marcatori": marcatori,
                    "fixture_id": fixture.get("id"),
                    "data": fixture.get("date","")[:10],
                    "ora": _utc_to_rome(fixture.get("date","")),
                })
            LIVE_RESULTS_CACHE_ML[league_key] = live_p
            LIVE_IN_CORSO_ML[league_key]       = has_live
    except Exception as e:
        print(f"⚠️ Live {league_key}: {e}")

    print(f"✅ {league['name']}: dati aggiornati")


# ─────────────────────────────
# STATISTICHE SQUADRE PER CAMPIONATO
# ─────────────────────────────
def _fetch_team_stats_league(league_key):
    """Fetch statistiche squadre da API Football per un campionato."""
    from league_mappings import _TEAM_IDS, PL_TEAM_IDS, LL_TEAM_IDS, BL_TEAM_IDS, L1_TEAM_IDS

    def _get_team_ids_local(lk):
        if lk == "premier-league": return PL_TEAM_IDS
        if lk == "la-liga":        return LL_TEAM_IDS
        if lk == "bundesliga":     return BL_TEAM_IDS
        if lk == "ligue-1":        return L1_TEAM_IDS
        return _TEAM_IDS

    if league_key not in ["serie-a", "premier-league", "la-liga", "bundesliga", "ligue-1"]:
        return
    cached = TEAM_STATS_CACHE.get(league_key)
    if cached and time.time() - cached.get("timestamp", 0) < 3600:
        return cached.get("data")
    league_id = LEAGUES[league_key]["id"]
    season    = LEAGUES[league_key]["season"]
    team_ids  = _get_team_ids_local(league_key)
    stats = {}
    for team_name, team_id in team_ids.items():
        try:
            req = urllib.request.Request(
                f"https://{FOOTBALL_API_HOST}/teams/statistics?league={league_id}&season={season}&team={team_id}",
                headers={"x-apisports-key": FOOTBALL_API_KEY, "User-Agent": "Mozilla/5.0"}
            )
            with urllib.request.urlopen(req, timeout=10) as r:
                data = json.loads(r.read().decode())
            resp     = data.get("response", {})
            fixtures = resp.get("fixtures", {})
            goals    = resp.get("goals", {})
            stats[team_name] = {
                "giocate": fixtures.get("played", {}).get("total", 0) or 0,
                "vinte":   fixtures.get("wins",   {}).get("total", 0) or 0,
                "pareggi": fixtures.get("draws",  {}).get("total", 0) or 0,
                "perse":   fixtures.get("loses",  {}).get("total", 0) or 0,
                "gf": goals.get("for",     {}).get("total", {}).get("total", 0) or 0,
                "gs": goals.get("against", {}).get("total", {}).get("total", 0) or 0,
                "clean_sheet": resp.get("clean_sheet", {}).get("total", 0) or 0,
                "form": resp.get("form", "") or "",
            }
            time.sleep(1)
        except Exception as e:
            print(f"Stats {team_name}: {e}")
            continue
    if stats:
        TEAM_STATS_CACHE[league_key] = {"data": stats, "timestamp": time.time()}
    return stats


def _compute_best_stats(league_key):
    """Calcola le migliori statistiche per il campionato. Fallback su classifica."""
    cached = TEAM_STATS_CACHE.get(league_key)
    if cached and cached.get("data") and len(cached["data"]) >= 3:
        stats = cached["data"]
        try:
            best_attack  = max(stats.items(), key=lambda x: x[1].get("gf", 0))
            best_defense = min(stats.items(), key=lambda x: x[1].get("gs", 999))
            most_cs      = max(stats.items(), key=lambda x: x[1].get("clean_sheet", 0))
            def form_score(form_str):
                score = 0
                for c in (form_str or "")[-5:]:
                    if c == "W": score += 3
                    elif c == "D": score += 1
                return score
            best_form = max(stats.items(), key=lambda x: form_score(x[1].get("form", "")))
            best_wins = max(stats.items(), key=lambda x: x[1].get("vinte", 0))
            return {
                "miglior_attacco":  {"squadra": best_attack[0],  "gf": best_attack[1]["gf"],  "media": round(best_attack[1]["gf"] / max(best_attack[1].get("giocate", 1), 1), 2)},
                "miglior_difesa":   {"squadra": best_defense[0], "gs": best_defense[1]["gs"],  "clean_sheet": best_defense[1].get("clean_sheet", 0)},
                "piu_clean_sheet":  {"squadra": most_cs[0],      "clean_sheet": most_cs[1].get("clean_sheet", 0)},
                "miglior_forma":    {"squadra": best_form[0],    "form": (best_form[1].get("form","") or "")[-5:], "punti_forma": form_score(best_form[1].get("form",""))},
                "miglior_casa":     {"squadra": best_wins[0],    "vittorie": best_wins[1].get("vinte", 0)},
            }
        except Exception:
            _logger.warning("Eccezione silenziata", exc_info=True)

    cl = CLASSIFICA_CACHE.get(league_key)
    if not cl or len(cl) < 3:
        return None
    try:
        def _gf(s): return s.get("GF", 0) or 0
        def _gs(s): return s.get("GS", 999) or 999
        def _v(s):  return s.get("V", 0) or 0
        def _g(s):  return max(s.get("G", 1) or 1, 1)
        def _sq(s): return s.get("Squadra", "?")

        att  = max(cl, key=_gf)
        dif  = min(cl, key=_gs)
        best_ratio = min(cl, key=lambda s: (_gs(s) if _gs(s) < 999 else 0) / _g(s))
        wins = max(cl, key=_v)
        def _pts_ratio(s): return (_v(s) * 3 + (s.get("N", 0) or 0)) / _g(s)
        forma = max(cl, key=_pts_ratio)
        return {
            "miglior_attacco":  {"squadra": _sq(att),        "gf": _gf(att),        "media": round(_gf(att) / _g(att), 2)},
            "miglior_difesa":   {"squadra": _sq(dif),        "gs": _gs(dif) if _gs(dif) < 999 else 0, "clean_sheet": 0},
            "piu_clean_sheet":  {"squadra": _sq(best_ratio), "clean_sheet": 0},
            "miglior_forma":    {"squadra": _sq(forma),      "form": "",  "punti_forma": round(_pts_ratio(forma), 2)},
            "miglior_casa":     {"squadra": _sq(wins),       "vittorie": _v(wins)},
        }
    except Exception as e:
        print(f"Compute best stats fallback {league_key}: {e}")
        return None


# ─────────────────────────────
# MAIN UPDATER LOOP
# ─────────────────────────────
def _live_updater(verify_predictions_fn=None):
    """Thread che aggiorna i dati. 2 min durante partite live, 30 min altrimenti."""
    global _updater_count
    from league_mappings import PL_TEAM_IDS, BL_TEAM_IDS, L1_TEAM_IDS
    from scraping_service import _scrape_live_data, _scrape_notizie, _scrape_odds

    while True:
        _updater_count += 1
        try:
            _scrape_live_data()
            _scrape_notizie()
            _scrape_odds()
            _fetch_live_results()
            # Notifiche gol (importa telegram_service a runtime per evitare circolo)
            try:
                from telegram_service import check_and_notify_goals
                check_and_notify_goals(LIVE_RESULTS_CACHE, LIVE_IN_CORSO)
            except Exception:
                _logger.warning("Eccezione silenziata", exc_info=True)
            _fetch_classifica_live()
            _fetch_marcatori_live()
            _fetch_infortunati_live()
            # Verifica predizioni con risultati reali
            if LIVE_RESULTS_CACHE and verify_predictions_fn:
                try:
                    verify_predictions_fn(LIVE_RESULTS_CACHE)
                except Exception:
                    _logger.warning("Eccezione silenziata", exc_info=True)
            # Rose e storico ogni 6 cicli (~3 ore)
            if _updater_count % 6 == 0:
                _fetch_rose_live()
                _fetch_rose_live(PL_TEAM_IDS)
                _fetch_rose_live(BL_TEAM_IDS)
                _fetch_rose_live(L1_TEAM_IDS)
                _fetch_risultati_stagione()
                for flk in FANTACALCIO_LEAGUES:
                    try:
                        _fetch_player_stats(flk)
                        time.sleep(1)
                    except Exception:
                        _logger.warning("Eccezione silenziata", exc_info=True)
                try:
                    _fetch_worldcup_data()
                except Exception:
                    _logger.warning("Eccezione silenziata", exc_info=True)
            # League extra
            if _updater_count % 3 == 0 or any(LIVE_IN_CORSO_ML.get(k) for k in ["champions-league","europa-league","conference-league","bundesliga","ligue-1"]):
                for lk in ["premier-league","la-liga","champions-league","europa-league","conference-league","bundesliga","ligue-1"]:
                    try:
                        _fetch_league_data(lk)
                    except Exception:
                        _logger.warning("Eccezione silenziata", exc_info=True)
        except Exception:
            _logger.warning("Eccezione silenziata", exc_info=True)
        time.sleep(120 if LIVE_IN_CORSO else 1800)


def start_live_updater(verify_predictions_fn=None):
    """Avvia il thread di aggiornamento live."""
    t = threading.Thread(target=_live_updater, args=(verify_predictions_fn,), daemon=True)
    t.start()
    return t
