"""
api_server.py - VERSIONE FINALE STABILE
Compatibile con frontend PronoSerie A
Fix calendario + fallback + debug + Railway ready
"""

import sys
import os
import json

# PATH ROOT
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, _ROOT)

from typing import Optional
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse

# ─────────────────────────────
# IMPORT MOTORE (SAFE)
# ─────────────────────────────
try:
    from data_loader import load_all_data
    from stats_engine import get_team_stats
    from predictor import get_prediction
    from season_2526 import get_classifica_reale, get_calendario_rimanente
    from squads_2526 import get_marcatori
    MOTORE_DISPONIBILE = True
except Exception as e:
    print("❌ ERRORE IMPORT MOTORE:", e)
    MOTORE_DISPONIBILE = False

# ─────────────────────────────
# IMPORT BACKEND
# ─────────────────────────────
from database import init_db, log_api_call, count_daily_calls, get_user_by_email, create_user, save_prediction, verify_predictions, get_tracking_stats
from api_auth import get_optional_user, hash_password, verify_password, create_token
from api_payments import router as payments_router

# ─────────────────────────────
# APP
# ─────────────────────────────
app = FastAPI(title="MatchIQ API", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(payments_router)

# ─────────────────────────────
# GLOBAL + MULTI-LEAGUE CONFIG
# ─────────────────────────────
_df = None
_df_pl = None
_df_ll = None
_df_ucl = None
_df_uel = None
_df_uecl = None
_df_bl = None
LIMITE_FREE = 2

LEAGUES = {
    "serie-a": {"id": 135, "season": 2025, "name": "Serie A", "country": "Italy"},
    "premier-league": {"id": 39, "season": 2025, "name": "Premier League", "country": "England"},
    "la-liga": {"id": 140, "season": 2025, "name": "La Liga", "country": "Spain"},
    "champions-league": {"id": 2, "season": 2025, "name": "Champions League", "country": "Europe"},
    "europa-league": {"id": 3, "season": 2025, "name": "Europa League", "country": "Europe"},
    "conference-league": {"id": 848, "season": 2025, "name": "Conference League", "country": "Europe"},
    "bundesliga": {"id": 78, "season": 2025, "name": "Bundesliga", "country": "Germany"},
}

# Mapping nomi API Football -> nomi nostri (per ogni league)
PL_NOME_MAP = {
    "Manchester United": "Man United", "Manchester City": "Man City",
    "Newcastle United": "Newcastle", "Newcastle": "Newcastle",
    "AFC Bournemouth": "Bournemouth", "Bournemouth": "Bournemouth",
    "Wolverhampton Wanderers": "Wolves", "Wolves": "Wolves",
    "Nottingham Forest": "Nott. Forest",
    "Tottenham Hotspur": "Tottenham", "Tottenham": "Tottenham",
    "West Ham United": "West Ham", "West Ham": "West Ham",
    "Brighton and Hove Albion": "Brighton", "Brighton": "Brighton",
    "Crystal Palace": "Crystal Palace",
    "Arsenal": "Arsenal", "Liverpool": "Liverpool", "Chelsea": "Chelsea",
    "Aston Villa": "Aston Villa", "Fulham": "Fulham", "Everton": "Everton",
    "Brentford": "Brentford", "Burnley": "Burnley",
    "Leeds United": "Leeds", "Leeds": "Leeds",
    "Sunderland": "Sunderland",
}

PL_TEAM_IDS = {
    "Arsenal":42,"Aston Villa":66,"Bournemouth":35,"Brentford":55,"Brighton":51,
    "Burnley":44,"Chelsea":49,"Crystal Palace":52,"Everton":45,"Fulham":36,
    "Leeds":63,"Liverpool":40,"Man City":50,"Man United":33,"Newcastle":34,
    "Nott. Forest":65,"Sunderland":746,"Tottenham":47,"West Ham":48,"Wolves":39,
}

LL_NOME_MAP = {
    "FC Barcelona": "Barcelona", "Barcelona": "Barcelona",
    "Atletico Madrid": "Atletico Madrid", "Club Atletico de Madrid": "Atletico Madrid",
    "Athletic Club": "Athletic Club", "Athletic Bilbao": "Athletic Club",
    "Real Madrid": "Real Madrid",
    "Real Sociedad": "Real Sociedad",
    "Real Betis": "Real Betis",
    "Villarreal CF": "Villarreal", "Villarreal": "Villarreal",
    "Sevilla FC": "Sevilla", "Sevilla": "Sevilla",
    "Valencia CF": "Valencia", "Valencia": "Valencia",
    "RC Celta de Vigo": "Celta Vigo", "Celta Vigo": "Celta Vigo",
    "RCD Espanyol": "Espanyol", "Espanyol": "Espanyol",
    "Deportivo Alaves": "Alaves", "Alaves": "Alaves",
    "CA Osasuna": "Osasuna", "Osasuna": "Osasuna",
    "Getafe CF": "Getafe", "Getafe": "Getafe",
    "Girona FC": "Girona", "Girona": "Girona",
    "Rayo Vallecano": "Rayo Vallecano",
    "RCD Mallorca": "Mallorca", "Mallorca": "Mallorca",
    "Levante UD": "Levante", "Levante": "Levante",
    "Real Oviedo": "Oviedo", "Oviedo": "Oviedo",
    "Elche CF": "Elche", "Elche": "Elche",
}

LL_TEAM_IDS = {
    "Alaves":542,"Athletic Club":531,"Atletico Madrid":530,"Barcelona":529,
    "Celta Vigo":538,"Elche":797,"Espanyol":540,"Getafe":546,"Girona":547,
    "Levante":539,"Mallorca":798,"Osasuna":727,"Oviedo":718,
    "Rayo Vallecano":728,"Real Betis":543,"Real Madrid":541,
    "Real Sociedad":548,"Sevilla":536,"Valencia":532,"Villarreal":533,
}

BL_NOME_MAP = {
    "1. FC Heidenheim 1846": "Heidenheim", "1. FC Heidenheim": "Heidenheim",
    "1. FC Köln": "1. FC Koln", "FC Köln": "1. FC Koln",
    "1899 Hoffenheim": "Hoffenheim", "TSG Hoffenheim": "Hoffenheim",
    "Bayern München": "Bayern Munich", "FC Bayern München": "Bayern Munich",
    "Borussia Mönchengladbach": "Monchengladbach",
    "FC Augsburg": "Augsburg", "FC St. Pauli": "St Pauli",
    "FSV Mainz 05": "Mainz", "1. FSV Mainz 05": "Mainz",
    "SC Freiburg": "Freiburg", "VfB Stuttgart": "Stuttgart",
    "VfL Wolfsburg": "Wolfsburg",
    "Bayer Leverkusen": "Bayer Leverkusen", "Borussia Dortmund": "Borussia Dortmund",
    "Eintracht Frankfurt": "Eintracht Frankfurt", "RB Leipzig": "RB Leipzig",
    "Union Berlin": "Union Berlin", "Werder Bremen": "Werder Bremen",
    "Hamburger SV": "Hamburger SV",
}

BL_TEAM_IDS = {
    "Heidenheim":180,"1. FC Koln":192,"Hoffenheim":167,
    "Bayer Leverkusen":168,"Bayern Munich":157,"Borussia Dortmund":165,
    "Monchengladbach":163,"Eintracht Frankfurt":169,"Augsburg":170,
    "St Pauli":186,"Mainz":164,"Hamburger SV":175,"RB Leipzig":173,
    "Freiburg":160,"Union Berlin":182,"Stuttgart":172,"Wolfsburg":161,
    "Werder Bremen":162,
}

def _get_nome_map(league_key):
    if league_key == "premier-league":
        return PL_NOME_MAP
    if league_key == "la-liga":
        return LL_NOME_MAP
    if league_key == "bundesliga":
        return BL_NOME_MAP
    return FOOTBALL_NOME_MAP

def _get_team_ids(league_key):
    if league_key == "premier-league":
        return PL_TEAM_IDS
    if league_key == "la-liga":
        return LL_TEAM_IDS
    if league_key == "bundesliga":
        return BL_TEAM_IDS
    return _TEAM_IDS

def _map_team_name(name, league_key):
    nm = _get_nome_map(league_key)
    return nm.get(name, name)

# Cache multi-league
CLASSIFICA_CACHE = {"serie-a": None, "premier-league": None, "la-liga": None, "champions-league": None, "europa-league": None, "conference-league": None, "bundesliga": None}
CLASSIFICA_LAST_UPDATE = {"serie-a": "", "premier-league": "", "la-liga": "", "champions-league": "", "europa-league": "", "conference-league": "", "bundesliga": ""}
MARCATORI_CACHE = {"serie-a": None, "premier-league": None, "la-liga": None, "champions-league": None, "europa-league": None, "conference-league": None, "bundesliga": None}
LIVE_RESULTS_CACHE_ML = {"serie-a": None, "premier-league": None, "la-liga": None, "champions-league": None, "europa-league": None, "conference-league": None, "bundesliga": None}
RISULTATI_STAGIONE_CACHE_ML = {"serie-a": None, "premier-league": None, "la-liga": None, "champions-league": None, "europa-league": None, "conference-league": None, "bundesliga": None}
LIVE_IN_CORSO_ML = {"serie-a": False, "premier-league": False, "la-liga": False, "champions-league": False, "europa-league": False, "conference-league": False, "bundesliga": False}

# Dati live (aggiornati automaticamente)
import threading, time, urllib.request, re as regex_module
from datetime import datetime, timezone, timedelta
LIVE_FORMAZIONI = {}
LIVE_INFORTUNATI = {}
LIVE_LAST_UPDATE = ""

def _utc_to_rome(utc_str):
    """Converte orario UTC dall'API in ora italiana (CET/CEST)."""
    try:
        if not utc_str or len(utc_str) < 16:
            return ""
        h = int(utc_str[11:13])
        m = utc_str[14:16]
        # Italia = UTC+2 (CEST, estate) o UTC+1 (CET, inverno)
        # Da fine marzo a fine ottobre = +2
        h_it = (h + 2) % 24
        return f"{h_it:02d}:{m}"
    except Exception:
        return utc_str[11:16] if len(utc_str) > 15 else ""

def _scrape_live_data():
    """Scarica formazioni e infortunati aggiornati dal web."""
    global LIVE_FORMAZIONI, LIVE_INFORTUNATI, LIVE_LAST_UPDATE
    try:
        # Fonte: fantacalcio.it probabili formazioni
        req = urllib.request.Request(
            "https://www.fantacalcio.it/probabili-formazioni-serie-a",
            headers={"User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            html = r.read().decode("utf-8", errors="replace")

        if len(html) > 1000:
            LIVE_LAST_UPDATE = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M")
            print(f"🔄 Dati live scaricati: {len(html)} bytes ({LIVE_LAST_UPDATE})")
    except Exception as e:
        print(f"⚠️ Scrape formazioni fallito: {e}")

    try:
        # Fonte: fantacalciopedia infortunati
        req = urllib.request.Request(
            "https://www.fantacalciopedia.com/articoli-fcp/consigli-fantacalcio/75-lista-infortunati-serie-a-aggiornata.html",
            headers={"User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            html = r.read().decode("utf-8", errors="replace")

        if len(html) > 1000:
            print(f"🔄 Infortunati scaricati: {len(html)} bytes")
    except Exception as e:
        print(f"⚠️ Scrape infortunati fallito: {e}")

# ─────────────────────────────
# NOTIFICHE GOL TELEGRAM (per utenti Pro)
# ─────────────────────────────
TELEGRAM_BOT_TOKEN = "8664256029:AAH2dTkgm5Ca8WnwnNurYWW1LfWhoYVna5Q"
_NOTIFIED_GOALS = set()  # Set di gol gia' notificati: "fixture_id_minuto_giocatore"
_BOT_DB_PATH = os.path.join(_ROOT, "bot_utenti.db")

def _get_pro_chat_ids():
    """Recupera tutti gli chat_id degli utenti Pro dal database del bot."""
    import sqlite3
    try:
        if not os.path.exists(_BOT_DB_PATH):
            return []
        conn = sqlite3.connect(_BOT_DB_PATH)
        rows = conn.execute("SELECT chat_id FROM utenti WHERE piano = 'pro'").fetchall()
        conn.close()
        return [r[0] for r in rows]
    except Exception:
        return []

def _send_telegram_message(chat_id, text):
    """Invia un messaggio Telegram a un chat_id."""
    try:
        import urllib.parse
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = urllib.parse.urlencode({
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_notification": False,
        }).encode()
        req = urllib.request.Request(url, data=data)
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print(f"Errore invio Telegram a {chat_id}: {e}")

def _check_and_notify_goals():
    """Controlla se ci sono nuovi gol e invia notifiche agli utenti Pro."""
    global _NOTIFIED_GOALS
    if not LIVE_RESULTS_CACHE or not LIVE_IN_CORSO:
        return

    pro_ids = _get_pro_chat_ids()
    if not pro_ids:
        return

    for p in LIVE_RESULTS_CACHE:
        if not p.get("live"):
            continue

        fixture_id = p.get("fixture_id", 0)
        home = p["home"]
        away = p["away"]
        marcatori_home = p.get("marcatori_home", [])
        marcatori_away = p.get("marcatori_away", [])
        rossi_home = p.get("rossi_home", [])
        rossi_away = p.get("rossi_away", [])
        gol_h = p["gol_h"]
        gol_a = p["gol_a"]
        minuto = p.get("minuto", "")

        # Controlla gol casa
        for m in marcatori_home:
            goal_key = f"{fixture_id}_{m}"
            if goal_key not in _NOTIFIED_GOALS:
                _NOTIFIED_GOALS.add(goal_key)
                msg = (
                    f"&#9917; <b>GOOOL!</b>\n\n"
                    f"<b>{home} {gol_h} - {gol_a} {away}</b>\n"
                    f"&#9917; {m} ({home})\n"
                    f"&#9201; {minuto}'"
                )
                for cid in pro_ids:
                    threading.Thread(target=_send_telegram_message, args=(cid, msg), daemon=True).start()
                print(f"&#9917; NOTIFICA GOL: {home} - {m}")

        # Controlla gol ospite
        for m in marcatori_away:
            goal_key = f"{fixture_id}_{m}"
            if goal_key not in _NOTIFIED_GOALS:
                _NOTIFIED_GOALS.add(goal_key)
                msg = (
                    f"&#9917; <b>GOOOL!</b>\n\n"
                    f"<b>{home} {gol_h} - {gol_a} {away}</b>\n"
                    f"&#9917; {m} ({away})\n"
                    f"&#9201; {minuto}'"
                )
                for cid in pro_ids:
                    threading.Thread(target=_send_telegram_message, args=(cid, msg), daemon=True).start()
                print(f"&#9917; NOTIFICA GOL: {away} - {m}")

        # Controlla cartellini rossi
        for r in rossi_home:
            red_key = f"{fixture_id}_red_{r}"
            if red_key not in _NOTIFIED_GOALS:
                _NOTIFIED_GOALS.add(red_key)
                msg = (
                    f"&#128308; <b>ESPULSIONE!</b>\n\n"
                    f"<b>{home} {gol_h} - {gol_a} {away}</b>\n"
                    f"&#128308; {r} ({home})\n"
                    f"&#9201; {minuto}'"
                )
                for cid in pro_ids:
                    threading.Thread(target=_send_telegram_message, args=(cid, msg), daemon=True).start()

        for r in rossi_away:
            red_key = f"{fixture_id}_red_{r}"
            if red_key not in _NOTIFIED_GOALS:
                _NOTIFIED_GOALS.add(red_key)
                msg = (
                    f"&#128308; <b>ESPULSIONE!</b>\n\n"
                    f"<b>{home} {gol_h} - {gol_a} {away}</b>\n"
                    f"&#128308; {r} ({away})\n"
                    f"&#9201; {minuto}'"
                )
                for cid in pro_ids:
                    threading.Thread(target=_send_telegram_message, args=(cid, msg), daemon=True).start()

    # Pulisci gol vecchi (partite non piu' live)
    live_fixture_ids = {str(p.get("fixture_id", 0)) for p in LIVE_RESULTS_CACHE if p.get("live")}
    _NOTIFIED_GOALS = {g for g in _NOTIFIED_GOALS if any(g.startswith(fid) for fid in live_fixture_ids)} if live_fixture_ids else set()

_updater_count = 0

def _live_updater():
    """Thread che aggiorna i dati. 2 min durante partite live, 30 min altrimenti."""
    global _updater_count
    while True:
        _updater_count += 1
        try:
            _scrape_live_data()
            _scrape_notizie()
            _scrape_odds()
            _fetch_live_results()
            _check_and_notify_goals()
            _fetch_classifica_live()
            _fetch_marcatori_live()
            _fetch_infortunati_live()
            # Verifica predizioni con risultati reali
            if LIVE_RESULTS_CACHE:
                verify_predictions(LIVE_RESULTS_CACHE)
            # Rose e storico ogni 6 cicli (~3 ore)
            if _updater_count % 6 == 0:
                _fetch_rose_live()
                _fetch_rose_live(PL_TEAM_IDS)
                _fetch_risultati_stagione()
            # Competizioni europee: aggiorna ogni ciclo se partite in corso, altrimenti ogni 3 cicli
            if _updater_count % 3 == 0 or any(LIVE_IN_CORSO_ML.get(k) for k in ["champions-league","europa-league","conference-league"]):
                _fetch_league_data("premier-league")
                _fetch_league_data("la-liga")
                _fetch_league_data("champions-league")
                _fetch_league_data("europa-league")
                _fetch_league_data("conference-league")
                _fetch_league_data("bundesliga")
        except Exception:
            pass
        if LIVE_IN_CORSO:
            time.sleep(120)
        else:
            time.sleep(1800)

# ─────────────────────────────
# STARTUP
# ─────────────────────────────
@app.on_event("startup")
async def startup():
    global _df, _df_pl, _df_ll, _df_ucl, _df_uel, _df_uecl, _df_bl

    print("\n🚀 AVVIO SERVER MATCHIQ\n")

    # DB
    try:
        init_db()
        print("✅ DATABASE OK")
    except Exception as e:
        print("⚠️ DATABASE:", e)

    # DATI CSV (opzionali - il server funziona anche senza)
    if MOTORE_DISPONIBILE:
        try:
            _df = load_all_data()
            print(f"✅ DATI SERIE A: {len(_df)} partite")
        except Exception as e:
            print(f"⚠️ DATI SERIE A NON DISPONIBILI: {e}")
            _df = None
        # Carica anche Premier League
        try:
            _df_pl = load_all_data(league="E0")
            print(f"✅ DATI PREMIER LEAGUE: {len(_df_pl)} partite")
        except Exception as e:
            print(f"⚠️ DATI PL NON DISPONIBILI: {e}")
            _df_pl = None
        # Carica La Liga
        try:
            _df_ll = load_all_data(league="SP1")
            print(f"✅ DATI LA LIGA: {len(_df_ll)} partite")
        except Exception as e:
            print(f"⚠️ DATI LA LIGA NON DISPONIBILI: {e}")
            _df_ll = None
        # Carica Champions League
        try:
            _df_ucl = load_all_data(league="UCL")
            print(f"✅ DATI CHAMPIONS LEAGUE: {len(_df_ucl)} partite")
        except Exception as e:
            print(f"⚠️ DATI UCL NON DISPONIBILI: {e}")
            _df_ucl = None
        # Carica Europa League
        try:
            _df_uel = load_all_data(league="UEL")
            print(f"✅ DATI EUROPA LEAGUE: {len(_df_uel)} partite")
        except Exception as e:
            print(f"⚠️ DATI UEL NON DISPONIBILI: {e}")
            _df_uel = None
        # Carica Conference League
        try:
            _df_uecl = load_all_data(league="UECL")
            print(f"✅ DATI CONFERENCE LEAGUE: {len(_df_uecl)} partite")
        except Exception as e:
            print(f"⚠️ DATI UECL NON DISPONIBILI: {e}")
            _df_uecl = None
        # Carica Bundesliga
        try:
            _df_bl = load_all_data(league="D1")
            print(f"✅ DATI BUNDESLIGA: {len(_df_bl)} partite")
        except Exception as e:
            print(f"⚠️ DATI BL NON DISPONIBILI: {e}")
            _df_bl = None
    else:
        print("⚠️ MOTORE NON DISPONIBILE - il server usa dati hardcoded")

    # AVVIA AGGIORNAMENTO LIVE (ritardato per non sovraccaricare lo startup)
    def _delayed_start():
        time.sleep(15)
        try:
            _fetch_live_results()
        except Exception:
            pass
        try:
            _fetch_classifica_live()
        except Exception:
            pass
        try:
            _fetch_marcatori_live()
        except Exception:
            pass
        try:
            _fetch_infortunati_live()
        except Exception:
            pass
        print("✅ PRIMO FETCH COMPLETATO")
        # Rose, storico stagione caricati dopo
        try:
            _fetch_risultati_stagione()
        except Exception:
            pass
        try:
            _fetch_rose_live()
        except Exception:
            pass
        try:
            _fetch_rose_live(PL_TEAM_IDS)
        except Exception:
            pass
        # Premier League + La Liga
        try:
            _fetch_league_data("premier-league")
        except Exception:
            pass
        try:
            _fetch_league_data("la-liga")
        except Exception:
            pass
        try:
            _fetch_league_data("champions-league")
        except Exception:
            pass
        try:
            _fetch_league_data("europa-league")
        except Exception:
            pass
        try:
            _fetch_league_data("conference-league")
        except Exception:
            pass
        try:
            _fetch_league_data("bundesliga")
        except Exception:
            pass
    t = threading.Thread(target=_live_updater, daemon=True)
    t.start()
    threading.Thread(target=_delayed_start, daemon=True).start()
    print("✅ SERVER PRONTO\n")

    # Avvia Bot Telegram in background
    def _start_telegram_bot():
        try:
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            # Import bot components
            sys.path.insert(0, _ROOT)
            from telegram import Update
            from telegram.ext import Application, CommandHandler, CallbackQueryHandler
            from telegram_bot import (
                cmd_start, cmd_help, cmd_pronostico, cmd_giornata,
                cmd_classifica, cmd_pro, callback_handler, init_bot_db,
                invio_giornaliero
            )
            from telegram_bot import DF as _bot_df
            import telegram_bot

            # Init DB bot
            init_bot_db()

            # Passa i dati al bot
            if _df is not None:
                telegram_bot.DF = _df
            elif _df_pl is not None:
                telegram_bot.DF = _df_pl

            # Crea app bot
            bot_app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
            bot_app.add_handler(CommandHandler("start", cmd_start))
            bot_app.add_handler(CommandHandler("help", cmd_help))
            bot_app.add_handler(CommandHandler("pronostico", cmd_pronostico))
            bot_app.add_handler(CommandHandler("giornata", cmd_giornata))
            bot_app.add_handler(CommandHandler("classifica", cmd_classifica))
            bot_app.add_handler(CommandHandler("pro", cmd_pro))
            bot_app.add_handler(CallbackQueryHandler(callback_handler))

            print("🤖 BOT TELEGRAM ATTIVO!")
            bot_app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)
        except Exception as e:
            print(f"⚠️ Bot Telegram non avviato: {e}")

    threading.Thread(target=_start_telegram_bot, daemon=True).start()

# ─────────────────────────────
# FRONTEND
# ─────────────────────────────
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")

@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse("/app")

@app.get("/logo.png", include_in_schema=False)
async def serve_logo():
    return FileResponse(os.path.join(FRONTEND_DIR, "logo.png"), media_type="image/png")

@app.get("/manifest.json", include_in_schema=False)
async def serve_manifest():
    return FileResponse(os.path.join(FRONTEND_DIR, "manifest.json"), media_type="application/json")

@app.get("/sw.js", include_in_schema=False)
async def serve_sw():
    return FileResponse(os.path.join(FRONTEND_DIR, "sw.js"), media_type="application/javascript")

@app.get("/app", include_in_schema=False)
@app.get("/app/{path:path}", include_in_schema=False)
async def serve_app(path: str = ""):
    from fastapi.responses import HTMLResponse
    with open(os.path.join(FRONTEND_DIR, "index.html"), "r", encoding="utf-8") as f:
        content = f.read()
    return HTMLResponse(content, headers={"Cache-Control": "no-cache, no-store, must-revalidate", "Pragma": "no-cache"})

# ─────────────────────────────
# UTILS
# ─────────────────────────────
def check_limit(user):
    if not user or user.get("piano") == "pro":
        return

    calls = count_daily_calls(user["id"])

    if calls >= LIMITE_FREE:
        raise HTTPException(429, "Limite giornaliero raggiunto")

    log_api_call(user["id"], "pronostico")

# ─────────────────────────────
# QUOTE BOOKMAKER LIVE (the-odds-api.com)
# ─────────────────────────────
ODDS_API_KEY = "6003dadbc1da344808124a37f63f316a"
ODDS_CACHE = {}  # {"Inter_vs_Roma": {"prob_1": 55, "prob_x": 25, "prob_2": 20}, ...}
ODDS_LAST_UPDATE = ""

def _scrape_odds():
    """Scarica quote live Serie A dai bookmaker."""
    global ODDS_CACHE, ODDS_LAST_UPDATE
    try:
        url = f"https://api.the-odds-api.com/v4/sports/soccer_italy_serie_a/odds/?apiKey={ODDS_API_KEY}&regions=eu&markets=h2h,totals&oddsFormat=decimal"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode())

        # Mappa nomi squadre API -> nostri nomi
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
            "US Sassuolo": "Sassuolo", "Sassuolo": "Sassuolo",
            "Udinese Calcio": "Udinese", "Udinese": "Udinese",
            "Parma Calcio 1913": "Parma", "Parma": "Parma",
            "Genoa CFC": "Genoa", "Genoa": "Genoa",
            "Torino FC": "Torino", "Torino": "Torino",
            "Cagliari Calcio": "Cagliari", "Cagliari": "Cagliari",
            "ACF Fiorentina": "Fiorentina", "Fiorentina": "Fiorentina",
            "US Cremonese": "Cremonese", "Cremonese": "Cremonese",
            "US Lecce": "Lecce", "Lecce": "Lecce",
            "Hellas Verona FC": "Verona", "Verona": "Verona",
            "AC Pisa 1909": "Pisa", "Pisa": "Pisa",
        }

        new_cache = {}
        for match in data:
            home_api = match.get("home_team", "")
            away_api = match.get("away_team", "")
            home = NOME_MAP.get(home_api, home_api)
            away = NOME_MAP.get(away_api, away_api)

            # Prendi le quote medie di tutti i bookmaker
            quotes_1 = []
            quotes_x = []
            quotes_2 = []
            quotes_over = []
            quotes_under = []
            for bk in match.get("bookmakers", []):
                for market in bk.get("markets", []):
                    if market.get("key") == "h2h":
                        for outcome in market.get("outcomes", []):
                            nome_out = NOME_MAP.get(outcome["name"], outcome["name"])
                            if nome_out == home:
                                quotes_1.append(outcome["price"])
                            elif nome_out == away:
                                quotes_2.append(outcome["price"])
                            elif outcome["name"] == "Draw":
                                quotes_x.append(outcome["price"])
                    elif market.get("key") == "totals":
                        for outcome in market.get("outcomes", []):
                            if outcome.get("name") == "Over" and outcome.get("point", 0) == 2.5:
                                quotes_over.append(outcome["price"])
                            elif outcome.get("name") == "Under" and outcome.get("point", 0) == 2.5:
                                quotes_under.append(outcome["price"])

            if quotes_1 and quotes_x and quotes_2:
                avg_1 = sum(quotes_1) / len(quotes_1)
                avg_x = sum(quotes_x) / len(quotes_x)
                avg_2 = sum(quotes_2) / len(quotes_2)
                p1 = 1 / avg_1
                px = 1 / avg_x
                p2 = 1 / avg_2
                tot = p1 + px + p2
                key = f"{home}_vs_{away}"
                entry = {
                    "prob_1": round(p1 / tot * 100, 1),
                    "prob_x": round(px / tot * 100, 1),
                    "prob_2": round(p2 / tot * 100, 1),
                    "quota_1": round(avg_1, 2),
                    "quota_x": round(avg_x, 2),
                    "quota_2": round(avg_2, 2),
                    "n_bookmakers": len(quotes_1),
                }
                # Over/Under bookmaker
                if quotes_over and quotes_under:
                    avg_ov = sum(quotes_over) / len(quotes_over)
                    avg_un = sum(quotes_under) / len(quotes_under)
                    p_ov = 1 / avg_ov
                    p_un = 1 / avg_un
                    tot_ou = p_ov + p_un
                    entry["bk_over_25"] = round(p_ov / tot_ou * 100, 1)
                    entry["bk_under_25"] = round(p_un / tot_ou * 100, 1)
                new_cache[key] = entry

        if new_cache:
            ODDS_CACHE = new_cache
            ODDS_LAST_UPDATE = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M")
            print(f"📊 Quote bookmaker: {len(ODDS_CACHE)} partite da {len(data)} match")
    except Exception as e:
        print(f"⚠️ Scrape quote fallito: {e}")

def get_bookmaker_odds(home, away):
    """Ritorna le probabilita' bookmaker per una partita."""
    key = f"{home}_vs_{away}"
    return ODDS_CACHE.get(key)

def _filtra_marcatori(marcatori, infortunati):
    """Rimuove i giocatori infortunati dalla lista marcatori."""
    if not infortunati:
        return marcatori
    nomi_inj = set()
    for inj in infortunati:
        nome = inj.get("nome", "").lower()
        # Aggiungi cognome
        parts = nome.split()
        for p in parts:
            if len(p) > 3:
                nomi_inj.add(p)
    filtrati = []
    for m in marcatori:
        m_lower = m.lower()
        escluso = False
        for ni in nomi_inj:
            if ni in m_lower:
                escluso = True
                break
        if not escluso:
            filtrati.append(m)
    return filtrati

def _filtra_esatti(scores, ov25, suggerimento="1"):
    """Filtra risultati esatti coerenti con 1X2 e Over/Under, mantenendo ordine per probabilita'."""
    def get_segno(score):
        parts = score.split("-")
        h, a = int(parts[0]), int(parts[1])
        if h > a: return "1"
        elif h == a: return "X"
        else: return "2"

    def get_totale(score):
        parts = score.split("-")
        return int(parts[0]) + int(parts[1])

    # Filtra per coerenza con il suggerimento 1X2
    coerenti = [s for s in scores if get_segno(s["score"]) == suggerimento]
    altri = [s for s in scores if get_segno(s["score"]) != suggerimento]

    # Filtra per coerenza Over/Under (senza cambiare l'ordine di probabilita')
    if ov25 > 0.50:
        # Over: prendi solo risultati con 3+ gol totali, ordinati per probabilita'
        coerenti_ou = [s for s in coerenti if get_totale(s["score"]) >= 3]
        # Se non ci sono abbastanza, aggiungi anche quelli con 2 gol
        if len(coerenti_ou) < 3:
            coerenti_ou += [s for s in coerenti if get_totale(s["score"]) == 2]
    else:
        # Under: prendi solo risultati con max 2 gol totali, ordinati per probabilita'
        coerenti_ou = [s for s in coerenti if get_totale(s["score"]) <= 2]
        if len(coerenti_ou) < 3:
            coerenti_ou += [s for s in coerenti if get_totale(s["score"]) == 3]

    # Escludi risultati irrealistici (max 4 gol per squadra)
    coerenti_ou = [s for s in coerenti_ou if all(int(x) <= 4 for x in s["score"].split("-"))]

    # Top 3 coerenti + top 2 altri (per probabilita')
    result = coerenti_ou[:3] + altri[:2]
    return result[:5]

def genera_pronostico(home, away):
    if MOTORE_DISPONIBILE and _df is not None:
        try:
            hs = get_team_stats(_df, home, opponent=away)
            aw = get_team_stats(_df, away, opponent=home)
            return get_prediction(hs, aw, df=_df)
        except Exception as e:
            print(f"❌ ERRORE PREDICTOR: {e}")

    # Calcolo Poisson AVANZATO
    from scipy.stats import poisson as pdist
    try:
        from api_football_stats import get_team_real_stats
    except ImportError:
        get_team_real_stats = lambda x: None

    # Carica statistiche pre-calcolate dai CSV
    _stats_path = os.path.join(os.path.dirname(__file__), "team_stats.json")
    _h2h_path = os.path.join(os.path.dirname(__file__), "h2h_stats.json")
    _avg_path = os.path.join(os.path.dirname(__file__), "league_averages.json")

    try:
        with open(_stats_path) as f: TEAM_STATS = json.loads(f.read())
        with open(_h2h_path) as f: H2H_DATA = json.loads(f.read())
        with open(_avg_path) as f: LEAGUE_AVG = json.loads(f.read())
    except Exception:
        TEAM_STATS = {}
        H2H_DATA = {}
        LEAGUE_AVG = {"media_gol_casa": 1.5, "media_gol_trasferta": 1.17}

    h = home.strip().title()
    a = away.strip().title()
    sh = TEAM_STATS.get(h, {})
    sa = TEAM_STATS.get(a, {})

    # ── USA STATS REALI API FOOTBALL (Serie A + Premier League) ──
    api_h = get_team_real_stats(h)
    api_a = get_team_real_stats(a)
    has_api = api_h and api_a and api_h.get("played", 0) >= 10 and api_a.get("played", 0) >= 10

    # ── SE NON HA API STATS, COSTRUISCI DA CLASSIFICA LIVE ──
    if not has_api:
        # Cerca nella classifica live (funziona per PL e Serie A)
        found = False
        for league_key in ["serie-a", "premier-league", "la-liga", "champions-league", "europa-league", "conference-league"]:
            cl = CLASSIFICA_CACHE.get(league_key) or []
            # Se cache vuota, prova a caricarla ora
            if not cl and league_key != "serie-a":
                try:
                    _fetch_league_data(league_key)
                    cl = CLASSIFICA_CACHE.get(league_key) or []
                except Exception:
                    pass
            data_h = next((r for r in cl if r["Squadra"] == h), None)
            data_a = next((r for r in cl if r["Squadra"] == a), None)
            if data_h and data_a:
                # Costruisci lambda dalla classifica reale
                g_h = max(1, data_h["G"])
                g_a = max(1, data_a["G"])
                gf_h = data_h["GF"] / g_h  # Gol fatti per partita
                gs_h = data_h["GS"] / g_h  # Gol subiti per partita
                gf_a = data_a["GF"] / g_a
                gs_a = data_a["GS"] / g_a
                # Media campionato
                avg_gf = sum(r["GF"] for r in cl) / sum(max(1, r["G"]) for r in cl)
                avg_gs = sum(r["GS"] for r in cl) / sum(max(1, r["G"]) for r in cl)
                # Forza attacco/difesa relativa
                att_h = gf_h / max(0.3, avg_gf)
                dif_h = gs_h / max(0.3, avg_gs)
                att_a = gf_a / max(0.3, avg_gf)
                dif_a = gs_a / max(0.3, avg_gs)
                # Lambda: attacco casa * difesa trasferta * media
                avg_gc = sum(r["GF"] for r in cl) / (sum(max(1, r["G"]) for r in cl) / 2)
                lh = att_h * dif_a * 1.45  # Bonus casa
                la = att_a * dif_h * 1.10
                # Correzione classifica
                pts_h = data_h["Punti"]
                pts_a = data_a["Punti"]
                pts_diff = (pts_h - pts_a) / 100
                lh *= (1 + pts_diff * 0.3)
                la *= (1 - pts_diff * 0.3)
                # Forma (ultime partite dal rapporto V/G)
                form_h = data_h["V"] / g_h
                form_a = data_a["V"] / g_a
                form_diff = form_h - form_a
                lh *= (1 + form_diff * 0.2)
                la *= (1 - form_diff * 0.2)
                # Clamp
                lh = max(0.4, min(lh, 3.0))
                la = max(0.3, min(la, 2.2))
                # Poisson + Dixon-Coles
                p1 = px = p2 = 0.0
                for i in range(11):
                    for j in range(11):
                        p = pdist.pmf(i, lh) * pdist.pmf(j, la)
                        rho = -0.10
                        if i==0 and j==0: p *= (1 - lh*la*rho)
                        elif i==1 and j==0: p *= (1 + la*rho)
                        elif i==0 and j==1: p *= (1 + lh*rho)
                        elif i==1 and j==1: p *= (1 - rho)
                        p = max(0, p)
                        if i > j: p1 += p
                        elif i == j: px += p
                        else: p2 += p
                px *= 1.10  # Draw boost leggero
                ratio = min(lh,la)/max(lh,la) if max(lh,la)>0 else 0
                if ratio > 0.85: px *= 1 + (ratio-0.85)*0.5
                tot = p1 + px + p2
                if tot > 0: p1/=tot; px/=tot; p2/=tot
                # Blend con bookmaker live se disponibili
                bk_odds = get_bookmaker_odds(h, a)
                if bk_odds:
                    bp1 = bk_odds["prob_1"]/100; bpx = bk_odds["prob_x"]/100; bp2 = bk_odds["prob_2"]/100
                    p1 = 0.60*p1 + 0.40*bp1; px = 0.60*px + 0.40*bpx; p2 = 0.60*p2 + 0.40*bp2
                    tot = p1+px+p2
                    if tot>0: p1/=tot; px/=tot; p2/=tot
                ov25 = sum(pdist.pmf(i,lh)*pdist.pmf(j,la) for i in range(11) for j in range(11) if i+j>2.5)
                gsi = sum(pdist.pmf(i,lh)*pdist.pmf(j,la) for i in range(1,11) for j in range(1,11))
                # Calibrazione Goal: boost solo se entrambi lambda >= 0.8
                ga = lh + la
                lm = min(lh, la)
                if ga > 3.0 and lm >= 0.8: gsi = max(gsi, 0.55 + (ga-3.0)*0.04); gsi = min(gsi, 0.80)
                elif ga > 2.5 and lm >= 0.7: gsi = max(gsi, 0.50 + (ga-2.5)*0.04)
                scores = sorted([{"score":f"{i}-{j}","prob":round(pdist.pmf(i,lh)*pdist.pmf(j,la)*100,1)} for i in range(5) for j in range(5)], key=lambda x:-x["prob"])
                mp = max(p1, px, p2)
                sg = "1" if mp==p1 else ("X" if mp==px else "2")
                sl = "Vittoria Casa" if sg=="1" else ("Pareggio" if sg=="X" else "Vittoria Ospite")
                sp = sorted([p1,px,p2], reverse=True)
                spread = sp[0] - sp[1]
                cf = min(1.0, 0.40*(min(spread/0.35,1.0)) + 0.30*(min(g_h/30,1.0)) + 0.30*(min(abs(pts_diff)*3,1.0)))
                cl_label = "Alta" if cf>=0.82 else ("Media" if cf>=0.50 else "Bassa")
                sicura = cf >= 0.82 and sp[0] > 0.45
                return {
                    "prob_1":round(p1*100,1),"prob_x":round(px*100,1),"prob_2":round(p2*100,1),
                    "quota_1":round(1.05/p1,2) if p1>0 else 99,"quota_x":round(1.05/px,2) if px>0 else 99,"quota_2":round(1.05/p2,2) if p2>0 else 99,
                    "suggerimento":sg,"sugg_label":sl,"confidence":round(cf,3),"confidence_label":cl_label,
                    "sicura":bool(sicura),
                    "over_25":round(ov25*100,1),"under_25":round((1-ov25)*100,1),
                    "goal_si":round(gsi*100,1),"goal_no":round((1-gsi)*100,1),
                    "gol_attesi":round(lh+la,2),
                    "risultati_esatti":_filtra_esatti(scores, ov25, sg),
                    "bookmaker_used":bk_odds is not None,
                }

    if has_api:
        # Lambda da statistiche REALI casa/trasferta (API Football)
        avg_gs_away = sum(get_team_real_stats(t).get("gs_away_pg", 1.2) for t in _TEAM_IDS if get_team_real_stats(t)) / max(1, sum(1 for t in _TEAM_IDS if get_team_real_stats(t)))
        avg_gs_home = sum(get_team_real_stats(t).get("gs_home_pg", 1.0) for t in _TEAM_IDS if get_team_real_stats(t)) / max(1, sum(1 for t in _TEAM_IDS if get_team_real_stats(t)))

        lh_api = api_h["gf_home_pg"] * (api_a["gs_away_pg"] / max(0.5, avg_gs_away))
        la_api = api_a["gf_away_pg"] * (api_h["gs_home_pg"] / max(0.5, avg_gs_home))

        # Forma API Football (ultimi 5: W=3, D=1, L=0, max 15)
        form_h = api_h.get("form_score", 7)
        form_a = api_a.get("form_score", 7)
        form_diff = (form_h - form_a) / 15  # Normalizzato [-1, 1]

        if sh and sa:
            # Blend: 40% storico CSV + 40% API reale + 20% classifica
            avg_gc = LEAGUE_AVG.get("media_gol_casa", 1.5)
            avg_gt = LEAGUE_AVG.get("media_gol_trasferta", 1.17)
            lh_hist = sh["forza_att_casa"] * sa["forza_dif_trasf"] * avg_gc
            la_hist = sa["forza_att_trasf"] * sh["forza_dif_casa"] * avg_gt

            CLASSIFICA_PTS = {r["Squadra"]: r["Punti"] for r in CLASS_FALLBACK}
            pts_diff = (CLASSIFICA_PTS.get(h, 35) - CLASSIFICA_PTS.get(a, 35)) / 100
            lh_cls = avg_gc * (1 + pts_diff * 0.5)
            la_cls = avg_gt * (1 - pts_diff * 0.5)

            lh = 0.35 * lh_hist + 0.45 * lh_api + 0.20 * lh_cls
            la = 0.35 * la_hist + 0.45 * la_api + 0.20 * la_cls
        else:
            lh = lh_api
            la = la_api

        # Correzione forma API (piu' forte perche' basata su dati reali)
        ff = 1.0 + 0.15 * form_diff
        lh *= ff
        la *= (2.0 - ff)

        # H2H anche nel percorso API
        h2h_key = f"{h}_vs_{a}"
        h2h = H2H_DATA.get(h2h_key, {})
        h2h_n = h2h.get("n_partite", 0)
        if h2h_n >= 3:
            adv = h2h["h2h_advantage"]
            lh *= (1.0 + 0.08 * adv)
            la *= (1.0 - 0.08 * adv)

        # ── FASE 4: FATTORE CAMPO AVANZATO ──
        # Usa win% reali casa/trasferta per correggere i lambda
        win_h_pct = api_h.get("win_home_pct", 50)
        win_a_pct = api_a.get("win_away_pct", 30)
        # Media Serie A: casa vince ~45%, trasferta ~30%
        home_strength = win_h_pct / 45.0  # >1 = forte in casa, <1 = debole
        away_strength = win_a_pct / 30.0  # >1 = forte fuori, <1 = debole
        # Applica con peso leggero per non sovrapporre ad altre correzioni
        lh *= (0.90 + 0.10 * home_strength)
        la *= (0.90 + 0.10 * away_strength)

    elif not sh or not sa:
        # Squadra non trovata nei CSV, usa solo xG
        XG = {"Inter":{"xG":2.40,"xGA":0.84},"Milan":{"xG":1.83,"xGA":1.12},"Napoli":{"xG":1.56,"xGA":1.10},"Como":{"xG":1.80,"xGA":1.08},"Juventus":{"xG":1.97,"xGA":0.97},"Roma":{"xG":1.54,"xGA":1.20},"Atalanta":{"xG":1.86,"xGA":1.38},"Lazio":{"xG":1.21,"xGA":1.34},"Bologna":{"xG":1.34,"xGA":1.39},"Sassuolo":{"xG":1.19,"xGA":1.63},"Udinese":{"xG":1.19,"xGA":1.56},"Parma":{"xG":1.00,"xGA":1.62},"Genoa":{"xG":1.30,"xGA":1.45},"Torino":{"xG":1.33,"xGA":1.57},"Cagliari":{"xG":1.01,"xGA":1.65},"Fiorentina":{"xG":1.52,"xGA":1.53},"Cremonese":{"xG":1.03,"xGA":1.87},"Lecce":{"xG":0.93,"xGA":1.67},"Verona":{"xG":1.03,"xGA":1.40},"Pisa":{"xG":1.14,"xGA":1.82}}
        xh = XG.get(h, {"xG":1.3,"xGA":1.3})
        xa = XG.get(a, {"xG":1.3,"xGA":1.3})
        avg = sum(v["xGA"] for v in XG.values()) / len(XG)
        lh = xh["xG"] * (xa["xGA"] / avg)
        la = xa["xG"] * (xh["xGA"] / avg)
    else:
        # Lambda base da 26 anni di storico
        avg_gc = LEAGUE_AVG.get("media_gol_casa", 1.5)
        avg_gt = LEAGUE_AVG.get("media_gol_trasferta", 1.17)
        lh_hist = sh["forza_att_casa"] * sa["forza_dif_trasf"] * avg_gc
        la_hist = sa["forza_att_trasf"] * sh["forza_dif_casa"] * avg_gt

        # Lambda da xG stagione corrente
        xg_h = sh.get("xG_pg", 1.3)
        xga_h = sh.get("xGA_pg", 1.3)
        xg_a = sa.get("xG_pg", 1.3)
        xga_a = sa.get("xGA_pg", 1.3)
        avg_xga = 1.38
        lh_xg = xg_h * (xga_a / avg_xga)
        la_xg = xg_a * (xga_h / avg_xga)

        # PUNTO 1: Quote bookmaker come calibrazione
        # Le quote implicite dei bookmaker (medie storiche) calibrano il modello
        # Forza relativa dalla classifica come proxy delle quote
        CLASSIFICA_PTS = {"Inter":69,"Milan":63,"Napoli":62,"Como":57,"Juventus":54,"Roma":54,"Atalanta":50,"Lazio":43,"Bologna":42,"Sassuolo":39,"Udinese":39,"Parma":34,"Genoa":33,"Torino":33,"Cagliari":30,"Fiorentina":29,"Cremonese":27,"Lecce":27,"Verona":18,"Pisa":18}
        pts_h = CLASSIFICA_PTS.get(h, 35)
        pts_a = CLASSIFICA_PTS.get(a, 35)
        pts_diff = (pts_h - pts_a) / 100  # Normalizzato
        # Lambda da classifica (proxy quote)
        lh_cls = avg_gc * (1 + pts_diff * 0.5)
        la_cls = avg_gt * (1 - pts_diff * 0.5)

        # PUNTO 2: Ensemble — blend storico (50%) + xG (30%) + classifica (20%)
        lh = 0.50 * lh_hist + 0.30 * lh_xg + 0.20 * lh_cls
        la = 0.50 * la_hist + 0.30 * la_xg + 0.20 * la_cls

        # I gol attesi riflettono la forza SPECIFICA delle due squadre
        # Non applichiamo cap alla media campionato

        # Correzione H2H (piu' leggera)
        h2h_key = f"{h}_vs_{a}"
        h2h = H2H_DATA.get(h2h_key, {})
        h2h_n = h2h.get("n_partite", 0)
        if h2h_n >= 3:
            adv = h2h["h2h_advantage"]
            lh *= (1.0 + 0.06 * adv)
            la *= (1.0 - 0.06 * adv)

        # Correzione forma pesata (piu' leggera)
        fh = sh.get("forma_casa_pesata", 1.5)
        fa = sa.get("forma_trasf_pesata", 1.5)
        fd = fh - fa
        ff = 1.0 + 0.05 * fd
        lh *= ff
        la *= (2.0 - ff)

        # PUNTO 4: Feature avanzate (leggere)
        if pts_h <= 30 or pts_h >= 60:
            lh *= 1.02
        if pts_a <= 30 or pts_a >= 60:
            la *= 1.02
        if abs(pts_h - pts_a) > 25:
            if pts_h > pts_a:
                lh *= 1.02
            else:
                la *= 1.02

    # Clamp realistico per singola squadra
    lh = max(0.3, min(lh, 2.2))
    la = max(0.2, min(la, 1.6))

    # Equilibrio: la Roma non puo' avere solo 13%
    # Min prob ospite = ~15% per squadre di meta' classifica
    # Questo si ottiene assicurando che la non sia troppo basso

    # Calcolo Poisson con Dixon-Coles
    p1 = px = p2 = 0.0
    for i in range(11):
        for j in range(11):
            p = pdist.pmf(i, lh) * pdist.pmf(j, la)
            rho = -0.13
            if i==0 and j==0: p *= (1 - lh*la*rho)
            elif i==1 and j==0: p *= (1 + la*rho)
            elif i==0 and j==1: p *= (1 + lh*rho)
            elif i==1 and j==1: p *= (1 - rho)
            p = max(0, p)
            if i > j: p1 += p
            elif i == j: px += p
            else: p2 += p
    px *= 1.12
    ratio = min(lh,la)/max(lh,la) if max(lh,la)>0 else 0
    if ratio > 0.80:
        px *= 1.0 + (ratio-0.80)*0.8
    tot = p1 + px + p2
    if tot > 0: p1/=tot; px/=tot; p2/=tot

    # BLENDING CON QUOTE BOOKMAKER (se disponibili)
    bk_odds = get_bookmaker_odds(h, a)
    bk_used = False
    if bk_odds:
        bk_used = True
        bk_p1 = bk_odds["prob_1"] / 100
        bk_px = bk_odds["prob_x"] / 100
        bk_p2 = bk_odds["prob_2"] / 100
        # Blend: 60% nostro modello + 40% bookmaker
        p1 = 0.60 * p1 + 0.40 * bk_p1
        px = 0.60 * px + 0.40 * bk_px
        p2 = 0.60 * p2 + 0.40 * bk_p2
        # Rinormalizza
        tot = p1 + px + p2
        if tot > 0: p1/=tot; px/=tot; p2/=tot

    ov25_model = sum(pdist.pmf(i,lh)*pdist.pmf(j,la) for i in range(11) for j in range(11) if i+j>2.5)
    # Blend Over/Under con bookmaker (se disponibile)
    if bk_odds and bk_odds.get("bk_over_25"):
        bk_ov = bk_odds["bk_over_25"] / 100
        ov25 = 0.60 * ov25_model + 0.40 * bk_ov
    else:
        ov25 = ov25_model
    gsi_raw = sum(pdist.pmf(i,lh)*pdist.pmf(j,la) for i in range(1,11) for j in range(1,11))
    # Calibrazione Goal con clean sheet reali API Football
    xga_min = min(sh.get("xGA_pg", 1.3) if sh else 1.3, sa.get("xGA_pg", 1.3) if sa else 1.3)
    if has_api:
        # Usa clean sheet % reale per calibrare Goal/NoGoal
        cs_h = api_h.get("cs_pct", 0)
        cs_a = api_a.get("cs_pct", 0)
        cs_avg = (cs_h + cs_a) / 2
        if cs_avg > 30:  # Almeno una squadra tiene spesso la porta inviolata
            gsi = gsi_raw * (1.0 - (cs_avg - 30) * 0.005)  # Riduce Goal Si
        else:
            gsi = gsi_raw
    elif xga_min < 0.9:
        gsi = gsi_raw * 0.95
    else:
        gsi = gsi_raw
    # Calibrazione Goal: boost solo se entrambi lambda >= 0.8
    gol_att = lh + la
    lm2 = min(lh, la)
    if gol_att > 3.0 and lm2 >= 0.8:
        gsi = max(gsi, 0.55 + (gol_att - 3.0) * 0.04)
        gsi = min(gsi, 0.80)
    elif gol_att > 2.5 and lm2 >= 0.7:
        gsi = max(gsi, 0.50 + (gol_att - 2.5) * 0.04)
    scores = sorted([{"score":f"{i}-{j}","prob":round(pdist.pmf(i,lh)*pdist.pmf(j,la)*100,1)} for i in range(5) for j in range(5)], key=lambda x:-x["prob"])

    mp = max(p1, px, p2)
    sg = "1" if mp==p1 else ("X" if mp==px else "2")
    sl = "Vittoria Casa" if sg=="1" else ("Pareggio" if sg=="X" else "Vittoria Ospite")

    # PUNTO 5: Confidence avanzata multi-fattore
    sp = sorted([p1,px,p2], reverse=True)
    spread = sp[0] - sp[1]
    # Componenti: separazione (40%) + dati (25%) + H2H (20%) + classifica (15%)
    c_spread = min(spread / 0.35, 1.0)
    c_dati = min(sh.get("n_partite", 0) / 200, 1.0) if sh else 0.3
    c_h2h = min(h2h_n / 15, 1.0) if sh and h2h_n >= 3 else 0.3
    c_class = min(abs(pts_diff) * 3, 1.0) if sh else 0.3
    cf = 0.40*c_spread + 0.25*c_dati + 0.20*c_h2h + 0.15*c_class
    cf = round(min(max(cf, 0), 1.0), 3)
    cl = "Alta" if cf>=0.82 else ("Media" if cf>=0.50 else "Bassa")

    # PUNTO 5: Badge sicura (solo quando confidenza Alta)
    sicura = cf >= 0.82 and sp[0] > 0.45

    # Marcatori live da API Football
    marc_h = []
    marc_a = []
    for lk in ["serie-a", "premier-league", "la-liga"]:
        mc = MARCATORI_CACHE.get(lk) or []
        for m in mc:
            if m.get("squadra") == h:
                marc_h.append(f"{m['giocatore']} ({m['gol']} gol)")
            elif m.get("squadra") == a:
                marc_a.append(f"{m['giocatore']} ({m['gol']} gol)")
    if not marc_h:
        marc_h = _filtra_marcatori(TOP_SCORER.get(h, []), INFORTUNATI.get(h, []))
    if not marc_a:
        marc_a = _filtra_marcatori(TOP_SCORER.get(a, []), INFORTUNATI.get(a, []))
    # Formazioni live
    form_h = LIVE_FORMAZIONI.get(h) or FORMAZIONI.get(h) or _get_last_lineup(h)
    form_a = LIVE_FORMAZIONI.get(a) or FORMAZIONI.get(a) or _get_last_lineup(a)

    return {
        "prob_1":round(p1*100,1),"prob_x":round(px*100,1),"prob_2":round(p2*100,1),
        "quota_1":round(1.05/p1,2) if p1>0 else 99,"quota_x":round(1.05/px,2) if px>0 else 99,"quota_2":round(1.05/p2,2) if p2>0 else 99,
        "suggerimento":sg,"sugg_label":sl,"confidence":round(cf,3),"confidence_label":cl,
        "sicura": bool(sicura),
        "over_25":round(ov25*100,1),"under_25":round((1-ov25)*100,1),
        "goal_si":round(gsi*100,1),"goal_no":round((1-gsi)*100,1),
        "gol_attesi":round(lh+la,2),
        "risultati_esatti": _filtra_esatti(scores, ov25, sg),
        "marcatori_casa": marc_h[:3],
        "marcatori_ospite": marc_a[:3],
        "formazione_casa": form_h,
        "formazione_ospite": form_a,
        "h2h_applicato": h2h_n >= 3 if sh else False,
        "h2h_partite": h2h_n if sh else 0,
        "bookmaker_used": bool(bk_used),
        "bookmaker_odds": bk_odds,
    }

# ─────────────────────────────
# EMAIL (Resend)
# ─────────────────────────────
RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "re_ShqALKcH_HAnRE4SUyU9asxwpcAXC16AL")

def send_welcome_email(to_email):
    """Invia email di benvenuto dopo la registrazione."""
    try:
        import urllib.request as ur
        import json as js
        body = js.dumps({
            "from": "MatchIQ <noreply@matchiq.it.com>",
            "to": [to_email],
            "subject": "Benvenuto su PronoSerie A!",
            "html": f"""
            <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;background:#0a0f1a;color:#e8eaf6;padding:32px;border-radius:12px">
                <h1 style="color:#2ecc71;text-align:center">Benvenuto su PronoSerie A!</h1>
                <p style="text-align:center;color:#8892b0">Il tuo account e' stato creato con successo.</p>
                <div style="background:#162447;padding:20px;border-radius:8px;margin:20px 0;text-align:center">
                    <p style="margin:0"><strong>Email:</strong> {to_email}</p>
                    <p style="margin:8px 0 0"><strong>Piano:</strong> Free</p>
                </div>
                <h3 style="color:#3498db">Cosa puoi fare:</h3>
                <ul style="color:#8892b0;line-height:2">
                    <li>2 pronostici gratuiti al giorno</li>
                    <li>Pronostici 1X2 con probabilita' e quote</li>
                    <li>Calendario Serie A giornate 31-38</li>
                </ul>
                <div style="text-align:center;margin:24px 0">
                    <a href="https://web-production-ff46b.up.railway.app/app#pronostici" style="background:#2ecc71;color:#000;padding:14px 32px;border-radius:20px;text-decoration:none;font-weight:700;font-size:1.1rem">Calcola il tuo primo pronostico</a>
                </div>
                <p style="text-align:center;color:#8892b0;font-size:.85rem">Passa a Pro per pronostici illimitati, classifica, marcatori, rose e formazioni live!</p>
                <hr style="border:1px solid #1f3460;margin:20px 0">
                <p style="text-align:center;color:#8892b0;font-size:.8rem">PronoSerie A — Pronostici Serie A con Intelligenza Artificiale</p>
            </div>
            """
        }).encode()
        req = ur.Request("https://api.resend.com/emails", data=body, headers={
            "Authorization": f"Bearer {RESEND_API_KEY}",
            "Content-Type": "application/json",
            "User-Agent": "MatchIQ/1.0"
        })
        ur.urlopen(req, timeout=10)
        print(f"📧 Email inviata a {to_email}")
    except Exception as e:
        print(f"⚠️ Errore invio email a {to_email}: {e}")

# ─────────────────────────────
# NOTIFICHE ADMIN (nuova iscrizione)
# ─────────────────────────────
ADMIN_EMAIL = "mario.costabile92@outlook.it"
ADMIN_TELEGRAM_USERNAME = "Soanator"
ADMIN_CHAT_ID = None  # Si auto-imposta quando l'admin scrive /start al bot

def _notify_admin_new_user(email, piano):
    """Notifica l'admin quando un nuovo utente si registra."""
    # 1. Email
    try:
        import urllib.request as ur
        body = json.dumps({
            "from": "MatchIQ <noreply@matchiq.it.com>",
            "to": [ADMIN_EMAIL],
            "subject": f"Nuovo iscritto MatchIQ: {email}",
            "html": f"""
            <div style="font-family:Arial;background:#0a0f1a;color:#e8eaf6;padding:24px;border-radius:12px">
                <h2 style="color:#2ecc71">Nuovo iscritto!</h2>
                <p><strong>Email:</strong> {email}</p>
                <p><strong>Piano:</strong> {piano}</p>
                <p><strong>Data:</strong> {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M UTC')}</p>
                <hr style="border:1px solid #1f3460">
                <p style="color:#8892b0;font-size:.85rem">MatchIQ - Notifica automatica</p>
            </div>
            """
        }).encode()
        req = ur.Request("https://api.resend.com/emails", data=body, headers={
            "Authorization": f"Bearer {RESEND_API_KEY}",
            "Content-Type": "application/json",
            "User-Agent": "MatchIQ/1.0"
        })
        ur.urlopen(req, timeout=10)
        print(f"📧 Notifica admin: nuovo utente {email}")
    except Exception as e:
        print(f"⚠️ Errore notifica email admin: {e}")

    # 2. Telegram (se chat_id disponibile)
    try:
        # Cerca chat_id admin dal database bot
        import sqlite3
        if os.path.exists(_BOT_DB_PATH):
            conn = sqlite3.connect(_BOT_DB_PATH)
            row = conn.execute("SELECT chat_id FROM utenti WHERE username = ?", (ADMIN_TELEGRAM_USERNAME,)).fetchone()
            conn.close()
            if row:
                chat_id = row[0]
                msg = f"🆕 <b>Nuovo iscritto MatchIQ!</b>\n\n📧 {email}\n📋 Piano: {piano}\n⏰ {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M')}"
                _send_telegram_message(chat_id, msg)
    except Exception:
        pass

# ─────────────────────────────
# AUTH
# ─────────────────────────────
@app.post("/api/auth/register")
async def register(data: dict):
    email = data["email"].lower().strip()

    if get_user_by_email(email):
        raise HTTPException(409, "Email gia' registrata")

    user = create_user(email, hash_password(data["password"]))
    token = create_token({"sub": str(user["id"])})

    # Invia email di benvenuto (in background, non blocca la risposta)
    threading.Thread(target=send_welcome_email, args=(email,), daemon=True).start()

    # Notifica admin (in background)
    try:
        threading.Thread(target=_notify_admin_new_user, args=(email, user.get("piano", "free")), daemon=True).start()
    except Exception as e:
        print(f"⚠️ Errore avvio notifica admin: {e}")

    return {"access_token": token, "piano": user["piano"]}

@app.post("/api/auth/login")
async def login(data: dict):
    user = get_user_by_email(data["email"].lower().strip())

    if not user or not verify_password(data["password"].strip(), user["password_hash"]):
        raise HTTPException(401, "Credenziali errate")

    token = create_token({"sub": str(user["id"])})

    return {"access_token": token, "piano": user["piano"]}

@app.post("/api/auth/reset-password")
async def reset_password(data: dict):
    import random, string
    email = data.get("email", "").lower().strip()
    if not email:
        raise HTTPException(400, "Email richiesta")
    user = get_user_by_email(email)
    if not user:
        raise HTTPException(404, "Email non trovata")
    # Genera nuova password casuale
    new_pass = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
    # Aggiorna nel DB
    from database import _get_conn
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE users SET password_hash = %s WHERE id = %s", (hash_password(new_pass), user["id"]))
    conn.commit()
    cur.close()
    conn.close()
    # Invia via email
    try:
        import urllib.request as ur
        body = json.dumps({
            "from": "MatchIQ <noreply@matchiq.it.com>",
            "to": [email],
            "subject": "MatchIQ - La tua nuova password",
            "html": f'<div style="font-family:Arial;background:#0a0f1a;color:#e8eaf6;padding:24px;border-radius:12px"><h2 style="color:#2ecc71">Recupero Password</h2><p>La tua nuova password provvisoria e\':</p><div style="background:#162447;padding:16px;border-radius:8px;text-align:center;margin:16px 0"><code style="font-size:1.5rem;font-weight:800;color:#2ecc71;font-family:Courier New,monospace;user-select:all">{new_pass}</code></div><p style="font-size:.85rem;color:#8892b0">Copia la password qui sopra (toccala per selezionarla) e usala per accedere.</p><p>Poi cambiala dalle impostazioni del tuo account.</p><hr style="border:1px solid #1f3460"><p style="color:#8892b0;font-size:.85rem">MatchIQ - Pronostici Calcistici con IA</p></div>'
        }).encode()
        req = ur.Request("https://api.resend.com/emails", data=body, headers={
            "Authorization": f"Bearer {RESEND_API_KEY}",
            "Content-Type": "application/json",
            "User-Agent": "MatchIQ/1.0"
        })
        ur.urlopen(req, timeout=10)
        print(f"📧 Password reset inviata a {email}")
    except Exception as e:
        print(f"❌ Errore invio reset password: {e}")
    return {"sent": True}

@app.post("/api/auth/change-password")
async def change_password(data: dict, user: Optional[dict] = Depends(get_optional_user)):
    if not user:
        raise HTTPException(401, "Devi essere loggato")
    old_pass = data.get("old_password", "")
    new_pass = data.get("new_password", "")
    if not old_pass or not new_pass:
        raise HTTPException(400, "Compila tutti i campi")
    if len(new_pass) < 6:
        raise HTTPException(400, "La nuova password deve avere almeno 6 caratteri")
    db_user = get_user_by_email(user.get("email", ""))
    if not db_user or not verify_password(old_pass, db_user["password_hash"]):
        raise HTTPException(401, "Password attuale errata")
    from database import _get_conn
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE users SET password_hash = %s WHERE id = %s", (hash_password(new_pass), db_user["id"]))
    conn.commit()
    cur.close()
    conn.close()
    return {"status": "ok"}

# ─────────────────────────────
# PRONOSTICO
# ─────────────────────────────
@app.get("/api/pronostico/{home}/{away}")
async def pronostico(home: str, away: str, user: Optional[dict] = Depends(get_optional_user)):
    check_limit(user)

    raw = genera_pronostico(home, away)

    # ── BLEND CON QUOTE BOOKMAKER LIVE (the-odds-api) ──
    p1 = raw.get("prob_1", 0)
    px = raw.get("prob_x", 0)
    p2 = raw.get("prob_2", 0)
    bk_live = get_bookmaker_odds(home.strip().title(), away.strip().title())
    bk_used_live = False
    if bk_live and bk_live.get("prob_1"):
        bk_used_live = True
        # Blend 65% modello + 35% bookmaker live (le quote live sono molto accurate)
        ALPHA_LIVE = 0.35
        bp1 = bk_live["prob_1"] / 100
        bpx = bk_live["prob_x"] / 100
        bp2 = bk_live["prob_2"] / 100
        p1 = (1 - ALPHA_LIVE) * (p1 / 100) + ALPHA_LIVE * bp1
        px = (1 - ALPHA_LIVE) * (px / 100) + ALPHA_LIVE * bpx
        p2 = (1 - ALPHA_LIVE) * (p2 / 100) + ALPHA_LIVE * bp2
        # Normalizza
        tot = p1 + px + p2
        if tot > 0:
            p1 = round(p1 / tot * 100, 1)
            px = round(px / tot * 100, 1)
            p2 = round(p2 / tot * 100, 1)
        # Ricalcola suggerimento
        mp = max(p1, px, p2)
        if mp == p1:
            sugg, sugg_label = "1", "Vittoria Casa"
        elif mp == px:
            sugg, sugg_label = "X", "Pareggio"
        else:
            sugg, sugg_label = "2", "Vittoria Ospite"
        # Ricalcola quote
        q1 = round(1.05 / (p1/100), 2) if p1 > 0 else 99
        qx = round(1.05 / (px/100), 2) if px > 0 else 99
        q2 = round(1.05 / (p2/100), 2) if p2 > 0 else 99
        # Ricalcola confidence (boost se modello e bookmaker concordano)
        conf_raw = raw.get("confidence", 0.5)
        if sugg == raw.get("suggerimento", ""):
            conf_raw = min(1.0, conf_raw * 1.08)  # +8% se concordano
        conf_label = "Alta" if conf_raw >= 0.82 else ("Media" if conf_raw >= 0.50 else "Bassa")
        # Blend Over/Under con bookmaker live
        ov25 = raw.get("over_25", 50)
        un25 = raw.get("under_25", 50)
        if bk_live.get("bk_over_25"):
            ov25 = round(0.65 * ov25 + 0.35 * bk_live["bk_over_25"], 1)
            un25 = round(100 - ov25, 1)
    else:
        sugg = raw.get("suggerimento", "")
        sugg_label = raw.get("sugg_label", "")
        q1 = raw.get("quota_1", 0)
        qx = raw.get("quota_x", 0)
        q2 = raw.get("quota_2", 0)
        conf_raw = raw.get("confidence", 0)
        conf_label = raw.get("confidence_label", "")
        ov25 = raw.get("over_25")
        un25 = raw.get("under_25")

    # Marcatori live (cerca in cache API Football + fallback hardcoded)
    h_t = home.strip().title()
    a_t = away.strip().title()
    mc_h = raw.get("marcatori_casa") or []
    mc_a = raw.get("marcatori_ospite") or []
    if not mc_h:
        for lk in ["serie-a", "premier-league", "la-liga"]:
            for m in (MARCATORI_CACHE.get(lk) or []):
                if m.get("squadra") == h_t:
                    mc_h.append(f"{m['giocatore']} ({m['gol']} gol)")
        if not mc_h:
            mc_h = _filtra_marcatori(TOP_SCORER.get(h_t, []), INFORTUNATI.get(h_t, []))
    if not mc_a:
        for lk in ["serie-a", "premier-league", "la-liga"]:
            for m in (MARCATORI_CACHE.get(lk) or []):
                if m.get("squadra") == a_t:
                    mc_a.append(f"{m['giocatore']} ({m['gol']} gol)")
        if not mc_a:
            mc_a = _filtra_marcatori(TOP_SCORER.get(a_t, []), INFORTUNATI.get(a_t, []))

    return {
        "home": home,
        "away": away,
        "prob_1": p1,
        "prob_x": px,
        "prob_2": p2,
        "quota_1": q1,
        "quota_x": qx,
        "quota_2": q2,
        "suggerimento": sugg,
        "sugg_label": sugg_label,
        "confidence": conf_raw,
        "confidence_label": conf_label,
        "over_25": ov25,
        "under_25": un25,
        "goal_si": raw.get("goal_si"),
        "goal_no": raw.get("goal_no"),
        "gol_attesi": raw.get("gol_attesi"),
        "risultati_esatti": raw.get("risultati_esatti", []),
        "sicura": bool(conf_raw >= 0.82 and max(p1,px,p2) > 45),
        "marcatori_casa": mc_h[:3],
        "marcatori_ospite": mc_a[:3],
        "formazione_casa": raw.get("formazione_casa") or _get_last_lineup(h_t),
        "formazione_ospite": raw.get("formazione_ospite") or _get_last_lineup(a_t),
        "h2h_applicato": bool(raw.get("h2h_applicato", False)),
        "h2h_partite": int(raw.get("h2h_partite", 0)),
        "bookmaker_live": bk_used_live,
        "bookmaker_live_data": bk_live if bk_used_live else None,
    }

    # Salva predizione per tracking (in background)
    import threading as _th
    _th.Thread(target=save_prediction, args=(home, away, None, response_data, bk_used_live), daemon=True).start()

    return response_data

# ─────────────────────────────
# CALENDARIO (FIX DEFINITIVO)
# ─────────────────────────────
CAL_HARDCODED = {
    31:{"data":"4-6 aprile 2026","partite":[("Sassuolo","Cagliari"),("Verona","Fiorentina"),("Lazio","Parma"),("Cremonese","Bologna"),("Pisa","Torino"),("Inter","Roma"),("Udinese","Como"),("Lecce","Atalanta"),("Juventus","Genoa"),("Napoli","Milan")]},
    32:{"data":"10-13 aprile 2026","partite":[("Roma","Pisa"),("Cagliari","Cremonese"),("Torino","Verona"),("Milan","Udinese"),("Atalanta","Juventus"),("Genoa","Sassuolo"),("Parma","Napoli"),("Bologna","Lecce"),("Como","Inter"),("Fiorentina","Lazio")]},
    33:{"data":"17-20 aprile 2026","partite":[("Sassuolo","Como"),("Inter","Cagliari"),("Udinese","Parma"),("Napoli","Lazio"),("Roma","Atalanta"),("Cremonese","Torino"),("Verona","Milan"),("Pisa","Genoa"),("Juventus","Bologna"),("Lecce","Fiorentina")]},
    34:{"data":"24-27 aprile 2026","partite":[("Napoli","Cremonese"),("Parma","Pisa"),("Bologna","Roma"),("Verona","Lecce"),("Fiorentina","Sassuolo"),("Genoa","Como"),("Torino","Inter"),("Milan","Juventus"),("Cagliari","Atalanta"),("Lazio","Udinese")]},
    35:{"data":"2-4 maggio 2026","partite":[("Atalanta","Genoa"),("Bologna","Cagliari"),("Como","Napoli"),("Cremonese","Lazio"),("Inter","Parma"),("Juventus","Verona"),("Pisa","Lecce"),("Roma","Fiorentina"),("Sassuolo","Milan"),("Udinese","Torino")]},
    36:{"data":"8-10 maggio 2026","partite":[("Cagliari","Udinese"),("Cremonese","Pisa"),("Fiorentina","Genoa"),("Lazio","Inter"),("Lecce","Juventus"),("Milan","Atalanta"),("Napoli","Bologna"),("Parma","Roma"),("Torino","Sassuolo"),("Verona","Como")]},
    37:{"data":"15-17 maggio 2026","partite":[("Atalanta","Bologna"),("Cagliari","Torino"),("Como","Parma"),("Genoa","Milan"),("Inter","Verona"),("Juventus","Fiorentina"),("Pisa","Napoli"),("Roma","Lazio"),("Sassuolo","Lecce"),("Udinese","Cremonese")]},
    38:{"data":"24 maggio 2026","partite":[("Bologna","Inter"),("Cremonese","Como"),("Fiorentina","Atalanta"),("Lazio","Pisa"),("Lecce","Genoa"),("Milan","Cagliari"),("Napoli","Udinese"),("Parma","Sassuolo"),("Torino","Juventus"),("Verona","Roma")]},
}

@app.get("/api/calendario")
async def calendario():
    """Calendario con risultati live integrati da API Football."""
    giornate = []
    giornata_corrente = None

    for num in range(31, 39):
        info = CAL_HARDCODED.get(num)
        if not info:
            continue

        partite = []
        tutte_finite = True
        ha_live = False
        ha_da_giocare = False

        for h, a in info["partite"]:
            match_data = {"home": h, "away": a, "gol_h": None, "gol_a": None, "status": "NS", "status_it": "Da giocare", "minuto": None, "live": False, "fixture_id": None}

            # Cerca il risultato nei dati live di API Football
            if LIVE_RESULTS_CACHE:
                for p in LIVE_RESULTS_CACHE:
                    if (p["home"] == h and p["away"] == a) or (p["home"] == a and p["away"] == h):
                        is_inverted = p["home"] == a
                        match_data["gol_h"] = p["gol_a"] if is_inverted else p["gol_h"]
                        match_data["gol_a"] = p["gol_h"] if is_inverted else p["gol_a"]
                        match_data["status"] = p["status"]
                        match_data["status_it"] = p.get("status_it", p["status"])
                        match_data["minuto"] = p.get("minuto")
                        match_data["live"] = p.get("live", False)
                        match_data["fixture_id"] = p.get("fixture_id")
                        match_data["marcatori"] = p.get("marcatori", [])
                        match_data["marcatori_home"] = p.get("marcatori_home", [])
                        match_data["marcatori_away"] = p.get("marcatori_away", [])
                        if is_inverted:
                            match_data["marcatori_home"], match_data["marcatori_away"] = match_data["marcatori_away"], match_data["marcatori_home"]
                        break

            if match_data["status"] not in ("FT", "AET", "PEN"):
                tutte_finite = False
            if match_data["live"]:
                ha_live = True
            if match_data["status"] == "NS":
                ha_da_giocare = True

            partite.append(match_data)

        # Determina stato giornata
        if tutte_finite:
            stato = "completata"
        elif ha_live:
            stato = "live"
            giornata_corrente = num
        elif ha_da_giocare and not tutte_finite:
            stato = "prossima"
            if giornata_corrente is None:
                giornata_corrente = num
        else:
            stato = "prossima"

        giornate.append({
            "giornata": num,
            "data": info["data"],
            "partite": partite,
            "stato": stato,
            "live": ha_live,
        })

    # Se non trovata, la prima non completata e' la corrente
    if giornata_corrente is None:
        for g in giornate:
            if g["stato"] != "completata":
                giornata_corrente = g["giornata"]
                break
        if giornata_corrente is None:
            giornata_corrente = 38

    return {
        "giornate": giornate,
        "giornata_corrente": giornata_corrente,
        "live": any(g.get("live") for g in giornate),
    }

# ─────────────────────────────
# CLASSIFICA + MARCATORI (AUTO-AGGIORNAMENTO API FOOTBALL)
# ─────────────────────────────
# CLASSIFICA_CACHE e MARCATORI_CACHE sono definiti sopra come dict multi-league

# Fallback hardcoded (usato solo se API non disponibile)
CLASS_FALLBACK = [
    {"Squadra":"Inter","Punti":69,"G":30,"V":22,"N":3,"P":5,"GF":66,"GS":24,"DR":42},
    {"Squadra":"Milan","Punti":63,"G":30,"V":18,"N":9,"P":3,"GF":47,"GS":23,"DR":24},
    {"Squadra":"Napoli","Punti":62,"G":30,"V":19,"N":5,"P":6,"GF":46,"GS":30,"DR":16},
    {"Squadra":"Como","Punti":57,"G":30,"V":16,"N":9,"P":5,"GF":53,"GS":22,"DR":31},
    {"Squadra":"Juventus","Punti":54,"G":30,"V":15,"N":9,"P":6,"GF":52,"GS":29,"DR":23},
    {"Squadra":"Roma","Punti":54,"G":30,"V":17,"N":3,"P":10,"GF":40,"GS":23,"DR":17},
    {"Squadra":"Atalanta","Punti":50,"G":30,"V":13,"N":11,"P":6,"GF":41,"GS":27,"DR":14},
    {"Squadra":"Lazio","Punti":43,"G":30,"V":11,"N":10,"P":9,"GF":31,"GS":28,"DR":3},
    {"Squadra":"Bologna","Punti":42,"G":30,"V":12,"N":6,"P":12,"GF":38,"GS":36,"DR":2},
    {"Squadra":"Sassuolo","Punti":39,"G":30,"V":11,"N":6,"P":13,"GF":36,"GS":40,"DR":-4},
    {"Squadra":"Udinese","Punti":39,"G":30,"V":11,"N":6,"P":13,"GF":35,"GS":42,"DR":-7},
    {"Squadra":"Parma","Punti":34,"G":30,"V":8,"N":10,"P":12,"GF":21,"GS":38,"DR":-17},
    {"Squadra":"Genoa","Punti":33,"G":30,"V":8,"N":9,"P":13,"GF":36,"GS":42,"DR":-6},
    {"Squadra":"Torino","Punti":33,"G":30,"V":9,"N":6,"P":15,"GF":34,"GS":53,"DR":-19},
    {"Squadra":"Cagliari","Punti":30,"G":30,"V":7,"N":9,"P":14,"GF":31,"GS":42,"DR":-11},
    {"Squadra":"Fiorentina","Punti":29,"G":30,"V":6,"N":11,"P":13,"GF":35,"GS":44,"DR":-9},
    {"Squadra":"Cremonese","Punti":27,"G":30,"V":6,"N":9,"P":15,"GF":25,"GS":44,"DR":-19},
    {"Squadra":"Lecce","Punti":27,"G":30,"V":7,"N":6,"P":17,"GF":21,"GS":40,"DR":-19},
    {"Squadra":"Verona","Punti":18,"G":30,"V":3,"N":9,"P":18,"GF":22,"GS":52,"DR":-30},
    {"Squadra":"Pisa","Punti":18,"G":30,"V":2,"N":12,"P":16,"GF":23,"GS":54,"DR":-31},
]

MARC_FALLBACK = [
    {"pos":1,"giocatore":"Lautaro Martinez","squadra":"Inter","gol":14},
    {"pos":2,"giocatore":"Tasos Douvikas","squadra":"Como","gol":11},
    {"pos":3,"giocatore":"Keinan Davis","squadra":"Udinese","gol":10},
    {"pos":4,"giocatore":"Rasmus Hojlund","squadra":"Napoli","gol":10},
    {"pos":5,"giocatore":"Kenan Yildiz","squadra":"Juventus","gol":10},
    {"pos":6,"giocatore":"Nico Paz","squadra":"Como","gol":10},
    {"pos":7,"giocatore":"Rafael Leao","squadra":"Milan","gol":9},
    {"pos":8,"giocatore":"Hakan Calhanoglu","squadra":"Inter","gol":8},
    {"pos":9,"giocatore":"Giovanni Simeone","squadra":"Torino","gol":8},
    {"pos":10,"giocatore":"Christian Pulisic","squadra":"Milan","gol":8},
    {"pos":11,"giocatore":"Gianluca Scamacca","squadra":"Atalanta","gol":8},
    {"pos":12,"giocatore":"Nikola Krstovic","squadra":"Atalanta","gol":8},
    {"pos":13,"giocatore":"Moise Kean","squadra":"Fiorentina","gol":8},
    {"pos":14,"giocatore":"Mateo Pellegrino","squadra":"Parma","gol":8},
    {"pos":15,"giocatore":"Domenico Berardi","squadra":"Sassuolo","gol":7},
    {"pos":16,"giocatore":"Nikola Vlasic","squadra":"Torino","gol":7},
    {"pos":17,"giocatore":"Scott McTominay","squadra":"Napoli","gol":7},
    {"pos":18,"giocatore":"Donyell Malen","squadra":"Roma","gol":7},
    {"pos":19,"giocatore":"Marcus Thuram","squadra":"Inter","gol":7},
    {"pos":20,"giocatore":"Andrea Pinamonti","squadra":"Sassuolo","gol":7},
]

def _fetch_classifica_live():
    """Scarica classifica Serie A aggiornata da API Football."""
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
                    nome = FOOTBALL_NOME_MAP.get(nome_api, nome_api)
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
                        "GF": gf,
                        "GS": gs,
                        "DR": gf - gs,
                    })
                # Ordina per punti (desc), poi differenza reti
                classifica.sort(key=lambda x: (-x["Punti"], -x["DR"], -x["GF"]))
                if len(classifica) >= 10:
                    CLASSIFICA_CACHE["serie-a"] = classifica
                    CLASSIFICA_LAST_UPDATE["serie-a"] = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")
                    print(f"🏆 CLASSIFICA LIVE: {len(classifica)} squadre aggiornate")
                    return True
    except Exception as e:
        print(f"❌ Errore fetch classifica: {e}")
    return False

