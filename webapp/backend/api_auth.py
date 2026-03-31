import os
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from database import get_user_by_id

# Configurazione JWT
SECRET_KEY = os.environ.get("JWT_SECRET", "chiave-segreta-32-caratteri-base")[:32]
ALGORITHM = "HS256"
TOKEN_EXPIRE_DAYS = 7

# CryptContext semplificato (senza parametri che causano crash)
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
_bearer_scheme = HTTPBearer(auto_error=False)

def hash_password(password: str) -> str:
    if not password:
        raise ValueError("Password vuota")
    # TRONCAMENTO MANUALE RIGIDO: bcrypt accetta max 72 byte.
    # Tagliamo a 71 per sicurezza totale.
    pwd_safe = password.encode('utf-8')[:71].decode('utf-8', 'ignore')
    return _pwd_context.hash(pwd_safe)

def verify_password(plain: str, hashed: str) -> bool:
    if not plain or not hashed:
        return False
    try:
        # Applichiamo lo stesso troncamento
        pwd_safe = plain.encode('utf-8')[:71].decode('utf-8', 'ignore')
        return _pwd_context.verify(pwd_safe, hashed)
    except Exception:
        return False

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