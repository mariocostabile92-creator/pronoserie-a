"""
api_server.py
Server FastAPI principale per la webapp pronostici Serie A.
Riutilizza il motore predittivo nella cartella parent del progetto.
"""

import sys
import os

# Aggiunge la cartella root del progetto al path Python
_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
sys.path.insert(0, _ROOT)

from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

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
    # Il motore predittivo non è disponibile (es. CSV mancante)
    MOTORE_DISPONIBILE = False
    _import_err_msg = str(_import_err)

# ── Moduli locali backend ───────────────────────────────────────────────────
from database import init_db, log_api_call, count_daily_calls
from api_auth import get_current_user, get_optional_user, hash_password, verify_password, create_token
from api_models import (
    UserRegister, UserLogin, TokenResponse,
    PronosticoResponse, GiornataResponse, PartitaGiornata,
    ClassificaResponse, SquadraClassifica, MarcatoreResponse,
    SquadraResponse, GiocatoreRosa, InfortunatoInfo,
    CalendarioResponse, GiornataCalendario, PartitaCalendario,
    HealthResponse, RisultatoEsatto,
)
from database import get_user_by_email, create_user
from api_payments import router as payments_router

# ── Costanti ─────────────────────────────────────────────────────────────────
LIMITE_CHIAMATE_FREE = 5      # Massimo pronostici al giorno per utenti Free
VERSIONE = "1.0.0"

# ── Dati storici (caricati all'avvio) ─────────────────────────────────────
_df_storico = None


def _carica_dati():
    """
    Carica i dati CSV storici all'avvio del server.
    In caso di errore, il server continua con dati limitati.
    """
    global _df_storico
    if not MOTORE_DISPONIBILE:
        return
    try:
        _df_storico = load_all_data()
        print(f"[API] Dati storici caricati: {len(_df_storico)} partite Serie A.")
    except Exception as e:
        print(f"[API] ATTENZIONE: impossibile caricare i dati storici. Errore: {e}")
        _df_storico = None


# ── Applicazione FastAPI ────────────────────────────────────────────────────
app = FastAPI(
    title="Pronostici Serie A API",
    description="Backend per la webapp pronostici calcio Serie A 2025-2026",
    version=VERSIONE,
)

# ── CORS Middleware ─────────────────────────────────────────────────────────
# In produzione sostituire ["*"] con il dominio del frontend
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

# ── Serve il frontend (index.html) ─────────────────────────────────────────
from fastapi.responses import FileResponse, RedirectResponse

_FRONTEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'frontend')

@app.get("/", include_in_schema=False)
async def root_redirect():
    return RedirectResponse(url="/app")

@app.get("/app", include_in_schema=False)
@app.get("/app/{path:path}", include_in_schema=False)
async def serve_frontend(path: str = ""):
    return FileResponse(os.path.join(_FRONTEND_DIR, "index.html"))


# ── Evento di avvio ─────────────────────────────────────────────────────────
@app.on_event("startup")
async def startup_event():
    """Inizializza database e carica dati all'avvio del server."""
    init_db()
    _carica_dati()
    print("[API] Server avviato correttamente.")


# ── Funzioni helper ─────────────────────────────────────────────────────────

def _verifica_limite_free(utente: Optional[dict], endpoint: str) -> None:
    """
    Controlla il limite giornaliero per gli utenti Free (5 pronostici/giorno).
    Se l'utente è Pro o non autenticato (trattato come Free ma senza log), bypassa.
    Lancia HTTP 429 se il limite è superato.
    """
    if utente is None:
        # Utente anonimo: non logghiamo, ma non blocchiamo (funziona come Free senza log)
        return
    if utente.get("piano") == "pro":
        return  # Pro non ha limiti

    chiamate_oggi = count_daily_calls(utente["id"])
    if chiamate_oggi >= LIMITE_CHIAMATE_FREE:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"Hai superato il limite di {LIMITE_CHIAMATE_FREE} pronostici giornalieri "
                "del piano Free. Passa al piano Pro per pronostici illimitati!"
            )
        )
    log_api_call(utente["id"], endpoint)