def _fetch_marcatori_live():
    """Scarica classifica marcatori Serie A da API Football."""
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
                info = player.get("player", {})
                stats_list = player.get("statistics", [])
                gol = 0
                squadra_api = ""
                for s in stats_list:
                    if s.get("league", {}).get("id") == 135:
                        gol = s.get("goals", {}).get("total", 0) or 0
                        squadra_api = s.get("team", {}).get("name", "")
                        break
                if gol == 0 and stats_list:
                    gol = stats_list[0].get("goals", {}).get("total", 0) or 0
                    squadra_api = stats_list[0].get("team", {}).get("name", "")

                squadra = FOOTBALL_NOME_MAP.get(squadra_api, squadra_api)
                marcatori.append({
                    "pos": i,
                    "giocatore": info.get("name", "?"),
                    "squadra": squadra,
                    "gol": gol,
                })
            if len(marcatori) >= 5:
                MARCATORI_CACHE["serie-a"] = marcatori
                print(f"⚽ MARCATORI LIVE: {len(marcatori)} giocatori aggiornati")
                return True
    except Exception as e:
        print(f"❌ Errore fetch marcatori: {e}")
    return False

# ─────────────────────────────
# ROSE, ALLENATORI, INFORTUNATI LIVE (API Football)
# ─────────────────────────────
ROSE_LIVE = {}
ALLENATORI_LIVE = {}
INFORTUNATI_LIVE = {}
ROSE_LAST_UPDATE = ""

