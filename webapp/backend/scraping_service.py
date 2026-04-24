"""
scraping_service.py - Funzioni di scraping web per MatchIQ
Gestisce: notizie (Google News RSS), quote bookmaker (the-odds-api.com),
          formazioni live (fantacalcio.it), infortunati (fantacalciopedia).
"""

import os
import json
import logging
import urllib.request
import re as regex_module
from datetime import datetime, timezone

_logger = logging.getLogger(__name__)

# ─────────────────────────────
# NOTIZIE LIVE
# ─────────────────────────────
NOTIZIE_CACHE = []
NOTIZIE_LAST_UPDATE = ""

def _scrape_notizie():
    """Scarica notizie calcio da Google News RSS (affidabile e sempre aggiornato)."""
    global NOTIZIE_CACHE, NOTIZIE_LAST_UPDATE
    notizie = []
    feeds = [
        ("https://news.google.com/rss/search?q=serie+a+calcio+2026&hl=it&gl=IT&ceid=IT:it", "Serie A"),
        ("https://news.google.com/rss/search?q=premier+league+football+2026&hl=it&gl=IT&ceid=IT:it", "Premier League"),
        ("https://news.google.com/rss/search?q=calciomercato+2026&hl=it&gl=IT&ceid=IT:it", "Calciomercato"),
    ]
    for feed_url, categoria in feeds:
        try:
            req = urllib.request.Request(feed_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as r:
                xml = r.read().decode("utf-8", errors="replace")
            items = regex_module.findall(
                r'<item>.*?<title>(.*?)</title>.*?<link>(.*?)</link>.*?<source[^>]*>(.*?)</source>.*?</item>',
                xml, regex_module.DOTALL
            )
            for titolo, url, fonte in items[:4]:
                titolo = regex_module.sub(r'<[^>]+>', '', titolo).strip()
                titolo = titolo.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>').replace('&#39;', "'")
                if titolo and len(titolo) > 15:
                    notizie.append({"titolo": titolo, "fonte": fonte or categoria, "url": url})
        except Exception as e:
            print(f"⚠️ RSS {categoria}: {e}")
    if notizie:
        seen = set()
        unique = []
        for n in notizie:
            if n["titolo"] not in seen:
                seen.add(n["titolo"])
                unique.append(n)
        NOTIZIE_CACHE = unique[:12]
        NOTIZIE_LAST_UPDATE = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M")
        print(f"📰 Notizie: {len(NOTIZIE_CACHE)} articoli live da Google News")


# ─────────────────────────────
# QUOTE BOOKMAKER (the-odds-api.com)
# ─────────────────────────────
ODDS_API_KEY = os.environ.get("ODDS_API_KEY", "")
ODDS_CACHE = {}
ODDS_LAST_UPDATE = ""

_ODDS_NOME_MAP = {
    "FC Internazionale Milano": "Inter", "Inter Milan": "Inter", "Inter": "Inter",
    "AC Milan": "Milan", "Milan": "Milan",
    "SSC Napoli": "Napoli", "Napoli": "Napoli",
    "Como 1907": "Como", "Como": "Como",
    "Juventus FC": "Juventus", "Juventus": "Juventus",
    "AS Roma": "Roma", "Roma": "Roma",
    "Atalanta BC": "Atalanta", "Atalanta": "Atalanta",
    "SS Lazio": "Lazio", "Lazio": "Lazio",
    "Bologna FC 1909": "Bologna", "Bologna": "Bologna",
    "US Sassuolo": "Sassuolo", "Sassuolo": "Sassuolo",
    "Udinese Calcio": "Udinese", "Udinese": "Udinese",
    "Parma Calcio 1913": "Parma", "Parma": "Parma",
    "Genoa CFC": "Genoa", "Genoa": "Genoa",
    "Torino FC": "Torino", "Torino": "Torino",
    "Cagliari Calcio": "Cagliari", "Cagliari": "Cagliari",
    "ACF Fiorentina": "Fiorentina", "Fiorentina": "Fiorentina",
    "US Cremonese": "Cremonese", "Cremonese": "Cremonese",
    "US Lecce": "Lecce", "Lecce": "Lecce",
    "Hellas Verona FC": "Verona", "Verona": "Verona",
    "AC Pisa 1909": "Pisa", "Pisa": "Pisa",
}


def _scrape_odds():
    """Scarica quote live Serie A dai bookmaker."""
    global ODDS_CACHE, ODDS_LAST_UPDATE
    try:
        url = (
            f"https://api.the-odds-api.com/v4/sports/soccer_italy_serie_a/odds/"
            f"?apiKey={ODDS_API_KEY}&regions=eu&markets=h2h,totals&oddsFormat=decimal"
        )
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode())

        new_cache = {}
        for match in data:
            home_api = match.get("home_team", "")
            away_api = match.get("away_team", "")
            home = _ODDS_NOME_MAP.get(home_api, home_api)
            away = _ODDS_NOME_MAP.get(away_api, away_api)

            quotes_1, quotes_x, quotes_2 = [], [], []
            quotes_over, quotes_under = [], []
            for bk in match.get("bookmakers", []):
                for market in bk.get("markets", []):
                    if market.get("key") == "h2h":
                        for outcome in market.get("outcomes", []):
                            nome_out = _ODDS_NOME_MAP.get(outcome["name"], outcome["name"])
                            if nome_out == home:
                                quotes_1.append(outcome["price"])
                            elif nome_out == away:
                                quotes_2.append(outcome["price"])
                            elif outcome["name"] == "Draw":
                                quotes_x.append(outcome["price"])
                    elif market.get("key") == "totals":
                        for outcome in market.get("outcomes", []):
                            if outcome.get("name") == "Over" and outcome.get("point", 0) == 2.5:
                                quotes_over.append(outcome["price"])
                            elif outcome.get("name") == "Under" and outcome.get("point", 0) == 2.5:
                                quotes_under.append(outcome["price"])

            if quotes_1 and quotes_x and quotes_2:
                avg_1 = sum(quotes_1) / len(quotes_1)
                avg_x = sum(quotes_x) / len(quotes_x)
                avg_2 = sum(quotes_2) / len(quotes_2)
                p1 = 1 / avg_1
                px = 1 / avg_x
                p2 = 1 / avg_2
                tot = p1 + px + p2
                key = f"{home}_vs_{away}"
                entry = {
                    "prob_1": round(p1 / tot * 100, 1),
                    "prob_x": round(px / tot * 100, 1),
                    "prob_2": round(p2 / tot * 100, 1),
                    "quota_1": round(avg_1, 2),
                    "quota_x": round(avg_x, 2),
                    "quota_2": round(avg_2, 2),
                    "n_bookmakers": len(quotes_1),
                }
                if quotes_over and quotes_under:
                    avg_ov = sum(quotes_over) / len(quotes_over)
                    avg_un = sum(quotes_under) / len(quotes_under)
                    p_ov = 1 / avg_ov
                    p_un = 1 / avg_un
                    tot_ou = p_ov + p_un
                    entry["bk_over_25"] = round(p_ov / tot_ou * 100, 1)
                    entry["bk_under_25"] = round(p_un / tot_ou * 100, 1)
                new_cache[key] = entry

        if new_cache:
            ODDS_CACHE = new_cache
            ODDS_LAST_UPDATE = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M")
            print(f"📊 Quote bookmaker: {len(ODDS_CACHE)} partite da {len(data)} match")
    except Exception as e:
        print(f"⚠️ Scrape quote fallito: {e}")