def _filtra_pronostico(raw: dict, utente: Optional[dict], home: str, away: str) -> PronosticoResponse:
    """
    Costruisce il PronosticoResponse filtrando i campi in base al piano.
    Free: solo 1X2, quote, suggerimento, confidence.
    Pro: tutto.
    """
    piano = utente.get("piano", "free") if utente else "free"
    is_pro = (piano == "pro")

    # Campi base (disponibili per tutti)
    response = PronosticoResponse(
        home=home,
        away=away,
        prob_1=raw.get("prob_1", 0),
        prob_x=raw.get("prob_x", 0),
        prob_2=raw.get("prob_2", 0),
        quota_1=raw.get("quota_1", 0),
        quota_x=raw.get("quota_x", 0),
        quota_2=raw.get("quota_2", 0),
        suggerimento=raw.get("suggerimento", ""),
        sugg_label=raw.get("sugg_label", ""),
        confidence=raw.get("confidence", 0),
        confidence_label=raw.get("confidence_label", ""),
        confidence_color=raw.get("confidence_color", ""),
        piano_utente=piano,
    )

    if is_pro:
        # Campi aggiuntivi solo per utenti Pro
        response.lambda_home = raw.get("lambda_home")
        response.lambda_away = raw.get("lambda_away")
        response.over_15 = raw.get("over_15")
        response.under_15 = raw.get("under_15")
        response.over_25 = raw.get("over_25")
        response.under_25 = raw.get("under_25")
        response.over_35 = raw.get("over_35")
        response.under_35 = raw.get("under_35")
        response.goal_si = raw.get("goal_si")
        response.goal_no = raw.get("goal_no")
        response.gol_attesi = raw.get("gol_attesi")
        # Risultati esatti
        esatti_raw = raw.get("risultati_esatti", [])
        response.risultati_esatti = [
            RisultatoEsatto(score=r["score"], prob=r["prob"])
            for r in esatti_raw
        ] if esatti_raw else []
        response.xg_applied = raw.get("xg_applied")
        response.xg_home = raw.get("xg_home")
        response.xg_away = raw.get("xg_away")
        response.book_prob_1 = raw.get("book_prob_1")
        response.book_prob_x = raw.get("book_prob_x")
        response.book_prob_2 = raw.get("book_prob_2")
        response.delta_bk_1 = raw.get("delta_bk_1")
        response.delta_bk_x = raw.get("delta_bk_x")
        response.delta_bk_2 = raw.get("delta_bk_2")
        response.n_bookmakers = raw.get("n_bookmakers")
        response.h2h_applied = raw.get("h2h_applied")
        response.h2h_n = raw.get("h2h_n")
        response.inj_home = raw.get("inj_home")
        response.inj_away = raw.get("inj_away")
        response.tips_extra = raw.get("tips_extra", [])

    return response


def _genera_pronostico(home: str, away: str) -> dict:
    """
    Chiama il motore predittivo e ritorna il dizionario grezzo del pronostico.
    Lancia HTTPException se i dati non sono disponibili o le squadre non esistono.
    """
    if not MOTORE_DISPONIBILE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Motore predittivo non disponibile. Controlla i dati CSV."
        )

    if _df_storico is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Dati storici non caricati. Riprova tra qualche secondo."
        )

    # Normalizza i nomi delle squadre
    home_norm = home.strip().title()
    away_norm = away.strip().title()

    try:
        home_stats = get_team_stats(_df_storico, home_norm, opponent=away_norm)
        away_stats = get_team_stats(_df_storico, away_norm, opponent=home_norm)

        if home_stats["n_partite"] == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Squadra '{home_norm}' non trovata nei dati storici."
            )
        if away_stats["n_partite"] == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Squadra '{away_norm}' non trovata nei dati storici."
            )

        raw = get_prediction(home_stats, away_stats, df=_df_storico)
        return raw

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Errore nel calcolo del pronostico: {e}"
        )


# ── ENDPOINT AUTENTICAZIONE ─────────────────────────────────────────────────

