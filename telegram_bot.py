"""
telegram_bot.py
Bot Telegram per pronostici Serie A 2025-2026.
Comandi: /start, /pronostico, /giornata, /classifica, /pro, /help
Piano Free: 2 pronostici/giorno, solo 1X2
Piano Pro: illimitato + Over/Under + Goal + Risultato Esatto + Formazioni
"""

import os
import sys
import sqlite3
import asyncio
import logging
from datetime import datetime, timedelta

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes, JobQueue
)

# Aggiungi la cartella corrente al path per importare i moduli
sys.path.insert(0, os.path.dirname(__file__))

from bot_config import *
from data_loader import load_all_data, get_teams
from stats_engine import get_team_stats
from predictor import get_prediction
from season_2526 import (
    SQUADRE_2526, CLASSIFICA_REALE_30G, get_classifica_reale,
    get_calendario_rimanente, GIORNATA_ATTUALE
)
from live_data import get_infortunati, get_formazione

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Dati globali
DF = None
SQUADRE = []


# ──────────────────────────────────────────────
# Database utenti
# ──────────────────────────────────────────────

def init_bot_db():
    conn = sqlite3.connect(BOT_DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS utenti (
            chat_id INTEGER PRIMARY KEY,
            username TEXT,
            piano TEXT DEFAULT 'free',
            data_iscrizione TEXT,
            pronostici_oggi INTEGER DEFAULT 0,
            ultimo_reset TEXT
        )
    """)
    conn.commit()
    conn.close()


def get_utente(chat_id: int) -> dict | None:
    conn = sqlite3.connect(BOT_DB_PATH)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM utenti WHERE chat_id = ?", (chat_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def registra_utente(chat_id: int, username: str):
    conn = sqlite3.connect(BOT_DB_PATH)
    conn.execute("""
        INSERT OR IGNORE INTO utenti (chat_id, username, piano, data_iscrizione, pronostici_oggi, ultimo_reset)
        VALUES (?, ?, 'free', ?, 0, ?)
    """, (chat_id, username, datetime.now().strftime("%d/%m/%Y"), datetime.now().strftime("%Y-%m-%d")))
    conn.commit()
    conn.close()


def incrementa_pronostici(chat_id: int):
    oggi = datetime.now().strftime("%Y-%m-%d")
    conn = sqlite3.connect(BOT_DB_PATH)
    utente = get_utente(chat_id)
    if utente and utente["ultimo_reset"] != oggi:
        conn.execute("UPDATE utenti SET pronostici_oggi = 1, ultimo_reset = ? WHERE chat_id = ?",
                     (oggi, chat_id))
    else:
        conn.execute("UPDATE utenti SET pronostici_oggi = pronostici_oggi + 1 WHERE chat_id = ?",
                     (chat_id,))
    conn.commit()
    conn.close()


def puo_pronosticare(chat_id: int) -> bool:
    utente = get_utente(chat_id)
    if not utente:
        return False
    if utente["piano"] == PIANO_PRO:
        return True
    oggi = datetime.now().strftime("%Y-%m-%d")
    if utente["ultimo_reset"] != oggi:
        return True
    return utente["pronostici_oggi"] < FREE_MAX_PARTITE_GIORNO


def is_pro(chat_id: int) -> bool:
    utente = get_utente(chat_id)
    return utente is not None and utente["piano"] == PIANO_PRO


def set_pro(chat_id: int):
    conn = sqlite3.connect(BOT_DB_PATH)
    conn.execute("UPDATE utenti SET piano = 'pro' WHERE chat_id = ?", (chat_id,))
    conn.commit()
    conn.close()


def get_n_utenti() -> int:
    conn = sqlite3.connect(BOT_DB_PATH)
    n = conn.execute("SELECT COUNT(*) FROM utenti").fetchone()[0]
    conn.close()
    return n


def get_tutti_chat_ids() -> list:
    conn = sqlite3.connect(BOT_DB_PATH)
    rows = conn.execute("SELECT chat_id FROM utenti").fetchall()
    conn.close()
    return [r[0] for r in rows]


def get_pro_chat_ids() -> list:
    conn = sqlite3.connect(BOT_DB_PATH)
    rows = conn.execute("SELECT chat_id FROM utenti WHERE piano = 'pro'").fetchall()
    conn.close()
    return [r[0] for r in rows]


# ──────────────────────────────────────────────
# Formattazione messaggi
# ──────────────────────────────────────────────

def formato_pronostico_free(home: str, away: str, pred: dict) -> str:
    """Formatta un pronostico per utenti Free."""
    sugg = pred["suggerimento"]
    sugg_emoji = {"1": "🏠", "X": "🤝", "2": "✈️"}.get(sugg, "")

    msg = f"⚽ *{home} vs {away}*\n"
    msg += f"━━━━━━━━━━━━━━━━━━\n"
    msg += f"1️⃣ Casa: *{pred['prob_1']:.1f}%* (quota {pred['quota_1']})\n"
    msg += f"❌ Pareggio: *{pred['prob_x']:.1f}%* (quota {pred['quota_x']})\n"
    msg += f"2️⃣ Ospite: *{pred['prob_2']:.1f}%* (quota {pred['quota_2']})\n"
    msg += f"━━━━━━━━━━━━━━━━━━\n"
    msg += f"{sugg_emoji} *Consiglio: {sugg} — {pred['sugg_label']}*\n"
    msg += f"📊 Affidabilita': {pred['confidence_label']} ({round(pred['confidence'] * 100)}%)\n"
    msg += f"\n🔒 _Over/Under, Goal, Risultato Esatto → /pro_"
    return msg


def formato_pronostico_pro(home: str, away: str, pred: dict, hs: dict, as_: dict) -> str:
    """Formatta un pronostico completo per utenti Pro."""
    sugg = pred["suggerimento"]
    sugg_emoji = {"1": "🏠", "X": "🤝", "2": "✈️"}.get(sugg, "")

    msg = f"⚽ *{home} vs {away}*\n"
    msg += f"━━━━━━━━━━━━━━━━━━━━━\n\n"

    # 1X2
    msg += f"📊 *PRONOSTICO 1X2*\n"
    msg += f"  1️⃣ Casa: *{pred['prob_1']:.1f}%* (quota {pred['quota_1']})\n"
    msg += f"  ❌ Pareggio: *{pred['prob_x']:.1f}%* (quota {pred['quota_x']})\n"
    msg += f"  2️⃣ Ospite: *{pred['prob_2']:.1f}%* (quota {pred['quota_2']})\n\n"

    # Over/Under
    msg += f"📈 *OVER / UNDER*\n"
    msg += f"  Over 1.5: {pred.get('over_15', '-')}%  |  Under 1.5: {pred.get('under_15', '-')}%\n"
    msg += f"  Over 2.5: {pred.get('over_25', '-')}%  |  Under 2.5: {pred.get('under_25', '-')}%\n"
    msg += f"  Over 3.5: {pred.get('over_35', '-')}%  |  Under 3.5: {pred.get('under_35', '-')}%\n\n"

    # Goal
    msg += f"⚽ *GOAL / NO GOAL*\n"
    msg += f"  Goal Si: {pred.get('goal_si', '-')}%  |  Goal No: {pred.get('goal_no', '-')}%\n\n"

    # Risultato esatto
    esatti = pred.get("risultati_esatti", [])
    if esatti:
        msg += f"🎯 *RISULTATO ESATTO*\n"
        for r in esatti[:3]:
            msg += f"  {r['score']}: {r['prob']}%\n"
        msg += f"\n"

    # xG
    if pred.get("xg_applied"):
        msg += f"📉 *xG STAGIONE*\n"
        msg += f"  {home}: {pred['xg_home']} xG/p  |  {away}: {pred['xg_away']} xG/p\n\n"

    # Infortunati
    inj_h = get_infortunati(home)
    inj_a = get_infortunati(away)
    if inj_h or inj_a:
        msg += f"🏥 *INDISPONIBILI*\n"
        if inj_h:
            nomi = ", ".join(i["nome"] for i in inj_h[:4])
            msg += f"  {home}: {nomi}\n"
        if inj_a:
            nomi = ", ".join(i["nome"] for i in inj_a[:4])
            msg += f"  {away}: {nomi}\n"
        msg += f"\n"

    # Tips
    tips = pred.get("tips_extra", [])
    msg += f"━━━━━━━━━━━━━━━━━━━━━\n"
    msg += f"{sugg_emoji} *CONSIGLIO: {sugg} — {pred['sugg_label']}*\n"
    if tips:
        tips_txt = " | ".join(f"{t[0]} ({t[1]}%)" for t in tips)
        msg += f"💡 Extra: {tips_txt}\n"
    msg += f"📊 Affidabilita': *{pred['confidence_label']}* ({round(pred['confidence'] * 100)}%)\n"
    msg += f"⏱ Gol attesi: {pred.get('gol_attesi', '-')}\n"

    return msg


def formato_giornata(g_num: int, pronostici_list: list, pro: bool) -> str:
    """Formatta i pronostici di un'intera giornata."""
    msg = f"🏟 *PRONOSTICI GIORNATA {g_num}*\n"
    msg += f"Serie A 2025-2026\n"
    msg += f"━━━━━━━━━━━━━━━━━━━━━\n\n"

    for p in pronostici_list:
        sugg_emoji = {"1": "🏠", "X": "🤝", "2": "✈️"}.get(p["suggerimento"], "")

        msg += f"⚽ {p['home']} vs {p['away']}\n"
        msg += f"  {sugg_emoji} *{p['suggerimento']}* ({p['prob']}%) "

        if pro:
            ou = "O2.5" if p.get("over_25", 50) > 55 else "U2.5"
            goal = "Goal" if p.get("goal_si", 50) > 55 else "NoGoal"
            msg += f"| {ou} | {goal} "

        msg += f"| Aff. {p['confidence']}%\n\n"

    msg += f"━━━━━━━━━━━━━━━━━━━━━\n"
    msg += f"📊 Generato il {datetime.now().strftime('%d/%m/%Y %H:%M')}\n"

    if not pro:
        msg += f"\n🔓 _Sblocca Over/Under + Goal + Esatto → /pro_"

    return msg


# ──────────────────────────────────────────────
# Comandi Bot
# ──────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    username = update.effective_user.username or update.effective_user.first_name
    registra_utente(chat_id, username)

    welcome = (
        f"👋 Ciao *{username}*!\n\n"
        f"⚽ Benvenuto nel *Bot Pronostici Serie A*\n"
        f"Il piu' avanzato sistema di predizione calcistica basato su:\n"
        f"📊 26 anni di dati storici\n"
        f"📈 xG stagione 2025-2026\n"
        f"🤖 Modello Dixon-Coles + AI\n"
        f"🏥 Infortunati e formazioni live\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"*COMANDI DISPONIBILI:*\n"
        f"/pronostico — Scegli una partita\n"
        f"/giornata — Pronostici giornata completa\n"
        f"/classifica — Classifica Serie A\n"
        f"/pro — Sblocca tutte le funzioni\n"
        f"/help — Guida completa\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"📌 Piano attuale: *FREE* (2 pronostici/giorno)\n"
        f"🔓 Passa a PRO per pronostici illimitati!"
    )
    await update.message.reply_text(welcome, parse_mode="Markdown")


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "📖 *GUIDA BOT PRONOSTICI*\n\n"
        "*Comandi:*\n"
        "/pronostico — Scegli 2 squadre e ottieni il pronostico\n"
        "/giornata — Pronostici di tutte le partite della prossima giornata\n"
        "/classifica — Classifica Serie A attuale\n"
        "/marcatori — Top 10 marcatori\n"
        "/pro — Info su come passare a PRO\n\n"
        "*Piano FREE:*\n"
        "• 2 pronostici al giorno\n"
        "• Solo 1X2 con probabilita' e quota\n\n"
        "*Piano PRO (9.99/mese):*\n"
        "• Pronostici illimitati\n"
        "• Over/Under 1.5, 2.5, 3.5\n"
        "• Goal Si/No\n"
        "• Risultato esatto top 3\n"
        "• xG confronto\n"
        "• Formazioni e infortunati\n"
        "• Alert pre-partita automatici\n"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")


async def cmd_pronostico(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra la lista squadre per scegliere casa."""
    keyboard = []
    row = []
    for i, sq in enumerate(SQUADRE_2526):
        row.append(InlineKeyboardButton(sq, callback_data=f"home_{sq}"))
        if len(row) == 3:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    await update.message.reply_text(
        "🏠 *Scegli la squadra di CASA:*",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gestisce i click sui pulsanti inline."""
    query = update.callback_query
    await query.answer()
    data = query.data
    chat_id = query.message.chat_id

    if data.startswith("home_"):
        home = data.replace("home_", "")
        context.user_data["home"] = home

        keyboard = []
        row = []
        for sq in SQUADRE_2526:
            if sq != home:
                row.append(InlineKeyboardButton(sq, callback_data=f"away_{sq}"))
                if len(row) == 3:
                    keyboard.append(row)
                    row = []
        if row:
            keyboard.append(row)

        await query.edit_message_text(
            f"🏠 Casa: *{home}*\n\n✈️ *Scegli la squadra OSPITE:*",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

    elif data.startswith("away_"):
        away = data.replace("away_", "")
        home = context.user_data.get("home", "")

        if not home:
            await query.edit_message_text("Errore. Riprova con /pronostico")
            return

        # Controlla limiti Free
        if not puo_pronosticare(chat_id):
            await query.edit_message_text(
                "🔒 Hai raggiunto il limite di 2 pronostici oggi.\n\n"
                "Passa a *PRO* per pronostici illimitati! → /pro",
                parse_mode="Markdown"
            )
            return

        await query.edit_message_text("⏳ Calcolo pronostico in corso...")

        try:
            hs = get_team_stats(DF, home, opponent=away)
            as_ = get_team_stats(DF, away, opponent=home)
            pred = get_prediction(hs, as_, df=DF)

            if is_pro(chat_id):
                msg = formato_pronostico_pro(home, away, pred, hs, as_)
            else:
                msg = formato_pronostico_free(home, away, pred)

            incrementa_pronostici(chat_id)
            await query.edit_message_text(msg, parse_mode="Markdown")
        except Exception as e:
            await query.edit_message_text(f"Errore nel calcolo: {e}")

    elif data.startswith("giornata_"):
        g_num = int(data.replace("giornata_", ""))
        await _invia_giornata(query.message, chat_id, g_num)


async def cmd_giornata(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra i pulsanti per scegliere la giornata."""
    keyboard = []
    row = []
    for g in range(31, 39):
        row.append(InlineKeyboardButton(f"G.{g}", callback_data=f"giornata_{g}"))
        if len(row) == 4:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    await update.message.reply_text(
        "📅 *Scegli la giornata:*",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


async def _invia_giornata(message, chat_id: int, g_num: int):
    """Calcola e invia i pronostici di una giornata."""
    calendario = get_calendario_rimanente()
    giornata = calendario.get(g_num)
    if not giornata:
        await message.edit_text("Giornata non disponibile.")
        return

    await message.edit_text(f"⏳ Calcolo pronostici giornata {g_num}...")

    pronostici = []
    for home, away in giornata["partite"]:
        try:
            hs = get_team_stats(DF, home, opponent=away)
            as_ = get_team_stats(DF, away, opponent=home)
            pred = get_prediction(hs, as_, df=DF)
            sugg = pred["suggerimento"]
            max_prob = max(pred["prob_1"], pred["prob_x"], pred["prob_2"])
            pronostici.append({
                "home": home, "away": away,
                "suggerimento": sugg,
                "prob": f"{max_prob:.0f}",
                "over_25": pred.get("over_25", 50),
                "goal_si": pred.get("goal_si", 50),
                "confidence": round(pred["confidence"] * 100),
            })
        except Exception:
            pronostici.append({
                "home": home, "away": away,
                "suggerimento": "?", "prob": "?",
                "confidence": 0,
            })

    pro = is_pro(chat_id)
    msg = formato_giornata(g_num, pronostici, pro)
    await message.edit_text(msg, parse_mode="Markdown")


async def cmd_classifica(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra la classifica attuale."""
    classifica = get_classifica_reale()
    msg = f"🏆 *CLASSIFICA SERIE A 2025-2026*\n"
    msg += f"Giornata {GIORNATA_ATTUALE}\n"
    msg += f"━━━━━━━━━━━━━━━━━━━━━\n\n"

    for i, r in enumerate(classifica, 1):
        if i <= 4:
            emoji = "🟢"
        elif i <= 6:
            emoji = "🟡"
        elif i >= 18:
            emoji = "🔴"
        else:
            emoji = "⚪"
        msg += f"{emoji} {i}. *{r['Squadra']}* — {r['Punti']} pt ({r['V']}V {r['N']}N {r['P']}P)\n"

    await update.message.reply_text(msg, parse_mode="Markdown")


async def cmd_pro(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Info sul piano Pro."""
    msg = (
        "⭐ *PIANO PRO — 9.99 EUR/mese*\n\n"
        "Sblocca tutte le funzionalita':\n\n"
        "✅ Pronostici illimitati\n"
        "✅ Over/Under 1.5, 2.5, 3.5\n"
        "✅ Goal Si / Goal No\n"
        "✅ Risultato esatto top 3\n"
        "✅ xG confronto squadre\n"
        "✅ Probabili formazioni\n"
        "✅ Lista infortunati live\n"
        "✅ Alert pre-partita automatici\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "💳 *Per abbonarti:*\n"
        "Contatta @TUO_USERNAME per ricevere il link di pagamento Stripe.\n\n"
        "Dopo il pagamento riceverai l'attivazione immediata!"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")


# ──────────────────────────────────────────────
# Invio automatico pronostici
# ──────────────────────────────────────────────

async def invio_giornaliero(context: ContextTypes.DEFAULT_TYPE):
    """Job che invia pronostici a tutti gli utenti ogni mattina."""
    calendario = get_calendario_rimanente()

    # Trova la prossima giornata
    prossima_g = None
    for g in range(31, 39):
        if g in calendario:
            prossima_g = g
            break

    if not prossima_g:
        return

    giornata = calendario[prossima_g]
    pronostici = []
    for home, away in giornata["partite"]:
        try:
            hs = get_team_stats(DF, home, opponent=away)
            as_ = get_team_stats(DF, away, opponent=home)
            pred = get_prediction(hs, as_, df=DF)
            sugg = pred["suggerimento"]
            max_prob = max(pred["prob_1"], pred["prob_x"], pred["prob_2"])
            pronostici.append({
                "home": home, "away": away,
                "suggerimento": sugg,
                "prob": f"{max_prob:.0f}",
                "over_25": pred.get("over_25", 50),
                "goal_si": pred.get("goal_si", 50),
                "confidence": round(pred["confidence"] * 100),
            })
        except Exception:
            continue

    # Invia a tutti i Pro
    for chat_id in get_pro_chat_ids():
        try:
            msg = formato_giornata(prossima_g, pronostici, True)
            await context.bot.send_message(chat_id, msg, parse_mode="Markdown")
        except Exception:
            continue

    # Invia versione Free a tutti gli altri
    for chat_id in get_tutti_chat_ids():
        if not is_pro(chat_id):
            try:
                msg = formato_giornata(prossima_g, pronostici, False)
                await context.bot.send_message(chat_id, msg, parse_mode="Markdown")
            except Exception:
                continue

    logger.info(f"Pronostici giornata {prossima_g} inviati a {get_n_utenti()} utenti")


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────

def main():
    global DF, SQUADRE

    if TELEGRAM_BOT_TOKEN == "IL_TUO_TOKEN_QUI":
        print("=" * 50)
        print("ERRORE: Configura il token del bot!")
        print()
        print("1. Apri Telegram e cerca @BotFather")
        print("2. Scrivi /newbot e segui le istruzioni")
        print("3. Copia il token che ti da'")
        print("4. Apri bot_config.py e incolla il token")
        print("   nella variabile TELEGRAM_BOT_TOKEN")
        print("=" * 50)
        input("\nPremi INVIO per chiudere...")
        return

    # Carica dati
    print("Caricamento dati CSV...")
    try:
        DF = load_all_data()
        SQUADRE = get_teams(DF)
        print(f"Dati caricati: {len(DF)} partite, {len(SQUADRE)} squadre")
    except Exception as e:
        print(f"Errore caricamento dati: {e}")
        print("Il bot funzionera' con dati limitati.")

    # Init database
    init_bot_db()

    # Crea app
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Registra comandi
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("pronostico", cmd_pronostico))
    app.add_handler(CommandHandler("giornata", cmd_giornata))
    app.add_handler(CommandHandler("classifica", cmd_classifica))
    app.add_handler(CommandHandler("pro", cmd_pro))
    app.add_handler(CallbackQueryHandler(callback_handler))

    # Job giornaliero (ogni giorno alle 9:00)
    job_queue = app.job_queue
    if job_queue:
        # Calcola il prossimo orario delle 9:00
        now = datetime.now()
        target = now.replace(hour=9, minute=0, second=0, microsecond=0)
        if now >= target:
            target += timedelta(days=1)
        first_run = (target - now).total_seconds()
        job_queue.run_repeating(invio_giornaliero, interval=86400, first=first_run)
        print(f"Invio automatico programmato alle 09:00 ogni giorno")

    print()
    print("=" * 50)
    print("BOT PRONOSTICI SERIE A - ATTIVO!")
    print(f"Utenti registrati: {get_n_utenti()}")
    print("Premi Ctrl+C per fermare")
    print("=" * 50)

    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
