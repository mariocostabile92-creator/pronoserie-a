"""
api_auth.py - Versione Corazzata 2.0 (Soluzione Finale ValueError)
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
# Chiave segreta forzata a 32 caratteri (sicurissima e zero errori)
_raw_secret = os.environ.get("JWT_SECRET", "cambiami-in-produzione-1234567890")
SECRET_KEY = _raw_secret[:32] 
ALGORITHM = "HS256"
TOKEN_EXPIRE_DAYS = 7

# ── Contesto Hashing (Configurazione Specifica per Python 3.12) ─────────────
# Forziamo bcrypt a non usare backend esterni che causano il crash dei 72 byte
_pwd_context = CryptContext(
    schemes=["bcrypt"], 
    deprecated="auto",
    bcrypt__truncate_error=False  # Dice a passlib di troncare lui invece di crashare
)

_bearer_scheme = HTTPBearer(auto_error=False)

# ── Funzioni Password ───────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    if not password:
        raise ValueError("Password vuota")
    
    # TRONCAMENTO MANUALE RIGIDO (Max 71 byte per sicurezza)
    # Trasformiamo in byte, tagliamo e torniamo in stringa
    pwd_bytes = password.encode('utf-8')[:71]
    pwd_to_hash = pwd_bytes.decode('utf-8', 'ignore')
    
    return _pwd_context.hash(pwd_to_hash)

def verify_password(plain: str, hashed: str) -> bool:
    if not plain or not hashed:
        return False
    try:
        # Applichiamo lo stesso trattamento in verifica
        pwd_bytes = plain.encode('utf-8')[:71]
        pwd_to_verify = pwd_bytes.decode('utf-8', 'ignore')
        
        return _pwd_context.verify(pwd_to_verify, hashed)
    except Exception as e:
        print(f"[AUTH] Errore verifica: {e}")
        return False

# ── Funzioni Token ──────────────────────────────────────────────────────────

def create_token(data: dict) -> str:
    try:
        payload = data.copy()
        expire = datetime.now(timezone.utc) + timedelta(days=TOKEN_EXPIRE_DAYS)
        payload.update({"exp": expire})
        return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    except Exception as e:
        print(f"[AUTH] Errore encoding token: {e}")
        raise e

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
        user_id = payload.get("sub")
        user = get_user_by_id(int(user_id))
        if not user:
            raise ValueError("Utente non trovato")
        return user
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Sessione invalida: {str(e)}")

def get_optional_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme)) -> Optional[dict]:
    if not credentials: return None
    try:
        payload = decode_token(credentials.credentials)
        return get_user_by_id(int(payload.get("sub")))
    except: return None