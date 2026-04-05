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
from database import init_db, log_api_call, count_daily_calls, get_user_by_email, create_user
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
# GLOBAL
# ─────────────────────────────
_df = None
LIMITE_FREE = 2

# Dati live (aggiornati automaticamente)
import threading, time, urllib.request, re as regex_module
from datetime import datetime, timezone
LIVE_FORMAZIONI = {}
LIVE_INFORTUNATI = {}
LIVE_LAST_UPDATE = ""

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

def _live_updater():
    """Thread che aggiorna i dati. 2 min durante partite live, 30 min altrimenti."""
    while True:
        try:
            _scrape_live_data()
            _scrape_notizie()
            _scrape_odds()
            _fetch_live_results()
            _check_and_notify_goals()  # Notifiche gol Telegram per utenti Pro
            _fetch_classifica_live()
            _fetch_marcatori_live()
        except Exception:
            pass
        # Se ci sono partite in corso, aggiorna ogni 2 minuti
        if LIVE_IN_CORSO:
            time.sleep(120)  # 2 minuti durante live
        else:
            time.sleep(1800)  # 30 minuti normalmente

# ─────────────────────────────
# STARTUP
# ─────────────────────────────
@app.on_event("startup")
async def startup():
    global _df

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
            print(f"✅ DATI CARICATI: {len(_df)} partite")
        except Exception as e:
            print(f"⚠️ DATI NON DISPONIBILI: {e}")
            _df = None
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
        print("✅ PRIMO FETCH COMPLETATO")
    t = threading.Thread(target=_live_updater, daemon=True)
    t.start()
    threading.Thread(target=_delayed_start, daemon=True).start()
    print("✅ SERVER PRONTO\n")

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
            print("❌ ERRORE PREDICTOR:", e)

    # Calcolo Poisson AVANZATO con 26 anni CSV + xG + H2H + forma
    from scipy.stats import poisson as pdist

    # Carica statistiche pre-calcolate dai CSV (26 anni)
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

    if not sh or not sa:
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
    # Calibrazione Goal: Serie A ha 57% Goal Si in media
    # Solo leggera correzione per difese top (xGA < 0.9)
    xga_min = min(sh.get("xGA_pg", 1.3) if sh else 1.3, sa.get("xGA_pg", 1.3) if sa else 1.3)
    if xga_min < 0.9:
        gsi = gsi_raw * 0.95  # Solo -5% per difese top (Inter 0.84)
    else:
        gsi = gsi_raw
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

    return {
        "prob_1":round(p1*100,1),"prob_x":round(px*100,1),"prob_2":round(p2*100,1),
        "quota_1":round(1.05/p1,2) if p1>0 else 99,"quota_x":round(1.05/px,2) if px>0 else 99,"quota_2":round(1.05/p2,2) if p2>0 else 99,
        "suggerimento":sg,"sugg_label":sl,"confidence":round(cf,3),"confidence_label":cl,
        "sicura": bool(sicura),
        "over_25":round(ov25*100,1),"under_25":round((1-ov25)*100,1),
        "goal_si":round(gsi*100,1),"goal_no":round((1-gsi)*100,1),
        "gol_attesi":round(lh+la,2),
        # Risultati esatti coerenti con Over/Under
        "risultati_esatti": _filtra_esatti(scores, ov25, sg),
        # Marcatori senza infortunati
        "marcatori_casa": _filtra_marcatori(TOP_SCORER.get(h, []), INFORTUNATI.get(h, [])),
        "marcatori_ospite": _filtra_marcatori(TOP_SCORER.get(a, []), INFORTUNATI.get(a, [])),
        "formazione_casa": FORMAZIONI.get(h),
        "formazione_ospite": FORMAZIONI.get(a),
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
            "from": "PronoSerie A <onboarding@resend.dev>",
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
            "Content-Type": "application/json"
        })
        ur.urlopen(req, timeout=10)
        print(f"📧 Email inviata a {to_email}")
    except Exception as e:
        print(f"⚠️ Errore invio email a {to_email}: {e}")

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

    return {"access_token": token, "piano": user["piano"]}

@app.post("/api/auth/login")
async def login(data: dict):
    user = get_user_by_email(data["email"].lower().strip())

    if not user or not verify_password(data["password"], user["password_hash"]):
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
    return {"new_password": new_pass}

