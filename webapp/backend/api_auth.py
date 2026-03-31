import os
import bcrypt
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from database import get_user_by_id

# Configurazione JWT
SECRET_KEY = os.environ.get("JWT_SECRET", "chiave-segreta-32-caratteri-base")[:32]
ALGORITHM = "HS256"
TOKEN_EXPIRE_DAYS = 7

_bearer_scheme = HTTPBearer(auto_error=False)

# --- FUNZIONI PASSWORD (USANDO BCRYPT DIRETTO) ---

def hash_password(password: str) -> str:
    if not password:
        raise ValueError("Password vuota")
    # Troncamento manuale di sicurezza (max 72 byte)
    pwd_bytes = password.encode('utf-8')[:71]
    # Generiamo il sale e l'hash
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    return hashed.decode('utf-8')

def verify_password(plain: str, hashed: str) -> bool:
    if not plain or not hashed:
        return False
    try:
        pwd_bytes = plain.encode('utf-8')[:71]
        hashed_bytes = hashed.encode('utf-8')
        return bcrypt.checkpw(pwd_bytes, hashed_bytes)
    except Exception as e:
        print(f"Errore verifica: {e}")
        return False

# --- FUNZIONI TOKEN JWT ---

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

# --- DIPENDENZE ---

def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme)) -> dict:
    if not credentials:
        raise HTTPException(status_code=401, detail="Token mancante")
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