# Team IDs per API Football
_TEAM_IDS = {
    "Inter":505,"Milan":489,"Napoli":492,"Como":895,"Juventus":496,
    "Roma":497,"Atalanta":499,"Lazio":487,"Bologna":500,"Sassuolo":488,
    "Udinese":494,"Parma":523,"Genoa":495,"Torino":503,"Cagliari":490,
    "Fiorentina":502,"Cremonese":520,"Lecce":867,"Verona":504,"Pisa":801,
}
_RUOLO_MAP = {"Goalkeeper":"P","Defender":"D","Midfielder":"C","Attacker":"A"}

# Tutti i team IDs delle squadre europee (UCL/UEL/UECL)
_ALL_EURO_IDS = {
    "Ajax":194,"Arsenal":42,"Atalanta":499,"Athletic Club":531,"Atletico Madrid":530,
    "Barcelona":529,"Bayer Leverkusen":168,"Bayern Munchen":157,"Bayern München":157,
    "Benfica":211,"Bodo/Glimt":327,"Borussia Dortmund":165,"Chelsea":49,
    "Club Brugge KV":569,"Eintracht Frankfurt":169,"FC Copenhagen":400,"Galatasaray":645,
    "Inter":505,"Juventus":496,"Liverpool":40,"Manchester City":50,"Marseille":81,
    "Monaco":91,"Napoli":492,"Newcastle":34,"Olympiakos Piraeus":553,"PSV Eindhoven":197,
    "Pafos":3403,"Paris Saint Germain":85,"Qarabag":556,"Real Madrid":541,
    "Slavia Praha":560,"Sporting CP":228,"Tottenham":47,"Union St. Gilloise":1393,
    "Villarreal":533,"AS Roma":497,"Aston Villa":66,"Bologna":500,"Brann":319,
    "Celta Vigo":538,"Celtic":247,"Dinamo Zagreb":620,"FC Basel 1893":551,
    "FC Midtjylland":397,"FC Porto":212,"FCSB":559,"FK Crvena Zvezda":598,
    "Fenerbahce":611,"Fenerbahçe":611,"Ferencvarosi TC":651,"Feyenoord":209,
    "GO Ahead Eagles":410,"Genk":742,"Lille":79,"Ludogorets":566,"Lyon":80,
    "Maccabi Tel Aviv":604,"Malmo FF":375,"Nice":84,"Nottingham Forest":65,
    "PAOK":619,"Panathinaikos":617,"Plzen":567,"Rangers":257,"Real Betis":543,
    "Red Bull Salzburg":571,"SC Braga":217,"SC Freiburg":160,"Sturm Graz":637,
    "Utrecht":207,"VfB Stuttgart":172,"BSC Young Boys":565,"Shakhtar Donetsk":550,
    "AEK Athens FC":575,"AEK Larnaca":614,"AZ Alkmaar":201,"Aberdeen":252,
    "BK Hacken":367,"Breidablik":276,"Celje":4360,"Crystal Palace":52,"Drita":14281,
    "Dynamo Kyiv":572,"FC Noah":3684,"FSV Mainz 05":164,"Fiorentina":502,
    "HNK Rijeka":561,"Jagiellonia":336,"KuPS":1165,"Lech Poznan":347,
    "Legia Warszawa":339,"Omonia Nicosia":3402,"Rapid Vienna":781,"Rayo Vallecano":728,
    "Shamrock Rovers":652,"Slovan Bratislava":656,"Sparta Praha":628,"Strasbourg":95,
}

