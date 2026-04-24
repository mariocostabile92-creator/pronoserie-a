"""
routes/auth.py - Gestione autenticazione utenti
Endpoint: registrazione, login, reset/change password
"""
import logging
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
from datetime import datetime, timezone
import threading

router = APIRouter(prefix="/api/auth", tags=["auth"])
logger = logging.getLogger(__name__)

# Import dipendenze dal modulo principale
import sys
import os
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
sys.path.insert(0, _ROOT)

from database import get_user_by_email, create_user, _get_conn
from api_auth import get_optional_user, hash_password, verify_password, create_token

# Configurazione email (Resend)
RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
ADMIN_EMAIL = "mario.costabile92@outlook.it"
ADMIN_TELEGRAM_USERNAME = "Soanator"

def send_welcome_email(to_email):
    """Invia email di benvenuto dopo la registrazione."""
    try:
        import urllib.request as ur
        import json as js
        body = js.dumps({
            "from": "MatchIQ <noreply@matchiq.it.com>",
            "to": [to_email],
            "subject": "Benvenuto su PronoSerie A!",
            "html": f"""
            <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;background:#0a0f1a;color:#e8eaf6;padding:32px;border-radius:12px">
                <h1 style="color:#2ecc71;text-align:center">Benvenuto su PronoSerie A!</h1>
                <p style="text-align:center;color:#8892b0">Il tuo account e' stato creato con successo.</p>
                <div style="background:#162447;padding:20px;border-radius:8px;margin:20px 0;text-align:center">
                    <p style="margin:0"><strong>Email:</strong> {to_email}</p>
                    <p style="margin:8px 0 0"><strong>Piano:</strong> Free</p>
                </div>
                <h3 style="color:#3498db">Cosa puoi fare:</h3>
                <ul style="color:#8892b0;line-height:2">
                    <li>2 pronostici gratuiti al giorno</li>
                    <li>Pronostici 1X2 con probabilita' e quote</li>
                    <li>Calendario Serie A giornate 31-38</li>
                </ul>
                <div style="text-align:center;margin:24px 0">
                    <a href="https://web-production-ff46b.up.railway.app/app#pronostici" style="background:#2ecc71;color:#000;padding:14px 32px;border-radius:20px;text-decoration:none;font-weight:700;font-size:1.1rem">Calcola il tuo primo pronostico</a>
                </div>
                <p style="text-align:center;color:#8892b0;font-size:.85rem">Passa a Pro per pronostici illimitati, classifica, marcatori, rose e formazioni live!</p>
                <hr style="border:1px solid #1f3460;margin:20px 0">
                <p style="text-align:center;color:#8892b0;font-size:.8rem">PronoSerie A — Pronostici Serie A con Intelligenza Artificiale</p>
            </div>
            """
        }).encode()
        req = ur.Request("https://api.resend.com/emails", data=body, headers={
            "Authorization": f"Bearer {RESEND_API_KEY}",
            "Content-Type": "application/json",
            "User-Agent": "MatchIQ/1.0"
        })
        ur.urlopen(req, timeout=10)
        logger.info("send_welcome_email: email inviata a %s", to_email)
    except Exception as e:
        logger.warning("send_welcome_email: errore invio email a %s: %s", to_email, e)

def _notify_admin_new_user(email, piano):
    """Notifica l'admin quando un nuovo utente si registra."""
    import json
    # 1. Email
    try:
        import urllib.request as ur
        body = json.dumps({
            "from": "MatchIQ <noreply@matchiq.it.com>",
            "to": [ADMIN_EMAIL],
            "subject": f"Nuovo iscritto MatchIQ: {email}",
            "html": f"""
            <div style="font-family:Arial;background:#0a0f1a;color:#e8eaf6;padding:24px;border-radius:12px">
                <h2 style="color:#2ecc71">Nuovo iscritto!</h2>
                <p><strong>Email:</strong> {email}</p>
                <p><strong>Piano:</strong> {piano}</p>
                <p><strong>Data:</strong> {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M UTC')}</p>
                <hr style="border:1px solid #1f3460">
                <p style="color:#8892b0;font-size:.85rem">MatchIQ - Notifica automatica</p>
            </div>
            """
        }).encode()
        req = ur.Request("https://api.resend.com/emails", data=body, headers={
            "Authorization": f"Bearer {RESEND_API_KEY}",
            "Content-Type": "application/json",
            "User-Agent": "MatchIQ/1.0"
        })
        ur.urlopen(req, timeout=10)
        logger.info("_notify_admin_new_user: notifica email inviata per nuovo utente %s", email)
    except Exception as e:
        logger.warning("_notify_admin_new_user: errore notifica email admin: %s", e)

