"""
routes/referral.py - Gestione sistema referral
Endpoint: /api/referral/my-code, /api/referral/apply
"""
import json
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from api_auth import get_optional_user

router = APIRouter(prefix="/api/referral", tags=["referral"])
limiter = Limiter(key_func=get_remote_address)


def _generate_referral_code(user_id: int, email: str) -> str:
    """Genera un codice referral univoco basato su ID utente e email."""
    import hashlib
    raw = f"{user_id}-{email}-matchiq"
    return hashlib.md5(raw.encode()).hexdigest()[:8].upper()


@router.get("/my-code")
@limiter.limit("20/minute")
async def get_referral_code(request: Request, user: Optional[dict] = Depends(get_optional_user)):
    """Restituisce il codice referral dell'utente corrente."""
    if not user:
        raise HTTPException(401, "Devi essere loggato")

    from database import _get_conn
    conn = _get_conn()
    cur = conn.cursor()

    cur.execute("SELECT referral_code FROM users WHERE id = %s", (user["id"],))
    row = cur.fetchone()
    code = row[0] if row and row[0] else None

    # Genera codice se non esiste ancora
    if not code:
        code = _generate_referral_code(user["id"], user["email"])
        cur.execute("UPDATE users SET referral_code = %s WHERE id = %s", (code, user["id"]))
        conn.commit()

    # Conta referral completati e in attesa
    cur.execute("SELECT COUNT(*) FROM referrals WHERE referrer_id = %s AND status = 'completed'", (user["id"],))
    completed = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM referrals WHERE referrer_id = %s AND status = 'pending'", (user["id"],))
    pending = cur.fetchone()[0]

    cur.close()
    conn.close()

    return {
        "code": code,
        "link": f"https://matchiq.it.com/app#registrati?ref={code}",
        "completati": completed,
        "in_attesa": pending,
    }


@router.post("/apply")
@limiter.limit("10/minute")
async def apply_referral(data: dict, request: Request):
    """Applica un codice referral quando un nuovo utente si registra."""
    from database import _get_conn
    import os

    code = data.get("code", "").strip().upper()
    new_user_email = data.get("email", "").strip().lower()

    if not code or not new_user_email:
        return {"status": "skip"}

    conn = _get_conn()
    cur = conn.cursor()

    # Cerca il proprietario del codice
    cur.execute("SELECT id, email FROM users WHERE referral_code = %s", (code,))
    referrer = cur.fetchone()

    if not referrer:
        cur.close()
        conn.close()
        return {"status": "code_not_found"}

    referrer_id, referrer_email = referrer

    # Impedisci auto-referral
    if referrer_email == new_user_email:
        cur.close()
        conn.close()
        return {"status": "self_referral"}

    # Salva il referral e aggiorna il piano dell'invitante a Pro
    cur.execute("""
        INSERT INTO referrals (referrer_id, referrer_email, referral_code, referred_email, status, created_at)
        VALUES (%s, %s, %s, %s, 'completed', %s)
    """, (referrer_id, referrer_email, code, new_user_email, datetime.now(timezone.utc).isoformat()))

    cur.execute("UPDATE users SET piano = 'pro' WHERE id = %s", (referrer_id,))
    conn.commit()
    cur.close()
    conn.close()

    # Notifica l'invitante via email (in background, non blocca la risposta)
    RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
    try:
        import urllib.request as ur
        body = json.dumps({
            "from": "MatchIQ <noreply@matchiq.it.com>",
            "to": [referrer_email],
            "subject": "Hai guadagnato 1 mese Pro gratis!",
            "html": f"""
            <div style="font-family:Arial;background:#0a0f1a;color:#e8eaf6;padding:24px;border-radius:12px">
                <h2 style="color:#2ecc71">Ottimo! Il tuo amico si e' registrato!</h2>
                <p><strong>{new_user_email}</strong> si e' iscritto con il tuo codice referral.</p>
                <p>Hai guadagnato <strong>1 mese Pro gratis</strong>!</p>
                <hr style="border:1px solid #1f3460">
                <p style="color:#8892b0;font-size:.85rem">MatchIQ - Pronostici Calcistici con IA</p>
            </div>
            """
        }).encode()
        req = ur.Request("https://api.resend.com/emails", data=body, headers={
            "Authorization": f"Bearer {RESEND_API_KEY}",
            "Content-Type": "application/json",
            "User-Agent": "MatchIQ/1.0"
        })
        ur.urlopen(req, timeout=10)
    except Exception as e:
        print(f"⚠️ Notifica referral non inviata: {e}")

    return {"status": "ok", "reward": "1 mese Pro gratis"}