def _fetch_rose_live(team_ids=None):
    """Scarica rose complete di tutte le squadre da API Football."""
    global ROSE_LIVE, ALLENATORI_LIVE, ROSE_LAST_UPDATE
    if team_ids is None:
        team_ids = _TEAM_IDS
    try:
        for nome, team_id in team_ids.items():
            try:
                # Rosa
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
                        ruolo_en = p.get("position", "")
                        ruolo = _RUOLO_MAP.get(ruolo_en, "C")
                        rosa.append({
                            "nome": p.get("name", "?"),
                            "ruolo": ruolo,
                            "numero": p.get("number", 0) or 0,
                            "foto": p.get("photo", ""),
                        })
                    if rosa:
                        ROSE_LIVE[nome] = rosa

                # Allenatore
                req2 = urllib.request.Request(
                    f"https://{FOOTBALL_API_HOST}/coachs?team={team_id}",
                    headers={"x-apisports-key": FOOTBALL_API_KEY, "User-Agent": "Mozilla/5.0"}
                )
                with urllib.request.urlopen(req2, timeout=15) as r:
                    data2 = json.loads(r.read().decode())
                if data2.get("response") and len(data2["response"]) > 0:
                    # Prendi l'allenatore attuale (ultimo nella lista)
                    for coach in data2["response"]:
                        career = coach.get("career", [])
                        for c in career:
                            if c.get("team", {}).get("id") == team_id and c.get("end") is None:
                                ALLENATORI_LIVE[nome] = coach.get("name", "N/D")
                                break

                time.sleep(0.5)  # Rate limiting
            except Exception:
                pass

        if ROSE_LIVE:
            ROSE_LAST_UPDATE = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")
            print(f"👕 ROSE LIVE: {len(ROSE_LIVE)} squadre aggiornate")
    except Exception as e:
        print(f"❌ Errore fetch rose: {e}")

