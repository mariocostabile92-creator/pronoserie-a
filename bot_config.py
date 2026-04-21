"""
bot_config.py
Configurazione del Bot Telegram per pronostici Serie A.
"""

import os

# ──────────────────────────────────────────────
# CONFIGURAZIONE BOT TELEGRAM
# Ottieni il token da @BotFather su Telegram
# ──────────────────────────────────────────────
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')

# ──────────────────────────────────────────────
# CONFIGURAZIONE STRIPE (per pagamenti Pro)
# Registrati su https://dashboard.stripe.com
# ──────────────────────────────────────────────
STRIPE_SECRET_KEY = "sk_test_IL_TUO_KEY_QUI"
STRIPE_PRICE_ID_PRO = "price_IL_TUO_PRICE_ID"  # Abbonamento Pro 9.99/mese
STRIPE_WEBHOOK_SECRET = "whsec_IL_TUO_WEBHOOK"

# ──────────────────────────────────────────────
# PIANI
# ──────────────────────────────────────────────
PIANO_FREE = "free"
PIANO_PRO = "pro"

# Limiti piano Free
FREE_MAX_PARTITE_GIORNO = 2
FREE_MOSTRA_OVER_UNDER = False
FREE_MOSTRA_GOAL = False
FREE_MOSTRA_ESATTO = False
FREE_MOSTRA_FORMAZIONI = False

# Piano Pro: tutto sbloccato
PRO_PREZZO = "9.99"
PRO_VALUTA = "EUR"

# ──────────────────────────────────────────────
# ORARI INVIO AUTOMATICO
# ──────────────────────────────────────────────
# Orario invio pronostici pre-partita (ore prima del match)
ORE_PRIMA_INVIO = 3

# Orario invio giornaliero pronostici giornata
ORARIO_INVIO_GIORNALIERO = "09:00"

# ──────────────────────────────────────────────
# DATABASE
# ──────────────────────────────────────────────
BOT_DB_PATH = "bot_utenti.db"
