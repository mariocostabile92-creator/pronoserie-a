"""
startup.py - Logica di bootstrap per MatchIQ
Gestisce: caricamento dataset, avvio servizi con ritardo,
          inizializzazione del server (live_updater, bot Telegram, prime fetch).
"""

import os
import time
import logging
import threading

_logger = logging.getLogger(__name__)

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))


def _load_dataset():
    """Carica il dataset CSV dal root del progetto. Ritorna DataFrame o None."""
    import sys
    sys.path.insert(0, _ROOT)
    df = None
    try:
        import pandas as pd
        csv_path = os.path.join(_ROOT, "dataset_partite.csv")
        if os.path.exists(csv_path):
            df = pd.read_csv(csv_path)
            print(f"✅ Dataset caricato: {len(df)} righe")
        else:
            print(f"⚠️ Dataset non trovato: {csv_path}")
    except Exception as e:
        print(f"⚠️ Dataset non caricabile: {e}")
    return df


def _delayed_start(df=None, enable_telegram=True, verify_predictions_fn=None):
    """
    Avvia tutti i servizi con un ritardo di 5 secondi dopo il boot.
    - live_service: fetch iniziali + loop updater
    - telegram_service: bot Telegram (se enable_telegram)
    """
    time.sleep(5)
    print("🚀 AVVIO SERVIZI MatchIQ...")

    from live_service import (
        _fetch_live_results, _fetch_classifica_live, _fetch_marcatori_live,
        _fetch_infortunati_live, _fetch_rose_live, _fetch_risultati_stagione,
        _fetch_worldcup_data, _fetch_league_data, start_live_updater,
        LEAGUES,
    )
    from league_mappings import PL_TEAM_IDS, BL_TEAM_IDS, L1_TEAM_IDS
    from scraping_service import _scrape_notizie, _scrape_odds, _scrape_live_data

    # 1. Prime fetch immediate
    try:
        _scrape_live_data()
    except Exception:
        _logger.warning("Eccezione silenziata", exc_info=True)
    try:
        _scrape_notizie()
    except Exception:
        _logger.warning("Eccezione silenziata", exc_info=True)
    try:
        _scrape_odds()
    except Exception:
        _logger.warning("Eccezione silenziata", exc_info=True)
    try:
        _fetch_live_results()
    except Exception:
        _logger.warning("Eccezione silenziata", exc_info=True)
    try:
        _fetch_classifica_live()
    except Exception:
        _logger.warning("Eccezione silenziata", exc_info=True)
    try:
        _fetch_marcatori_live()
    except Exception:
        _logger.warning("Eccezione silenziata", exc_info=True)
    try:
        _fetch_infortunati_live()
    except Exception:
        _logger.warning("Eccezione silenziata", exc_info=True)
    try:
        _fetch_risultati_stagione()
    except Exception:
        _logger.warning("Eccezione silenziata", exc_info=True)
    try:
        _fetch_worldcup_data()
    except Exception:
        _logger.warning("Eccezione silenziata", exc_info=True)

    # 2. Fetch per leagues extra
    extra_leagues = ["premier-league", "la-liga", "champions-league",
                     "europa-league", "conference-league", "bundesliga", "ligue-1"]
    for lk in extra_leagues:
        try:
            _fetch_league_data(lk)
        except Exception:
            _logger.warning("Eccezione silenziata", exc_info=True)

    # 3. Rose (in background, non blocca)
    try:
        t = threading.Thread(target=_fetch_rose_live, daemon=True)
        t.start()
        t = threading.Thread(target=_fetch_rose_live, args=(PL_TEAM_IDS,), daemon=True)
        t.start()
        t = threading.Thread(target=_fetch_rose_live, args=(BL_TEAM_IDS,), daemon=True)
        t.start()
        t = threading.Thread(target=_fetch_rose_live, args=(L1_TEAM_IDS,), daemon=True)
        t.start()
    except Exception:
        _logger.warning("Eccezione silenziata", exc_info=True)

    # 4. Avvia loop updater
    try:
        start_live_updater(verify_predictions_fn=verify_predictions_fn)
        print("🔄 Live updater avviato")
    except Exception as e:
        print(f"❌ Live updater non avviato: {e}")

    # 5. Bot Telegram (opzionale)
    if enable_telegram:
        try:
            from telegram_service import start_telegram_bot
            start_telegram_bot(df=df)
            print("🤖 Bot Telegram avviato")
        except Exception as e:
            print(f"⚠️ Bot Telegram non avviato: {e}")

    print("✅ TUTTI I SERVIZI AVVIATI")


def bootstrap(df=None, enable_telegram=True, verify_predictions_fn=None):
    """
    Entry point principale per il bootstrap di MatchIQ.
    Avvia il delayed_start in un thread daemon.
    """
    t = threading.Thread(
        target=_delayed_start,
        kwargs={
            "df": df,
            "enable_telegram": enable_telegram,
            "verify_predictions_fn": verify_predictions_fn,
        },
        daemon=True,
    )
    t.start()
    return t
