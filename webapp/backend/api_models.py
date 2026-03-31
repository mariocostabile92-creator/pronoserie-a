"""
api_models.py
Modelli Pydantic per request/response della webapp pronostici Serie A.
"""

from typing import Optional, List, Any
from pydantic import BaseModel, EmailStr


# ── Autenticazione ──────────────────────────────────────────────────────────

class UserRegister(BaseModel):
    """Dati per la registrazione di un nuovo utente."""
    email: str
    password: str


class UserLogin(BaseModel):
    """Dati per il login di un utente esistente."""
    email: str
    password: str


class TokenResponse(BaseModel):
    """Risposta dopo login o registrazione con successo."""
    access_token: str
    token_type: str = "bearer"
    piano: str  # 'free' o 'pro'


# ── Pronostici ──────────────────────────────────────────────────────────────

class RisultatoEsatto(BaseModel):
    """Probabilità per un risultato esatto specifico."""
    score: str        # es. "2-1"
    prob: float       # percentuale (0-100)


class TipExtra(BaseModel):
    """Consiglio aggiuntivo (es. Over 2.5, Goal Sì)."""
    label: str
    prob: float
    colore: str


class PronosticoResponse(BaseModel):
    """
    Risposta completa di un pronostico.
    I campi Pro sono None per gli utenti Free.
    """
    # Squadre
    home: str
    away: str

    # Probabilità 1X2 (disponibili per tutti)
    prob_1: float
    prob_x: float
    prob_2: float

    # Quote consigliate (disponibili per tutti)
    quota_1: float
    quota_x: float
    quota_2: float

    # Suggerimento principale (disponibile per tutti)
    suggerimento: str        # "1", "X" o "2"
    sugg_label: str          # "Vittoria Casa", "Pareggio", "Vittoria Ospite"

    # Indice di affidabilità (disponibile per tutti)
    confidence: float
    confidence_label: str    # "Alta", "Media", "Bassa"
    confidence_color: str

    # ── Campi Pro (None per utenti Free) ───────────────────────────────────

    # Lambda Poisson
    lambda_home: Optional[float] = None
    lambda_away: Optional[float] = None

    # Over/Under
    over_15: Optional[float] = None
    under_15: Optional[float] = None
    over_25: Optional[float] = None
    under_25: Optional[float] = None
    over_35: Optional[float] = None
    under_35: Optional[float] = None

    # Goal / NoGoal
    goal_si: Optional[float] = None
    goal_no: Optional[float] = None

    # Gol attesi
    gol_attesi: Optional[float] = None

    # Risultati esatti più probabili
    risultati_esatti: Optional[List[RisultatoEsatto]] = None

    # xG stagione corrente
    xg_applied: Optional[bool] = None
    xg_home: Optional[float] = None
    xg_away: Optional[float] = None

    # Confronto bookmaker
    book_prob_1: Optional[float] = None
    book_prob_x: Optional[float] = None
    book_prob_2: Optional[float] = None
    delta_bk_1: Optional[float] = None
    delta_bk_x: Optional[float] = None
    delta_bk_2: Optional[float] = None
    n_bookmakers: Optional[int] = None

    # H2H (testa a testa)
    h2h_applied: Optional[bool] = None
    h2h_n: Optional[int] = None
    h2h_stats: Optional[Any] = None      # dict completo h2h

    # Infortunati
    inj_home: Optional[int] = None
    inj_away: Optional[int] = None

    # Consigli extra
    tips_extra: Optional[List[Any]] = None

    # Info piano utente
    piano_utente: str = "free"           # "free" o "pro"


# ── Giornata ────────────────────────────────────────────────────────────────

class PartitaGiornata(BaseModel):
    """Singola partita nella risposta di una giornata."""
    home: str
    away: str
    pronostico: PronosticoResponse


class GiornataResponse(BaseModel):
    """Risposta con tutti i pronostici di una giornata."""
    giornata: int
    data: str
    partite: List[PartitaGiornata]
    piano_utente: str = "free"


# ── Classifica ──────────────────────────────────────────────────────────────

class SquadraClassifica(BaseModel):
    """Riga della classifica."""
    Squadra: str
    Punti: int
    G: int
    V: int
    N: int
    P: int
    GF: int
    GS: int
    DR: int


class MarcatoreResponse(BaseModel):
    """Riga della classifica marcatori."""
    pos: int
    giocatore: str
    squadra: str
    gol: int


class ClassificaResponse(BaseModel):
    """Risposta con classifica e classifica marcatori."""
    classifica: List[SquadraClassifica]
    marcatori: List[MarcatoreResponse]
    giornata_attuale: int


# ── Squadra ─────────────────────────────────────────────────────────────────

class GiocatoreRosa(BaseModel):
    """Singolo giocatore nella rosa."""
    nome: str
    ruolo: str   # P, D, C, A
    numero: int


class InfortunatoInfo(BaseModel):
    """Giocatore infortunato o squalificato."""
    nome: str
    tipo: str        # "infortunio" o "squalifica"
    dettaglio: str


class SquadraResponse(BaseModel):
    """Risposta con info complete di una squadra."""
    nome: str
    allenatore: str
    rosa: List[GiocatoreRosa]
    infortunati: List[InfortunatoInfo]
    # Formazione base (solo Pro)
    formazione: Optional[Any] = None
    piano_utente: str = "free"


# ── Calendario ──────────────────────────────────────────────────────────────

class PartitaCalendario(BaseModel):
    """Singola partita nel calendario."""
    home: str
    away: str


class GiornataCalendario(BaseModel):
    """Giornata nel calendario."""
    giornata: int
    data: str
    partite: List[PartitaCalendario]


class CalendarioResponse(BaseModel):
    """Risposta con il calendario completo delle giornate 31-38."""
    giornate: List[GiornataCalendario]


# ── Health check ────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    """Risposta al health check."""
    status: str
    dati_caricati: bool
    n_partite_storiche: int
    versione: str = "1.0.0"
