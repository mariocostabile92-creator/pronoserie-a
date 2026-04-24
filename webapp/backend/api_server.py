"""
api_server.py - Entry point MatchIQ (versione modulare)
Contiene: app FastAPI, CORS, middleware, import router, startup event.
Tutto il codice heavy e' stato estratto in moduli dedicati:
  - live_service.py   : live updater, fetch API Football, cache globali
  - telegram_service.py: notifiche gol, bot Telegram
  - scraping_service.py: notizie RSS, quote bookmaker, formazioni live
  - startup.py        : bootstrap, delayed start, caricamento dataset
"""

import sys
import os
import json
import logging
_logger = logging.getLogger(__name__)

# PATH ROOT
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, _ROOT)

import threading
import time
import urllib.request
from typing import Optional
from datetime import datetime, timezone

from fastapi import FastAPI, Depends, HTTPException, Request
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
# IMPORT MODULI SERVICE
# ─────────────────────────────
from live_service import (
    # Variabili globali (cache live)
    LIVE_RESULTS_CACHE, LIVE_RESULTS_TIME, LIVE_IN_CORSO,
    CLASSIFICA_CACHE, CLASSIFICA_LAST_UPDATE,
    MARCATORI_CACHE, LIVE_RESULTS_CACHE_ML,
    RISULTATI_STAGIONE_CACHE_ML, LIVE_IN_CORSO_ML,
    RISULTATI_STAGIONE_CACHE, RISULTATI_STAGIONE_TIME,
    ROSE_LIVE, ALLENATORI_LIVE, INFORTUNATI_LIVE, ROSE_LAST_UPDATE,
    PLAYER_STATS_CACHE, PLAYER_STATS_LAST, FANTACALCIO_LEAGUES,
    MATCHDAY_CACHE, TEAM_STATS_CACHE,
    WC_GIRONI_CACHE, WC_FIXTURES_CACHE, WC_LAST_UPDATE,
    # Config
    LEAGUES, FOOTBALL_API_KEY, FOOTBALL_API_HOST,
    # Funzioni helper
    _utc_to_rome, _get_nome_map,
    # Funzioni fetch
    _fetch_live_results, _fetch_classifica_live, _fetch_marcatori_live,
    _fetch_infortunati_live, _fetch_rose_live, _fetch_risultati_stagione,
    _fetch_player_stats, _fetch_worldcup_data, _fetch_league_data,
    _fetch_team_stats_league, _compute_best_stats,
    start_live_updater,
)

from scraping_service import (
    NOTIZIE_CACHE, NOTIZIE_LAST_UPDATE,
    ODDS_CACHE, ODDS_LAST_UPDATE,
    LIVE_FORMAZIONI, LIVE_INFORTUNATI, LIVE_LAST_UPDATE,
    _scrape_notizie, _scrape_odds, _scrape_live_data,
    get_bookmaker_odds,
)

from league_mappings import (
    PL_NOME_MAP, PL_TEAM_IDS,
    LL_NOME_MAP, LL_TEAM_IDS,
    BL_NOME_MAP, BL_TEAM_IDS,
    L1_NOME_MAP, L1_TEAM_IDS,
    WC_NOME_MAP, WC_TEAM_IDS,
    FOOTBALL_NOME_MAP,
    _TEAM_IDS, _RUOLO_MAP, _ALL_EURO_IDS,
)

# ─────────────────────────────
# RATE LIMITING (slowapi)
# ─────────────────────────────
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)

# ─────────────────────────────
# APP
# ─────────────────────────────
app = FastAPI(title="MatchIQ API", version="2.0")

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://matchiq.it.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(payments_router)

# ─────────────────────────────
# IMPORT E REGISTRAZIONE ROUTER MODULARI
# ─────────────────────────────
from routes.auth import router as auth_router
from routes.pronostici import router as pronostici_router
from routes.live import router as live_router
from routes.leghe import router as leghe_router
from routes.schedina import router as schedina_router
from routes.referral import router as referral_router
from routes.tracking import router as tracking_router
from routes.fantacalcio import router as fantacalcio_router

app.include_router(auth_router)
app.include_router(pronostici_router)
app.include_router(live_router)
app.include_router(leghe_router)
app.include_router(schedina_router)
app.include_router(referral_router)
app.include_router(tracking_router)
app.include_router(fantacalcio_router)

# ─────────────────────────────
# GLOBAL STATE (DataFrames CSV per ogni campionato)
# ─────────────────────────────
_df = None
_df_pl = None
_df_ll = None
_df_ucl = None
_df_uel = None
_df_uecl = None
_df_bl = None
_df_l1 = None
_df_wc = None
LIMITE_FREE = 2

# ─────────────────────────────
# HELPERS
# ─────────────────────────────
def _get_team_ids(league_key):
    if league_key == "premier-league":
        return PL_TEAM_IDS
    if league_key == "la-liga":
        return LL_TEAM_IDS
    if league_key == "bundesliga":
        return BL_TEAM_IDS
    if league_key == "ligue-1":
        return L1_TEAM_IDS
    return _TEAM_IDS

def _map_team_name(name, league_key):
    nm = _get_nome_map(league_key)
    return nm.get(name, name)

