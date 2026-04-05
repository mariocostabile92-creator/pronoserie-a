"""
api_football_stats.py
Scarica e cache statistiche squadre dalla API Football.
Usato dal predictor per migliorare le predizioni con dati reali.
"""

import json
import os
import time
import urllib.request
from datetime import datetime

API_KEY = "3f8ed68a9b1cb532479096f33bfbc568"
API_HOST = "v3.football.api-sports.io"
LEAGUE_ID = 135  # Serie A
SEASON = 2025

# Cache locale per non fare troppe chiamate API
_STATS_CACHE = {}
_CACHE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "api_stats_cache.json")
_CACHE_LOADED = False

# Mapping nomi API -> nostri nomi
NOME_MAP = {
    "FC Internazionale Milano": "Inter", "Inter Milan": "Inter", "Inter": "Inter",
    "AC Milan": "Milan", "Milan": "Milan",
    "SSC Napoli": "Napoli", "Napoli": "Napoli",
    "Como 1907": "Como", "Como": "Como",
    "Juventus FC": "Juventus", "Juventus": "Juventus",
    "AS Roma": "Roma", "Roma": "Roma",
    "Atalanta BC": "Atalanta", "Atalanta": "Atalanta",
    "SS Lazio": "Lazio", "Lazio": "Lazio",
    "Bologna FC 1909": "Bologna", "Bologna": "Bologna",
    "US Sassuolo Calcio": "Sassuolo", "Sassuolo": "Sassuolo",
    "Udinese Calcio": "Udinese", "Udinese": "Udinese",
    "Parma Calcio 1913": "Parma", "Parma": "Parma",
    "Genoa CFC": "Genoa", "Genoa": "Genoa",
    "Torino FC": "Torino", "Torino": "Torino",
    "Cagliari Calcio": "Cagliari", "Cagliari": "Cagliari",
    "ACF Fiorentina": "Fiorentina", "Fiorentina": "Fiorentina",
    "US Cremonese": "Cremonese", "Cremonese": "Cremonese",
    "US Lecce": "Lecce", "Lecce": "Lecce",
    "Hellas Verona FC": "Verona", "Hellas Verona": "Verona", "Verona": "Verona",
    "AC Pisa 1909": "Pisa", "Pisa": "Pisa",
}

# Mapping inverso nome -> team_id API Football
TEAM_IDS = {
    "Inter": 505, "Milan": 489, "Napoli": 492, "Como": 895,
    "Juventus": 496, "Roma": 497, "Atalanta": 499, "Lazio": 487,
    "Bologna": 500, "Sassuolo": 488, "Udinese": 494, "Parma": 523,
    "Genoa": 495, "Torino": 503, "Cagliari": 490, "Fiorentina": 502,
    "Cremonese": 520, "Lecce": 867, "Verona": 504, "Pisa": 801,
}


def _load_cache():
    """Carica la cache da file."""
    global _STATS_CACHE, _CACHE_LOADED
    if _CACHE_LOADED:
        return
    try:
        if os.path.exists(_CACHE_FILE):
            with open(_CACHE_FILE, "r") as f:
                data = json.load(f)
            # Controlla se la cache e' fresca (meno di 6 ore)
            ts = data.get("_timestamp", 0)
            if time.time() - ts < 21600:  # 6 ore
                _STATS_CACHE = data
                _CACHE_LOADED = True
                return
    except Exception:
        pass
    _CACHE_LOADED = True


def _save_cache():
    """Salva la cache su file."""
    try:
        _STATS_CACHE["_timestamp"] = time.time()
        with open(_CACHE_FILE, "w") as f:
            json.dump(_STATS_CACHE, f)
    except Exception:
        pass


def _api_request(endpoint):
    """Fa una richiesta all'API Football."""
    try:
        url = f"https://{API_HOST}/{endpoint}"
        req = urllib.request.Request(url, headers={
            "x-apisports-key": API_KEY,
            "User-Agent": "Mozilla/5.0"
        })
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        print(f"API Football error: {e}")
        return None


def get_team_real_stats(team_name: str, fetch_if_missing: bool = False) -> dict:
    """
    Ritorna le statistiche reali della squadra dalla API Football.
    Se fetch_if_missing=False (default), ritorna None se non in cache.
    """
    _load_cache()

    if team_name in _STATS_CACHE and team_name != "_timestamp":
        return _STATS_CACHE[team_name]

    if not fetch_if_missing:
        return None

    team_id = TEAM_IDS.get(team_name)
    if not team_id:
        return None

    data = _api_request(f"teams/statistics?league={LEAGUE_ID}&season={SEASON}&team={team_id}")
    if not data or not data.get("response"):
        return None

    resp = data["response"]
    fixtures = resp.get("fixtures", {})
    goals = resp.get("goals", {})
    clean_sheet = resp.get("clean_sheet", {})
    lineups = resp.get("lineups", [])

    # Gol fatti/subiti per partita casa e trasferta
    gf_home = goals.get("for", {}).get("average", {}).get("home", "0")
    gf_away = goals.get("for", {}).get("average", {}).get("away", "0")
    gs_home = goals.get("against", {}).get("average", {}).get("home", "0")
    gs_away = goals.get("against", {}).get("average", {}).get("away", "0")

    # Forma (ultimi 5: WWDLW)
    form = resp.get("form", "")

    # Clean sheet %
    cs_home = clean_sheet.get("home", 0) or 0
    cs_away = clean_sheet.get("away", 0) or 0
    cs_total = clean_sheet.get("total", 0) or 0

    # Partite giocate
    played_home = fixtures.get("played", {}).get("home", 0) or 0
    played_away = fixtures.get("played", {}).get("away", 0) or 0
    played_total = played_home + played_away

    # Vittorie
    wins_home = fixtures.get("wins", {}).get("home", 0) or 0
    wins_away = fixtures.get("wins", {}).get("away", 0) or 0
    draws_home = fixtures.get("draws", {}).get("home", 0) or 0
    draws_away = fixtures.get("draws", {}).get("away", 0) or 0

    stats = {
        "gf_home_pg": float(gf_home) if gf_home else 0,
        "gf_away_pg": float(gf_away) if gf_away else 0,
        "gs_home_pg": float(gs_home) if gs_home else 0,
        "gs_away_pg": float(gs_away) if gs_away else 0,
        "form": form[-5:] if form else "",
        "form_score": sum(3 if c == "W" else (1 if c == "D" else 0) for c in (form[-5:] if form else "")),
        "cs_total": cs_total,
        "cs_pct": round(cs_total / played_total * 100, 1) if played_total > 0 else 0,
        "win_home_pct": round(wins_home / played_home * 100, 1) if played_home > 0 else 0,
        "win_away_pct": round(wins_away / played_away * 100, 1) if played_away > 0 else 0,
        "played": played_total,
    }

    _STATS_CACHE[team_name] = stats
    _save_cache()
    return stats


def fetch_all_team_stats():
    """Scarica le statistiche di tutte le squadre (da chiamare periodicamente)."""
    print("Scaricamento statistiche API Football...")
    for team in TEAM_IDS:
        stats = get_team_real_stats(team)
        if stats:
            print(f"  {team}: GF casa={stats['gf_home_pg']}, GF trasf={stats['gf_away_pg']}, forma={stats['form']}")
        time.sleep(1)  # Rate limiting
    _save_cache()
    print(f"Statistiche salvate per {len(TEAM_IDS)} squadre")
