"""
routes/config.py - Endpoint GET /api/config
Ritorna team IDs, nome mapping e configurazione leghe per il frontend.
Permette di rimuovere tutti i dati hardcoded dall'HTML.
"""

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


@router.get("/api/config")
async def get_config():
    """
    Configurazione globale del frontend: team IDs, nome mapping, leghe.
    Nessuna autenticazione richiesta (dati pubblici).
    """
    leagues = [
        {
            "key": "serie-a",
            "nome": "Serie A",
            "bandiera": "IT",
            "colore": "#2ecc71",
            "logo": "https://media.api-sports.io/football/leagues/135.png",
            "teams": list(_TEAM_IDS.keys()),
            "team_ids": _TEAM_IDS,
            "nome_map": FOOTBALL_NOME_MAP,
        },
        {
            "key": "premier-league",
            "nome": "Premier League",
            "bandiera": "EN",
            "colore": "#3498db",
            "logo": "https://media.api-sports.io/football/leagues/39.png",
            "teams": list(PL_TEAM_IDS.keys()),
            "team_ids": PL_TEAM_IDS,
            "nome_map": PL_NOME_MAP,
        },
        {
            "key": "la-liga",
            "nome": "La Liga",
            "bandiera": "ES",
            "colore": "#e74c3c",
            "logo": "https://media.api-sports.io/football/leagues/140.png",
            "teams": list(LL_TEAM_IDS.keys()),
            "team_ids": LL_TEAM_IDS,
            "nome_map": LL_NOME_MAP,
        },
        {
            "key": "bundesliga",
            "nome": "Bundesliga",
            "bandiera": "DE",
            "colore": "#f39c12",
            "logo": "https://media.api-sports.io/football/leagues/78.png",
            "teams": list(BL_TEAM_IDS.keys()),
            "team_ids": BL_TEAM_IDS,
            "nome_map": BL_NOME_MAP,
        },
        {
            "key": "ligue-1",
            "nome": "Ligue 1",
            "bandiera": "FR",
            "colore": "#9b59b6",
            "logo": "https://media.api-sports.io/football/leagues/61.png",
            "teams": list(L1_TEAM_IDS.keys()),
            "team_ids": L1_TEAM_IDS,
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
        "serie_a_teams": list(_TEAM_IDS.keys()),
        "serie_a_team_ids": _TEAM_IDS,
    })
