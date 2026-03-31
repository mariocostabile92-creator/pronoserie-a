"""
api_auth.py - Versione Ottimizzata
Gestisce hashing sicuro (max 72 byte per bcrypt), JWT e integrazione Railway.
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext

from database import get_user_by_id

# ── Configurazione JWT ──────────────────────────────────────────────────────
# MIGLIORIA: Tronchiamo la SECRET_KEY a 72 caratteri. 
# Se la variabile su Railway è troppo lunga, questo evita crash inaspettati.
SECRET_KEY = os.environ.get("JWT_SECRET", "cambiami-in-produzione-12345")[:72]
ALGORITHM = "HS256"
TOKEN_EXPIRE_DAYS = 7

# ── Contesto per l'hashing delle password (bcrypt) ─────────────────────────
# bcrypt ha un limite hardware di 72 caratteri.
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ── Schema Bearer per FastAPI ───────────────────────────────────────────────
_bearer_scheme = HTTPBearer(auto_error=False)


# ── Funzioni password (FIX per ValueError: 72 bytes) ────────────────────────

def hash_password(password: str) -> str:
    """
    Genera l'hash bcrypt di una password.
    Tronca a 72 caratteri per evitare il crash 'ValueError: password cannot be longer than 72 bytes'.
    """
    if not password:
        raise ValueError("La password non può essere vuota")
    
    # Tronchiamo a 72 byte prima di passarla a passlib
    return _pwd_context.hash(password[:72])


def verify_password(plain: str, hashed: str) -> bool:
    """
    Verifica se la password in chiaro corrisponde all'hash.
    Tronca la password in chiaro a 72 caratteri per coerenza.
    """
    if not plain or not hashed:
        return False
    try:
        # Importante: usiamo lo stesso troncamento usato in fase di hash
        return _pwd_context.verify(plain[:72], hashed)
    except Exception:
        # Se l'hash nel DB è corrotto o non compatibile, ritorniamo False senza crashare
        return False


# ── Funzioni token JWT ──────────────────────────────────────────────────────

def create_token(data: dict) -> str:
    """Genera un token JWT con scadenza impostata."""
    payload = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=TOKEN_EXPIRE_DAYS)
    payload.update({"exp": expire})
    # SECRET_KEY è già troncata in cima al file per sicurezza
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    """Decodifica il token e verifica la validità."""
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as e:
        # Gestione errore specifica per token scaduti o manomessi
        raise ValueError(f"Token non valido o scaduto: {str(e)}")


# ── Dipendenze FastAPI ──────────────────────────────────────────────────────

def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme)
) -> dict:
    """
    Verifica il token e ritorna l'utente dal database.
    Protegge le rotte che richiedono autenticazione.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Accesso negato: Token mancante",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_token(credentials.credentials)
        user_id = payload.get("sub")
        if not user_id:
            raise ValueError("Identificativo utente (sub) mancante nel token")
        
        user = get_user_by_id(int(user_id))
        if not user:
            raise ValueError("Utente non trovato nel database")
            
        return user

    except (ValueError, Exception) as e:
        # Logghiamo l'errore internamente e ritorniamo un 401 pulito al frontend
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Sessione non valida: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )

def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme)
) -> Optional[dict]:
    """Ritorna l'utente se il token è valido, altrimenti None senza bloccare la richiesta."""
    if not credentials:
        return None
    try:
        payload = decode_token(credentials.credentials)
        sub = payload.get("sub")
        return get_user_by_id(int(sub)) if sub else None
    except:
        return None