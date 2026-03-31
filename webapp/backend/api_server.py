"""
api_server.py
Server FastAPI principale per la webapp pronostici Serie A.
Versione Aggiornata con Inizializzazione Database e Gestione Stripe.
"""

import sys
import os

# Aggiunge la cartella root del progetto al path Python
_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
sys.path.insert(0, _ROOT)

from typing import Optional
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse

# ── Moduli del motore predittivo (cartella parent) ──────────────────────────
try:
    from data_loader import load_all_data
    from stats_engine import get_team_stats
    from predictor import get_prediction
    from season_2526 import (
        get_classifica_reale,
        get_calendario_rimanente,
        SQUADRE_2526,
        GIORNATA_ATTUALE,
        CALENDARIO_31_38,
    )
    from squads_2526 import (
        get_rosa,
        get_allenatore,
        get_marcatori,
        get_giocatori_per_ruolo,
        ROSE_2526,
    )
    from live_data import get_infortunati, get_formazione
    MOTORE_DISPONIBILE = True
except ImportError as _import_err:
    MOTORE_DISPONIBILE = False
    _import_err_msg = str(_import_err)

# ── Moduli locali backend ───────────────────────────────────────────────────
# Assicurati che questi file siano nella stessa cartella di api_server.py
from database import init_db, log_api_call, count_daily_calls, get_user_by_email, create_user
from api_auth import get_current_user, get_optional_user, hash_password, verify_password, create_token
from api_models import (
    UserRegister, UserLogin, TokenResponse,
    PronosticoResponse, GiornataResponse, PartitaGiornata,
    ClassificaResponse, SquadraClassifica, MarcatoreResponse,
    SquadraResponse, GiocatoreRosa, InfortunatoInfo,
    CalendarioResponse, GiornataCalendario, PartitaCalendario,
    HealthResponse, RisultatoEsatto,
)
from api_payments import router as payments_router

# ── Costanti ─────────────────────────────────────────────────────────────────
LIMITE_CHIAMATE_FREE = 5      # Massimo pronostici al giorno per utenti Free
VERSIONE = "1.1.0"            # Incrementata versione per migrazione DB

# ── Dati storici (caricati all'avvio) ─────────────────────────────────────
_df_storico = None

def _carica_dati():
    """Carica i dati CSV storici all'avvio del server."""
    global _df_storico
    if not MOTORE_DISPONIBILE:
        return
    try:
        _df_storico = load_all_data()
        print(f"[API] Dati storici caricati: {len(_df_storico)} partite.")
    except Exception as e:
        print(f"[API] ERRORE caricamento CSV: {e}")
        _df_storico = None

# ── Applicazione FastAPI ────────────────────────────────────────────────────
app = FastAPI(
    title="Pronostici Serie A API",
    description="Backend per la webapp pronostici calcio Serie A 2025-2026",
    version=VERSIONE,
)

# ── CORS Middleware ─────────────────────────────────────────────────────────
CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Includi router pagamenti ────────────────────────────────────────────────
app.include_router(payments_router)

# ── Gestione Frontend ──────────────────────────────────────────────────────
_FRONTEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'frontend')

@app.get("/", include_in_schema=False)
async def root_redirect():
    return RedirectResponse(url="/app")

@app.get("/app", include_in_schema=False)
@app.get("/app/{path:path}", include_in_schema=False)
async def serve_frontend(path: str = ""):
    return FileResponse(os.path.join(_FRONTEND_DIR, "index.html"))

# ── EVENTO DI AVVIO (MIGLIORATO) ─────────────────────────────────────────────
@app.on_event("startup")
async def startup_event():
    """Inizializza database (migrazioni incluse) e carica dati."""
    print(f"\n{'='*40}")
    print(f"AVVIO SERVER PRONOSTICI v{VERSIONE}")
    print(f"{'='*40}")
    
    # 1. Inizializzazione DB e Migrazioni Colonne Stripe
    try:
        print("[DATABASE] Controllo tabelle e applicazione migrazioni...")
        init_db() 
        print("[DATABASE] OK: Tabelle pronte e colonne aggiornate.")
    except Exception as e:
        print(f"[DATABASE] ERRORE CRITICO in startup: {e}")

    # 2. Caricamento dati Motore
    _carica_dati()
    
    print(f"[SYSTEM] Pronto a ricevere richieste.\n{'='*40}\n")