def get_bookmaker_odds(home, away):
    """Ritorna le probabilita' bookmaker per una partita."""
    key = f"{home}_vs_{away}"
    return ODDS_CACHE.get(key)


# ─────────────────────────────
# FORMAZIONI LIVE (fantacalcio.it)
# ─────────────────────────────
LIVE_FORMAZIONI = {}
LIVE_INFORTUNATI = {}
LIVE_LAST_UPDATE = ""


def _scrape_live_data():
    """Scarica formazioni e infortunati aggiornati dal web."""
    global LIVE_FORMAZIONI, LIVE_INFORTUNATI, LIVE_LAST_UPDATE
    try:
        req = urllib.request.Request(
            "https://www.fantacalcio.it/probabili-formazioni-serie-a",
            headers={"User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            html = r.read().decode("utf-8", errors="replace")
        if len(html) > 1000:
            LIVE_LAST_UPDATE = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M")
            print(f"🔄 Dati live scaricati: {len(html)} bytes ({LIVE_LAST_UPDATE})")
    except Exception as e:
        print(f"⚠️ Scrape formazioni fallito: {e}")

    try:
        req = urllib.request.Request(
            "https://www.fantacalciopedia.com/articoli-fcp/consigli-fantacalcio/75-lista-infortunati-serie-a-aggiornata.html",
            headers={"User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            html = r.read().decode("utf-8", errors="replace")
        if len(html) > 1000:
            print(f"🔄 Infortunati scaricati: {len(html)} bytes")
    except Exception as e:
        print(f"⚠️ Scrape infortunati fallito: {e}")