@router.post("/register")
async def register(data: dict):
    """Registrazione nuovo utente."""
    email = data["email"].lower().strip()

    if get_user_by_email(email):
        raise HTTPException(409, "Email gia' registrata")

    user = create_user(email, hash_password(data["password"]))
    token = create_token({"sub": str(user["id"])})

    # Invia email di benvenuto (in background, non blocca la risposta)
    threading.Thread(target=send_welcome_email, args=(email,), daemon=True).start()

    # Notifica admin (in background)
    try:
        threading.Thread(target=_notify_admin_new_user, args=(email, user.get("piano", "free")), daemon=True).start()
    except Exception as e:
        logger.warning("register: errore avvio notifica admin per %s: %s", email, e)

    return {"access_token": token, "piano": user["piano"]}

@router.post("/login")
async def login(data: dict):
    """Login utente."""
    email = data["email"].lower().strip()
    user = get_user_by_email(email)

    if not user:
        logger.warning("login: tentativo fallito - utente non trovato per email '%s'", email)
        raise HTTPException(401, "Credenziali errate")

    if not verify_password(data["password"].strip(), user["password_hash"]):
        logger.warning("login: tentativo fallito - password errata per email '%s'", email)
        raise HTTPException(401, "Credenziali errate")

    token = create_token({"sub": str(user["id"])})
    return {"access_token": token, "piano": user["piano"]}

@router.post("/reset-password")
async def reset_password(data: dict):
    """Reset password (invia nuova password via email)."""
    import random, string, json
    email = data.get("email", "").lower().strip()
    if not email:
        raise HTTPException(400, "Email richiesta")
    user = get_user_by_email(email)
    if not user:
        raise HTTPException(404, "Email non trovata")
    # Genera nuova password casuale
    new_pass = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
    # Aggiorna nel DB
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE users SET password_hash = %s WHERE id = %s", (hash_password(new_pass), user["id"]))
    conn.commit()
    cur.close()
    conn.close()
    # Invia via email
    try:
        import urllib.request as ur
        body = json.dumps({
            "from": "MatchIQ <noreply@matchiq.it.com>",
            "to": [email],
            "subject": "MatchIQ - La tua nuova password",
            "html": f'<div style="font-family:Arial;background:#0a0f1a;color:#e8eaf6;padding:24px;border-radius:12px"><h2 style="color:#2ecc71">Recupero Password</h2><p>La tua nuova password provvisoria e\':</p><div style="background:#162447;padding:16px;border-radius:8px;text-align:center;margin:16px 0"><code style="font-size:1.5rem;font-weight:800;color:#2ecc71;font-family:Courier New,monospace;user-select:all">{new_pass}</code></div><p style="font-size:.85rem;color:#8892b0">Copia la password qui sopra (toccala per selezionarla) e usala per accedere.</p><p>Poi cambiala dalle impostazioni del tuo account.</p><hr style="border:1px solid #1f3460"><p style="color:#8892b0;font-size:.85rem">MatchIQ - Pronostici Calcistici con IA</p></div>'
        }).encode()
        req = ur.Request("https://api.resend.com/emails", data=body, headers={
            "Authorization": f"Bearer {RESEND_API_KEY}",
            "Content-Type": "application/json",
            "User-Agent": "MatchIQ/1.0"
        })
        ur.urlopen(req, timeout=10)
        logger.info("reset_password: email con nuova password inviata a %s", email)
    except Exception as e:
        logger.error("reset_password: errore invio email a %s: %s", email, e)
    return {"sent": True}

@router.post("/change-password")
async def change_password(data: dict, user: Optional[dict] = Depends(get_optional_user)):
    """Cambio password per utente loggato."""
    if not user:
        raise HTTPException(401, "Devi essere loggato")
    old_pass = data.get("old_password", "")
    new_pass = data.get("new_password", "")
    if not old_pass or not new_pass:
        raise HTTPException(400, "Compila tutti i campi")
    if len(new_pass) < 6:
        raise HTTPException(400, "La nuova password deve avere almeno 6 caratteri")
    db_user = get_user_by_email(user.get("email", ""))
    if not db_user or not verify_password(old_pass, db_user["password_hash"]):
        raise HTTPException(401, "Password attuale errata")
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE users SET password_hash = %s WHERE id = %s", (hash_password(new_pass), db_user["id"]))
    conn.commit()
    cur.close()
    conn.close()
    return {"status": "ok"}