# ── Helper Funzioni ─────────────────────────────────────────────────────────

def _verifica_limite_free(utente: Optional[dict], endpoint: str) -> None:
    if utente is None: return
    if utente.get("piano") == "pro": return

    chiamate_oggi = count_daily_calls(utente["id"])
    if chiamate_oggi >= LIMITE_CHIAMATE_FREE:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Limite di {LIMITE_CHIAMATE_FREE} pronostici raggiunto. Passa a Pro!"
        )
    log_api_call(utente["id"], endpoint)

def _filtra_pronostico(raw: dict, utente: Optional[dict], home: str, away: str) -> PronosticoResponse:
    piano = utente.get("piano", "free") if utente else "free"
    is_pro = (piano == "pro")

    response = PronosticoResponse(
        home=home, away=away,
        prob_1=raw.get("prob_1", 0), prob_x=raw.get("prob_x", 0), prob_2=raw.get("prob_2", 0),
        quota_1=raw.get("quota_1", 0), quota_x=raw.get("quota_x", 0), quota_2=raw.get("quota_2", 0),
        suggerimento=raw.get("suggerimento", ""), sugg_label=raw.get("sugg_label", ""),
        confidence=raw.get("confidence", 0), confidence_label=raw.get("confidence_label", ""),
        confidence_color=raw.get("confidence_color", ""), piano_utente=piano,
    )

    if is_pro:
        # Campi extra solo per Pro
        for campo in ["lambda_home", "lambda_away", "over_15", "under_15", "over_25", "under_25", 
                     "over_35", "under_35", "goal_si", "goal_no", "gol_attesi", "xg_applied", 
                     "xg_home", "xg_away", "tips_extra"]:
            setattr(response, campo, raw.get(campo))
        
        esatti_raw = raw.get("risultati_esatti", [])
        response.risultati_esatti = [RisultatoEsatto(score=r["score"], prob=r["prob"]) for r in esatti_raw]

    return response

def _genera_pronostico(home: str, away: str) -> dict:
    home_norm, away_norm = home.strip().title(), away.strip().title()
    
    if MOTORE_DISPONIBILE and _df_storico is not None:
        try:
            h_stats = get_team_stats(_df_storico, home_norm, opponent=away_norm)
            a_stats = get_team_stats(_df_storico, away_norm, opponent=home_norm)
            return get_prediction(h_stats, a_stats, df=_df_storico)
        except: pass

    # Fallback semplice se il motore fallisce
    return {"prob_1": 33.3, "prob_x": 33.4, "prob_2": 33.3, "suggerimento": "X", "sugg_label": "N/D"}

# ── ENDPOINTS ────────────────────────────────────────────────────────────────

@app.post("/api/auth/register", response_model=TokenResponse, tags=["Autenticazione"])
async def registra(dati: UserRegister):
    email = dati.email.lower().strip()
    if get_user_by_email(email):
        raise HTTPException(status_code=409, detail="Email già registrata.")
    
    pw_hash = hash_password(dati.password)
    nuovo_utente = create_user(email, pw_hash)
    if not nuovo_utente:
        raise HTTPException(status_code=400, detail="Errore creazione utente.")

    token = create_token({"sub": str(nuovo_utente["id"])})
    return TokenResponse(access_token=token, token_type="bearer", piano=nuovo_utente["piano"])

@app.post("/api/auth/login", response_model=TokenResponse, tags=["Autenticazione"])
async def login(dati: UserLogin):
    utente = get_user_by_email(dati.email.lower().strip())
    if not utente or not verify_password(dati.password, utente["password_hash"]):
        raise HTTPException(status_code=401, detail="Credenziali errate.")

    token = create_token({"sub": str(utente["id"])})
    return TokenResponse(access_token=token, token_type="bearer", piano=utente["piano"])

@app.get("/api/pronostico/{home}/{away}", response_model=PronosticoResponse, tags=["Pronostici"])
async def pronostico_partita(home: str, away: str, utente: Optional[dict] = Depends(get_optional_user)):
    _verifica_limite_free(utente, f"pronostico/{home}/{away}")
    raw = _genera_pronostico(home, away)
    return _filtra_pronostico(raw, utente, home, away)

@app.get("/api/health", response_model=HealthResponse, tags=["Sistema"])
async def health_check():
    return HealthResponse(status="ok", dati_caricati=(_df_storico is not None), versione=VERSIONE)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api_server:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))