def check_limit(user):
    if not user or user.get("piano") == "pro":
        return
    calls = count_daily_calls(user["id"])
    if calls >= LIMITE_FREE:
        raise HTTPException(429, "Limite giornaliero raggiunto")
    log_api_call(user["id"], "pronostico")

# ─────────────────────────────
# EMAIL (Resend)
# ─────────────────────────────
RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")

def send_welcome_email(to_email):
    try:
        import urllib.request as ur
        import json as js
        body = js.dumps({
            "from": "MatchIQ <noreply@matchiq.it.com>",
            "to": [to_email],
            "subject": "Benvenuto su MatchIQ!",
            "html": f"""
            <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;background:#0a0f1a;color:#e8eaf6;padding:32px;border-radius:12px">
                <h1 style="color:#2ecc71;text-align:center">Benvenuto su MatchIQ!</h1>
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
                    <a href="https://matchiq.it.com/app#pronostici" style="background:#2ecc71;color:#000;padding:14px 32px;border-radius:20px;text-decoration:none;font-weight:700;font-size:1.1rem">Calcola il tuo primo pronostico</a>
                </div>
                <p style="text-align:center;color:#8892b0;font-size:.85rem">Passa a Pro per pronostici illimitati, classifica, marcatori, rose e formazioni live!</p>
                <hr style="border:1px solid #1f3460;margin:20px 0">
                <p style="text-align:center;color:#8892b0;font-size:.8rem">MatchIQ - Pronostici con Intelligenza Artificiale</p>
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
def _notify_admin_new_user(email, piano):
    try:
        from telegram_service import notify_admin_new_user
        notify_admin_new_user(email, piano, resend_api_key=RESEND_API_KEY)
    except Exception as e:
        print(f"⚠️ Errore notifica admin: {e}")

# ─────────────────────────────
# DATI HARDCODED (fallback + helpers interni)
# ─────────────────────────────
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
]

ALLENATORI = {
    "Inter":"Cristian Chivu","Milan":"Massimiliano Allegri","Napoli":"Antonio Conte",
    "Como":"Cesc Fabregas","Juventus":"Luciano Spalletti","Roma":"Gian Piero Gasperini",
    "Atalanta":"Raffaele Palladino","Lazio":"Maurizio Sarri","Bologna":"Vincenzo Italiano",
    "Sassuolo":"Fabio Grosso","Udinese":"Kosta Runjaic","Parma":"Carlos Cuesta",
    "Genoa":"Patrick Vieira","Torino":"Roberto D'Aversa","Cagliari":"Fabio Pisacane",
    "Fiorentina":"Paolo Vanoli","Cremonese":"Davide Nicola","Lecce":"Eusebio Di Francesco",
    "Verona":"Paolo Sammarco","Pisa":"Oscar Hiljemark",
}

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
    "Inter":[{"nome":"Lautaro Martinez","tipo":"infortunio","dettaglio":"Da monitorare"},{"nome":"Mkhitaryan","tipo":"infortunio","dettaglio":"Problema muscolare"}],
    "Milan":[{"nome":"Gabbia","tipo":"infortunio","dettaglio":"Problema muscolare"},{"nome":"Loftus-Cheek","tipo":"infortunio","dettaglio":"Infortunio ginocchio"}],
    "Napoli":[{"nome":"Neres","tipo":"infortunio","dettaglio":"Problema muscolare"},{"nome":"Di Lorenzo","tipo":"infortunio","dettaglio":"Distorsione ginocchio"}],
    "Juventus":[{"nome":"Holm","tipo":"infortunio","dettaglio":"Rientro inizio aprile"}],
    "Roma":[{"nome":"Kone","tipo":"infortunio","dettaglio":"Fine aprile"},{"nome":"Dybala","tipo":"infortunio","dettaglio":"Fine aprile"},{"nome":"Dovbyk","tipo":"infortunio","dettaglio":"Rientro maggio"}],
    "Atalanta":[{"nome":"Scamacca","tipo":"dubbio","dettaglio":"Da monitorare"}],
    "Lazio":[{"nome":"Zaccagni","tipo":"infortunio","dettaglio":"Fine aprile"},{"nome":"Rovella","tipo":"infortunio","dettaglio":"Stagione finita"}],
    "Bologna":[{"nome":"Odgaard","tipo":"infortunio","dettaglio":"Meta aprile"}],
    "Sassuolo":[{"nome":"Pieragnolo","tipo":"infortunio","dettaglio":"Inizio aprile"}],
    "Udinese":[{"nome":"Buksa","tipo":"infortunio","dettaglio":"Meta aprile"}],
    "Parma":[{"nome":"Almqvist","tipo":"infortunio","dettaglio":"Rientro dopo sosta"}],
    "Genoa":[{"nome":"Onana","tipo":"dubbio","dettaglio":"Da valutare"}],
    "Torino":[{"nome":"Aboukhlal","tipo":"dubbio","dettaglio":"Da valutare"}],
    "Cagliari":[{"nome":"Felici","tipo":"infortunio","dettaglio":"Stagione finita"}],
    "Fiorentina":[{"nome":"Solomon","tipo":"infortunio","dettaglio":"Rientro aprile"}],
    "Cremonese":[{"nome":"Baschirotto","tipo":"infortunio","dettaglio":"Inizio aprile"}],
    "Lecce":[{"nome":"Gaspar","tipo":"infortunio","dettaglio":"Stagione finita"}],
    "Verona":[], "Pisa":[{"nome":"Denoon","tipo":"infortunio","dettaglio":"Lungodegente"}],
    "Como":[{"nome":"Addai","tipo":"infortunio","dettaglio":"Stagione finita"}],
}

ROSE = {
    "Inter":[("Sommer","P",1),("Bastoni","D",95),("Akanji","D",25),("Bisseck","D",31),("Dimarco","D",32),("Barella","C",23),("Calhanoglu","C",20),("Sucic","C",8),("Dumfries","D",2),("Thuram","A",9),("Lautaro Martinez","A",10)],
    "Milan":[("Maignan","P",16),("Pavlovic","D",31),("De Winter","D",5),("Tomori","D",23),("Estupinan","D",2),("Fofana","C",19),("Ricci","C",4),("Modric","C",14),("Leao","A",10),("Pulisic","A",11),("Gimenez","A",7)],
}

# ─────────────────────────────
# ON-DEMAND FORMAZIONI/ROSE/ALLENATORI
# ─────────────────────────────
_FORMAZIONE_CACHE = {}
_COACH_CACHE = {}
_ROSA_CACHE_OD = {}

def _get_last_lineup(team_name):
    if team_name in _FORMAZIONE_CACHE:
        return _FORMAZIONE_CACHE[team_name]
    team_id = _TEAM_IDS.get(team_name) or PL_TEAM_IDS.get(team_name) or LL_TEAM_IDS.get(team_name) or BL_TEAM_IDS.get(team_name) or L1_TEAM_IDS.get(team_name) or _ALL_EURO_IDS.get(team_name)
    if not team_id:
        return None
    try:
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
                    coach = lineup.get("coach", {}).get("name", "")
                    if coach:
                        _COACH_CACHE[team_name] = coach
                        ALLENATORI_LIVE[team_name] = coach
                    if titolari:
                        result = {"modulo": formazione, "titolari": titolari}
                        _FORMAZIONE_CACHE[team_name] = result
                        return result
    except Exception:
        _logger.warning("Eccezione silenziata", exc_info=True)
    return None

def _get_coach_ondemand(team_name):
    if team_name in _COACH_CACHE:
        return _COACH_CACHE[team_name]
    team_id = _TEAM_IDS.get(team_name) or PL_TEAM_IDS.get(team_name) or LL_TEAM_IDS.get(team_name) or BL_TEAM_IDS.get(team_name) or L1_TEAM_IDS.get(team_name) or _ALL_EURO_IDS.get(team_name)
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
                for c in coach.get("career", []):
                    if c.get("team", {}).get("id") == team_id and c.get("end") is None:
                        name = coach.get("name", "N/D")
                        _COACH_CACHE[team_name] = name
                        return name
            if data["response"]:
                name = data["response"][-1].get("name", "N/D")
                _COACH_CACHE[team_name] = name
                return name
    except Exception:
        _logger.warning("Eccezione silenziata", exc_info=True)
    return None

def _get_squad_ondemand(team_name):
    if team_name in _ROSA_CACHE_OD:
        return _ROSA_CACHE_OD[team_name]
    team_id = _TEAM_IDS.get(team_name) or PL_TEAM_IDS.get(team_name) or LL_TEAM_IDS.get(team_name) or BL_TEAM_IDS.get(team_name) or L1_TEAM_IDS.get(team_name) or _ALL_EURO_IDS.get(team_name)
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
            rosa = [{"nome": p.get("name", "?"), "ruolo": _RUOLO_MAP.get(p.get("position", ""), "C"), "numero": p.get("number", 0) or 0, "foto": p.get("photo", "")} for p in players]
            if rosa:
                _ROSA_CACHE_OD[team_name] = rosa
                return rosa
    except Exception:
        _logger.warning("Eccezione silenziata", exc_info=True)
    return []

def _get_injuries_ondemand(team_name):
    team_id = _TEAM_IDS.get(team_name) or PL_TEAM_IDS.get(team_name) or LL_TEAM_IDS.get(team_name) or BL_TEAM_IDS.get(team_name) or L1_TEAM_IDS.get(team_name) or _ALL_EURO_IDS.get(team_name)
    if not team_id:
        return []
    try:
        req = urllib.request.Request(
            f"https://{FOOTBALL_API_HOST}/injuries?team={team_id}&season=2025",
            headers={"x-apisports-key": FOOTBALL_API_KEY, "User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read().decode())
        if data.get("response"):
            fixtures_dates = sorted(set(item.get("fixture", {}).get("date", "")[:10] for item in data["response"]), reverse=True)
            recent_dates = set(fixtures_dates[:2])
            seen = {}
            for item in data["response"]:
                if item.get("fixture", {}).get("date", "")[:10] not in recent_dates:
                    continue
                player = item.get("player", {})
                name = player.get("name", "?")
                reason = player.get("reason", "") or ""
                ptype = player.get("type", "") or ""
                if name in seen:
                    continue
                seen[name] = {"nome": name, "tipo": "squalifica" if "Suspended" in reason or "Red" in reason else "infortunio", "dettaglio": reason or ptype or "Indisponibile"}
            return list(seen.values())[:6]
    except Exception:
        _logger.warning("Eccezione silenziata", exc_info=True)
    return []

# ─────────────────────────────
# HELPER PRONOSTICI
# ─────────────────────────────
def _filtra_marcatori(marcatori, infortunati):
    if not infortunati:
        return marcatori
    nomi_inj = set()
    for inj in infortunati:
        nome = inj.get("nome", "").lower()
        for p in nome.split():
            if len(p) > 3:
                nomi_inj.add(p)
    return [m for m in marcatori if not any(ni in m.lower() for ni in nomi_inj)]

def _filtra_esatti(scores, ov25, suggerimento="1"):
    def get_segno(score):
        h, a = int(score.split("-")[0]), int(score.split("-")[1])
        return "1" if h > a else ("X" if h == a else "2")
    def get_totale(score):
        return int(score.split("-")[0]) + int(score.split("-")[1])
    coerenti = [s for s in scores if get_segno(s["score"]) == suggerimento]
    altri = [s for s in scores if get_segno(s["score"]) != suggerimento]
    if ov25 > 0.50:
        coerenti_ou = [s for s in coerenti if get_totale(s["score"]) >= 3]
        if len(coerenti_ou) < 3:
            coerenti_ou += [s for s in coerenti if get_totale(s["score"]) == 2]
    else:
        coerenti_ou = [s for s in coerenti if get_totale(s["score"]) <= 2]
        if len(coerenti_ou) < 3:
            coerenti_ou += [s for s in coerenti if get_totale(s["score"]) == 3]
    coerenti_ou = [s for s in coerenti_ou if all(int(x) <= 4 for x in s["score"].split("-"))]
    return (coerenti_ou[:3] + altri[:2])[:5]

def genera_pronostico(home, away):
    """Pronostico Poisson/xG per Serie A (o fallback generico)."""
    if MOTORE_DISPONIBILE and _df is not None:
        try:
            hs = get_team_stats(_df, home, opponent=away)
            aw = get_team_stats(_df, away, opponent=home)
            return get_prediction(hs, aw, df=_df)
        except Exception as e:
            print(f"❌ ERRORE PREDICTOR: {e}")

    from scipy.stats import poisson as pdist
    try:
        from api_football_stats import get_team_real_stats
    except ImportError:
        get_team_real_stats = lambda x: None

    _stats_path = os.path.join(os.path.dirname(__file__), "team_stats.json")
    _h2h_path = os.path.join(os.path.dirname(__file__), "h2h_stats.json")
    _avg_path = os.path.join(os.path.dirname(__file__), "league_averages.json")
    try:
        with open(_stats_path) as f: TEAM_STATS = json.loads(f.read())
        with open(_h2h_path) as f: H2H_DATA = json.loads(f.read())
        with open(_avg_path) as f: LEAGUE_AVG = json.loads(f.read())
    except Exception:
        TEAM_STATS = {}; H2H_DATA = {}; LEAGUE_AVG = {"media_gol_casa": 1.5, "media_gol_trasferta": 1.17}

    h = home.strip().title()
    a = away.strip().title()
    sh = TEAM_STATS.get(h, {})
    sa = TEAM_STATS.get(a, {})
    api_h = get_team_real_stats(h)
    api_a = get_team_real_stats(a)
    has_api = api_h and api_a and api_h.get("played", 0) >= 10 and api_a.get("played", 0) >= 10

    if not has_api:
        for league_key in ["serie-a", "premier-league", "la-liga", "champions-league", "europa-league", "conference-league"]:
            cl = CLASSIFICA_CACHE.get(league_key) or []
            if not cl and league_key != "serie-a":
                try:
                    _fetch_league_data(league_key)
                    cl = CLASSIFICA_CACHE.get(league_key) or []
                except Exception:
                    _logger.warning("Eccezione silenziata", exc_info=True)
            data_h = next((r for r in cl if r["Squadra"] == h), None)
            data_a = next((r for r in cl if r["Squadra"] == a), None)
            if data_h and data_a:
                g_h = max(1, data_h["G"])
                g_a = max(1, data_a["G"])
                gf_h = data_h["GF"] / g_h
                gs_h = data_h["GS"] / g_h
                gf_a = data_a["GF"] / g_a
                gs_a = data_a["GS"] / g_a
                avg_gf = sum(r["GF"] for r in cl) / sum(max(1, r["G"]) for r in cl)
                avg_gs = sum(r["GS"] for r in cl) / sum(max(1, r["G"]) for r in cl)
                att_h = gf_h / max(0.3, avg_gf)
                dif_h = gs_h / max(0.3, avg_gs)
                att_a = gf_a / max(0.3, avg_gf)
                dif_a = gs_a / max(0.3, avg_gs)
                lh = att_h * dif_a * 1.45
                la = att_a * dif_h * 1.10
                pts_diff = (data_h["Punti"] - data_a["Punti"]) / 100
                lh *= (1 + pts_diff * 0.3)
                la *= (1 - pts_diff * 0.3)
                form_h = data_h["V"] / g_h
                form_a = data_a["V"] / g_a
                form_diff = form_h - form_a
                lh *= (1 + form_diff * 0.2)
                la *= (1 - form_diff * 0.2)
                lh = max(0.4, min(lh, 3.0))
                la = max(0.3, min(la, 2.2))
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
                px *= 1.10
                ratio = min(lh,la)/max(lh,la) if max(lh,la)>0 else 0
                if ratio > 0.85: px *= 1 + (ratio-0.85)*0.5
                tot = p1 + px + p2
                if tot > 0: p1/=tot; px/=tot; p2/=tot
                bk_odds = get_bookmaker_odds(h, a)
                if bk_odds:
                    bp1 = bk_odds["prob_1"]/100; bpx = bk_odds["prob_x"]/100; bp2 = bk_odds["prob_2"]/100
                    p1 = 0.60*p1 + 0.40*bp1; px = 0.60*px + 0.40*bpx; p2 = 0.60*p2 + 0.40*bp2
                    tot = p1+px+p2
                    if tot>0: p1/=tot; px/=tot; p2/=tot
                ov25 = sum(pdist.pmf(i,lh)*pdist.pmf(j,la) for i in range(11) for j in range(11) if i+j>2.5)
                gsi = sum(pdist.pmf(i,lh)*pdist.pmf(j,la) for i in range(1,11) for j in range(1,11))
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
                return {"prob_1":round(p1*100,1),"prob_x":round(px*100,1),"prob_2":round(p2*100,1),"quota_1":round(1.05/p1,2) if p1>0 else 99,"quota_x":round(1.05/px,2) if px>0 else 99,"quota_2":round(1.05/p2,2) if p2>0 else 99,"suggerimento":sg,"sugg_label":sl,"confidence":round(cf,3),"confidence_label":cl_label,"sicura":bool(sicura),"over_25":round(ov25*100,1),"under_25":round((1-ov25)*100,1),"goal_si":round(gsi*100,1),"goal_no":round((1-gsi)*100,1),"gol_attesi":round(lh+la,2),"risultati_esatti":_filtra_esatti(scores, ov25, sg),"bookmaker_used":bk_odds is not None}

    # Fallback xG
    XG = {"Inter":{"xG":2.40,"xGA":0.84},"Milan":{"xG":1.83,"xGA":1.12},"Napoli":{"xG":1.56,"xGA":1.10},"Como":{"xG":1.80,"xGA":1.08},"Juventus":{"xG":1.97,"xGA":0.97},"Roma":{"xG":1.54,"xGA":1.20},"Atalanta":{"xG":1.86,"xGA":1.38},"Lazio":{"xG":1.21,"xGA":1.34},"Bologna":{"xG":1.34,"xGA":1.39},"Sassuolo":{"xG":1.19,"xGA":1.63},"Udinese":{"xG":1.19,"xGA":1.56},"Parma":{"xG":1.00,"xGA":1.62},"Genoa":{"xG":1.30,"xGA":1.45},"Torino":{"xG":1.33,"xGA":1.57},"Cagliari":{"xG":1.01,"xGA":1.65},"Fiorentina":{"xG":1.52,"xGA":1.53},"Cremonese":{"xG":1.03,"xGA":1.87},"Lecce":{"xG":0.93,"xGA":1.67},"Verona":{"xG":1.03,"xGA":1.40},"Pisa":{"xG":1.14,"xGA":1.82}}
    xh = XG.get(h, {"xG":1.3,"xGA":1.3})
    xa = XG.get(a, {"xG":1.3,"xGA":1.3})
    avg = sum(v["xGA"] for v in XG.values()) / len(XG)
    lh = xh["xG"] * (xa["xGA"] / avg)
    la = xa["xG"] * (xh["xGA"] / avg)
    lh = max(0.3, min(lh, 2.2))
    la = max(0.2, min(la, 1.6))
    p1 = px = p2 = 0.0
    for i in range(11):
        for j in range(11):
            p = pdist.pmf(i, lh) * pdist.pmf(j, la)
            p = max(0, p)
            if i > j: p1 += p
            elif i == j: px += p
            else: p2 += p
    tot = p1 + px + p2
    if tot > 0: p1/=tot; px/=tot; p2/=tot
    ov25 = sum(pdist.pmf(i,lh)*pdist.pmf(j,la) for i in range(11) for j in range(11) if i+j>2.5)
    gsi = sum(pdist.pmf(i,lh)*pdist.pmf(j,la) for i in range(1,11) for j in range(1,11))
    scores = sorted([{"score":f"{i}-{j}","prob":round(pdist.pmf(i,lh)*pdist.pmf(j,la)*100,1)} for i in range(5) for j in range(5)], key=lambda x:-x["prob"])
    mp = max(p1, px, p2)
    sg = "1" if mp==p1 else ("X" if mp==px else "2")
    sl = "Vittoria Casa" if sg=="1" else ("Pareggio" if sg=="X" else "Vittoria Ospite")
    return {"prob_1":round(p1*100,1),"prob_x":round(px*100,1),"prob_2":round(p2*100,1),"quota_1":round(1.05/p1,2) if p1>0 else 99,"quota_x":round(1.05/px,2) if px>0 else 99,"quota_2":round(1.05/p2,2) if p2>0 else 99,"suggerimento":sg,"sugg_label":sl,"confidence":0.5,"confidence_label":"Media","sicura":False,"over_25":round(ov25*100,1),"under_25":round((1-ov25)*100,1),"goal_si":round(gsi*100,1),"goal_no":round((1-gsi)*100,1),"gol_attesi":round(lh+la,2),"risultati_esatti":_filtra_esatti(scores, ov25, sg),"bookmaker_used":False}


def _compute_pronostico(league: str, home: str, away: str) -> dict:
    """Calcola pronostico unificato per qualsiasi campionato."""
    raw = None
    if league == "premier-league" and _df_pl is not None and len(_df_pl) > 100:
        try:
            hs = get_team_stats(_df_pl, home, opponent=away)
            aw = get_team_stats(_df_pl, away, opponent=home)
            raw = get_prediction(hs, aw, df=_df_pl, league="premier-league")
        except Exception:
            raw = None
    elif league == "la-liga" and _df_ll is not None and len(_df_ll) > 100:
        try:
            hs = get_team_stats(_df_ll, home, opponent=away)
            aw = get_team_stats(_df_ll, away, opponent=home)
            raw = get_prediction(hs, aw, df=_df_ll, league="la-liga")
        except Exception:
            raw = None
    elif league == "bundesliga" and _df_bl is not None and len(_df_bl) > 100:
        try:
            hs = get_team_stats(_df_bl, home, opponent=away)
            aw = get_team_stats(_df_bl, away, opponent=home)
            raw = get_prediction(hs, aw, df=_df_bl, league="bundesliga")
        except Exception:
            raw = None
    elif league == "ligue-1" and _df_l1 is not None and len(_df_l1) > 100:
        try:
            hs = get_team_stats(_df_l1, home, opponent=away)
            aw = get_team_stats(_df_l1, away, opponent=home)
            raw = get_prediction(hs, aw, df=_df_l1, league="ligue-1")
        except Exception:
            raw = None
    elif league in ("champions-league", "europa-league", "conference-league"):
        euro_df = _df_ucl if league == "champions-league" else (_df_uel if league == "europa-league" else _df_uecl)
        raw_euro = None
        if euro_df is not None and len(euro_df) > 100:
            try:
                hs = get_team_stats(euro_df, home, opponent=away)
                aw = get_team_stats(euro_df, away, opponent=home)
                raw_euro = get_prediction(hs, aw, df=euro_df)
            except Exception:
                raw_euro = None
        raw_domestic = None
        for dom_df in [_df, _df_pl, _df_ll, _df_bl, _df_l1]:
            if dom_df is None:
                continue
            try:
                hs_d = get_team_stats(dom_df, home, opponent=away)
                aw_d = get_team_stats(dom_df, away, opponent=home)
                raw_domestic = get_prediction(hs_d, aw_d, df=dom_df)
                break
            except Exception:
                continue
        raw_classifica = genera_pronostico(home, away)
        sources = []
        if raw_domestic:
            sources.append((raw_domestic, 0.45))
        if raw_euro:
            sources.append((raw_euro, 0.20))
        if raw_classifica:
            sources.append((raw_classifica, 0.35 if raw_domestic else 0.80))
        if sources:
            raw = {}
            for k in (sources[0][0] or {}).keys():
                vals = [(s.get(k), w) for s, w in sources if isinstance(s.get(k), (int, float))]
                if vals:
                    raw[k] = round(sum(v * w for v, w in vals) / sum(w for _, w in vals), 2)
                else:
                    raw[k] = sources[0][0].get(k)
            mp = max(raw.get("prob_1", 0), raw.get("prob_x", 0), raw.get("prob_2", 0))
            raw["suggerimento"] = "1" if mp == raw.get("prob_1") else ("X" if mp == raw.get("prob_x") else "2")
            raw["sugg_label"] = "Vittoria Casa" if raw["suggerimento"] == "1" else ("Pareggio" if raw["suggerimento"] == "X" else "Vittoria Ospite")
            raw["risultati_esatti"] = (raw_domestic or raw_euro or raw_classifica or {}).get("risultati_esatti", [])
        else:
            raw = raw_classifica or genera_pronostico(home, away)
    elif league == "mondiali-2026":
        raw = genera_pronostico(home, away)
    if raw is None:
        raw = genera_pronostico(home, away)

    # Blend bookmaker live
    p1 = raw.get("prob_1", 0)
    px = raw.get("prob_x", 0)
    p2 = raw.get("prob_2", 0)
    bk_live = get_bookmaker_odds(home.strip().title(), away.strip().title())
    bk_used_live = False
    if bk_live and bk_live.get("prob_1"):
        bk_used_live = True
        ALPHA_LIVE = 0.35
        bp1 = bk_live["prob_1"] / 100; bpx = bk_live["prob_x"] / 100; bp2 = bk_live["prob_2"] / 100
        p1 = (1 - ALPHA_LIVE) * (p1 / 100) + ALPHA_LIVE * bp1
        px = (1 - ALPHA_LIVE) * (px / 100) + ALPHA_LIVE * bpx
        p2 = (1 - ALPHA_LIVE) * (p2 / 100) + ALPHA_LIVE * bp2
        tot = p1 + px + p2
        if tot > 0:
            p1 = round(p1 / tot * 100, 1); px = round(px / tot * 100, 1); p2 = round(p2 / tot * 100, 1)
        mp = max(p1, px, p2)
        sugg = "1" if mp==p1 else ("X" if mp==px else "2")
        sugg_label = "Vittoria Casa" if sugg=="1" else ("Pareggio" if sugg=="X" else "Vittoria Ospite")
        q1 = round(1.05 / (p1/100), 2) if p1 > 0 else 99
        qx = round(1.05 / (px/100), 2) if px > 0 else 99
        q2 = round(1.05 / (p2/100), 2) if p2 > 0 else 99
        conf_raw = raw.get("confidence", 0.5)
        if sugg == raw.get("suggerimento", ""): conf_raw = min(1.0, conf_raw * 1.08)
        conf_label = "Alta" if conf_raw >= 0.82 else ("Media" if conf_raw >= 0.50 else "Bassa")
        ov25 = raw.get("over_25", 50); un25 = raw.get("under_25", 50)
        if bk_live.get("bk_over_25"):
            ov25 = round(0.65 * ov25 + 0.35 * bk_live["bk_over_25"], 1); un25 = round(100 - ov25, 1)
    else:
        sugg = raw.get("suggerimento", ""); sugg_label = raw.get("sugg_label", "")
        q1 = raw.get("quota_1", 0); qx = raw.get("quota_x", 0); q2 = raw.get("quota_2", 0)
        conf_raw = raw.get("confidence", 0); conf_label = raw.get("confidence_label", "")
        ov25 = raw.get("over_25"); un25 = raw.get("under_25")

    h_t = home.strip().title()
    a_t = away.strip().title()
    mc_h = raw.get("marcatori_casa") or []
    mc_a = raw.get("marcatori_ospite") or []
    all_leagues = [league, "serie-a", "premier-league", "la-liga", "bundesliga", "ligue-1", "champions-league", "europa-league", "conference-league"]
    if not mc_h:
        for lk in all_leagues:
            for m in (MARCATORI_CACHE.get(lk) or []):
                if m.get("squadra") == h_t and len(mc_h) < 3:
                    entry = f"{m['giocatore']} ({m['gol']} gol)"
                    if entry not in mc_h: mc_h.append(entry)
        if not mc_h: mc_h = _filtra_marcatori(TOP_SCORER.get(h_t, []), INFORTUNATI.get(h_t, []))
    if not mc_a:
        for lk in all_leagues:
            for m in (MARCATORI_CACHE.get(lk) or []):
                if m.get("squadra") == a_t and len(mc_a) < 3:
                    entry = f"{m['giocatore']} ({m['gol']} gol)"
                    if entry not in mc_a: mc_a.append(entry)
        if not mc_a: mc_a = _filtra_marcatori(TOP_SCORER.get(a_t, []), INFORTUNATI.get(a_t, []))

    return {
        "home": home, "away": away,
        "prob_1": p1, "prob_x": px, "prob_2": p2,
        "quota_1": q1, "quota_x": qx, "quota_2": q2,
        "suggerimento": sugg, "sugg_label": sugg_label,
        "confidence": conf_raw, "confidence_label": conf_label,
        "over_25": ov25, "under_25": un25,
        "goal_si": raw.get("goal_si"), "goal_no": raw.get("goal_no"),
        "gol_attesi": raw.get("gol_attesi"),
        "risultati_esatti": raw.get("risultati_esatti", []),
        "sicura": bool(conf_raw >= 0.82 and max(p1, px, p2) > 45),
        "marcatori_casa": mc_h[:3], "marcatori_ospite": mc_a[:3],
        "formazione_casa": raw.get("formazione_casa") or _get_last_lineup(h_t),
        "formazione_ospite": raw.get("formazione_ospite") or _get_last_lineup(a_t),
        "h2h_applicato": bool(raw.get("h2h_applicato", False)),
        "h2h_partite": int(raw.get("h2h_partite", 0)),
        "bookmaker_live": bk_used_live,
        "bookmaker_live_data": bk_live if bk_used_live else None,
    }

# ─────────────────────────────
# CALENDARIO HARDCODED (fallback)
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

# ─────────────────────────────
# FANTACALCIO
# ─────────────────────────────
def _fantacalcio_impl(league, giornata):
    """Implementazione endpoint fantacalcio: statistiche giocatori per giornata."""
    stats = PLAYER_STATS_CACHE.get(league) or {}
    if not stats:
        try:
            _fetch_player_stats(league)
            stats = PLAYER_STATS_CACHE.get(league) or {}
        except Exception as e:
            print(f"⚠️ Fantacalcio stats {league}: {e}")

    cl = CLASSIFICA_CACHE.get(league) or []
    squadre = [r["Squadra"] for r in cl] if cl else []

    # Costruisci risposta
    giocatori = []
    for key, ps in stats.items():
        giocatori.append({
            "nome": ps.get("nome", ""),
            "squadra": ps.get("squadra", ""),
            "ruolo": ps.get("posizione", "C"),
            "gol": ps.get("gol", 0),
            "assist": ps.get("assist", 0),
            "media": ps.get("media", 0),
            "minuti": ps.get("minuti", 0),
            "presenze": ps.get("presenze", 0),
            "gialli": ps.get("gialli", 0),
            "rossi": ps.get("rossi", 0),
            "rigori_segnati": ps.get("rigori_segnati", 0),
            "forma": ps.get("forma", 1.0),
            "forma_trend": ps.get("forma_trend", "stabile"),
        })

    giocatori.sort(key=lambda x: (-x["gol"], -x["assist"], -x["media"]))
    return {
        "giocatori": giocatori,
        "squadre": squadre,
        "league": league,
        "giornata": giornata,
        "aggiornamento": datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC") if stats else "Non disponibile",
    }

# ─────────────────────────────
# PUSH NOTIFICATIONS
# ─────────────────────────────
VAPID_PUBLIC_KEY = "BBrZeD51wgoA9ITtBo8UPhHUf6o1lu1zwP16tZ9RNoI1F0yhVpMoWshroZI_nQIPqoZ_DRLVR2cu6B-WB9vE8J0"
VAPID_PRIVATE_KEY_PATH = os.path.join(_ROOT, "vapid_private.pem")
VAPID_EMAIL = "mailto:mario.costabile92@outlook.it"
_PUSH_SUBSCRIPTIONS = []

@app.get("/api/push/vapid-key")
async def get_vapid_key():
    return {"publicKey": VAPID_PUBLIC_KEY}

@app.post("/api/push/subscribe")
async def push_subscribe(data: dict, user: Optional[dict] = Depends(get_optional_user)):
    sub = data.get("subscription")
    if not sub:
        raise HTTPException(400, "Subscription mancante")
    _PUSH_SUBSCRIPTIONS.append({"subscription": sub, "user_id": user["id"] if user else None})
    return {"ok": True}

# ─────────────────────────────
# CALENDARIO ENDPOINT
# ─────────────────────────────
@app.get("/api/calendario")
async def calendario():
    """Calendario con risultati live integrati."""
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
            if LIVE_RESULTS_CACHE:
                for p in LIVE_RESULTS_CACHE:
                    if p["home"] == h and p["away"] == a:
                        match_data.update({"gol_h": p["gol_h"], "gol_a": p["gol_a"], "status": p["status"], "status_it": p.get("status_it", p["status"]), "minuto": p.get("minuto"), "live": p.get("live", False), "fixture_id": p.get("fixture_id"), "marcatori": p.get("marcatori", [])})
                        break
            if match_data["status"] == "NS":
                tutte_finite = False
                ha_da_giocare = True
            elif match_data["live"]:
                tutte_finite = False
                ha_live = True
            partite.append(match_data)
        if tutte_finite:
            stato = "completata"
        elif ha_live:
            stato = "live"
            giornata_corrente = str(num)
        else:
            stato = "prossima"
            if giornata_corrente is None and ha_da_giocare:
                giornata_corrente = str(num)
        giornate.append({"giornata": str(num), "data": info["data"], "partite": partite, "stato": stato, "live": ha_live})
    return {"giornate": giornate, "giornata_corrente": giornata_corrente or "38", "live": any(g.get("live") for g in giornate)}

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
# STARTUP EVENT
# ─────────────────────────────
@app.on_event("startup")
async def startup():
    global _df, _df_pl, _df_ll, _df_ucl, _df_uel, _df_uecl, _df_bl, _df_l1

    print("\n🚀 AVVIO SERVER MATCHIQ (modular)\n")

    # DB
    try:
        init_db()
        print("✅ DATABASE OK")
    except Exception as e:
        print("⚠️ DATABASE:", e)

    # DataFrames CSV (opzionali)
    if MOTORE_DISPONIBILE:
        for league_code, attr in [("", "_df"), ("E0", "_df_pl"), ("SP1", "_df_ll"), ("UCL", "_df_ucl"), ("UEL", "_df_uel"), ("UECL", "_df_uecl"), ("D1", "_df_bl"), ("F1", "_df_l1")]:
            try:
                df = load_all_data() if not league_code else load_all_data(league=league_code)
                globals()[attr] = df
                print(f"✅ Dataset {attr}: {len(df)} partite")
            except Exception as e:
                print(f"⚠️ Dataset {attr} non disponibile: {e}")
    else:
        print("⚠️ MOTORE NON DISPONIBILE - il server usa dati hardcoded")

    # Bootstrap servizi (delayed)
    try:
        from startup import bootstrap
        bootstrap(
            df=_df,
            enable_telegram=bool(os.environ.get("TELEGRAM_BOT_TOKEN", "")),
            verify_predictions_fn=verify_predictions,
        )
        print("✅ SERVER PRONTO\n")
    except Exception as e:
        print(f"⚠️ Bootstrap: {e}")
        # Fallback: avvia live updater direttamente
        threading.Thread(target=start_live_updater, kwargs={"verify_predictions_fn": verify_predictions}, daemon=True).start()

# ─────────────────────────────
# RUN LOCALE
# ─────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api_server:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
