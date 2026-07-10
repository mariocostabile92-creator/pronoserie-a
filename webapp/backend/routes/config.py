"""
routes/config.py - Endpoint GET /api/config
Ritorna team IDs, nome mapping e configurazione leghe per il frontend.
Permette di rimuovere tutti i dati hardcoded dall'HTML.
"""

import json
import os
import time
import urllib.request

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from league_mappings import (
    PL_NOME_MAP, PL_TEAM_IDS,
    LL_NOME_MAP, LL_TEAM_IDS,
    BL_NOME_MAP, BL_TEAM_IDS,
    L1_NOME_MAP, L1_TEAM_IDS,
    WC_NOME_MAP, WC_TEAM_IDS,
    FOOTBALL_NOME_MAP,
    _TEAM_IDS,
)

router = APIRouter()

FOOTBALL_API_KEY = os.environ.get("FOOTBALL_API_KEY", "")
FOOTBALL_API_HOST = "v3.football.api-sports.io"
CONFIG_CACHE_TTL = 6 * 60 * 60
_LIVE_CONFIG_CACHE = {}

LEAGUE_SPECS = {
    "serie-a": (135, 2026),
    "premier-league": (39, 2026),
    "la-liga": (140, 2026),
    "bundesliga": (78, 2026),
    "ligue-1": (61, 2026),
}


def _live_or_fallback(key, fallback_ids, nome_map):
    fallback = (list(fallback_ids.keys()), dict(fallback_ids))
    if not FOOTBALL_API_KEY or key not in LEAGUE_SPECS:
        return fallback

    cached = _LIVE_CONFIG_CACHE.get(key)
    now = time.time()
    if cached and now - cached["t"] < CONFIG_CACHE_TTL:
        return cached["teams"], cached["team_ids"]

    league_id, season = LEAGUE_SPECS[key]
    try:
        req = urllib.request.Request(
            f"https://{FOOTBALL_API_HOST}/teams?league={league_id}&season={season}",
            headers={"x-apisports-key": FOOTBALL_API_KEY, "User-Agent": "Mozilla/5.0"},
        )
        with urllib.request.urlopen(req, timeout=12) as r:
            data = json.loads(r.read().decode())
        team_ids = {}
        for item in data.get("response", []):
            team = item.get("team", {})
            api_name = team.get("name", "")
            team_id = team.get("id")
            display_name = nome_map.get(api_name, api_name)
            if display_name and team_id:
                team_ids[display_name] = team_id
        if len(team_ids) >= 16:
            teams = list(team_ids.keys())
            _LIVE_CONFIG_CACHE[key] = {"t": now, "teams": teams, "team_ids": team_ids}
            return teams, team_ids
    except Exception:
        pass
    return fallback


@router.get("/api/config")
async def get_config():
    """
    Configurazione globale del frontend: team IDs, nome mapping, leghe.
    Nessuna autenticazione richiesta (dati pubblici).
    """
    serie_teams, serie_ids = _live_or_fallback("serie-a", _TEAM_IDS, FOOTBALL_NOME_MAP)
    pl_teams, pl_ids = _live_or_fallback("premier-league", PL_TEAM_IDS, PL_NOME_MAP)
    ll_teams, ll_ids = _live_or_fallback("la-liga", LL_TEAM_IDS, LL_NOME_MAP)
    bl_teams, bl_ids = _live_or_fallback("bundesliga", BL_TEAM_IDS, BL_NOME_MAP)
    l1_teams, l1_ids = _live_or_fallback("ligue-1", L1_TEAM_IDS, L1_NOME_MAP)

    leagues = [
        {
            "key": "serie-a",
            "nome": "Serie A",
            "bandiera": "IT",
            "colore": "#2ecc71",
            "logo": "https://media.api-sports.io/football/leagues/135.png",
            "teams": serie_teams,
            "team_ids": serie_ids,
            "nome_map": FOOTBALL_NOME_MAP,
        },
        {
            "key": "premier-league",
            "nome": "Premier League",
            "bandiera": "EN",
            "colore": "#3498db",
            "logo": "https://media.api-sports.io/football/leagues/39.png",
            "teams": pl_teams,
            "team_ids": pl_ids,
            "nome_map": PL_NOME_MAP,
        },
        {
            "key": "la-liga",
            "nome": "La Liga",
            "bandiera": "ES",
            "colore": "#e74c3c",
            "logo": "https://media.api-sports.io/football/leagues/140.png",
            "teams": ll_teams,
            "team_ids": ll_ids,
            "nome_map": LL_NOME_MAP,
        },
        {
            "key": "bundesliga",
            "nome": "Bundesliga",
            "bandiera": "DE",
            "colore": "#f39c12",
            "logo": "https://media.api-sports.io/football/leagues/78.png",
            "teams": bl_teams,
            "team_ids": bl_ids,
            "nome_map": BL_NOME_MAP,
        },
        {
            "key": "ligue-1",
            "nome": "Ligue 1",
            "bandiera": "FR",
            "colore": "#9b59b6",
            "logo": "https://media.api-sports.io/football/leagues/61.png",
            "teams": l1_teams,
            "team_ids": l1_ids,
            "nome_map": L1_NOME_MAP,
        },
        {
            "key": "champions-league",
            "nome": "Champions League",
            "bandiera": "EU",
            "colore": "#2ecc71",
            "logo": "https://media.api-sports.io/football/leagues/2.png",
            "teams": [],
            "team_ids": {},
            "nome_map": {},
        },
        {
            "key": "europa-league",
            "nome": "Europa League",
            "bandiera": "EU",
            "colore": "#f39c12",
            "logo": "https://media.api-sports.io/football/leagues/3.png",
            "teams": [],
            "team_ids": {},
            "nome_map": {},
        },
        {
            "key": "conference-league",
            "nome": "Conference League",
            "bandiera": "EU",
            "colore": "#3498db",
            "logo": "https://media.api-sports.io/football/leagues/848.png",
            "teams": [],
            "team_ids": {},
            "nome_map": {},
        },
        {
            "key": "mondiali-2026",
            "nome": "Mondiali 2026",
            "bandiera": "WC",
            "colore": "#FFD700",
            "logo": "https://media.api-sports.io/football/leagues/1.png",
            "teams": list(WC_TEAM_IDS.keys()),
            "team_ids": WC_TEAM_IDS,
            "nome_map": WC_NOME_MAP,
        },
    ]

    # Struttura compatta: team -> {league, id}
    all_teams = {}
    for lg in leagues:
        for team, tid in lg["team_ids"].items():
            all_teams[team] = {"league": lg["key"], "id": tid}

    return JSONResponse({
        "leagues": leagues,
        "all_teams": all_teams,
        "serie_a_teams": serie_teams,
        "serie_a_team_ids": serie_ids,
    })
