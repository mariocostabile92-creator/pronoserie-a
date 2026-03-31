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
# Recupera la chiave da Railway. Se manca, usa una chiave di backup (solo per local test).
SECRET_KEY = os.environ.get("JWT_SECRET", "cambiami-in-produzione-12345")
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
    
    # Tronchiamo a 72 byte (limite di sicurezza di bcrypt)
    return _pwd_context.hash(password[:72])


def verify_password(plain: str, hashed: str) -> bool:
    """
    Verifica se la password in chiaro corrisponde all'hash.
    Tronca la password in chiaro a 72 caratteri per coerenza con l'hashing.
    """
    if not plain or not hashed:
        return False
    try:
        return _pwd_context.verify(plain[:72], hashed)
    except Exception:
        return False


# ── Funzioni token JWT ──────────────────────────────────────────────────────

def create_token(data: dict) -> str:
    """Genera un token JWT con scadenza impostata."""
    payload = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=TOKEN_EXPIRE_DAYS)
    payload.update({"exp": expire})
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    """Decodifica il token e verifica la validità."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError as e:
        raise ValueError(f"Token non valido o scaduto: {e}")


# ── Dipendenze FastAPI ──────────────────────────────────────────────────────

def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme)
) -> dict:
    """
    Verifica il token e ritorna l'utente dal database.
    Usato per proteggere le rotte (es. /checkout).
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
            raise ValueError("sub mancante")
        
        user = get_user_by_id(int(user_id))
        if not user:
            raise ValueError("Utente non trovato")
            
        return user

    except (ValueError, Exception) as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Sessione non valida: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )

def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme)
) -> Optional[dict]:
    """Ritorna l'utente se loggato, altrimenti None (senza bloccare la richiesta)."""
    if not credentials:
        return None
    try:
        payload = decode_token(credentials.credentials)
        return get_user_by_id(int(payload.get("sub")))
    except:
        return None