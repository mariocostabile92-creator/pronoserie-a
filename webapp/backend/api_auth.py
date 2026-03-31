"""
api_auth.py - Versione Corazzata (Anti-Crash 72 Byte)
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
# Prendiamo la chiave e la forziamo a stare sotto i 64 byte per sicurezza totale
_raw_secret = os.environ.get("JWT_SECRET", "chiave-di-backup-molto-lunga-e-sicura-12345")
SECRET_KEY = _raw_secret.encode('utf-8')[:64].decode('utf-8', 'ignore')
ALGORITHM = "HS256"
TOKEN_EXPIRE_DAYS = 7

# ── Contesto Hashing ───────────────────────────────────────────────────────
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
_bearer_scheme = HTTPBearer(auto_error=False)

# ── IL FIX DEFINITIVO ───────────────────────────────────────────────────────
def _safe_bcrypt_input(s: str) -> str:
    """
    Questa funzione è il paracadute. Prende una stringa, la trasforma in byte,
    la taglia a 71 byte (per stare larghi) e la riporta a stringa.
    Bcrypt non vedrà MAI più di 72 byte.
    """
    if not s: return ""
    encoded = s.encode('utf-8')
    # Tagliamo a 71 per evitare qualsiasi arrotondamento strano della libreria
    truncated = encoded[:71]
    return truncated.decode('utf-8', 'ignore')

# ── Funzioni Password ───────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    if not password:
        raise ValueError("Password vuota")
    
    # Applichiamo il taglio di sicurezza prima di passare a passlib
    return _pwd_context.hash(_safe_bcrypt_input(password))

def verify_password(plain: str, hashed: str) -> bool:
    if not plain or not hashed:
        return False
    try:
        # Applichiamo lo stesso taglio anche in verifica
        return _pwd_context.verify(_safe_bcrypt_input(plain), hashed)
    except Exception as e:
        print(f"[AUTH] Errore critico verifica: {e}")
        return False

# ── Funzioni Token ──────────────────────────────────────────────────────────

def create_token(data: dict) -> str:
    payload = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=TOKEN_EXPIRE_DAYS)
    payload.update({"exp": expire})
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as e:
        raise ValueError(f"Token non valido: {str(e)}")

# ── Dipendenze FastAPI ──────────────────────────────────────────────────────

def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme)) -> dict:
    if not credentials:
        raise HTTPException(status_code=401, detail="Token mancante")
    try:
        payload = decode_token(credentials.credentials)
        user = get_user_by_id(int(payload.get("sub")))
        if not user: raise ValueError("Utente non trovato")
        return user
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Sessione invalida: {str(e)}")

def get_optional_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme)) -> Optional[dict]:
    if not credentials: return None
    try:
        payload = decode_token(credentials.credentials)
        return get_user_by_id(int(payload.get("sub")))
    except: return None