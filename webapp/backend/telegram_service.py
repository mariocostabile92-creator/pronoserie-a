"""
telegram_service.py - Servizi Telegram per MatchIQ
Gestisce: invio messaggi, notifiche gol/espulsioni per utenti Pro,
          bot Telegram (polling), notifiche admin nuovi iscritti.
"""

import os
import sys
import threading
import logging
import urllib.request
from datetime import datetime, timezone

_logger = logging.getLogger(__name__)

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
_BOT_DB_PATH = os.path.join(_ROOT, "bot_utenti.db")
ADMIN_EMAIL = "mario.costabile92@outlook.it"
ADMIN_TELEGRAM_USERNAME = "Soanator"

# Set di gol gia' notificati: "fixture_id_minuto_giocatore"
_NOTIFIED_GOALS = set()


def _get_pro_chat_ids():
    """Recupera tutti gli chat_id degli utenti Pro dal database del bot."""
    import sqlite3
    try:
        if not os.path.exists(_BOT_DB_PATH):
            return []
        conn = sqlite3.connect(_BOT_DB_PATH)
        rows = conn.execute("SELECT chat_id FROM utenti WHERE piano = 'pro'").fetchall()
        conn.close()
        return [r[0] for r in rows]
    except Exception:
        return []


def _send_telegram_message(chat_id, text):
    """Invia un messaggio Telegram a un chat_id."""
    try:
        import urllib.parse
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = urllib.parse.urlencode({
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_notification": False,
        }).encode()
        req = urllib.request.Request(url, data=data)
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print(f"Errore invio Telegram a {chat_id}: {e}")


def check_and_notify_goals(LIVE_RESULTS_CACHE, LIVE_IN_CORSO):
    """Controlla se ci sono nuovi gol e invia notifiche agli utenti Pro."""
    global _NOTIFIED_GOALS
    if not LIVE_RESULTS_CACHE or not LIVE_IN_CORSO:
        return

    pro_ids = _get_pro_chat_ids()
    if not pro_ids:
        return

    for p in LIVE_RESULTS_CACHE:
        if not p.get("live"):
            continue

        fixture_id = p.get("fixture_id", 0)
        home = p["home"]
        away = p["away"]
        marcatori_home = p.get("marcatori_home", [])
        marcatori_away = p.get("marcatori_away", [])
        rossi_home = p.get("rossi_home", [])
        rossi_away = p.get("rossi_away", [])
        gol_h = p["gol_h"]
        gol_a = p["gol_a"]
        minuto = p.get("minuto", "")

        for m in marcatori_home:
            goal_key = f"{fixture_id}_{m}"
            if goal_key not in _NOTIFIED_GOALS:
                _NOTIFIED_GOALS.add(goal_key)
                msg = (
                    f"&#9917; <b>GOOOL!</b>\n\n"
                    f"<b>{home} {gol_h} - {gol_a} {away}</b>\n"
                    f"&#9917; {m} ({home})\n"
                    f"&#9201; {minuto}'"
                )
                for cid in pro_ids:
                    threading.Thread(target=_send_telegram_message, args=(cid, msg), daemon=True).start()
                print(f"&#9917; NOTIFICA GOL: {home} - {m}")

        for m in marcatori_away:
            goal_key = f"{fixture_id}_{m}"
            if goal_key not in _NOTIFIED_GOALS:
                _NOTIFIED_GOALS.add(goal_key)
                msg = (
                    f"&#9917; <b>GOOOL!</b>\n\n"
                    f"<b>{home} {gol_h} - {gol_a} {away}</b>\n"
                    f"&#9917; {m} ({away})\n"
                    f"&#9201; {minuto}'"
                )
                for cid in pro_ids:
                    threading.Thread(target=_send_telegram_message, args=(cid, msg), daemon=True).start()
                print(f"&#9917; NOTIFICA GOL: {away} - {m}")

        for r in rossi_home:
            red_key = f"{fixture_id}_red_{r}"
            if red_key not in _NOTIFIED_GOALS:
                _NOTIFIED_GOALS.add(red_key)
                msg = (
                    f"&#128308; <b>ESPULSIONE!</b>\n\n"
                    f"<b>{home} {gol_h} - {gol_a} {away}</b>\n"
                    f"&#128308; {r} ({home})\n"
                    f"&#9201; {minuto}'"
                )
                for cid in pro_ids:
                    threading.Thread(target=_send_telegram_message, args=(cid, msg), daemon=True).start()

        for r in rossi_away:
            red_key = f"{fixture_id}_red_{r}"
            if red_key not in _NOTIFIED_GOALS:
                _NOTIFIED_GOALS.add(red_key)
                msg = (
                    f"&#128308; <b>ESPULSIONE!</b>\n\n"
                    f"<b>{home} {gol_h} - {gol_a} {away}</b>\n"
                    f"&#128308; {r} ({away})\n"
                    f"&#9201; {minuto}'"
                )
                for cid in pro_ids:
                    threading.Thread(target=_send_telegram_message, args=(cid, msg), daemon=True).start()

    live_fixture_ids = {str(p.get("fixture_id", 0)) for p in LIVE_RESULTS_CACHE if p.get("live")}
    _NOTIFIED_GOALS = (
        {g for g in _NOTIFIED_GOALS if any(g.startswith(fid) for fid in live_fixture_ids)}
        if live_fixture_ids else set()
    )