@app.post("/api/auth/register", response_model=TokenResponse, tags=["Autenticazione"])
async def registra(dati: UserRegister):
    """
    Registra un nuovo utente con email e password.
    Ritorna un token JWT valido 7 giorni.
    """
    email = dati.email.lower().strip()
    if not email or "@" not in email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Indirizzo email non valido."
        )
    if len(dati.password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La password deve essere di almeno 6 caratteri."
        )

    # Controlla se l'email è già registrata
    esistente = get_user_by_email(email)
    if esistente:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email già registrata. Effettua il login."
        )

    # Crea l'utente
    pw_hash = hash_password(dati.password)
    nuovo_utente = create_user(email, pw_hash)
    if nuovo_utente is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email già registrata. Effettua il login."
        )

    token = create_token({"sub": str(nuovo_utente["id"])})
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        piano=nuovo_utente["piano"]
    )


@app.post("/api/auth/login", response_model=TokenResponse, tags=["Autenticazione"])
async def login(dati: UserLogin):
    """
    Autentica un utente esistente con email e password.
    Ritorna un token JWT valido 7 giorni.
    """
    email = dati.email.lower().strip()
    utente = get_user_by_email(email)

    if utente is None or not verify_password(dati.password, utente["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o password non corretti."
        )

    token = create_token({"sub": str(utente["id"])})
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        piano=utente["piano"]
    )


# ── ENDPOINT PRONOSTICI ─────────────────────────────────────────────────────

@app.get("/api/pronostico/{home}/{away}", response_model=PronosticoResponse, tags=["Pronostici"])
async def pronostico_partita(
    home: str,
    away: str,
    utente: Optional[dict] = Depends(get_optional_user)
):
    """
    Calcola il pronostico per una partita specifica.
    - Utenti Free / non autenticati: solo 1X2, quote, suggerimento, confidence (max 5 al giorno se loggati)
    - Utenti Pro: pronostico completo con Over/Under, Goal, xG, H2H, infortunati, risultati esatti
    """
    _verifica_limite_free(utente, f"pronostico/{home}/{away}")

    raw = _genera_pronostico(home, away)
    return _filtra_pronostico(raw, utente, home.strip().title(), away.strip().title())


@app.get("/api/giornata/{num}", response_model=GiornataResponse, tags=["Pronostici"])
async def pronostici_giornata(
    num: int,
    utente: Optional[dict] = Depends(get_optional_user)
):
    """
    Calcola i pronostici per tutte le partite di una giornata (31-38).
    - Free: solo 1X2 base per ogni partita
    - Pro: pronostico completo per ogni partita
    """
    if num < 31 or num > 38:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Giornata non valida. Sono disponibili le giornate dalla 31 alla 38."
        )

    if not MOTORE_DISPONIBILE or _df_storico is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Motore predittivo non disponibile."
        )

    giornata_info = CALENDARIO_31_38.get(num)
    if not giornata_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Giornata {num} non trovata nel calendario."
        )

    # Log e verifica limite (conta come 1 chiamata la richiesta di giornata intera)
    _verifica_limite_free(utente, f"giornata/{num}")

    partite_result = []
    for home, away in giornata_info["partite"]:
        try:
            raw = _genera_pronostico(home, away)
            pronostico = _filtra_pronostico(raw, utente, home, away)
        except Exception:
            # Se il calcolo fallisce per una partita, inserisce dati vuoti
            pronostico = PronosticoResponse(
                home=home, away=away,
                prob_1=33.3, prob_x=33.3, prob_2=33.3,
                quota_1=3.0, quota_x=3.0, quota_2=3.0,
                suggerimento="?", sugg_label="Dati non disponibili",
                confidence=0.0, confidence_label="N/D", confidence_color="#999999",
                piano_utente=utente.get("piano", "free") if utente else "free",
            )
        partite_result.append(PartitaGiornata(home=home, away=away, pronostico=pronostico))

    piano = utente.get("piano", "free") if utente else "free"
    return GiornataResponse(
        giornata=num,
        data=giornata_info["data"],
        partite=partite_result,
        piano_utente=piano,
    )


# ── ENDPOINT CLASSIFICA ─────────────────────────────────────────────────────

