"""
api_auth.py
Autenticazione JWT per la webapp pronostici Serie A.
Gestisce hashing password, generazione e verifica token JWT.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext

from database import get_user_by_id

# ── Configurazione JWT ──────────────────────────────────────────────────────
SECRET_KEY = "pronostici-serie-a-secret-key-change-in-production"
ALGORITHM = "HS256"
TOKEN_EXPIRE_DAYS = 7

# ── Contesto per l'hashing delle password (bcrypt) ─────────────────────────
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ── Schema Bearer per FastAPI ───────────────────────────────────────────────
_bearer_scheme = HTTPBearer(auto_error=False)


# ── Funzioni password ───────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    """Genera l'hash bcrypt di una password in chiaro."""
    return _pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """Verifica che la password in chiaro corrisponda all'hash bcrypt."""
    return _pwd_context.verify(plain, hashed)


# ── Funzioni token JWT ──────────────────────────────────────────────────────

def create_token(data: dict) -> str:
    """
    Genera un token JWT con scadenza TOKEN_EXPIRE_DAYS giorni.
    Il payload viene copiato per evitare mutazioni indesiderate.
    """
    payload = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=TOKEN_EXPIRE_DAYS)
    payload["exp"] = expire
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    """
    Decodifica e valida un token JWT.
    Ritorna il payload come dizionario.
    Lancia ValueError se il token è scaduto o non valido.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError as e:
        raise ValueError(f"Token non valido: {e}")


# ── Dipendenze FastAPI ──────────────────────────────────────────────────────

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme)
) -> dict:
    """
    Dipendenza FastAPI: estrae e valida il token Bearer.
    Ritorna il dict dell'utente autenticato.
    Lancia HTTP 401 se il token manca, è scaduto o non valido.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token di autenticazione mancante",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_token(credentials.credentials)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token non valido o scaduto",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token non valido: campo 'sub' mancante",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = get_user_by_id(int(user_id))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Utente non trovato",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme)
) -> Optional[dict]:
    """
    Dipendenza FastAPI: prova a estrarre l'utente dal token Bearer.
    Ritorna il dict dell'utente se autenticato, altrimenti None.
    Non lancia eccezioni: usato per endpoint pubblici con funzionalità extra per utenti loggati.
    """
    if credentials is None:
        return None

    try:
        payload = decode_token(credentials.credentials)
    except ValueError:
        return None

    user_id = payload.get("sub")
    if user_id is None:
        return None

    try:
        return get_user_by_id(int(user_id))
    except Exception:
        return None
