import os
import logging
import bcrypt
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from database import get_user_by_id

logger = logging.getLogger(__name__)

# Configurazione JWT
SECRET_KEY = os.environ.get("JWT_SECRET")
if not SECRET_KEY:
    raise RuntimeError("JWT_SECRET non configurata. Imposta la variabile d'ambiente JWT_SECRET prima di avviare il server.")
ALGORITHM = "HS256"
TOKEN_EXPIRE_DAYS = 7

_bearer_scheme = HTTPBearer(auto_error=False)

# --- FUNZIONI PASSWORD (USANDO BCRYPT DIRETTO) ---

_MAX_PASSWORD_BYTES = 72

def hash_password(password: str) -> str:
    if not password:
        raise ValueError("Password vuota")
    pwd_bytes = password.encode("utf-8")
    if len(pwd_bytes) > _MAX_PASSWORD_BYTES:
        raise ValueError(
            f"Password troppo lunga: {len(pwd_bytes)} byte (massimo {_MAX_PASSWORD_BYTES})."
        )
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    return hashed.decode("utf-8")

def verify_password(plain: str, hashed: str) -> bool:
    if not plain or not hashed:
        return False
    pwd_bytes = plain.encode("utf-8")
    if len(pwd_bytes) > _MAX_PASSWORD_BYTES:
        logger.warning("verify_password: password troppo lunga (%d byte), rifiutata.", len(pwd_bytes))
        return False
    try:
        hashed_bytes = hashed.encode("utf-8")
        return bcrypt.checkpw(pwd_bytes, hashed_bytes)
    except (ValueError, TypeError) as e:
        logger.warning("verify_password: errore bcrypt: %s", e)
        return False
    except Exception as e:
        logger.error("verify_password: errore inatteso: %s", e)
        return False

# --- FUNZIONI TOKEN JWT ---

def create_token(data: dict) -> str:
    """Crea un JWT firmato. `data` deve contenere la chiave 'sub' con l'ID utente (str)."""
    if "sub" not in data:
        raise ValueError("create_token: 'sub' claim obbligatorio mancante in data.")
    payload = data.copy()
    now = datetime.now(timezone.utc)
    expire = now + timedelta(days=TOKEN_EXPIRE_DAYS)
    payload.update({"exp": expire, "iat": now})
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as e:
        logger.warning("decode_token: JWTError: %s", e)
        raise ValueError("Token non valido")

# --- DIPENDENZE ---

def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme)) -> dict:
    if not credentials:
        raise HTTPException(status_code=401, detail="Token mancante")
    try:
        payload = decode_token(credentials.credentials)
    except ValueError:
        raise HTTPException(status_code=401, detail="Token non valido")
    except Exception as e:
        logger.error("get_current_user: errore decodifica token inatteso: %s", e)
        raise HTTPException(status_code=401, detail="Token non valido")
    sub = payload.get("sub")
    if sub is None:
        logger.warning("get_current_user: claim 'sub' assente nel token.")
        raise HTTPException(status_code=401, detail="Token non valido")
    try:
        user = get_user_by_id(int(sub))
    except (ValueError, TypeError) as e:
        logger.warning("get_current_user: sub non convertibile in int: %s", e)
        raise HTTPException(status_code=401, detail="Token non valido")
    if not user:
        logger.warning("get_current_user: utente con id=%s non trovato nel DB.", sub)
        raise HTTPException(status_code=401, detail="Utente non trovato")
    return user

def get_optional_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme)) -> Optional[dict]:
    if not credentials:
        return None
    try:
        payload = decode_token(credentials.credentials)
    except ValueError:
        logger.warning("get_optional_user: token non valido, ritorna None.")
        return None
    except Exception as e:
        logger.error("get_optional_user: errore decodifica token inatteso: %s", e)
        return None
    sub = payload.get("sub")
    if sub is None:
        logger.warning("get_optional_user: claim 'sub' assente nel token.")
        return None
    try:
        return get_user_by_id(int(sub))
    except (ValueError, TypeError) as e:
        logger.warning("get_optional_user: sub non convertibile in int: %s", e)
        return None
    except Exception as e:
        logger.error("get_optional_user: errore inatteso lookup utente: %s", e)
        return None