@app.get("/api/classifica", response_model=ClassificaResponse, tags=["Classifica"])
async def classifica():
    """
    Ritorna la classifica reale Serie A e la classifica marcatori.
    Endpoint pubblico, non richiede autenticazione.
    """
    if not MOTORE_DISPONIBILE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Dati classifica non disponibili."
        )

    try:
        class_raw = get_classifica_reale()
        marcatori_raw = get_marcatori()

        class_list = [SquadraClassifica(**sq) for sq in class_raw]
        marc_list = [MarcatoreResponse(**m) for m in marcatori_raw]

        return ClassificaResponse(
            classifica=class_list,
            marcatori=marc_list,
            giornata_attuale=GIORNATA_ATTUALE,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Errore nel recupero della classifica: {e}"
        )


# ── ENDPOINT CALENDARIO ─────────────────────────────────────────────────────

@app.get("/api/calendario", response_model=CalendarioResponse, tags=["Calendario"])
async def calendario():
    """
    Ritorna il calendario completo delle giornate 31-38 con tutte le partite.
    Endpoint pubblico, non richiede autenticazione.
    """
    if not MOTORE_DISPONIBILE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Dati calendario non disponibili."
        )

    try:
        giornate = []
        for num in range(31, 39):
            info = CALENDARIO_31_38.get(num)
            if info:
                partite = [PartitaCalendario(home=h, away=a) for h, a in info["partite"]]
                giornate.append(GiornataCalendario(
                    giornata=num,
                    data=info["data"],
                    partite=partite,
                ))
        return CalendarioResponse(giornate=giornate)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Errore nel recupero del calendario: {e}"
        )


# ── ENDPOINT SQUADRA ────────────────────────────────────────────────────────

@app.get("/api/squadra/{nome}", response_model=SquadraResponse, tags=["Squadre"])
async def info_squadra(
    nome: str,
    utente: Optional[dict] = Depends(get_optional_user)
):
    """
    Ritorna informazioni sulla squadra: rosa, infortunati, allenatore.
    - Endpoint pubblico: rosa base e infortunati sempre visibili
    - Utenti Pro: include anche la formazione probabile dettagliata
    """
    if not MOTORE_DISPONIBILE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Dati squadre non disponibili."
        )

    # Normalizza il nome
    nome_norm = nome.strip().title()

    # Controlla che la squadra esista
    squadre_valide = list(ROSE_2526.keys())
    if nome_norm not in squadre_valide:
        # Prova una ricerca case-insensitive
        match = next((s for s in squadre_valide if s.lower() == nome_norm.lower()), None)
        if match:
            nome_norm = match
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Squadra '{nome_norm}' non trovata. Squadre disponibili: {', '.join(sorted(squadre_valide))}"
            )

    try:
        rosa_raw = get_rosa(nome_norm)
        allenatore = get_allenatore(nome_norm)

        # Infortunati
        try:
            infort_raw = get_infortunati(nome_norm)
        except Exception:
            infort_raw = []

        rosa_list = [
            GiocatoreRosa(nome=g[0], ruolo=g[1], numero=g[2])
            for g in rosa_raw
        ]
        infort_list = [
            InfortunatoInfo(
                nome=i.get("nome", ""),
                tipo=i.get("tipo", "infortunio"),
                dettaglio=i.get("dettaglio", "")
            )
            for i in infort_raw
        ]

        piano = utente.get("piano", "free") if utente else "free"

        # Formazione probabile: solo per utenti Pro
        formazione = None
        if piano == "pro":
            try:
                formazione = get_formazione(nome_norm)
            except Exception:
                formazione = None

        return SquadraResponse(
            nome=nome_norm,
            allenatore=allenatore,
            rosa=rosa_list,
            infortunati=infort_list,
            formazione=formazione,
            piano_utente=piano,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Errore nel recupero dei dati squadra: {e}"
        )


# ── ENDPOINT HEALTH CHECK ───────────────────────────────────────────────────

@app.get("/api/health", response_model=HealthResponse, tags=["Sistema"])
async def health_check():
    """
    Verifica lo stato del server.
    Ritorna info sul motore predittivo e i dati caricati.
    """
    n_partite = len(_df_storico) if _df_storico is not None else 0
    return HealthResponse(
        status="ok",
        dati_caricati=(_df_storico is not None),
        n_partite_storiche=n_partite,
        versione=VERSIONE,
    )


# ── Avvio diretto (per sviluppo) ────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    porta = int(os.environ.get("PORT", 8000))
    uvicorn.run("api_server:app", host="0.0.0.0", port=porta, reload=True)