# ─────────────────────────────
# PRONOSTICO
# ─────────────────────────────
@app.get("/api/pronostico/{home}/{away}")
async def pronostico(home: str, away: str, user: Optional[dict] = Depends(get_optional_user)):
    check_limit(user)

    raw = genera_pronostico(home, away)

    return {
        "home": home,
        "away": away,
        "prob_1": raw.get("prob_1", 0),
        "prob_x": raw.get("prob_x", 0),
        "prob_2": raw.get("prob_2", 0),
        "quota_1": raw.get("quota_1", 0),
        "quota_x": raw.get("quota_x", 0),
        "quota_2": raw.get("quota_2", 0),
        "suggerimento": raw.get("suggerimento", ""),
        "sugg_label": raw.get("sugg_label", ""),
        "confidence": raw.get("confidence", 0),
        "confidence_label": raw.get("confidence_label", ""),
        "over_25": raw.get("over_25"),
        "under_25": raw.get("under_25"),
        "goal_si": raw.get("goal_si"),
        "goal_no": raw.get("goal_no"),
        "gol_attesi": raw.get("gol_attesi"),
        "risultati_esatti": raw.get("risultati_esatti", []),
        "sicura": bool(raw.get("sicura", False)),
        "marcatori_casa": raw.get("marcatori_casa") or _filtra_marcatori(TOP_SCORER.get(home.strip().title(), []), INFORTUNATI.get(home.strip().title(), [])),
        "marcatori_ospite": raw.get("marcatori_ospite") or _filtra_marcatori(TOP_SCORER.get(away.strip().title(), []), INFORTUNATI.get(away.strip().title(), [])),
        "formazione_casa": raw.get("formazione_casa") or FORMAZIONI.get(home.strip().title()),
        "formazione_ospite": raw.get("formazione_ospite") or FORMAZIONI.get(away.strip().title()),
        "h2h_applicato": bool(raw.get("h2h_applicato", False)),
        "h2h_partite": int(raw.get("h2h_partite", 0)),
    }

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
CLASSIFICA_CACHE = None
MARCATORI_CACHE = None
CLASSIFICA_LAST_UPDATE = ""

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
    global CLASSIFICA_CACHE, CLASSIFICA_LAST_UPDATE
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
                    CLASSIFICA_CACHE = classifica
                    CLASSIFICA_LAST_UPDATE = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")
                    print(f"🏆 CLASSIFICA LIVE: {len(classifica)} squadre aggiornate ({CLASSIFICA_LAST_UPDATE})")
                    return True
    except Exception as e:
        print(f"❌ Errore fetch classifica: {e}")
    return False

def _fetch_marcatori_live():
    """Scarica classifica marcatori Serie A da API Football."""
    global MARCATORI_CACHE
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
                MARCATORI_CACHE = marcatori
                print(f"⚽ MARCATORI LIVE: {len(marcatori)} giocatori aggiornati")
                return True
    except Exception as e:
        print(f"❌ Errore fetch marcatori: {e}")
    return False