def notify_admin_new_user(email, piano, resend_api_key=""):
    """Notifica l'admin quando un nuovo utente si registra (email + Telegram)."""
    # 1. Email
    try:
        import json as js
        body = js.dumps({
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
        req = urllib.request.Request("https://api.resend.com/emails", data=body, headers={
            "Authorization": f"Bearer {resend_api_key}",
            "Content-Type": "application/json",
            "User-Agent": "MatchIQ/1.0"
        })
        urllib.request.urlopen(req, timeout=10)
        print(f"📧 Notifica admin: nuovo utente {email}")
    except Exception as e:
        print(f"⚠️ Errore notifica email admin: {e}")

    # 2. Telegram
    try:
        import sqlite3
        if os.path.exists(_BOT_DB_PATH):
            conn = sqlite3.connect(_BOT_DB_PATH)
            row = conn.execute(
                "SELECT chat_id FROM utenti WHERE username = ?",
                (ADMIN_TELEGRAM_USERNAME,)
            ).fetchone()
            conn.close()
            if row:
                chat_id = row[0]
                msg = (
                    f"🆕 <b>Nuovo iscritto MatchIQ!</b>\n\n"
                    f"📧 {email}\n"
                    f"📋 Piano: {piano}\n"
                    f"⏰ {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M')}"
                )
                _send_telegram_message(chat_id, msg)
    except Exception:
        _logger.warning("Eccezione silenziata", exc_info=True)


def start_telegram_bot(df=None, bot_token=None):
    """Avvia il bot Telegram in background (daemon thread)."""
    token = bot_token or TELEGRAM_BOT_TOKEN

    def _run():
        try:
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            sys.path.insert(0, _ROOT)
            from telegram import Update
            from telegram.ext import Application, CommandHandler, CallbackQueryHandler
            from telegram_bot import (
                cmd_start, cmd_help, cmd_pronostico, cmd_giornata,
                cmd_classifica, cmd_pro, callback_handler, init_bot_db,
            )
            import telegram_bot

            init_bot_db()

            if df is not None:
                telegram_bot.DF = df

            bot_app = Application.builder().token(token).build()
            bot_app.add_handler(CommandHandler("start", cmd_start))
            bot_app.add_handler(CommandHandler("help", cmd_help))
            bot_app.add_handler(CommandHandler("pronostico", cmd_pronostico))
            bot_app.add_handler(CommandHandler("giornata", cmd_giornata))
            bot_app.add_handler(CommandHandler("classifica", cmd_classifica))
            bot_app.add_handler(CommandHandler("pro", cmd_pro))
            bot_app.add_handler(CallbackQueryHandler(callback_handler))

            print("🤖 BOT TELEGRAM ATTIVO!")
            bot_app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)
        except Exception as e:
            print(f"⚠️ Bot Telegram non avviato: {e}")

    threading.Thread(target=_run, daemon=True).start()
