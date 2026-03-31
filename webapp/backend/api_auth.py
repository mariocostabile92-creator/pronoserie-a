"""
api_auth.py - Versione 3.0 (Fix definitivo hashpw)
Risolve il crash ValueError: password cannot be longer than 72 bytes.
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
# Usiamo una chiave fissa di 32 byte per evitare errori di checksum
SECRET_KEY = os.environ.get("JWT_SECRET", "secret-key-32-chars-long-1234567")[:32]
ALGORITHM = "HS256"
TOKEN_EXPIRE_DAYS = 7

# ── Contesto Hashing ───────────────────────────────────────────────────────
# Importante: impostiamo truncate_error=False per forzare la libreria a gestire il limite
_pwd_context = CryptContext(
    schemes=["bcrypt"], 
    deprecated="auto",
    bcrypt__truncate_error=False 
)

_bearer_scheme = HTTPBearer(auto_error=False)

# ── IL FIX PER HASHPW ───────────────────────────────────────────────────────

def _prepare_password(password: str) -> str:
    """
    Prepara la password per bcrypt:
    1. La codifica in UTF-8.
    2. La taglia a 71 byte (limite hardware 72).
    3. La riporta a stringa per passlib.
    """
    if not password:
        return ""
    # Taglio reale sui byte, non sui caratteri
    pwd_bytes = password.encode('utf-8')[:71]
    return pwd_bytes.decode('utf-8', 'ignore')

# ── Funzioni Password ───────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    if not password:
        raise ValueError("Password non fornita")
    
    # Passiamo la password già troncata
    return _pwd_context.hash(_prepare_password(password))


def verify_password(plain: str, hashed: str) -> bool:
    if not plain or not hashed:
        return False
    try:
        # Verifichiamo usando lo stesso troncamento
        return _pwd_context.verify(_prepare_password(plain), hashed)
    except Exception as e:
        print(f"[AUTH] Errore critico hashpw: {e}")
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
    except JWTError:
        raise ValueError("Token non valido")

# ── Dipendenze FastAPI ──────────────────────────────────────────────────────

def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme)) -> dict:
    if not credentials:
        raise HTTPException(status_code=401, detail="Non autenticato")
    try:
        payload = decode_token(credentials.credentials)
        user = get_user_by_id(int(payload.get("sub")))
        if not user: raise ValueError()
        return user
    except:
        raise HTTPException(status_code=401, detail="Sessione non valida")

def get_optional_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme)) -> Optional[dict]:
    if not credentials: return None
    try:
        payload = decode_token(credentials.credentials)
        return get_user_by_id(int(payload.get("sub")))
    except: return None