@app.get("/api/classifica")
async def classifica():
    cl = CLASSIFICA_CACHE if CLASSIFICA_CACHE else CLASS_FALLBACK
    mc = MARCATORI_CACHE if MARCATORI_CACHE else MARC_FALLBACK
    return {
        "classifica": cl,
        "marcatori": mc,
        "aggiornamento": CLASSIFICA_LAST_UPDATE or "Dati base",
        "live": CLASSIFICA_CACHE is not None,
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

@app.get("/api/squadra/{nome}")
async def squadra(nome: str):
    n = nome.strip().title()
    # Usa dati live se disponibili, altrimenti hardcoded
    form = LIVE_FORMAZIONI.get(n) or FORMAZIONI.get(n)
    inj = LIVE_INFORTUNATI.get(n) if LIVE_INFORTUNATI.get(n) is not None else INFORTUNATI.get(n, [])
    return {
        "nome": n,
        "allenatore": ALLENATORI.get(n, "N/D"),
        "formazione": form,
        "infortunati": inj,
        "rosa": [{"nome":g[0],"ruolo":g[1],"numero":g[2]} for g in ROSE.get(n, [])],
        "ultimo_aggiornamento": LIVE_LAST_UPDATE or "Dati base",
    }

# ─────────────────────────────
# SCHEDINA DEL GIORNO (IA)
# ─────────────────────────────
@app.get("/api/schedina")
async def schedina_del_giorno():
    """L'IA seleziona le 3-5 giocate piu' sicure della giornata 31."""
    giocate = []
    cal = CAL_HARDCODED.get(31, {})
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

    # Ordina per confidence e prendi top 5
    giocate.sort(key=lambda x: -x["confidence"])
    top = giocate[:5]

    # Calcola quota totale schedina
    quota_tot = 1.0
    for g in top:
        q = g.get("quota", 1.5)
        if q > 1: quota_tot *= q

    return {
        "giornata": 31,
        "data": cal.get("data", ""),
        "giocate": top,
        "n_giocate": len(top),
        "quota_totale": round(quota_tot, 2),
        "tipo": "Schedina SICURA — Solo giocate ad alta confidenza",
    }

# ─────────────────────────────
# NOTIZIE LIVE SERIE A
# ─────────────────────────────
NOTIZIE_CACHE = []
NOTIZIE_LAST_UPDATE = ""

def _scrape_notizie():
    """Scarica notizie Serie A con link specifici agli articoli."""
    global NOTIZIE_CACHE, NOTIZIE_LAST_UPDATE
    import urllib.request as ur
    import re
    notizie = []
    try:
        req = ur.Request("https://sport.sky.it/calcio/serie-a", headers={"User-Agent":"Mozilla/5.0"})
        with ur.urlopen(req, timeout=10) as r:
            html = r.read().decode("utf-8", errors="replace")
        # Estrai coppie link+titolo: <a href="/calcio/serie-a/...">Titolo</a>
        links = re.findall(r'<a[^>]+href="(/calcio/serie-a/[^"]{20,})"[^>]*>([^<]{15,120})</a>', html)
        seen = set()
        for url, titolo in links:
            t = re.sub(r'<[^>]+>','',titolo).strip()
            if t and t not in seen and len(t)>15:
                seen.add(t)
                notizie.append({"titolo":t,"fonte":"Sky Sport","url":"https://sport.sky.it"+url})
                if len(notizie)>=6: break
    except Exception as e:
        print(f"⚠️ Scrape Sky: {e}")
    try:
        req = ur.Request("https://www.gazzetta.it/calcio/serie-a/", headers={"User-Agent":"Mozilla/5.0"})
        with ur.urlopen(req, timeout=10) as r:
            html = r.read().decode("utf-8", errors="replace")
        links = re.findall(r'<a[^>]+href="(https?://www\.gazzetta\.it/calcio/serie-a/[^"]{10,})"[^>]*>([^<]{15,120})</a>', html)
        seen2 = set()
        for url, titolo in links:
            t = re.sub(r'<[^>]+>','',titolo).strip()
            if t and t not in seen2 and len(t)>15:
                seen2.add(t)
                notizie.append({"titolo":t,"fonte":"Gazzetta","url":url})
                if len(notizie)>=12: break
    except Exception as e:
        print(f"⚠️ Scrape Gazzetta: {e}")
    if notizie:
        NOTIZIE_CACHE = notizie[:12]
        NOTIZIE_LAST_UPDATE = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M")
        print(f"📰 Notizie: {len(NOTIZIE_CACHE)} articoli con link")

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
# RISULTATI LIVE
# ─────────────────────────────
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
                    "ora": fixture.get("date", "")[11:16] if len(fixture.get("date", "")) > 15 else "",
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
                        "ora": fixture.get("date", "")[11:16] if len(fixture.get("date", "")) > 15 else "",
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
    """Ritorna risultati: live da API Football + storico hardcoded."""
    # Se abbiamo dati live, usali
    live_partite = []
    if LIVE_RESULTS_CACHE:
        for p in LIVE_RESULTS_CACHE:
            live_partite.append({
                "home": p["home"],
                "away": p["away"],
                "gol_h": p["gol_h"],
                "gol_a": p["gol_a"],
                "marcatori": p["marcatori"],
                "marcatori_home": p.get("marcatori_home", []),
                "marcatori_away": p.get("marcatori_away", []),
                "status": p["status"],
                "status_it": p.get("status_it", p["status"]),
                "minuto": p["minuto"],
                "live": p["live"],
                "data": p["data"],
                "ora": p.get("ora", ""),
                "rossi_home": p.get("rossi_home", []),
                "rossi_away": p.get("rossi_away", []),
                "gialli": p.get("gialli", []),
                "stats": p.get("stats", {}),
                "fixture_id": p.get("fixture_id"),
            })

    # Raggruppa per data
    from collections import defaultdict
    per_data = defaultdict(list)
    for p in live_partite:
        per_data[p["data"]].append(p)

    giornate_live = []
    for data_str in sorted(per_data.keys(), reverse=True)[:5]:
        giornate_live.append({
            "giornata": "Live",
            "data": data_str,
            "partite": per_data[data_str],
            "live": any(p["live"] for p in per_data[data_str]),
        })

    # Aggiungi storico hardcoded
    giornate_storico = []
    for g_num in sorted(RISULTATI_GIORNATE.keys(), reverse=True):
        g = RISULTATI_GIORNATE[g_num]
        giornate_storico.append({
            "giornata": g_num,
            "data": g["data"],
            "partite": g["partite"],
            "live": False,
        })

    return {
        "giornate": giornate_live + giornate_storico,
        "live": any(g.get("live") for g in giornate_live),
        "aggiornamento": LIVE_RESULTS_TIME or "Storico",
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
            result["ora"] = fixture.get("date", "")[11:16] if len(fixture.get("date", "")) > 15 else ""
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