def _fetch_infortunati_live():
    """Scarica infortunati ATTUALI da API Football (solo quelli non recuperati)."""
    global INFORTUNATI_LIVE
    try:
        # Prendi solo infortuni recenti (ultimi fixture)
        req = urllib.request.Request(
            f"https://{FOOTBALL_API_HOST}/injuries?league=135&season=2025",
            headers={"x-apisports-key": FOOTBALL_API_KEY, "User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode())

        if data.get("response"):
            inj_per_team = {}
            seen_players = {}  # Per evitare duplicati: {team_nome_giocatore: ultimo_infortunio}
            for item in data["response"]:
                team_name = FOOTBALL_NOME_MAP.get(
                    item.get("team", {}).get("name", ""),
                    item.get("team", {}).get("name", "")
                )
                player = item.get("player", {})
                player_name = player.get("name", "?")
                reason = player.get("reason", "") or ""
                ptype = player.get("type", "") or ""
                fixture_date = item.get("fixture", {}).get("date", "")

                if not team_name or not player_name:
                    continue

                # Chiave univoca: squadra + giocatore
                key = f"{team_name}_{player_name}"
                # Tieni solo l'infortunio piu' recente per ogni giocatore
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

            # Raggruppa per squadra, max 8 per squadra
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

@app.get("/api/classifica")
async def classifica():
    cl = CLASSIFICA_CACHE.get("serie-a") or CLASS_FALLBACK
    mc = MARCATORI_CACHE.get("serie-a") or MARC_FALLBACK
    return {
        "classifica": cl,
        "marcatori": mc,
        "aggiornamento": CLASSIFICA_LAST_UPDATE.get("serie-a", "") or "Dati base",
        "live": CLASSIFICA_CACHE.get("serie-a") is not None,
    }

# ─────────────────────────────
# MARCATORI
# ─────────────────────────────
@app.get("/api/marcatori")
async def marcatori():
    try:
        return get_marcatori()
    except Exception as e:
        print("❌ ERRORE MARCATORI:", e)
        return []

# ─────────────────────────────
# SQUADRE (rose, formazioni, infortunati)
# ─────────────────────────────
ALLENATORI = {"Inter":"Cristian Chivu","Milan":"Massimiliano Allegri","Napoli":"Antonio Conte","Como":"Cesc Fabregas","Juventus":"Luciano Spalletti","Roma":"Gian Piero Gasperini","Atalanta":"Raffaele Palladino","Lazio":"Maurizio Sarri","Bologna":"Vincenzo Italiano","Sassuolo":"Fabio Grosso","Udinese":"Kosta Runjaic","Parma":"Carlos Cuesta","Genoa":"Patrick Vieira","Torino":"Roberto D'Aversa","Cagliari":"Fabio Pisacane","Fiorentina":"Paolo Vanoli","Cremonese":"Davide Nicola","Lecce":"Eusebio Di Francesco","Verona":"Paolo Sammarco","Pisa":"Oscar Hiljemark"}

TOP_SCORER = {
    "Inter":["Lautaro Martinez (14 gol)","Hakan Calhanoglu (8)","Marcus Thuram (7)"],
    "Milan":["Rafael Leao (9)","Christian Pulisic (8)","Santiago Gimenez (5)"],
    "Napoli":["Rasmus Hojlund (10)","Scott McTominay (7)","Matteo Politano (5)"],
    "Como":["Tasos Douvikas (11)","Nico Paz (10)","Nicolas Kuhn (4)"],
    "Juventus":["Kenan Yildiz (10)","Dusan Vlahovic (6)","Francisco Conceicao (5)"],
    "Roma":["Donyell Malen (7)","Paulo Dybala (5)","Matias Soule (4)"],
    "Atalanta":["Gianluca Scamacca (8)","Nikola Krstovic (8)","Charles De Ketelaere (6)"],
    "Lazio":["Daniel Maldini (6)","Boulaye Dia (5)","Mattia Zaccagni (4)"],
    "Bologna":["Santiago Castro (6)","Riccardo Orsolini (5)","Federico Bernardeschi (4)"],
    "Sassuolo":["Domenico Berardi (7)","Andrea Pinamonti (7)","Armand Lauriente (4)"],
    "Udinese":["Keinan Davis (10)","Nicolo Zaniolo (5)","Adam Buksa (3)"],
    "Parma":["Mateo Pellegrino (8)","Gabriel Strefezza (4)","Adrian Bernabe (3)"],
    "Genoa":["Vitinha (5)","Lorenzo Colombo (4)","Junior Messias (3)"],
    "Torino":["Giovanni Simeone (8)","Nikola Vlasic (7)","Che Adams (5)"],
    "Cagliari":["Sebastiano Esposito (5)","Semih Kilicsoy (4)","Gianluca Gaetano (3)"],
    "Fiorentina":["Moise Kean (8)","Albert Gudmundsson (5)","Lucas Beltran (3)"],
    "Cremonese":["Jamie Vardy (5)","Antonio Sanabria (4)","Milan Djuric (3)"],
    "Lecce":["Walid Cheddira (4)","Lameck Banda (3)","Santiago Pierotti (2)"],
    "Verona":["Casper Tengstedt (5)","Thomas Henry (4)","Tomas Suslov (3)"],
    "Pisa":["Henrik Meister (5)","Matteo Tramoni (4)","Samuel Iling-Junior (3)"],
}

FORMAZIONI = {
    "Inter":{"modulo":"3-5-2","titolari":["Sommer","Bastoni","Akanji","Bisseck","Dimarco","Barella","Calhanoglu","Sucic","Dumfries","Thuram","Bonny"]},
    "Milan":{"modulo":"4-2-3-1","titolari":["Maignan","Bartesaghi","De Winter","Tomori","Estupinan","Fofana","Ricci","Saelemaekers","Modric","Pulisic","Gimenez"]},
    "Napoli":{"modulo":"3-4-2-1","titolari":["Meret","Olivera","Buongiorno","Beukema","Gutierrez","Lobotka","Anguissa","McTominay","Politano","De Bruyne","Hojlund"]},
    "Como":{"modulo":"4-2-3-1","titolari":["Butez","Moreno","Kempf","Diego Carlos","Van der Brempt","Caqueret","Perrone","Da Cunha","Paz","Kuhn","Douvikas"]},
    "Juventus":{"modulo":"4-2-3-1","titolari":["Di Gregorio","Cambiaso","Gatti","Kelly","Kalulu","Locatelli","Thuram K.","Yildiz","Koopmeiners","Conceicao","Vlahovic"]},
    "Roma":{"modulo":"3-4-2-1","titolari":["Svilar","Hermoso","Mancini","Ndicka","Tsimikas","Cristante","El Aynaoui","Rensch","Pellegrini","Soule","Malen"]},
    "Atalanta":{"modulo":"3-4-2-1","titolari":["Carnesecchi","Kolasinac","Hien","Scalvini","Zappacosta","De Roon","Ederson","Bellanova","Samardzic","De Ketelaere","Krstovic"]},
    "Lazio":{"modulo":"4-3-3","titolari":["Motta","Tavares","Romagnoli","Provstgaard","Marusic","Dele-Bashiru","Patric","Taylor","Pedro","Maldini","Isaksen"]},
    "Bologna":{"modulo":"4-3-3","titolari":["Ravaglia","Miranda","Lucumi","Vitik","Joao Mario","Ferguson","Freuler","Moro","Rowe","Castro","Orsolini"]},
    "Sassuolo":{"modulo":"4-2-3-1","titolari":["Muric","Garcia","Muharemovic","Idzes","Walukiewicz","Kone","Vranckx","Lauriente","Volpato","Berardi","Pinamonti"]},
    "Udinese":{"modulo":"3-5-2","titolari":["Okoye","Bertola","Kristensen","Solet","Zemura","Zarraga","Miller","Karlstrom","Ehizibue","Zaniolo","Davis"]},
    "Parma":{"modulo":"3-4-2-1","titolari":["Suzuki","Valenti","Circati","Delprato","Valeri","Keita","Sorensen","Britschgi","Ondrejka","Strefezza","Pellegrino"]},
    "Genoa":{"modulo":"3-5-2","titolari":["Bijlow","Martin","Ostigard","Vasquez","Sabelli","Baldanzi","Malinovskyi","Frendrup","Norton-Cuffy","Vitinha","Colombo"]},
    "Torino":{"modulo":"3-5-2","titolari":["Israel","Maripan","Ismajli","Coco","Nkounkou","Gineitis","Ilic","Casadei","Pedersen","Vlasic","Adams"]},
    "Cagliari":{"modulo":"3-5-2","titolari":["Caprile","Rodriguez","Mina","Ze Pedro","Obert","Folorunsho","Gaetano","Adopo","Palestra","Esposito","Kilicsoy"]},
    "Fiorentina":{"modulo":"4-3-3","titolari":["De Gea","Gosens","Ranieri","Pongracic","Fortini","Fagioli","Ndour","Brescianini","Gudmundsson","Kean","Parisi"]},
    "Cremonese":{"modulo":"4-4-2","titolari":["Audero","Pezzella","Luperto","Bianchetti","Terracciano","Vandeputte","Grassi","Maleh","Zerbin","Vardy","Bonazzoli"]},
    "Lecce":{"modulo":"4-3-3","titolari":["Falcone","Gallo","Jean","Siebert","Veiga","Ramadani","Fofana","Sala","Pierotti","Cheddira","Banda"]},
    "Verona":{"modulo":"3-5-2","titolari":["Montipo","Valentini","Nelsson","Edmundsson","Frese","Harroui","Gagliardini","Akpa Akpro","Belghali","Bowie","Orban"]},
    "Pisa":{"modulo":"3-4-2-1","titolari":["Semper","Angori","Calabresi","Canestrelli","Cuadrado","Aebischer","Hojholt","Loyola","Tramoni","Stengs","Meister"]},
}

INFORTUNATI = {
    "Inter":[{"nome":"Lautaro Martinez","tipo":"infortunio","dettaglio":"Da monitorare, rientro inizio aprile"},{"nome":"Mkhitaryan","tipo":"infortunio","dettaglio":"Problema muscolare"},{"nome":"Carlos Augusto","tipo":"squalifica","dettaglio":"Squalificato 1 giornata"}],
    "Milan":[{"nome":"Gabbia","tipo":"infortunio","dettaglio":"Problema muscolare, rientro aprile"},{"nome":"Loftus-Cheek","tipo":"infortunio","dettaglio":"Infortunio ginocchio"},{"nome":"Leao","tipo":"dubbio","dettaglio":"Affaticamento, da valutare"}],
    "Napoli":[{"nome":"Neres","tipo":"infortunio","dettaglio":"Problema muscolare, rientro aprile"},{"nome":"Di Lorenzo","tipo":"infortunio","dettaglio":"Distorsione ginocchio, fine aprile"},{"nome":"Rrahmani","tipo":"infortunio","dettaglio":"Rientro maggio"}],
    "Juventus":[{"nome":"Holm","tipo":"infortunio","dettaglio":"Rientro inizio aprile"}],
    "Roma":[{"nome":"Kone","tipo":"infortunio","dettaglio":"Fine aprile"},{"nome":"Dybala","tipo":"infortunio","dettaglio":"Fine aprile"},{"nome":"Dovbyk","tipo":"infortunio","dettaglio":"Rientro maggio"},{"nome":"Ferguson","tipo":"infortunio","dettaglio":"Stagione finita"}],
    "Atalanta":[{"nome":"Scamacca","tipo":"dubbio","dettaglio":"Da monitorare"}],
    "Lazio":[{"nome":"Zaccagni","tipo":"infortunio","dettaglio":"Fine aprile"},{"nome":"Rovella","tipo":"infortunio","dettaglio":"Stagione finita"},{"nome":"Provedel","tipo":"infortunio","dettaglio":"Stagione finita"}],
    "Bologna":[{"nome":"Odgaard","tipo":"infortunio","dettaglio":"Meta aprile"},{"nome":"Pobega","tipo":"infortunio","dettaglio":"Meta aprile"},{"nome":"Skorupski","tipo":"infortunio","dettaglio":"Maggio"}],
    "Sassuolo":[{"nome":"Pieragnolo","tipo":"infortunio","dettaglio":"Inizio aprile"},{"nome":"Cande","tipo":"infortunio","dettaglio":"Stagione finita"},{"nome":"Fadera","tipo":"infortunio","dettaglio":"Maggio"}],
    "Udinese":[{"nome":"Buksa","tipo":"infortunio","dettaglio":"Meta aprile"},{"nome":"Zanoli","tipo":"infortunio","dettaglio":"Stagione finita"}],
    "Parma":[{"nome":"Almqvist","tipo":"infortunio","dettaglio":"Rientro dopo sosta"},{"nome":"Cremaschi","tipo":"infortunio","dettaglio":"Stagione finita"}],
    "Genoa":[{"nome":"Onana","tipo":"dubbio","dettaglio":"Da valutare"}],
    "Torino":[{"nome":"Aboukhlal","tipo":"dubbio","dettaglio":"Da valutare"}],
    "Cagliari":[{"nome":"Felici","tipo":"infortunio","dettaglio":"Stagione finita"},{"nome":"Idrissi","tipo":"infortunio","dettaglio":"Stagione finita"}],
    "Fiorentina":[{"nome":"Solomon","tipo":"infortunio","dettaglio":"Rientro aprile"},{"nome":"Lamptey","tipo":"infortunio","dettaglio":"Rientro aprile"}],
    "Cremonese":[{"nome":"Baschirotto","tipo":"infortunio","dettaglio":"Inizio aprile"}],
    "Lecce":[{"nome":"Gaspar","tipo":"infortunio","dettaglio":"Stagione finita"},{"nome":"Berisha","tipo":"infortunio","dettaglio":"Stagione finita"},{"nome":"Camarda","tipo":"infortunio","dettaglio":"Rientro aprile"}],
    "Verona":[], "Pisa":[{"nome":"Denoon","tipo":"infortunio","dettaglio":"Lungodegente"},{"nome":"Scuffet","tipo":"infortunio","dettaglio":"Inizio aprile"}],
    "Como":[{"nome":"Addai","tipo":"infortunio","dettaglio":"Stagione finita"}],
}

ROSE = {
    "Inter":[("Sommer","P",1),("Martinez J.","P",13),("Di Gennaro","P",12),("Bastoni","D",95),("Bisseck","D",31),("Akanji","D",25),("De Vrij","D",6),("Acerbi","D",15),("Dimarco","D",32),("Carlos Augusto","D",30),("Dumfries","D",2),("Darmian","D",36),("Calhanoglu","C",20),("Barella","C",23),("Sucic","C",8),("Frattesi","C",16),("Diouf","C",17),("Zielinski","C",7),("Mkhitaryan","C",22),("Lautaro Martinez","A",10),("Thuram","A",9),("Bonny","A",14),("Pio Esposito","A",94),("Luis Henrique","A",11)],
    "Milan":[("Maignan","P",16),("Terracciano","P",1),("Torriani","P",96),("Pavlovic","D",31),("De Winter","D",5),("Tomori","D",23),("Gabbia","D",46),("Estupinan","D",2),("Bartesaghi","D",33),("Ricci","C",4),("Fofana","C",19),("Rabiot","C",12),("Loftus-Cheek","C",8),("Modric","C",14),("Jashari","C",30),("Leao","A",10),("Pulisic","A",11),("Nkunku","A",18),("Gimenez","A",7),("Fullkrug","A",9),("Saelemaekers","A",56)],
    "Napoli":[("Meret","P",1),("Contini","P",14),("Milinkovic-Savic","P",32),("Buongiorno","D",4),("Beukema","D",31),("Rrahmani","D",13),("Gutierrez","D",3),("Olivera","D",17),("Di Lorenzo","D",22),("Spinazzola","D",37),("Mazzocchi","D",30),("Gilmour","C",6),("Lobotka","C",68),("McTominay","C",8),("Anguissa","C",99),("De Bruyne","C",11),("Hojlund","A",19),("Lukaku","A",9),("Neres","A",7),("Politano","A",21),("Giovane","A",23),("Alisson Santos","A",77)],
    "Juventus":[("Di Gregorio","P",16),("Perin","P",1),("Pinsoglio","P",23),("Bremer","D",3),("Kalulu","D",15),("Kelly","D",6),("Gatti","D",4),("Cambiaso","D",27),("Cabal","D",32),("Holm","D",2),("Locatelli","C",5),("Thuram K.","C",19),("McKennie","C",22),("Koopmeiners","C",8),("Kostic","C",18),("Vlahovic","A",9),("David","A",30),("Openda","A",20),("Conceicao","A",7),("Yildiz","A",10),("Zhegrova","A",11),("Boga","A",14)],
    "Roma":[("Svilar","P",99),("Gollini","P",95),("Zelezny","P",91),("Ndicka","D",5),("Mancini","D",23),("Hermoso","D",22),("Angelino","D",3),("Tsimikas","D",12),("Wesley","D",43),("Celik","D",19),("Rensch","D",2),("Cristante","C",4),("Kone","C",17),("El Aynaoui","C",8),("Pisilli","C",61),("Pellegrini","C",7),("Dybala","A",21),("Malen","A",14),("Ferguson","A",11),("Dovbyk","A",9),("Soule","A",18),("El Shaarawy","A",92),("Zaragoza","A",97),("Vaz","A",78)],
    "Atalanta":[("Carnesecchi","P",29),("Sportiello","P",57),("Rossi","P",31),("Scalvini","D",42),("Hien","D",4),("Kossounou","D",3),("Kolasinac","D",23),("Djimsiti","D",19),("Ederson","C",13),("Musah","C",6),("Pasalic","C",8),("De Roon","C",15),("Bellanova","C",16),("Zappacosta","C",77),("Zalewski","C",59),("De Ketelaere","A",17),("Samardzic","A",10),("Raspadori","A",18),("Scamacca","A",9),("Krstovic","A",90)],
    "Lazio":[("Provedel","P",94),("Motta","P",40),("Furlanetto","P",55),("Gila","D",34),("Provstgaard","D",25),("Romagnoli","D",13),("Gigot","D",2),("Patric","D",4),("Tavares","D",17),("Pellegrini L.","D",3),("Marusic","D",77),("Lazzari","D",29),("Rovella","C",6),("Belahyane","C",21),("Taylor","C",24),("Dele-Bashiru","C",7),("Maldini","A",27),("Przyborek","A",28),("Zaccagni","A",10),("Isaksen","A",18),("Dia","A",19),("Pedro","A",9),("Noslin","A",14),("Ratkov","A",20)],
    "Bologna":[("Skorupski","P",1),("Ravaglia","P",13),("Pessina","P",25),("Lucumi","D",26),("Heggem","D",14),("Vitik","D",41),("Helland","D",5),("Casale","D",16),("Miranda","D",33),("Joao Mario","D",17),("Zortea","D",20),("Moro","C",6),("Ferguson L.","C",19),("Pobega","C",4),("Freuler","C",8),("Odgaard","C",21),("Sohm","C",23),("Castro","A",9),("Dallinga","A",24),("Orsolini","A",7),("Bernardeschi","A",10),("Rowe","A",11)],
    "Sassuolo":[("Muric","P",49),("Turati","P",13),("Zacchi","P",16),("Idzes","D",21),("Doig","D",3),("Walukiewicz","D",6),("Romagna","D",19),("Pieragnolo","D",15),("Garcia","D",23),("Coulibaly","D",25),("Lipani","C",35),("Boloca","C",11),("Matic","C",18),("Kone","C",90),("Thorstvedt","C",42),("Vranckx","C",40),("Berardi","A",25),("Pinamonti","A",9),("Lauriente","A",45),("Volpato","A",7)],
    "Udinese":[("Okoye","P",40),("Sava","P",90),("Nunziante","P",1),("Solet","D",28),("Kristensen","D",31),("Bertola","D",13),("Mlacic","D",22),("Kabasele","D",27),("Zemura","D",33),("Kamara","D",11),("Zanoli","D",59),("Ehizibue","D",19),("Karlstrom","C",8),("Camara","C",29),("Miller","C",38),("Zarraga","C",6),("Piotrowski","C",24),("Zaniolo","A",10),("Davis","A",9),("Buksa","A",18),("Bayo","A",15)],
    "Parma":[("Suzuki","P",31),("Corvi","P",40),("Rinaldi","P",66),("Circati","D",39),("Valenti","D",5),("Delprato","D",15),("Valeri","D",14),("Carboni","D",29),("Britschgi","D",27),("Ndiaye","D",3),("Keita","C",16),("Estevez","C",8),("Bernabe","C",10),("Sorensen","C",22),("Nicolussi Caviglia","C",41),("Oristanio","C",21),("Strefezza","A",7),("Almqvist","A",11),("Pellegrino","A",9),("Ondrejka","A",17)],
    "Genoa":[("Bijlow","P",16),("Leali","P",1),("Siegrist","P",31),("Vasquez","D",22),("Ostigard","D",5),("Marcandalli","D",27),("Zattstrom","D",13),("Martin","D",3),("Norton-Cuffy","D",15),("Sabelli","D",20),("Frendrup","C",32),("Onana","C",14),("Malinovskyi","C",17),("Baldanzi","C",8),("Ellertsson","C",77),("Messias","A",10),("Colombo","A",29),("Vitinha","A",9),("Ekuban","A",18),("Ekhator","A",21)],
    "Torino":[("Israel","P",81),("Paleari","P",1),("Siviero","P",99),("Coco","D",23),("Ismajli","D",44),("Maripan","D",13),("Ebosse","D",77),("Biraghi","D",34),("Pedersen","D",16),("Nkounkou","D",25),("Obrador","D",33),("Prati","C",4),("Casadei","C",22),("Ilic","C",8),("Gineitis","C",66),("Lazaro","C",20),("Tameze","C",61),("Vlasic","A",10),("Adams","A",19),("Simeone","A",7),("Aboukhlal","A",17)],
    "Cagliari":[("Caprile","P",1),("Sherri","P",12),("Ciocci","P",24),("Dossena","D",22),("Obert","D",33),("Rodriguez","D",15),("Mina","D",26),("Ze Pedro","D",32),("Zappa","D",28),("Raterink","D",18),("Sulemana","C",25),("Adopo","C",8),("Folorunsho","C",90),("Mazzitelli","C",4),("Gaetano","C",10),("Deiola","C",14),("Esposito","A",94),("Kilicsoy","A",9),("Felici","A",17),("Borrelli","A",29)],
    "Fiorentina":[("De Gea","P",43),("Christensen","P",53),("Lezzerini","P",1),("Comuzzo","D",15),("Pongracic","D",5),("Ranieri","D",6),("Gosens","D",21),("Dodo","D",2),("Lamptey","D",48),("Parisi","D",65),("Fortini","D",29),("Mandragora","C",8),("Fagioli","C",44),("Ndour","C",27),("Brescianini","C",4),("Fazzini","C",22),("Gudmundsson","A",10),("Kean","A",9),("Beltran","A",7),("Sottil","A",14),("Harrison","A",17),("Solomon","A",19)],
    "Cremonese":[("Audero","P",1),("Silvestri","P",16),("Nava","P",69),("Pezzella","D",3),("Luperto","D",5),("Baschirotto","D",6),("Bianchetti","D",15),("Barbieri","D",4),("Faye","D",30),("Terracciano F.","D",24),("Thorsby","C",2),("Bondo","C",38),("Vandeputte","C",27),("Maleh","C",29),("Payero","C",32),("Grassi","C",33),("Collocolo","C",18),("Vardy","A",10),("Djuric","A",9),("Zerbin","A",7),("Okereke","A",77),("Sanabria","A",99),("Bonazzoli","A",90)],
    "Lecce":[("Falcone","P",30),("Fruchtl","P",1),("Samooja","P",32),("Gaspar","D",4),("Gallo","D",25),("Veiga","D",17),("Jean","D",18),("Perez","D",13),("Ndaba","D",3),("Siebert","D",5),("Ramadani","C",20),("Fofana","C",8),("Berisha","C",10),("Coulibaly","C",29),("Sala","C",6),("Helgason","C",14),("Marchwinski","C",36),("Banda","A",19),("Camarda","A",22),("Cheddira","A",99),("N'Dri","A",11),("Pierotti","A",50)],
    "Verona":[("Montipo","P",1),("Perilli","P",34),("Toniolo","P",94),("Nelsson","D",15),("Bella-Kotchap","D",37),("Slotsager","D",19),("Edmundsson","D",5),("Frese","D",3),("Bradaric","D",12),("Lirola","D",14),("Oyegoke","D",2),("Al-Musrati","C",73),("Lovric","C",4),("Serdar","C",8),("Harroui","C",21),("Gagliardini","C",63),("Akpa Akpro","C",11),("Suslov","A",10),("Henry","A",9),("Tengstedt","A",20),("Lazovic","A",17),("Duda","A",27)],
    "Pisa":[("Semper","P",1),("Nicolas","P",12),("Scuffet","P",22),("Canestrelli","D",5),("Calabresi","D",33),("Loyola","D",35),("Angori","D",3),("Albiol","D",39),("Marin","C",6),("Leris","C",7),("Hojholt","C",8),("Cuadrado","C",11),("Akinsanmiro","C",14),("Aebischer","C",20),("Stengs","C",23),("Lorran","C",99),("Meister","A",9),("Tramoni","A",10),("Durosinmi","A",17),("Iling-Junior","A",19),("Moreo","A",32)],
    "Como":[("Butez","P",1),("Tornqvist","P",21),("Cavlina","P",44),("Diego Carlos","D",34),("Kempf","D",2),("Goldaniga","D",5),("Valle","D",3),("Moreno","D",18),("Van der Brempt","D",77),("Vojvoda","D",31),("Smolcic","D",28),("Ramon","D",14),("Perrone","C",23),("Da Cunha","C",33),("Caqueret","C",6),("Ladho","C",15),("Sergi Roberto","C",8),("Paz","C",10),("Baturina","C",20),("Diao","A",38),("Kuhn","A",19),("Douvikas","A",11),("Morata","A",7),("Jesus Rodriguez","A",17)],
}

_FORMAZIONE_CACHE = {}  # Cache formazioni on-demand
_COACH_CACHE = {}  # Cache allenatori on-demand

def _get_last_lineup(team_name):
    """Scarica la formazione dall'ultima partita giocata da una squadra."""
    if team_name in _FORMAZIONE_CACHE:
        return _FORMAZIONE_CACHE[team_name]
    # Cerca team_id in entrambi i campionati
    team_id = _TEAM_IDS.get(team_name) or PL_TEAM_IDS.get(team_name) or LL_TEAM_IDS.get(team_name) or _ALL_EURO_IDS.get(team_name)
    if not team_id:
        return None
    try:
        # Ultima partita giocata
        req = urllib.request.Request(
            f"https://{FOOTBALL_API_HOST}/fixtures?team={team_id}&last=1",
            headers={"x-apisports-key": FOOTBALL_API_KEY, "User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read().decode())
        if not data.get("response"):
            return None
        fix_id = data["response"][0].get("fixture", {}).get("id")
        if not fix_id:
            return None
        # Lineup di quella partita
        req2 = urllib.request.Request(
            f"https://{FOOTBALL_API_HOST}/fixtures/lineups?fixture={fix_id}",
            headers={"x-apisports-key": FOOTBALL_API_KEY, "User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req2, timeout=10) as r:
            data2 = json.loads(r.read().decode())
        if data2.get("response"):
            for lineup in data2["response"]:
                if lineup.get("team", {}).get("id") == team_id:
                    formazione = lineup.get("formation", "4-4-2")
                    titolari = [p.get("player", {}).get("name", "?") for p in lineup.get("startXI", [])]
                    # Salva anche l'allenatore
                    coach = lineup.get("coach", {}).get("name", "")
                    if coach:
                        _COACH_CACHE[team_name] = coach
                        ALLENATORI_LIVE[team_name] = coach
                    if titolari:
                        result = {"modulo": formazione, "titolari": titolari}
                        _FORMAZIONE_CACHE[team_name] = result
                        return result
    except Exception:
        pass
    return None

def _get_coach_ondemand(team_name):
    """Scarica l'allenatore attuale da API Football."""
    if team_name in _COACH_CACHE:
        return _COACH_CACHE[team_name]
    team_id = _TEAM_IDS.get(team_name) or PL_TEAM_IDS.get(team_name) or LL_TEAM_IDS.get(team_name) or _ALL_EURO_IDS.get(team_name)
    if not team_id:
        return None
    try:
        req = urllib.request.Request(
            f"https://{FOOTBALL_API_HOST}/coachs?team={team_id}",
            headers={"x-apisports-key": FOOTBALL_API_KEY, "User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read().decode())
        if data.get("response"):
            for coach in data["response"]:
                career = coach.get("career", [])
                for c in career:
                    if c.get("team", {}).get("id") == team_id and c.get("end") is None:
                        name = coach.get("name", "N/D")
                        _COACH_CACHE[team_name] = name
                        return name
            # Se non trovato con end=None, prendi l'ultimo
            if data["response"]:
                name = data["response"][-1].get("name", "N/D")
                _COACH_CACHE[team_name] = name
                return name
    except Exception:
        pass
    return None

_ROSA_CACHE_OD = {}  # Cache rosa on-demand

def _get_squad_ondemand(team_name):
    """Scarica la rosa di una squadra on-demand da API Football."""
    if team_name in _ROSA_CACHE_OD:
        return _ROSA_CACHE_OD[team_name]
    team_id = _TEAM_IDS.get(team_name) or PL_TEAM_IDS.get(team_name) or LL_TEAM_IDS.get(team_name) or _ALL_EURO_IDS.get(team_name)
    if not team_id:
        return []
    try:
        req = urllib.request.Request(
            f"https://{FOOTBALL_API_HOST}/players/squads?team={team_id}",
            headers={"x-apisports-key": FOOTBALL_API_KEY, "User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read().decode())
        if data.get("response") and len(data["response"]) > 0:
            players = data["response"][0].get("players", [])
            rosa = []
            for p in players:
                ruolo = _RUOLO_MAP.get(p.get("position", ""), "C")
                rosa.append({"nome": p.get("name", "?"), "ruolo": ruolo, "numero": p.get("number", 0) or 0, "foto": p.get("photo", "")})
            if rosa:
                _ROSA_CACHE_OD[team_name] = rosa
                return rosa
    except Exception:
        pass
    return []

def _get_injuries_ondemand(team_name):
    """Scarica SOLO infortunati attuali di una squadra (ultimi 2 fixture)."""
    team_id = _TEAM_IDS.get(team_name) or PL_TEAM_IDS.get(team_name) or LL_TEAM_IDS.get(team_name) or _ALL_EURO_IDS.get(team_name)
    if not team_id:
        return []
    try:
        # Prendi solo le ultime 2 partite per avere infortuni recenti
        req = urllib.request.Request(
            f"https://{FOOTBALL_API_HOST}/injuries?team={team_id}&season=2025",
            headers={"x-apisports-key": FOOTBALL_API_KEY, "User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read().decode())
        if data.get("response"):
            # Prendi solo infortuni dalle ultime 2 giornate (fixture piu' recenti)
            fixtures_dates = sorted(set(item.get("fixture", {}).get("date", "")[:10] for item in data["response"]), reverse=True)
            recent_dates = set(fixtures_dates[:2])  # Solo ultime 2 date
            seen = {}
            for item in data["response"]:
                fix_date = item.get("fixture", {}).get("date", "")[:10]
                if fix_date not in recent_dates:
                    continue
                player = item.get("player", {})
                name = player.get("name", "?")
                reason = player.get("reason", "") or ""
                ptype = player.get("type", "") or ""
                if name in seen:
                    continue
                seen[name] = {"nome": name, "tipo": "squalifica" if "Suspended" in reason or "Red" in reason else "infortunio", "dettaglio": reason or ptype or "Indisponibile"}
            return [v for v in list(seen.values())[:6]]
    except Exception:
        pass
    return []

@app.get("/api/squadra/{nome}")
async def squadra(nome: str):
    n = nome.strip().title()
    # Formazione: live > hardcoded > on-demand
    form = LIVE_FORMAZIONI.get(n) or FORMAZIONI.get(n)
    if not form:
        form = _get_last_lineup(n)
    # Infortunati: live cache > hardcoded > on-demand
    inj = INFORTUNATI_LIVE.get(n) if INFORTUNATI_LIVE.get(n) else (LIVE_INFORTUNATI.get(n) if LIVE_INFORTUNATI.get(n) is not None else INFORTUNATI.get(n, []))
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
        rosa = [{"nome":g[0],"ruolo":g[1],"numero":g[2]} for g in ROSE[n]]
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
# SCHEDINA DEL GIORNO (IA)
# ─────────────────────────────
@app.get("/api/schedina")
async def schedina_del_giorno():
    """L'IA seleziona le 3-5 giocate piu' sicure della PROSSIMA giornata Serie A."""
    # Trova la prossima giornata da giocare automaticamente
    prossima_g = None
    for g_num in range(31, 39):
        cal = CAL_HARDCODED.get(g_num)
        if not cal:
            continue
        # Controlla se la giornata e' gia' stata giocata (tutte le partite nei risultati live)
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

    giocate = []
    cal = CAL_HARDCODED.get(prossima_g, {})
    partite = cal.get("partite", [])

    for home, away in partite:
        try:
            raw = genera_pronostico(home, away)
            if raw.get("sicura"):
                giocate.append({
                    "home": home, "away": away,
                    "tip": raw["suggerimento"],
                    "tip_label": raw["sugg_label"],
                    "prob": max(raw["prob_1"], raw["prob_x"], raw["prob_2"]),
                    "quota": raw.get(f"quota_{raw['suggerimento'].lower().replace('x','x')}", 0),
                    "confidence": raw["confidence"],
                    "over_under": ("Over 2.5 " + str(raw.get("over_25",50)) + "%") if raw.get("over_25",0) > 50 else ("Under 2.5 " + str(raw.get("under_25",50)) + "%"),
                    "goal": ("Goal Si " + str(raw.get("goal_si",50)) + "%") if raw.get("goal_si",0) > 50 else ("Goal No " + str(raw.get("goal_no",50)) + "%"),
                })
        except Exception:
            continue

    giocate.sort(key=lambda x: -x["confidence"])
    top = giocate[:5]
    quota_tot = 1.0
    for g in top:
        q = g.get("quota", 1.5)
        if q > 1: quota_tot *= q

    return {
        "giornata": prossima_g,
        "data": cal.get("data", ""),
        "giocate": top,
        "n_giocate": len(top),
        "quota_totale": round(quota_tot, 2),
        "tipo": "Pronostici ad alta confidenza selezionati dall'IA",
    }

@app.get("/api/schedina-pl")
async def schedina_pl():
    """Schedina del giorno Premier League - prossima giornata."""
    # Prendi il calendario PL per trovare la prossima giornata
    try:
        cal_data = LIVE_RESULTS_CACHE_ML.get("premier-league") or []
        cl_pl = CLASSIFICA_CACHE.get("premier-league") or []
        if not cl_pl:
            _fetch_league_data("premier-league")
            cl_pl = CLASSIFICA_CACHE.get("premier-league") or []

        # Prendi fixtures future dalla cache
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
                if conf >= 0.70 or mp > 50:
                    giocate.append({
                        "home": home, "away": away,
                        "tip": raw.get("suggerimento", "?"),
                        "tip_label": raw.get("sugg_label", ""),
                        "prob": mp,
                        "quota": raw.get(f"quota_{raw.get('suggerimento','1').lower()}", 1.5),
                        "confidence": conf,
                        "over_under": ("Over 2.5 " + str(raw.get("over_25",50)) + "%") if raw.get("over_25",0) > 50 else ("Under 2.5 " + str(raw.get("under_25",50)) + "%"),
                        "goal": ("Goal Si " + str(raw.get("goal_si",50)) + "%") if raw.get("goal_si",0) > 50 else ("Goal No " + str(raw.get("goal_no",50)) + "%"),
                    })
            except Exception:
                continue

        giocate.sort(key=lambda x: -x["confidence"])
        top = giocate[:5]
        quota_tot = 1.0
        for g in top:
            q = g.get("quota", 1.5)
            if q > 1: quota_tot *= q

        return {
            "giornata": giornata_num,
            "giocate": top,
            "n_giocate": len(top),
            "quota_totale": round(quota_tot, 2),
            "tipo": "Pronostici ad alta confidenza selezionati dall'IA",
        }
    except Exception as e:
        return {"giornata": "?", "giocate": [], "n_giocate": 0, "quota_totale": 0, "tipo": f"Errore: {e}"}

@app.get("/api/schedina-ll")
async def schedina_ll():
    """Schedina del giorno La Liga - prossima giornata."""
    try:
        cl_ll = CLASSIFICA_CACHE.get("la-liga") or []
        if not cl_ll:
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
                if conf >= 0.70 or mp > 50:
                    giocate.append({
                        "home": home, "away": away,
                        "tip": raw.get("suggerimento", "?"),
                        "prob": mp,
                        "quota": raw.get(f"quota_{raw.get('suggerimento','1').lower()}", 1.5),
                        "confidence": conf,
                        "over_under": ("Over 2.5 " + str(raw.get("over_25",50)) + "%") if raw.get("over_25",0) > 50 else ("Under 2.5 " + str(raw.get("under_25",50)) + "%"),
                        "goal": ("Goal Si " + str(raw.get("goal_si",50)) + "%") if raw.get("goal_si",0) > 50 else ("Goal No " + str(raw.get("goal_no",50)) + "%"),
                    })
            except Exception:
                continue

        giocate.sort(key=lambda x: -x["confidence"])
        top = giocate[:5]
        quota_tot = 1.0
        for g in top:
            q = g.get("quota", 1.5)
            if q > 1: quota_tot *= q

        return {
            "giornata": giornata_num,
            "giocate": top,
            "n_giocate": len(top),
            "quota_totale": round(quota_tot, 2),
            "tipo": "Pronostici ad alta confidenza selezionati dall'IA",
        }
    except Exception as e:
        return {"giornata": "?", "giocate": [], "n_giocate": 0, "quota_totale": 0, "tipo": f"Errore: {e}"}

@app.get("/api/{league}/squadre-attive")
async def squadre_attive(league: str):
    """Ritorna le squadre ancora attive in una competizione (da prossime fixtures)."""
    if league not in LEAGUES:
        raise HTTPException(404, "Competizione non trovata")
    lg = LEAGUES[league]
    nome_map = _get_nome_map(league)
    try:
        # Prendi le prossime 20 fixtures per trovare le squadre ancora in gioco
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
            if h_mapped: teams.add(h_mapped)
            if a_mapped: teams.add(a_mapped)
        return {"squadre": sorted(teams)}
    except Exception:
        return {"squadre": []}

# ─────────────────────────────
# WEB PUSH NOTIFICATIONS
# ─────────────────────────────
VAPID_PUBLIC_KEY = "BBrZeD51wgoA9ITtBo8UPhHUf6o1lu1zwP16tZ9RNoI1F0yhVpMoWshroZI_nQIPqoZ_DRLVR2cu6B-WB9vE8J0"
VAPID_PRIVATE_KEY_PATH = os.path.join(_ROOT, "vapid_private.pem")
VAPID_EMAIL = "mailto:mario.costabile92@outlook.it"
_PUSH_SUBSCRIPTIONS = []  # In-memory, persistito su DB

@app.get("/api/push/vapid-key")
async def get_vapid_key():
    return {"publicKey": VAPID_PUBLIC_KEY}

@app.post("/api/push/subscribe")
async def push_subscribe(data: dict, user: Optional[dict] = Depends(get_optional_user)):
    """Salva una subscription push per un utente."""
    sub = data.get("subscription")
    if not sub:
        raise HTTPException(400, "Subscription mancante")
    # Salva in memory (e DB)
    _PUSH_SUBSCRIPTIONS.append({"subscription": sub, "user_id": user["id"] if user else None})
    try:
        from database import _get_conn
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS push_subscriptions (id SERIAL PRIMARY KEY, user_id INTEGER, subscription TEXT NOT NULL, created_at TEXT)")
        cur.execute("INSERT INTO push_subscriptions (user_id, subscription, created_at) VALUES (%s, %s, %s)",
                    (user["id"] if user else None, json.dumps(sub), datetime.now(timezone.utc).isoformat()))
        conn.commit()
        cur.close()
        conn.close()
    except Exception:
        pass
    return {"status": "ok"}

def send_push_notification(title, body, url="/app#home"):
    """Invia push notification a tutti i subscriber."""
    try:
        from pywebpush import webpush
        from database import _get_conn
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute("SELECT subscription FROM push_subscriptions")
        rows = cur.fetchall()
        cur.close()
        conn.close()
        payload = json.dumps({"title": title, "body": body, "url": url})
        priv_key = open(VAPID_PRIVATE_KEY_PATH, "r").read() if os.path.exists(VAPID_PRIVATE_KEY_PATH) else None
        if not priv_key:
            return
        sent = 0
        for row in rows:
            try:
                sub = json.loads(row[0])
                webpush(sub, payload, vapid_private_key=priv_key, vapid_claims={"sub": VAPID_EMAIL})
                sent += 1
            except Exception:
                pass
        print(f"📱 Push inviata a {sent}/{len(rows)} dispositivi")
    except Exception as e:
        print(f"⚠️ Push error: {e}")

# ─────────────────────────────
# SISTEMA REFERRAL
# ─────────────────────────────
import hashlib

def _generate_referral_code(user_id, email):
    """Genera un codice referral unico."""
    raw = f"{user_id}_{email}_{os.urandom(4).hex()}"
    return hashlib.md5(raw.encode()).hexdigest()[:8].upper()

@app.get("/api/referral/my-code")
async def get_referral_code(user: Optional[dict] = Depends(get_optional_user)):
    if not user:
        raise HTTPException(401, "Devi essere loggato")
    from database import _get_conn
    conn = _get_conn()
    cur = conn.cursor()
    # Controlla se l'utente ha gia' un codice
    cur.execute("SELECT referral_code FROM users WHERE id = %s", (user["id"],))
    row = cur.fetchone()
    code = row[0] if row and row[0] else None
    if not code:
        code = _generate_referral_code(user["id"], user["email"])
        cur.execute("UPDATE users SET referral_code = %s WHERE id = %s", (code, user["id"]))
        conn.commit()
    # Conta referral completati
    cur.execute("SELECT COUNT(*) FROM referrals WHERE referrer_id = %s AND status = 'completed'", (user["id"],))
    completed = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM referrals WHERE referrer_id = %s AND status = 'pending'", (user["id"],))
    pending = cur.fetchone()[0]
    cur.close()
    conn.close()
    return {
        "code": code,
        "link": f"https://matchiq.it.com/app#registrati?ref={code}",
        "completati": completed,
        "in_attesa": pending,
    }

@app.post("/api/referral/apply")
async def apply_referral(data: dict):
    """Applica un codice referral quando un nuovo utente si registra."""
    code = data.get("code", "").strip().upper()
    new_user_email = data.get("email", "").strip().lower()
    if not code or not new_user_email:
        return {"status": "skip"}
    from database import _get_conn
    conn = _get_conn()
    cur = conn.cursor()
    # Trova chi ha il codice
    cur.execute("SELECT id, email FROM users WHERE referral_code = %s", (code,))
    referrer = cur.fetchone()
    if not referrer:
        cur.close(); conn.close()
        return {"status": "code_not_found"}
    referrer_id, referrer_email = referrer
    # Non puoi invitare te stesso
    if referrer_email == new_user_email:
        cur.close(); conn.close()
        return {"status": "self_referral"}
    # Registra il referral
    cur.execute("""
        INSERT INTO referrals (referrer_id, referrer_email, referral_code, referred_email, status, created_at)
        VALUES (%s, %s, %s, %s, 'completed', %s)
    """, (referrer_id, referrer_email, code, new_user_email, datetime.now(timezone.utc).isoformat()))
    # Premio: attiva Pro per 30 giorni all'invitante
    cur.execute("UPDATE users SET piano = 'pro' WHERE id = %s", (referrer_id,))
    conn.commit()
    cur.close()
    conn.close()
    # Notifica l'invitante via email
    try:
        import urllib.request as ur
        body = json.dumps({
            "from": "MatchIQ <noreply@matchiq.it.com>",
            "to": [referrer_email],
            "subject": "Un amico si e' iscritto con il tuo codice!",
            "html": f'<div style="font-family:Arial;background:#0a0f1a;color:#e8eaf6;padding:24px;border-radius:12px"><h2 style="color:#2ecc71">Referral completato!</h2><p><strong>{new_user_email}</strong> si e\' iscritto con il tuo codice referral.</p><p style="color:#2ecc71;font-size:1.2rem;font-weight:700">Hai ottenuto 1 mese Pro gratis!</p><hr style="border:1px solid #1f3460"><p style="color:#8892b0;font-size:.85rem">MatchIQ - Pronostici Calcistici con IA</p></div>'
        }).encode()
        req = ur.Request("https://api.resend.com/emails", data=body, headers={
            "Authorization": f"Bearer {RESEND_API_KEY}",
            "Content-Type": "application/json",
            "User-Agent": "MatchIQ/1.0"
        })
        ur.urlopen(req, timeout=10)
    except Exception:
        pass
    return {"status": "ok", "reward": "1 mese Pro gratis"}

# ─────────────────────────────
# STORICO PRONOSTICI UTENTE
# ─────────────────────────────
@app.post("/api/user/save-prediction")
async def save_user_prediction(data: dict, user: Optional[dict] = Depends(get_optional_user)):
    if not user:
        raise HTTPException(401, "Devi essere loggato")
    from database import _get_conn
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO user_predictions (user_id, league, home, away, pronostico, prob, confidence, over_under, goal, created_at, match_date)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, (
        user["id"], data.get("league",""), data.get("home",""), data.get("away",""),
        data.get("pronostico",""), data.get("prob",0), data.get("confidence",""),
        data.get("over_under",""), data.get("goal",""),
        datetime.now(timezone.utc).isoformat(), data.get("match_date","")
    ))
    conn.commit()
    cur.close()
    conn.close()
    return {"status": "ok"}

@app.get("/api/user/my-predictions")
async def get_user_predictions(user: Optional[dict] = Depends(get_optional_user)):
    if not user:
        raise HTTPException(401, "Devi essere loggato")
    from database import _get_conn
    import psycopg2.extras
    conn = _get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT * FROM user_predictions WHERE user_id = %s ORDER BY id DESC LIMIT 50
    """, (user["id"],))
    preds = cur.fetchall()
    # Statistiche
    cur.execute("""
        SELECT
            COUNT(*) as totale,
            SUM(CASE WHEN corretto THEN 1 ELSE 0 END) as ok_1x2,
            SUM(CASE WHEN ou_corretto THEN 1 ELSE 0 END) as ok_ou,
            SUM(CASE WHEN goal_corretto THEN 1 ELSE 0 END) as ok_goal,
            SUM(CASE WHEN verificato THEN 1 ELSE 0 END) as verificati
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
        }
    }

@app.post("/api/user/verify-predictions")
async def verify_user_predictions(user: Optional[dict] = Depends(get_optional_user)):
    """Verifica i pronostici dell'utente con i risultati reali."""
    if not user:
        raise HTTPException(401, "Devi essere loggato")
    from database import _get_conn
    import psycopg2.extras
    conn = _get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM user_predictions WHERE user_id = %s AND verificato = FALSE", (user["id"],))
    preds = cur.fetchall()
    verificati = 0
    # Cerca risultati in tutte le cache
    all_results = []
    for lk in LEAGUES:
        for p in (RISULTATI_STAGIONE_CACHE_ML.get(lk) or []):
            all_results.append(p)
        for p in (LIVE_RESULTS_CACHE_ML.get(lk) or []):
            if p.get("status") in ("FT","AET","PEN"):
                all_results.append(p)
    if LIVE_RESULTS_CACHE:
        for p in LIVE_RESULTS_CACHE:
            if p.get("status") in ("FT","AET","PEN"):
                all_results.append(p)
    for pred in preds:
        for ris in all_results:
            if ris.get("home") == pred["home"] and ris.get("away") == pred["away"] and ris.get("status") in ("FT","AET","PEN"):
                gol_h = ris["gol_h"]
                gol_a = ris["gol_a"]
                if gol_h > gol_a: ris_1x2 = "1"
                elif gol_h == gol_a: ris_1x2 = "X"
                else: ris_1x2 = "2"
                corretto = pred["pronostico"] == ris_1x2
                gol_tot = gol_h + gol_a
                ou_pred = "Over" in (pred.get("over_under") or "")
                ou_ok = (gol_tot > 2.5) == ou_pred
                goal_pred = "Si" in (pred.get("goal") or "")
                is_goal = gol_h >= 1 and gol_a >= 1
                goal_ok = is_goal == goal_pred
                cur.execute("""
                    UPDATE user_predictions SET gol_h_reale=%s, gol_a_reale=%s, risultato_reale=%s,
                    corretto=%s, ou_corretto=%s, goal_corretto=%s, verificato=TRUE WHERE id=%s
                """, (gol_h, gol_a, ris_1x2, corretto, ou_ok, goal_ok, pred["id"]))
                verificati += 1
                break
    conn.commit()
    cur.close()
    conn.close()
    return {"verificati": verificati}

# ─────────────────────────────
# DASHBOARD ACCURATEZZA
# ─────────────────────────────
@app.get("/api/accuratezza")
async def accuratezza():
    """Calcola accuratezza pronostici vs risultati reali per ogni giornata."""
    risultati = []

    for league_key in ["serie-a", "premier-league", "la-liga"]:
        league = LEAGUES.get(league_key)
        if not league:
            continue
        lid = league["id"]
        season = league["season"]
        nome_map = _get_nome_map(league_key)

        # Prendi CSV giusto per i pronostici
        if league_key == "serie-a":
            csv_df = _df
        elif league_key == "premier-league":
            csv_df = _df_pl
        elif league_key == "la-liga":
            csv_df = _df_ll
        else:
            csv_df = None

        # Prendi risultati finiti dalla cache
        storico = RISULTATI_STAGIONE_CACHE_ML.get(league_key) or []
        if not storico:
            continue

        # Raggruppa per round
        from collections import defaultdict
        per_round = defaultdict(list)
        for p in storico:
            per_round[p.get("round", "")].append(p)

        # Ultime 5 giornate completate
        rounds_sorted = sorted(per_round.keys(), key=lambda r: int(r.split(" - ")[-1]) if " - " in r and r.split(" - ")[-1].isdigit() else 0, reverse=True)

        for rd in rounds_sorted[:5]:
            partite = per_round[rd]
            if len(partite) < 5:
                continue
            g_num = rd.split(" - ")[-1] if " - " in rd else rd
            ok_1x2 = 0
            ok_ou = 0
            ok_goal = 0
            tot = 0
            ok_alta = 0
            tot_alta = 0
            dettagli = []

            for p in partite:
                h, a = p["home"], p["away"]
                gol_h, gol_a = p["gol_h"], p["gol_a"]
                if gol_h is None:
                    continue

                # Calcola pronostico
                try:
                    if csv_df is not None and len(csv_df) > 100:
                        hs = get_team_stats(csv_df, h, opponent=a)
                        aws = get_team_stats(csv_df, a, opponent=h)
                        pred = get_prediction(hs, aws, df=csv_df)
                    else:
                        pred = genera_pronostico(h, a)
                except Exception:
                    continue

                # Risultato reale
                if gol_h > gol_a:
                    ris = "1"
                elif gol_h == gol_a:
                    ris = "X"
                else:
                    ris = "2"

                sugg = pred.get("suggerimento", "")
                corretto = sugg == ris
                if corretto:
                    ok_1x2 += 1

                gol_tot = gol_h + gol_a
                pred_over = pred.get("over_25", 50) > 50
                ou_ok = (gol_tot > 2.5) == pred_over
                if ou_ok:
                    ok_ou += 1

                is_goal = gol_h >= 1 and gol_a >= 1
                pred_goal = pred.get("goal_si", 50) > 50
                goal_ok = is_goal == pred_goal
                if goal_ok:
                    ok_goal += 1

                conf = pred.get("confidence_label", "")
                if conf == "Alta":
                    tot_alta += 1
                    if corretto:
                        ok_alta += 1

                tot += 1
                dettagli.append({
                    "home": h, "away": a,
                    "gol_h": gol_h, "gol_a": gol_a,
                    "pronostico": sugg,
                    "risultato": ris,
                    "corretto": corretto,
                    "confidenza": conf,
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

    # Calcola totali
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
        }
    }

# ─────────────────────────────
# NOTIZIE LIVE SERIE A
# ─────────────────────────────
NOTIZIE_CACHE = []
NOTIZIE_LAST_UPDATE = ""

def _scrape_notizie():
    """Scarica notizie calcio da Google News RSS (affidabile e sempre aggiornato)."""
    global NOTIZIE_CACHE, NOTIZIE_LAST_UPDATE
    import urllib.request as ur
    import re
    notizie = []
    feeds = [
        ("https://news.google.com/rss/search?q=serie+a+calcio+2026&hl=it&gl=IT&ceid=IT:it", "Serie A"),
        ("https://news.google.com/rss/search?q=premier+league+football+2026&hl=it&gl=IT&ceid=IT:it", "Premier League"),
        ("https://news.google.com/rss/search?q=calciomercato+2026&hl=it&gl=IT&ceid=IT:it", "Calciomercato"),
    ]
    for feed_url, categoria in feeds:
        try:
            req = ur.Request(feed_url, headers={"User-Agent": "Mozilla/5.0"})
            with ur.urlopen(req, timeout=10) as r:
                xml = r.read().decode("utf-8", errors="replace")
            # Parse RSS XML
            items = re.findall(r'<item>.*?<title>(.*?)</title>.*?<link>(.*?)</link>.*?<source[^>]*>(.*?)</source>.*?</item>', xml, re.DOTALL)
            for titolo, url, fonte in items[:4]:
                titolo = re.sub(r'<[^>]+>', '', titolo).strip()
                titolo = titolo.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>').replace('&#39;', "'")
                if titolo and len(titolo) > 15:
                    notizie.append({"titolo": titolo, "fonte": fonte or categoria, "url": url})
        except Exception as e:
            print(f"⚠️ RSS {categoria}: {e}")
    if notizie:
        # Rimuovi duplicati per titolo
        seen = set()
        unique = []
        for n in notizie:
            if n["titolo"] not in seen:
                seen.add(n["titolo"])
                unique.append(n)
        NOTIZIE_CACHE = unique[:12]
        NOTIZIE_LAST_UPDATE = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M")
        print(f"📰 Notizie: {len(NOTIZIE_CACHE)} articoli live da Google News")

@app.get("/api/notizie")
async def notizie():
    """Ritorna le ultime notizie Serie A."""
    if not NOTIZIE_CACHE or len(NOTIZIE_CACHE) < 4:
        return {"notizie":[
            {"titolo":"Probabili formazioni Serie A Giornata 31: le scelte dei tecnici","fonte":"Fantacalcio.it","url":"https://www.fantacalcio.it/probabili-formazioni-serie-a"},
            {"titolo":"Calciomercato Serie A: tutti i trasferimenti di gennaio 2026","fonte":"Sky Sport","url":"https://sport.sky.it/calciomercato/serie-a"},
            {"titolo":"Serie A Giornata 31: Inter-Roma, Napoli-Milan - pronostici e analisi","fonte":"Sky Sport","url":"https://sport.sky.it/calcio/serie-a/calendario-risultati"},
            {"titolo":"Classifica marcatori Serie A: Lautaro 14 gol, Douvikas secondo","fonte":"Tuttosport","url":"https://www.tuttosport.com/live/classifica-marcatori-serie-a"},
            {"titolo":"Infortunati Serie A: tutti gli indisponibili per la giornata 31","fonte":"Fantacalciopedia","url":"https://www.fantacalciopedia.com/articoli-fcp/consigli-fantacalcio/75-lista-infortunati-serie-a-aggiornata.html"},
            {"titolo":"Champions League: calendario e risultati delle italiane","fonte":"UEFA","url":"https://www.uefa.com/uefachampionsleague/"},
            {"titolo":"Premier League 2025-2026: classifica e risultati aggiornati","fonte":"Premier League","url":"https://www.premierleague.com/tables"},
            {"titolo":"La Liga 2025-2026: classifica e calendario aggiornato","fonte":"La Liga","url":"https://www.laliga.com/en-GB/laliga-easports/standing"},
            {"titolo":"Bundesliga 2025-2026: risultati e classifica","fonte":"Bundesliga","url":"https://www.bundesliga.com/en/bundesliga/table"},
            {"titolo":"Ligue 1 2025-2026: classifica e top scorer","fonte":"Ligue 1","url":"https://www.ligue1.com/ranking"},
            {"titolo":"Europa League: il cammino delle squadre italiane","fonte":"UEFA","url":"https://www.uefa.com/uefaeuropaleague/"},
            {"titolo":"Serie A, la lotta salvezza: Verona e Pisa a 18 punti, chi retrocede?","fonte":"Gazzetta","url":"https://www.gazzetta.it/calcio/serie-a/"},
        ],"aggiornamento":"Aggiornamento automatico ogni 30 min"}
    return {"notizie":NOTIZIE_CACHE,"aggiornamento":NOTIZIE_LAST_UPDATE}

# ─────────────────────────────
# RISULTATI LIVE + STORICO COMPLETO
# ─────────────────────────────
RISULTATI_STAGIONE_CACHE = None  # Tutte le partite della stagione da API Football
RISULTATI_STAGIONE_TIME = ""

def _fetch_risultati_stagione():
    """Scarica TUTTI i risultati della stagione da API Football."""
    global RISULTATI_STAGIONE_CACHE, RISULTATI_STAGIONE_TIME
    try:
        # Tutte le partite giocate (FT = Full Time)
        req = urllib.request.Request(
            f"https://{FOOTBALL_API_HOST}/fixtures?league=135&season=2025&status=FT-AET-PEN",
            headers={"x-apisports-key": FOOTBALL_API_KEY, "User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.loads(r.read().decode())

        if data.get("response"):
            partite = []
            for fix in data["response"]:
                teams = fix.get("teams", {})
                goals = fix.get("goals", {})
                fixture = fix.get("fixture", {})
                events = fix.get("events", [])
                league = fix.get("league", {})

                home_name = FOOTBALL_NOME_MAP.get(teams.get("home", {}).get("name", "?"), teams.get("home", {}).get("name", "?"))
                away_name = FOOTBALL_NOME_MAP.get(teams.get("away", {}).get("name", "?"), teams.get("away", {}).get("name", "?"))

                marcatori = []
                marcatori_home = []
                marcatori_away = []
                home_id = teams.get("home", {}).get("id")
                for ev in events:
                    if ev.get("type") == "Goal":
                        nome = ev.get("player", {}).get("name", "?")
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

                partite.append({
                    "home": home_name,
                    "away": away_name,
                    "gol_h": goals.get("home", 0) or 0,
                    "gol_a": goals.get("away", 0) or 0,
                    "status": "FT",
                    "status_it": "Terminata",
                    "live": False,
                    "marcatori": marcatori,
                    "marcatori_home": marcatori_home,
                    "marcatori_away": marcatori_away,
                    "fixture_id": fixture.get("id"),
                    "data": fixture.get("date", "")[:10],
                    "ora": _utc_to_rome(fixture.get("date", "")),
                    "round": league.get("round", ""),
                })

            if partite:
                # Ordina per data (piu' recente prima)
                partite.sort(key=lambda x: x["data"], reverse=True)
                RISULTATI_STAGIONE_CACHE = partite
                RISULTATI_STAGIONE_CACHE_ML["serie-a"] = partite
                RISULTATI_STAGIONE_TIME = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")
                print(f"📊 STORICO STAGIONE: {len(partite)} partite caricate")
    except Exception as e:
        print(f"❌ Errore fetch storico stagione: {e}")
RISULTATI_GIORNATE = {
    30:{"data":"20-22 marzo 2026","partite":[
        {"home":"Genoa","away":"Torino","gol_h":2,"gol_a":1,"marcatori":["Vitinha 23'","Colombo 67'","Vlasic 45'"]},
        {"home":"Atalanta","away":"Napoli","gol_h":2,"gol_a":1,"marcatori":["Krstovic 12'","De Ketelaere 78'","Hojlund 55'"]},
        {"home":"Milan","away":"Parma","gol_h":3,"gol_a":0,"marcatori":["Pulisic 15'","Leao 44'","Gimenez 71'"]},
        {"home":"Roma","away":"Cremonese","gol_h":2,"gol_a":0,"marcatori":["Malen 33'","Soule 62'"]},
        {"home":"Cagliari","away":"Lazio","gol_h":0,"gol_a":0,"marcatori":[]},
        {"home":"Lecce","away":"Inter","gol_h":0,"gol_a":2,"marcatori":["Thuram 28'","Calhanoglu 59' (R)"]},
        {"home":"Juventus","away":"Como","gol_h":0,"gol_a":2,"marcatori":["Douvikas 37'","Paz 82'"]},
        {"home":"Sassuolo","away":"Verona","gol_h":3,"gol_a":0,"marcatori":["Berardi 11'","Pinamonti 53'","Lauriente 88'"]},
        {"home":"Fiorentina","away":"Pisa","gol_h":1,"gol_a":1,"marcatori":["Kean 42'","Tramoni 76'"]},
        {"home":"Bologna","away":"Udinese","gol_h":1,"gol_a":2,"marcatori":["Castro 30'","Davis 18'","Zaniolo 65'"]},
    ]},
    29:{"data":"14-16 marzo 2026","partite":[
        {"home":"Inter","away":"Genoa","gol_h":2,"gol_a":0,"marcatori":["Thuram 22'","Barella 68'"]},
        {"home":"Napoli","away":"Torino","gol_h":2,"gol_a":1,"marcatori":["Hojlund 35'","McTominay 71'","Adams 55'"]},
        {"home":"Lazio","away":"Milan","gol_h":1,"gol_a":0,"marcatori":["Maldini 63'"]},
        {"home":"Como","away":"Cagliari","gol_h":1,"gol_a":0,"marcatori":["Douvikas 48'"]},
        {"home":"Cremonese","away":"Sassuolo","gol_h":1,"gol_a":1,"marcatori":["Vardy 32'","Berardi 77'"]},
        {"home":"Parma","away":"Lecce","gol_h":0,"gol_a":1,"marcatori":["Cheddira 56'"]},
        {"home":"Verona","away":"Roma","gol_h":0,"gol_a":3,"marcatori":["Malen 12'","Dovbyk 41'","Pellegrini 85'"]},
        {"home":"Torino","away":"Fiorentina","gol_h":0,"gol_a":0,"marcatori":[]},
        {"home":"Udinese","away":"Juventus","gol_h":0,"gol_a":1,"marcatori":["Yildiz 73'"]},
        {"home":"Pisa","away":"Atalanta","gol_h":1,"gol_a":2,"marcatori":["Meister 40'","Scamacca 28'","Raspadori 90'"]},
    ]},
    28:{"data":"7-9 marzo 2026","partite":[
        {"home":"Milan","away":"Juventus","gol_h":1,"gol_a":1,"marcatori":["Pulisic 55'","Yildiz 78'"]},
        {"home":"Napoli","away":"Lecce","gol_h":2,"gol_a":1,"marcatori":["Hojlund 20'","McTominay 64'","Banda 88'"]},
        {"home":"Inter","away":"Atalanta","gol_h":1,"gol_a":1,"marcatori":["Calhanoglu 37' (R)","Krstovic 71'"]},
        {"home":"Roma","away":"Bologna","gol_h":2,"gol_a":0,"marcatori":["Malen 29'","Dybala 82'"]},
        {"home":"Fiorentina","away":"Lazio","gol_h":1,"gol_a":1,"marcatori":["Kean 45'","Dia 66'"]},
        {"home":"Como","away":"Sassuolo","gol_h":2,"gol_a":1,"marcatori":["Paz 14'","Douvikas 52'","Pinamonti 80'"]},
        {"home":"Genoa","away":"Cagliari","gol_h":1,"gol_a":0,"marcatori":["Vitinha 61'"]},
        {"home":"Cremonese","away":"Verona","gol_h":2,"gol_a":0,"marcatori":["Sanabria 33'","Vardy 70'"]},
        {"home":"Torino","away":"Parma","gol_h":3,"gol_a":1,"marcatori":["Simeone 8'","Vlasic 42'","Adams 67'","Pellegrino 55'"]},
        {"home":"Udinese","away":"Pisa","gol_h":1,"gol_a":0,"marcatori":["Davis 39'"]},
    ]},
}

FOOTBALL_API_KEY = "3f8ed68a9b1cb532479096f33bfbc568"
FOOTBALL_API_HOST = "v3.football.api-sports.io"
LIVE_RESULTS_CACHE = None
LIVE_RESULTS_TIME = ""
LIVE_IN_CORSO = False  # True se ci sono partite in corso

# Mapping nomi API Football -> nostri nomi
FOOTBALL_NOME_MAP = {
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

def _fetch_live_results():
    """Scarica risultati live dalla API Football (ultimi 30 + oggi)."""
    global LIVE_RESULTS_CACHE, LIVE_RESULTS_TIME, LIVE_IN_CORSO
    try:
        # Scarica ultime 30 partite giocate (con eventi e statistiche)
        req = urllib.request.Request(
            f"https://{FOOTBALL_API_HOST}/fixtures?league=135&season=2025&last=30",
            headers={"x-apisports-key": FOOTBALL_API_KEY, "User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode())

        partite = []
        has_live = False

        if data.get("response"):
            for fix in data["response"]:
                teams = fix.get("teams", {})
                goals = fix.get("goals", {})
                fixture = fix.get("fixture", {})
                status = fixture.get("status", {})
                events = fix.get("events", [])

                # Marcatori con dettagli + squadra
                marcatori = []
                marcatori_home = []
                marcatori_away = []
                home_id = teams.get("home", {}).get("id")
                away_id = teams.get("away", {}).get("id")
                for ev in events:
                    if ev.get("type") == "Goal":
                        nome = ev.get("player", {}).get("name", "?")
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

                # Cartellini
                cartellini_gialli = []
                rossi_home = []
                rossi_away = []
                for ev in events:
                    if ev.get("type") == "Card":
                        nome = ev.get("player", {}).get("name", "?")
                        minuto = ev.get("time", {}).get("elapsed", "?")
                        team_id = ev.get("team", {}).get("id")
                        if ev.get("detail") == "Red Card":
                            if team_id == home_id:
                                rossi_home.append(f"{nome} {minuto}'")
                            else:
                                rossi_away.append(f"{nome} {minuto}'")
                        elif ev.get("detail") == "Yellow Card":
                            cartellini_gialli.append(f"{nome} {minuto}'")

                # Statistiche partita (se disponibili nell'oggetto fixture)
                stats_list = fix.get("statistics", [])
                stats = {}
                if stats_list and len(stats_list) >= 2:
                    home_stats_raw = stats_list[0].get("statistics", []) if stats_list[0] else []
                    away_stats_raw = stats_list[1].get("statistics", []) if stats_list[1] else []
                    for s in home_stats_raw:
                        tipo = s.get("type", "")
                        val = s.get("value")
                        if tipo == "Ball Possession":
                            stats["possesso_home"] = val
                        elif tipo == "Total Shots":
                            stats["tiri_home"] = val
                        elif tipo == "Shots on Goal":
                            stats["tiri_porta_home"] = val
                        elif tipo == "Corner Kicks":
                            stats["corner_home"] = val
                        elif tipo == "Fouls":
                            stats["falli_home"] = val
                        elif tipo == "Offsides":
                            stats["fuorigioco_home"] = val
                    for s in away_stats_raw:
                        tipo = s.get("type", "")
                        val = s.get("value")
                        if tipo == "Ball Possession":
                            stats["possesso_away"] = val
                        elif tipo == "Total Shots":
                            stats["tiri_away"] = val
                        elif tipo == "Shots on Goal":
                            stats["tiri_porta_away"] = val
                        elif tipo == "Corner Kicks":
                            stats["corner_away"] = val
                        elif tipo == "Fouls":
                            stats["falli_away"] = val
                        elif tipo == "Offsides":
                            stats["fuorigioco_away"] = val

                status_short = status.get("short", "FT")
                is_live = status_short in ("1H", "2H", "HT", "ET", "P", "BT", "INT")
                if is_live:
                    has_live = True

                # Mappa status in italiano
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

                home_name = FOOTBALL_NOME_MAP.get(teams.get("home", {}).get("name", "?"),
                                                   teams.get("home", {}).get("name", "?"))
                away_name = FOOTBALL_NOME_MAP.get(teams.get("away", {}).get("name", "?"),
                                                   teams.get("away", {}).get("name", "?"))

                partite.append({
                    "home": home_name,
                    "away": away_name,
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

        # Prova anche a prendere le partite di OGGI (potrebbero non essere nelle ultime 30)
        try:
            oggi = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            req2 = urllib.request.Request(
                f"https://{FOOTBALL_API_HOST}/fixtures?league=135&season=2025&date={oggi}",
                headers={"x-apisports-key": FOOTBALL_API_KEY, "User-Agent": "Mozilla/5.0"}
            )
            with urllib.request.urlopen(req2, timeout=15) as r2:
                data2 = json.loads(r2.read().decode())

            if data2.get("response"):
                existing_ids = set()
                for fix in data.get("response", []):
                    existing_ids.add(fix.get("fixture", {}).get("id"))

                for fix in data2["response"]:
                    if fix.get("fixture", {}).get("id") in existing_ids:
                        continue  # Gia' presente

                    teams = fix.get("teams", {})
                    goals = fix.get("goals", {})
                    fixture = fix.get("fixture", {})
                    status = fixture.get("status", {})
                    events = fix.get("events", [])

                    marcatori = []
                    for ev in events:
                        if ev.get("type") == "Goal":
                            nome = ev.get("player", {}).get("name", "?")
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

                    home_name = FOOTBALL_NOME_MAP.get(teams.get("home", {}).get("name", "?"),
                                                       teams.get("home", {}).get("name", "?"))
                    away_name = FOOTBALL_NOME_MAP.get(teams.get("away", {}).get("name", "?"),
                                                       teams.get("away", {}).get("name", "?"))

                    partite.append({
                        "home": home_name,
                        "away": away_name,
                        "gol_h": goals.get("home", 0) or 0,
                        "gol_a": goals.get("away", 0) or 0,
                        "status": status_short,
                        "status_it": {"FT":"Terminata","NS":"Non iniziata","1H":"1° Tempo","2H":"2° Tempo","HT":"Intervallo"}.get(status_short, status_short),
                        "minuto": status.get("elapsed"),
                        "live": is_live,
                        "marcatori": marcatori,
                        "rossi_home": [],
                        "rossi_away": [],
                        "data": fixture.get("date", "")[:10],
                        "ora": _utc_to_rome(fixture.get("date", "")),
                    })
        except Exception as e:
            print(f"⚠️ Fetch partite oggi: {e}")

        if partite:
            LIVE_RESULTS_CACHE = partite
            LIVE_RESULTS_TIME = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")
            LIVE_IN_CORSO = has_live
            print(f"⚽ RISULTATI LIVE: {len(partite)} partite {'(LIVE IN CORSO!)' if has_live else ''}")
    except Exception as e:
        print(f"❌ Errore API Football: {e}")

@app.get("/api/risultati")
async def risultati():
    """Ritorna risultati: live + storico completo da API Football."""
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

    # 2. Storico completo da API Football (raggruppato per round/giornata)
    if RISULTATI_STAGIONE_CACHE:
        from collections import defaultdict
        per_round = defaultdict(list)
        for p in RISULTATI_STAGIONE_CACHE:
            # Raggruppa per round (es. "Regular Season - 30")
            rd = p.get("round", "")
            per_round[rd].append(p)

        # Ordina i round dal piu' recente
        rounds_sorted = sorted(per_round.keys(), key=lambda r: int(r.split(" - ")[-1]) if " - " in r and r.split(" - ")[-1].isdigit() else 0, reverse=True)

        for rd in rounds_sorted:
            partite = per_round[rd]
            # Estrai numero giornata dal round
            g_num = rd.split(" - ")[-1] if " - " in rd else rd
            # Data = data della prima partita
            data_str = partite[0]["data"] if partite else ""
            giornate.append({
                "giornata": g_num,
                "data": data_str,
                "partite": partite,
                "live": False,
            })
    elif LIVE_RESULTS_CACHE:
        # Fallback: usa le ultime 30 partite raggruppate per data
        from collections import defaultdict
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

# ─────────────────────────────
# DETTAGLIO PARTITA LIVE (API Football completo)
# ─────────────────────────────
@app.get("/api/fixture/{fixture_id}")
async def fixture_detail(fixture_id: int):
    """Scarica dettagli completi di una partita: eventi, statistiche, formazioni."""
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

            # Parziali
            ht = score.get("halftime", {})
            result["primo_tempo"] = f"{ht.get('home', '-')}-{ht.get('away', '-')}" if ht else ""

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

    # 2. Statistiche partita
    try:
        req = urllib.request.Request(
            f"https://{FOOTBALL_API_HOST}/fixtures/statistics?fixture={fixture_id}",
            headers={"x-apisports-key": FOOTBALL_API_KEY, "User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode())

        stats = {}
        if data.get("response") and len(data["response"]) >= 2:
            for side, idx in [("home", 0), ("away", 1)]:
                for s in data["response"][idx].get("statistics", []):
                    tipo = s.get("type", "")
                    val = s.get("value")
                    key_map = {
                        "Ball Possession": "possesso",
                        "Total Shots": "tiri",
                        "Shots on Goal": "tiri_porta",
                        "Shots off Goal": "tiri_fuori",
                        "Blocked Shots": "tiri_bloccati",
                        "Corner Kicks": "corner",
                        "Fouls": "falli",
                        "Offsides": "fuorigioco",
                        "Yellow Cards": "gialli",
                        "Red Cards": "rossi",
                        "Goalkeeper Saves": "parate",
                        "Total passes": "passaggi",
                        "Passes accurate": "passaggi_riusciti",
                        "Passes %": "passaggi_pct",
                        "expected_goals": "xg",
                    }
                    for api_name, our_name in key_map.items():
                        if tipo == api_name:
                            stats[f"{our_name}_{side}"] = val
        result["stats"] = stats
    except Exception as e:
        result["stats"] = {}

    # 3. Formazioni
    try:
        req = urllib.request.Request(
            f"https://{FOOTBALL_API_HOST}/fixtures/lineups?fixture={fixture_id}",
            headers={"x-apisports-key": FOOTBALL_API_KEY, "User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode())

        lineups = {}
        if data.get("response") and len(data["response"]) >= 2:
            for idx, side in enumerate(["home", "away"]):
                team_data = data["response"][idx]
                formazione = team_data.get("formation", "")
                coach = team_data.get("coach", {}).get("name", "")
                titolari = [p.get("player", {}).get("name", "?") for p in team_data.get("startXI", [])]
                panchina = [p.get("player", {}).get("name", "?") for p in team_data.get("substitutes", [])]
                lineups[side] = {
                    "modulo": formazione,
                    "allenatore": coach,
                    "titolari": titolari,
                    "panchina": panchina[:7],
                }
        result["formazioni"] = lineups
    except Exception as e:
        result["formazioni"] = {}

    return result

# ─────────────────────────────
# ENDPOINT MULTI-LEAGUE (Premier League + futuri campionati)
# ─────────────────────────────

def _fetch_league_data(league_key):
    """Scarica classifica, marcatori, risultati per un campionato da API Football."""
    league = LEAGUES.get(league_key)
    if not league:
        return
    lid = league["id"]
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
                    nome = nome_map.get(nome_api, nome_api)
                    stats = team.get("all", {})
                    gf = stats.get("goals", {}).get("for", 0)
                    gs = stats.get("goals", {}).get("against", 0)
                    classifica.append({"Squadra":nome,"Punti":team.get("points",0),"G":stats.get("played",0),"V":stats.get("win",0),"N":stats.get("draw",0),"P":stats.get("lose",0),"GF":gf,"GS":gs,"DR":gf-gs})
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
                gol = 0
                squadra_api = ""
                for s in player.get("statistics", []):
                    if s.get("league", {}).get("id") == lid:
                        gol = s.get("goals", {}).get("total", 0) or 0
                        squadra_api = s.get("team", {}).get("name", "")
                        break
                squadra = nome_map.get(squadra_api, squadra_api)
                marcatori.append({"pos":i,"giocatore":info.get("name","?"),"squadra":squadra,"gol":gol})
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
                teams = fix.get("teams", {})
                goals = fix.get("goals", {})
                fixture = fix.get("fixture", {})
                events = fix.get("events", [])
                lg = fix.get("league", {})
                home_name = nome_map.get(teams.get("home",{}).get("name","?"), teams.get("home",{}).get("name","?"))
                away_name = nome_map.get(teams.get("away",{}).get("name","?"), teams.get("away",{}).get("name","?"))
                marcatori = []
                marcatori_home = []
                marcatori_away = []
                home_id = teams.get("home",{}).get("id")
                for ev in events:
                    if ev.get("type") == "Goal":
                        nome = ev.get("player",{}).get("name","?")
                        minuto = ev.get("time",{}).get("elapsed","?")
                        detail = ev.get("detail","")
                        gol_str = f"{nome} {minuto}'" + (" (R)" if detail=="Penalty" else " (aut.)" if detail=="Own Goal" else "")
                        marcatori.append(gol_str)
                        if ev.get("team",{}).get("id") == home_id:
                            marcatori_home.append(gol_str)
                        else:
                            marcatori_away.append(gol_str)
                partite.append({"home":home_name,"away":away_name,"gol_h":goals.get("home",0) or 0,"gol_a":goals.get("away",0) or 0,"status":"FT","status_it":"Terminata","live":False,"marcatori":marcatori,"marcatori_home":marcatori_home,"marcatori_away":marcatori_away,"fixture_id":fixture.get("id"),"data":fixture.get("date","")[:10],"ora":_utc_to_rome(fixture.get("date","")),"round":lg.get("round","")})
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
            live_p = []
            has_live = False
            for fix in data["response"]:
                teams = fix.get("teams",{})
                goals = fix.get("goals",{})
                fixture = fix.get("fixture",{})
                status = fixture.get("status",{})
                events = fix.get("events",[])
                home_name = nome_map.get(teams.get("home",{}).get("name","?"), teams.get("home",{}).get("name","?"))
                away_name = nome_map.get(teams.get("away",{}).get("name","?"), teams.get("away",{}).get("name","?"))
                marcatori=[]
                for ev in events:
                    if ev.get("type")=="Goal":
                        nome=ev.get("player",{}).get("name","?")
                        minuto=ev.get("time",{}).get("elapsed","?")
                        detail=ev.get("detail","")
                        marcatori.append(f"{nome} {minuto}'" + (" (R)" if detail=="Penalty" else " (aut.)" if detail=="Own Goal" else ""))
                ss = status.get("short","FT")
                is_live = ss in ("1H","2H","HT","ET","P")
                if is_live: has_live = True
                live_p.append({"home":home_name,"away":away_name,"gol_h":goals.get("home",0) or 0,"gol_a":goals.get("away",0) or 0,"status":ss,"minuto":status.get("elapsed"),"live":is_live,"marcatori":marcatori,"fixture_id":fixture.get("id"),"data":fixture.get("date","")[:10],"ora":_utc_to_rome(fixture.get("date",""))})
            LIVE_RESULTS_CACHE_ML[league_key] = live_p
            LIVE_IN_CORSO_ML[league_key] = has_live
    except Exception as e:
        print(f"⚠️ Live {league_key}: {e}")

    print(f"✅ {league['name']}: dati aggiornati")

@app.get("/api/{league}/classifica")
async def classifica_league(league: str):
    if league not in LEAGUES:
        raise HTTPException(404, "Campionato non trovato")
    cl = CLASSIFICA_CACHE.get(league)
    mc = MARCATORI_CACHE.get(league)
    return {"classifica": cl or [], "marcatori": mc or [], "aggiornamento": CLASSIFICA_LAST_UPDATE.get(league, ""), "live": cl is not None}

@app.get("/api/{league}/calendario")
async def calendario_league(league: str):
    """Calendario per qualsiasi campionato - prossime giornate + risultati da API Football."""
    if league not in LEAGUES:
        raise HTTPException(404, "Campionato non trovato")
    lg = LEAGUES[league]
    lid = lg["id"]
    season = lg["season"]
    nome_map = _get_nome_map(league)

    giornate = []
    giornata_corrente = None

    try:
        # Prendi TUTTE le fixtures della stagione (giocate + da giocare)
        req = urllib.request.Request(
            f"https://{FOOTBALL_API_HOST}/fixtures?league={lid}&season={season}",
            headers={"x-apisports-key": FOOTBALL_API_KEY, "User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.loads(r.read().decode())

        if data.get("response"):
            from collections import defaultdict
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

                marcatori = []
                for ev in events:
                    if ev.get("type") == "Goal":
                        nome = ev.get("player", {}).get("name", "?")
                        minuto = ev.get("time", {}).get("elapsed", "?")
                        detail = ev.get("detail", "")
                        marcatori.append(f"{nome} {minuto}'" + (" (R)" if detail == "Penalty" else " (aut.)" if detail == "Own Goal" else ""))

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
                    "marcatori": marcatori,
                }

                rd = lg_data.get("round", "")
                per_round[rd].append(match_data)

            # Ordina i round per numero
            def round_num(r):
                try:
                    return int(r.split(" - ")[-1])
                except:
                    return 0

            for rd in sorted(per_round.keys(), key=round_num):
                partite = per_round[rd]
                g_num = rd.split(" - ")[-1] if " - " in rd else rd

                tutte_finite = all(p["status"] in ("FT", "AET", "PEN") for p in partite)
                ha_live = any(p["live"] for p in partite)
                ha_da_giocare = any(p["status"] in ("NS", "TBD") for p in partite)
                # Se nessuna partita da giocare e nessuna live -> completata
                nessuna_futura = not ha_da_giocare and not ha_live

                if tutte_finite or nessuna_futura:
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

@app.get("/api/{league}/risultati")
async def risultati_league(league: str):
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
        from collections import defaultdict
        per_round = defaultdict(list)
        for p in storico:
            per_round[p.get("round","")].append(p)
        for rd in sorted(per_round.keys(), key=lambda r: int(r.split(" - ")[-1]) if " - " in r and r.split(" - ")[-1].isdigit() else 0, reverse=True):
            g_num = rd.split(" - ")[-1] if " - " in rd else rd
            giornate.append({"giornata":g_num,"data":per_round[rd][0]["data"],"partite":per_round[rd],"live":False})
    return {"giornate":giornate,"live":LIVE_IN_CORSO_ML.get(league,False),"aggiornamento":CLASSIFICA_LAST_UPDATE.get(league,"")}

@app.get("/api/{league}/pronostico/{home}/{away}")
async def pronostico_league(league: str, home: str, away: str):
    if league not in LEAGUES:
        raise HTTPException(404, "Campionato non trovato")
    # Per PL/LL usa dati CSV se disponibili, altrimenti fallback
    if league == "premier-league" and _df_pl is not None and len(_df_pl) > 100:
        try:
            hs = get_team_stats(_df_pl, home, opponent=away)
            aw = get_team_stats(_df_pl, away, opponent=home)
            raw = get_prediction(hs, aw, df=_df_pl)
        except Exception:
            raw = genera_pronostico(home, away)
    elif league == "la-liga" and _df_ll is not None and len(_df_ll) > 100:
        try:
            hs = get_team_stats(_df_ll, home, opponent=away)
            aw = get_team_stats(_df_ll, away, opponent=home)
            raw = get_prediction(hs, aw, df=_df_ll)
        except Exception:
            raw = genera_pronostico(home, away)
    elif league == "bundesliga" and _df_bl is not None and len(_df_bl) > 100:
        try:
            hs = get_team_stats(_df_bl, home, opponent=away)
            aw = get_team_stats(_df_bl, away, opponent=home)
            raw = get_prediction(hs, aw, df=_df_bl)
        except Exception:
            raw = genera_pronostico(home, away)
    elif league in ("champions-league", "europa-league", "conference-league"):
        # Per competizioni europee: blend dati europei + nazionali + classifica live
        euro_df = _df_ucl if league == "champions-league" else (_df_uel if league == "europa-league" else _df_uecl)
        raw = None

        # 1. Prova dati europei H2H
        raw_euro = None
        if euro_df is not None and len(euro_df) > 100:
            try:
                hs = get_team_stats(euro_df, home, opponent=away)
                aw = get_team_stats(euro_df, away, opponent=home)
                raw_euro = get_prediction(hs, aw, df=euro_df)
            except Exception:
                raw_euro = None

        # 2. Prova dati campionato nazionale
        raw_domestic = None
        for dom_df in [_df, _df_pl, _df_ll, _df_bl]:
            if dom_df is None:
                continue
            try:
                hs_d = get_team_stats(dom_df, home, opponent=away)
                aw_d = get_team_stats(dom_df, away, opponent=home)
                raw_domestic = get_prediction(hs_d, aw_d, df=dom_df)
                break
            except Exception:
                continue

        # 3. Classifica live europea (sempre disponibile)
        raw_classifica = genera_pronostico(home, away)

        # 4. Blend intelligente
        sources = []
        if raw_domestic:
            sources.append((raw_domestic, 0.45))  # Nazionale piu' affidabile
        if raw_euro:
            sources.append((raw_euro, 0.20))  # Dati europei H2H
        if raw_classifica:
            # Se non abbiamo dati nazionali, la classifica live diventa la fonte principale
            sources.append((raw_classifica, 0.35 if raw_domestic else 0.80))

        if sources:
            raw = {}
            total_w = sum(w for _, w in sources)
            for k in (sources[0][0] or {}).keys():
                vals = [(s.get(k), w) for s, w in sources if isinstance(s.get(k), (int, float))]
                if vals:
                    raw[k] = round(sum(v * w for v, w in vals) / sum(w for _, w in vals), 2)
                else:
                    raw[k] = sources[0][0].get(k)

            # Ricalcola suggerimento
            mp = max(raw.get("prob_1", 0), raw.get("prob_x", 0), raw.get("prob_2", 0))
            raw["suggerimento"] = "1" if mp == raw.get("prob_1") else ("X" if mp == raw.get("prob_x") else "2")
            raw["sugg_label"] = "Vittoria Casa" if raw["suggerimento"] == "1" else ("Pareggio" if raw["suggerimento"] == "X" else "Vittoria Ospite")

            # Confidence: usa la fonte migliore, non il blend
            best_conf = max((s.get("confidence", 0) for s, w in sources if isinstance(s.get("confidence"), (int, float))), default=0)
            sp = sorted([raw.get("prob_1", 0), raw.get("prob_x", 0), raw.get("prob_2", 0)], reverse=True)
            if sp[0] > 1:
                spread = (sp[0] - sp[1]) / 100
            else:
                spread = sp[0] - sp[1]
            raw["confidence"] = round(max(best_conf, min(1.0, spread * 2.5)), 3)
            raw["confidence_label"] = "Alta" if raw["confidence"] >= 0.82 else ("Media" if raw["confidence"] >= 0.50 else "Bassa")
            raw["sicura"] = raw["confidence"] >= 0.82 and sp[0] > 45

            # O/U: calibra sulla media gol reale della competizione
            # UCL/UEL/UECL hanno media gol alta (~2.7-3.0)
            ov = raw.get("over_25", 50)
            un = raw.get("under_25", 50)
            gol_att = raw.get("gol_attesi", 2.5)
            if isinstance(gol_att, (int, float)) and gol_att > 2.5:
                # Se gol attesi > 2.5, boost Over
                ov = max(ov, 50 + (gol_att - 2.5) * 8)
                ov = min(ov, 75)
            raw["over_25"] = round(ov, 1)
            raw["under_25"] = round(100 - ov, 1) if ov > 1 else round(un, 1)

            # Goal Si/No: ricalcola dalla fonte piu' affidabile, non dal blend
            # Il blend dei valori Goal produce risultati incoerenti
            best_source = raw_domestic or raw_classifica or raw_euro or {}
            gsi_best = best_source.get("goal_si", 50)
            gno_best = best_source.get("goal_no", 50)
            # Normalizza: se sono decimali (0-1) converti in percentuali
            if isinstance(gsi_best, (int, float)) and gsi_best < 1:
                gsi_best = gsi_best * 100
            if isinstance(gno_best, (int, float)) and gno_best < 1:
                gno_best = gno_best * 100
            # Assicura coerenza
            if gsi_best + gno_best > 110:
                tot_g = gsi_best + gno_best
                gsi_best = gsi_best / tot_g * 100
            raw["goal_si"] = round(gsi_best, 1)
            raw["goal_no"] = round(100 - gsi_best, 1)
            # Boost se gol attesi alti
            ga = raw.get("gol_attesi", 2.5)
            if isinstance(ga, (int, float)) and ga > 2.3 and raw["goal_si"] < 50:
                raw["goal_si"] = round(50 + (ga - 2.3) * 5, 1)
                raw["goal_no"] = round(100 - raw["goal_si"], 1)

            # Quote
            for tip in ["1", "x", "2"]:
                p = raw.get(f"prob_{tip}", 33)
                raw[f"quota_{tip}"] = round(105 / max(1, p), 2)

            # Risultati esatti e altri campi non numerici
            raw["risultati_esatti"] = (raw_domestic or raw_euro or raw_classifica or {}).get("risultati_esatti", [])
            raw["gol_attesi"] = round(raw.get("gol_attesi", 2.5), 2) if isinstance(raw.get("gol_attesi"), (int, float)) else 2.5
        else:
            raw = raw_classifica or genera_pronostico(home, away)
    else:
        raw = genera_pronostico(home, away)
    # Formazioni e marcatori (fetch on-demand per PL)
    h_title = home.strip().title()
    a_title = away.strip().title()
    form_casa = _get_last_lineup(h_title)
    form_ospite = _get_last_lineup(a_title)
    # Marcatori: cerca in TUTTI i campionati per trovare i goleador
    marc_casa = []
    marc_ospite = []
    for lk in [league, "serie-a", "premier-league", "la-liga", "champions-league", "europa-league", "conference-league"]:
        mc = MARCATORI_CACHE.get(lk) or []
        for m in mc:
            if m.get("squadra") == h_title and len(marc_casa) < 3:
                entry = f"{m['giocatore']} ({m['gol']} gol)"
                if entry not in marc_casa:
                    marc_casa.append(entry)
            elif m.get("squadra") == a_title and len(marc_ospite) < 3:
                entry = f"{m['giocatore']} ({m['gol']} gol)"
                if entry not in marc_ospite:
                    marc_ospite.append(entry)

    return {
        "home":home,"away":away,
        "prob_1":raw.get("prob_1",0),"prob_x":raw.get("prob_x",0),"prob_2":raw.get("prob_2",0),
        "quota_1":raw.get("quota_1",0),"quota_x":raw.get("quota_x",0),"quota_2":raw.get("quota_2",0),
        "suggerimento":raw.get("suggerimento",""),"sugg_label":raw.get("sugg_label",""),
        "confidence":raw.get("confidence",0),"confidence_label":raw.get("confidence_label",""),
        "over_25":raw.get("over_25"),"under_25":raw.get("under_25"),
        "goal_si":raw.get("goal_si"),"goal_no":raw.get("goal_no"),
        "gol_attesi":raw.get("gol_attesi"),
        "risultati_esatti":raw.get("risultati_esatti",[]),
        "sicura":bool(raw.get("sicura",False)),
        "formazione_casa": form_casa,
        "formazione_ospite": form_ospite,
        "marcatori_casa": marc_casa[:3],
        "marcatori_ospite": marc_ospite[:3],
    }

# ─────────────────────────────
# HEALTH CHECK
# ─────────────────────────────
@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "motore": MOTORE_DISPONIBILE,
        "dati_caricati": _df is not None,
        "live_in_corso": LIVE_IN_CORSO,
        "risultati_live": LIVE_RESULTS_CACHE is not None and len(LIVE_RESULTS_CACHE or []) > 0,
        "ultimo_aggiornamento_live": LIVE_RESULTS_TIME,
    }

# ─────────────────────────────
# RUN LOCALE
# ─────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api_server:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))