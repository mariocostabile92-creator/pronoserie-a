"""
api_payments.py
Integrazione Stripe per la webapp pronostici Serie A.
Gestisce la creazione delle sessioni di checkout e i webhook di pagamento.
"""

import logging
import os
from typing import Optional

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request, status

from api_auth import get_current_user
from database import get_user_by_email, get_user_by_id, update_plan, update_stripe_customer

logger = logging.getLogger(__name__)

# ── Configurazione Stripe (da variabili d'ambiente) ─────────────────────────
# Fix (2): RuntimeError se le variabili critiche mancano (come JWT_SECRET)
_STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
_STRIPE_PRICE_ID = os.environ.get("STRIPE_PRICE_ID", "")
_STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
_BASE_URL = os.environ.get("FRONTEND_URL", "")

if not _STRIPE_SECRET_KEY:
    raise RuntimeError("STRIPE_SECRET_KEY mancante nelle variabili d'ambiente.")
if not _STRIPE_PRICE_ID:
    raise RuntimeError("STRIPE_PRICE_ID mancante nelle variabili d'ambiente.")
if not _STRIPE_WEBHOOK_SECRET:
    raise RuntimeError("STRIPE_WEBHOOK_SECRET mancante nelle variabili d'ambiente.")
if not _BASE_URL:
    raise RuntimeError("FRONTEND_URL mancante nelle variabili d'ambiente.")

STRIPE_SECRET_KEY = _STRIPE_SECRET_KEY
STRIPE_PRICE_ID = _STRIPE_PRICE_ID
STRIPE_WEBHOOK_SECRET = _STRIPE_WEBHOOK_SECRET
BASE_URL = _BASE_URL

# URL di redirect dopo il pagamento
SUCCESS_URL = BASE_URL + "/app?paid=1#home"
CANCEL_URL = BASE_URL + "/app#pricing"

# Configura la chiave Stripe
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
        logger.error("Errore imprevisto in create_checkout_session user_id=%s", user_id, exc_info=True)
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

    NOTA IDEMPOTENZA: Stripe può recapitare lo stesso evento più di una volta.
    Le funzioni _processa_pagamento e _revoca_piano chiamano update_plan che è
    idempotente (SET piano = ?), quindi rielaborare lo stesso evento non causa
    danni. Se in futuro si aggiunge logica non idempotente (es. invio email,
    crediti), occorre deduplicare tramite event.id persistito nel DB.
    """
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except stripe.error.SignatureVerificationError:
        logger.warning("Firma webhook Stripe non valida - possibile replay attack o config errata.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Firma webhook Stripe non valida."
        )
    except Exception as e:
        logger.error("Errore costruzione evento webhook Stripe", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Errore lettura webhook: {e}"
        )

    # Gestione eventi rilevanti
    event_type = event.get("type", "")
    event_id = event.get("id", "?")
    logger.info("Webhook Stripe ricevuto: event_type=%s event_id=%s", event_type, event_id)

    if event_type == "checkout.session.completed":
        logger.info("Checkout completato (event_id=%s): aggiorno piano a 'pro'.", event_id)
        _processa_pagamento(event["data"]["object"])

    elif event_type == "invoice.paid":
        logger.info("Fattura pagata (event_id=%s): aggiorno piano a 'pro'.", event_id)
        _processa_pagamento(event["data"]["object"])

    elif event_type == "customer.subscription.deleted":
        logger.info("Abbonamento cancellato (event_id=%s): revoco piano a 'free'.", event_id)
        _revoca_piano(event["data"]["object"])

    elif event_type == "invoice.payment_failed":
        logger.warning("Pagamento fallito (event_id=%s): revoco piano a 'free'.", event_id)
        _revoca_piano(event["data"]["object"])

    else:
        logger.debug("Evento Stripe ignorato: event_type=%s event_id=%s", event_type, event_id)

    return {"status": "ok", "event": event_type}


def _processa_pagamento(obj: dict) -> None:
    """Estrae lo user_id dai metadata e aggiorna il piano a 'pro'."""
    metadata = obj.get("metadata", {})
    user_id_str = metadata.get("user_id")

    if not user_id_str:
        # Prova a recuperarlo dal customer Stripe
        customer_id = obj.get("customer")
        if customer_id:
            try:
                customer = stripe.Customer.retrieve(customer_id)
                user_id_str = customer.get("metadata", {}).get("user_id")
                if not user_id_str:
                    # Fallback: cerca utente per email del customer
                    customer_email = customer.get("email", "")
                    if customer_email:
                        user = get_user_by_email(customer_email)
                        if user:
                            user_id_str = str(user["id"])
                            logger.info("_processa_pagamento: user trovato via email customer (%s)", customer_email)
            except Exception:
                logger.warning("_processa_pagamento: impossibile recuperare customer_id=%s", customer_id, exc_info=True)

    if user_id_str:
        try:
            update_plan(int(user_id_str), "pro")
            logger.info("_processa_pagamento: piano aggiornato a 'pro' per user_id=%s", user_id_str)
        except Exception:
            logger.error("_processa_pagamento: errore update_plan user_id=%s", user_id_str, exc_info=True)
    else:
        logger.warning("_processa_pagamento: user_id non trovato nell'evento Stripe, obj=%s", obj.get("id", "?"))


def _revoca_piano(obj: dict) -> None:
    """Estrae lo user_id e ripristina il piano a 'free'."""
    metadata = obj.get("metadata", {})
    user_id_str = metadata.get("user_id")

    if not user_id_str:
        # Fix (4): fallback customer lookup come in _processa_pagamento
        customer_id = obj.get("customer")
        if customer_id:
            try:
                customer = stripe.Customer.retrieve(customer_id)
                user_id_str = customer.get("metadata", {}).get("user_id")
                if not user_id_str:
                    customer_email = customer.get("email", "")
                    if customer_email:
                        user = get_user_by_email(customer_email)
                        if user:
                            user_id_str = str(user["id"])
                            logger.info("_revoca_piano: user trovato via email customer (%s)", customer_email)
            except Exception:
                logger.warning("_revoca_piano: impossibile recuperare customer_id=%s", customer_id, exc_info=True)

    if user_id_str:
        try:
            update_plan(int(user_id_str), "free")
            logger.info("_revoca_piano: piano ripristinato a 'free' per user_id=%s", user_id_str)
        except Exception:
            logger.error("_revoca_piano: errore update_plan user_id=%s", user_id_str, exc_info=True)
    else:
        logger.warning("_revoca_piano: user_id non trovato nell'evento Stripe, obj=%s", obj.get("id", "?"))


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
    except stripe.error.StripeError as e:
        logger.error("checkout_diretto: errore Stripe", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Errore Stripe: {e}")
    except Exception:
        logger.error("checkout_diretto: errore imprevisto", exc_info=True)
        raise HTTPException(status_code=500, detail="Errore interno.")


# Fix (1): endpoint /activate-pro RIMOSSO.
# Chiunque poteva attivare Pro su qualsiasi email senza autenticazione.
# L'attivazione avviene esclusivamente tramite webhook Stripe (/api/payments/webhook)
# che verifica la firma crittografica di Stripe.


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
        logger.warning("stripe_webhook: header stripe-signature mancante - richiesta rifiutata.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Header stripe-signature mancante."
        )

    result = handle_webhook(payload, sig_header)
    return result
