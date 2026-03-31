"""
api_auth.py - Versione Blindata (Fix 72 Byte)
Gestisce hashing sicuro, JWT e previene il crash di bcrypt su Railway.
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
# Tagliamo la SECRET_KEY a 64 caratteri (più che sicura e sotto il limite dei 72)
_raw_secret = os.environ.get("JWT_SECRET", "cambiami-in-produzione-12345678901234567890")
SECRET_KEY = _raw_secret[:64] 
ALGORITHM = "HS256"
TOKEN_EXPIRE_DAYS = 7

# ── Contesto per l'hashing delle password (bcrypt) ─────────────────────────
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ── Schema Bearer per FastAPI ───────────────────────────────────────────────
_bearer_scheme = HTTPBearer(auto_error=False)

# ── Helper per il limite dei 72 byte ────────────────────────────────────────

def _truncate_to_72_bytes(s: str) -> str:
    """
    Assicura che la stringa, convertita in byte, non superi i 72 byte.
    Questo evita il ValueError di bcrypt.
    """
    b = s.encode('utf-8')
    return b[:72].decode('utf-8', 'ignore')

# ── Funzioni password ───────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    """Genera l'hash bcrypt troncando preventivamente a 72 byte."""
    if not password:
        raise ValueError("La password non può essere vuota")
    
    # Applichiamo il taglio rigoroso sui byte
    password_safe = _truncate_to_72_bytes(password)
    return _pwd_context.hash(password_safe)


def verify_password(plain: str, hashed: str) -> bool:
    """Verifica la password troncando l'input per coerenza con l'hash."""
    if not plain or not hashed:
        return False
    try:
        password_safe = _truncate_to_72_bytes(plain)
        return _pwd_context.verify(password_safe, hashed)
    except Exception as e:
        print(f"[AUTH ERROR] Errore verifica: {e}")
        return False


# ── Funzioni token JWT ──────────────────────────────────────────────────────

def create_token(data: dict) -> str:
    """Genera un token JWT."""
    payload = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=TOKEN_EXPIRE_DAYS)
    payload.update({"exp": expire})
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    """Decodifica il token."""
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as e:
        raise ValueError(f"Token non valido: {str(e)}")


# ── Dipendenze FastAPI ──────────────────────────────────────────────────────

def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme)
) -> dict:
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token mancante",
        )

    try:
        payload = decode_token(credentials.credentials)
        user_id = payload.get("sub")
        user = get_user_by_id(int(user_id))
        if not user:
            raise ValueError("Utente non trovato")
        return user
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Sessione scaduta: {str(e)}",
        )

def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme)
) -> Optional[dict]:
    if not credentials:
        return None
    try:
        payload = decode_token(credentials.credentials)
        return get_user_by_id(int(payload.get("sub")))
    except:
        return None