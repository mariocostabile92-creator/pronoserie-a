"""
api_payments.py
Integrazione Stripe per la webapp pronostici Serie A.
Gestisce la creazione delle sessioni di checkout e i webhook di pagamento.
"""

import os
from typing import Optional

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request, status

from api_auth import get_current_user
from database import update_plan, update_stripe_customer, get_user_by_id

# ── Configurazione Stripe (da variabili d'ambiente) ─────────────────────────
STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_PRICE_ID = os.environ.get("STRIPE_PRICE_ID", "price_1TH2aTCHxpJyCrvZwsA44539")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")

# URL di redirect dopo il pagamento
BASE_URL = os.environ.get("FRONTEND_URL", "https://web-production-ff46b.up.railway.app")
SUCCESS_URL = BASE_URL + "/app?paid=1#home"
CANCEL_URL = BASE_URL + "/app#pricing"

# Configura la chiave Stripe
if STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY


# ── Router FastAPI ──────────────────────────────────────────────────────────
router = APIRouter(prefix="/api/payments", tags=["Pagamenti"])


# ── Funzioni di business logic ──────────────────────────────────────────────

def create_checkout_session(user_id: int, email: str) -> str:
    """
    Crea una sessione di checkout Stripe per l'upgrade al piano Pro.
    Ritorna l'URL della pagina di pagamento Stripe.
    Lancia HTTPException in caso di errore Stripe.
    """
    if not STRIPE_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Pagamenti non configurati. Contatta il supporto."
        )

    if not STRIPE_PRICE_ID:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Piano Pro non configurato. Contatta il supporto."
        )

    try:
        # Recupera o crea il customer Stripe
        user = get_user_by_id(user_id)
        stripe_customer_id = user.get("stripe_customer_id") if user else None

        if not stripe_customer_id:
            # Crea nuovo customer Stripe
            customer = stripe.Customer.create(
                email=email,
                metadata={"user_id": str(user_id)}
            )
            stripe_customer_id = customer.id
            update_stripe_customer(user_id, stripe_customer_id)

        # Crea la sessione di checkout
        session = stripe.checkout.Session.create(
            customer=stripe_customer_id,
            payment_method_types=["card"],
            line_items=[
                {
                    "price": STRIPE_PRICE_ID,
                    "quantity": 1,
                }
            ],
            mode="subscription",           # Abbonamento ricorrente
            success_url=SUCCESS_URL + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=CANCEL_URL,
            metadata={"user_id": str(user_id)},
        )

        return session.url

    except stripe.error.StripeError as e:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Errore pagamento: {str(e.user_message or e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Errore interno durante la creazione del pagamento."
        )


def handle_webhook(payload: bytes, sig_header: str) -> dict:
    """
    Verifica e gestisce i webhook Stripe.
    In caso di pagamento completato, aggiorna il piano utente a 'pro'.
    Ritorna dict con l'esito dell'operazione.
    Lancia HTTPException se la firma non è valida.
    """
    if not STRIPE_WEBHOOK_SECRET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Webhook Stripe non configurato."
        )

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except stripe.error.SignatureVerificationError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Firma webhook Stripe non valida."
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Errore lettura webhook: {e}"
        )

    # Gestione eventi rilevanti
    event_type = event.get("type", "")

    if event_type in ("checkout.session.completed", "invoice.paid"):
        # Pagamento completato: aggiorna il piano a 'pro'
        _processa_pagamento(event["data"]["object"])

    elif event_type in ("customer.subscription.deleted", "invoice.payment_failed"):
        # Abbonamento cancellato o pagamento fallito: torna a 'free'
        _revoca_piano(event["data"]["object"])

    return {"status": "ok", "event": event_type}


def _processa_pagamento(obj: dict) -> None:
    """Estrae lo user_id dai metadata e aggiorna il piano a 'pro'."""
    metadata = obj.get("metadata", {})
    user_id_str = metadata.get("user_id")

    if not user_id_str:
        # Prova a recuperarlo dal customer
        customer_id = obj.get("customer")
        if customer_id:
            try:
                customer = stripe.Customer.retrieve(customer_id)
                user_id_str = customer.get("metadata", {}).get("user_id")
            except Exception:
                pass

    if user_id_str:
        try:
            update_plan(int(user_id_str), "pro")
        except Exception:
            pass


def _revoca_piano(obj: dict) -> None:
    """Estrae lo user_id e ripristina il piano a 'free'."""
    metadata = obj.get("metadata", {})
    user_id_str = metadata.get("user_id")

    if user_id_str:
        try:
            update_plan(int(user_id_str), "free")
        except Exception:
            pass


# ── Endpoint API ────────────────────────────────────────────────────────────

@router.post("/checkout")
async def crea_checkout(utente: dict = Depends(get_current_user)):
    """Crea checkout Stripe (richiede auth)."""
    if utente.get("piano") == "pro":
        raise HTTPException(status_code=400, detail="Sei gia' abbonato Pro.")
    url = create_checkout_session(utente["id"], utente["email"])
    return {"checkout_url": url}


@router.get("/checkout-direct")
async def checkout_diretto(email: str = ""):
    """Crea checkout Stripe. Se email fornita, la pre-compila."""
    try:
        params = {
            "payment_method_types": ["card"],
            "line_items": [{"price": STRIPE_PRICE_ID, "quantity": 1}],
            "mode": "subscription",
            "success_url": SUCCESS_URL,
            "cancel_url": CANCEL_URL,
        }
        if email:
            params["customer_email"] = email
        session = stripe.checkout.Session.create(**params)
        return {"checkout_url": session.url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore Stripe: {e}")


@router.post("/activate-pro")
async def activate_pro(data: dict):
    """Attiva Pro per un utente (tramite email). Chiamato dopo pagamento."""
    email = data.get("email", "").lower().strip()
    if not email:
        raise HTTPException(400, "Email richiesta")
    from database import get_user_by_email, update_plan
    user = get_user_by_email(email)
    if user:
        update_plan(user["id"], "pro")
        return {"status": "ok", "piano": "pro"}
    return {"status": "utente_non_trovato"}


@router.get("/check-plan")
async def check_plan(user: dict = Depends(get_current_user)):
    """Ritorna il piano attuale dell'utente."""
    return {"piano": user.get("piano", "free"), "email": user.get("email", "")}


@router.post("/webhook")
async def stripe_webhook(request: Request):
    """
    Endpoint per i webhook Stripe.
    Pubblico (nessuna autenticazione), ma verifica la firma Stripe.
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    if not sig_header:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Header stripe-signature mancante."
        )

    result = handle_webhook(payload, sig_header)
    return result
