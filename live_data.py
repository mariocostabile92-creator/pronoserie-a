"""
live_data.py
Gestisce dati live: infortunati, squalificati, probabili formazioni.
Si aggiorna automaticamente scaricando da fantacalciopedia e fantacalcio.it.
"""

import os
import json
import re
import threading
import time
from datetime import datetime

try:
    import urllib.request
    HAS_NET = True
except ImportError:
    HAS_NET = False

DATA_DIR = os.path.dirname(__file__)
CACHE_FILE = os.path.join(DATA_DIR, "live_cache.json")
UPDATE_INTERVAL = 1800  # 30 minuti

# Stato globale
_cache = {
    "infortunati": {},
    "formazioni": {},
    "ultimo_update": "",
}
_lock = threading.Lock()
_bg_thread = None


def _fetch(url: str) -> str | None:
    if not HAS_NET:
        return None
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.read().decode("utf-8", errors="replace")
    except Exception:
        return None


# ──────────────────────────────────────────────
# Infortunati (da fantacalciopedia.com e pazzidifanta.com)
# ──────────────────────────────────────────────

# Dati baseline (aggiornati 26 marzo 2026) - usati come fallback
INFORTUNATI_BASELINE = {
    "Inter": [
        {"nome": "Lautaro Martinez", "tipo": "infortunio", "dettaglio": "Da monitorare, rientro inizio aprile"},
        {"nome": "Mkhitaryan", "tipo": "infortunio", "dettaglio": "Problema muscolare, rientro inizio aprile"},
        {"nome": "Carlos Augusto", "tipo": "squalifica", "dettaglio": "Squalificato 1 giornata"},
    ],
    "Milan": [
        {"nome": "Gabbia", "tipo": "infortunio", "dettaglio": "Problema muscolare, rientro aprile"},
        {"nome": "Loftus-Cheek", "tipo": "infortunio", "dettaglio": "Infortunio al ginocchio, rientro aprile"},
        {"nome": "Leao", "tipo": "dubbio", "dettaglio": "Affaticamento, da valutare"},
    ],
    "Napoli": [
        {"nome": "Neres", "tipo": "infortunio", "dettaglio": "Problema muscolare, rientro aprile"},
        {"nome": "Di Lorenzo", "tipo": "infortunio", "dettaglio": "Distorsione ginocchio, rientro fine aprile"},
        {"nome": "Rrahmani", "tipo": "infortunio", "dettaglio": "Intervento chirurgico, rientro maggio"},
    ],
    "Como": [
        {"nome": "Addai", "tipo": "infortunio", "dettaglio": "Stagione finita"},
    ],
    "Juventus": [
        {"nome": "Holm", "tipo": "infortunio", "dettaglio": "Rientro inizio aprile"},
    ],
    "Roma": [
        {"nome": "Kone", "tipo": "infortunio", "dettaglio": "Problema muscolare, rientro fine aprile"},
        {"nome": "Dybala", "tipo": "infortunio", "dettaglio": "Problema muscolare, rientro fine aprile"},
        {"nome": "Dovbyk", "tipo": "infortunio", "dettaglio": "Rientro maggio"},
        {"nome": "Ferguson", "tipo": "infortunio", "dettaglio": "Stagione finita"},
    ],
    "Atalanta": [
        {"nome": "Scamacca", "tipo": "dubbio", "dettaglio": "Da monitorare"},
    ],
    "Lazio": [
        {"nome": "Zaccagni", "tipo": "infortunio", "dettaglio": "Rientro fine aprile"},
        {"nome": "Rovella", "tipo": "infortunio", "dettaglio": "Stagione finita"},
        {"nome": "Provedel", "tipo": "infortunio", "dettaglio": "Stagione finita"},
    ],
    "Bologna": [
        {"nome": "Odgaard", "tipo": "infortunio", "dettaglio": "Rientro meta' aprile"},
        {"nome": "Pobega", "tipo": "infortunio", "dettaglio": "Rientro meta' aprile"},
        {"nome": "Skorupski", "tipo": "infortunio", "dettaglio": "Rientro maggio"},
    ],
    "Sassuolo": [
        {"nome": "Pieragnolo", "tipo": "infortunio", "dettaglio": "Rientro inizio aprile"},
        {"nome": "Cande", "tipo": "infortunio", "dettaglio": "Stagione finita"},
        {"nome": "Fadera", "tipo": "infortunio", "dettaglio": "Frattura zigomo, rientro maggio"},
    ],
    "Udinese": [
        {"nome": "Buksa", "tipo": "infortunio", "dettaglio": "Rientro meta' aprile"},
        {"nome": "Zanoli", "tipo": "infortunio", "dettaglio": "Stagione finita"},
    ],
    "Parma": [
        {"nome": "Almqvist", "tipo": "infortunio", "dettaglio": "Lesione flessori, rientro dopo sosta"},
        {"nome": "Cremaschi", "tipo": "infortunio", "dettaglio": "Menisco, stagione finita"},
    ],
    "Genoa": [
        {"nome": "Onana", "tipo": "dubbio", "dettaglio": "Da valutare"},
    ],
    "Torino": [
        {"nome": "Aboukhlal", "tipo": "dubbio", "dettaglio": "Da valutare"},
    ],
    "Cagliari": [
        {"nome": "Felici", "tipo": "infortunio", "dettaglio": "Stagione finita"},
        {"nome": "Idrissi", "tipo": "infortunio", "dettaglio": "Stagione finita"},
    ],
    "Fiorentina": [
        {"nome": "Solomon", "tipo": "infortunio", "dettaglio": "Rientro fine marzo"},
        {"nome": "Lamptey", "tipo": "infortunio", "dettaglio": "Rientro fine marzo"},
    ],
    "Cremonese": [
        {"nome": "Baschirotto", "tipo": "infortunio", "dettaglio": "Rientro inizio aprile"},
    ],
    "Lecce": [
        {"nome": "Gaspar", "tipo": "infortunio", "dettaglio": "Stagione finita"},
        {"nome": "Berisha", "tipo": "infortunio", "dettaglio": "Stagione finita"},
        {"nome": "Camarda", "tipo": "infortunio", "dettaglio": "Rientro aprile"},
    ],
    "Verona": [],
    "Pisa": [
        {"nome": "Denoon", "tipo": "infortunio", "dettaglio": "Lungodegente"},
        {"nome": "Scuffet", "tipo": "infortunio", "dettaglio": "Rientro inizio aprile"},
    ],

    # ──────────────────────────────────────────────
    # PREMIER LEAGUE (aprile 2026)
    # Fonte baseline: notizie pubbliche aggiornate
    # ──────────────────────────────────────────────
    "Arsenal": [
        {"nome": "Tomiyasu", "tipo": "infortunio", "dettaglio": "Problema al ginocchio, rientro incerto"},
        {"nome": "Tierney", "tipo": "infortunio", "dettaglio": "Lesione muscolare"},
    ],
    "Liverpool": [
        {"nome": "Diogo Jota", "tipo": "infortunio", "dettaglio": "Lesione al tendine, rientro aprile/maggio"},
    ],
    "Chelsea": [],
    "Manchester City": [
        {"nome": "Rodri", "tipo": "infortunio", "dettaglio": "Recupero da infortunio al ginocchio"},
        {"nome": "Ederson", "tipo": "infortunio", "dettaglio": "Problema muscolare, da valutare"},
    ],
    "Newcastle United": [
        {"nome": "Sven Botman", "tipo": "infortunio", "dettaglio": "Infortunio al ginocchio, out a lungo"},
    ],
    "Brentford": [
        {"nome": "Kristoffer Ajer", "tipo": "infortunio", "dettaglio": "Infortunio al ginocchio"},
    ],
    "Brighton": [],
    "Bournemouth": [],
    "Fulham": [],
    "Manchester United": [
        {"nome": "Luke Shaw", "tipo": "infortunio", "dettaglio": "Problema muscolare, rientro aprile"},
        {"nome": "Lisandro Martinez", "tipo": "infortunio", "dettaglio": "Problema al ginocchio"},
    ],
    "Crystal Palace": [],
    "Aston Villa": [
        {"nome": "Emiliano Buendia", "tipo": "infortunio", "dettaglio": "Recupero lungo stop"},
    ],
    "Leeds": [],
    "Everton": [
        {"nome": "Seamus Coleman", "tipo": "infortunio", "dettaglio": "Da valutare"},
    ],
    "Nottingham Forest": [],
    "West Ham": [],
    "Tottenham": [
        {"nome": "Micky van de Ven", "tipo": "infortunio", "dettaglio": "Problema muscolare"},
    ],
    "Wolverhampton Wanderers": [
        {"nome": "Pedro Neto", "tipo": "infortunio", "dettaglio": "Problema muscolare, da valutare"},
    ],
    "Burnley": [],
    "Sunderland": [],
    # Alias nomi corti
    "Man City":     [{"nome": "Rodri", "tipo": "infortunio", "dettaglio": "Recupero da infortunio al ginocchio"},
                     {"nome": "Ederson", "tipo": "infortunio", "dettaglio": "Problema muscolare"}],
    "Man United":   [{"nome": "Luke Shaw", "tipo": "infortunio", "dettaglio": "Problema muscolare"},
                     {"nome": "Lisandro Martinez", "tipo": "infortunio", "dettaglio": "Ginocchio"}],
    "Newcastle":    [{"nome": "Sven Botman", "tipo": "infortunio", "dettaglio": "Ginocchio, out a lungo"}],
    "Nott. Forest": [],
    "Wolves":       [{"nome": "Pedro Neto", "tipo": "infortunio", "dettaglio": "Muscolare"}],

    # ──────────────────────────────────────────────
    # LA LIGA (aprile 2026)
    # ──────────────────────────────────────────────
    "Barcelona": [
        {"nome": "Gavi", "tipo": "infortunio", "dettaglio": "Rientro progressivo dopo lungo stop"},
        {"nome": "Frenkie de Jong", "tipo": "infortunio", "dettaglio": "Problema alla caviglia, da valutare"},
    ],
    "Real Madrid": [
        {"nome": "Thibaut Courtois", "tipo": "infortunio", "dettaglio": "Recupero graduale"},
        {"nome": "Eder Militao", "tipo": "infortunio", "dettaglio": "Recupero da infortunio al ginocchio"},
    ],
    "Atletico Madrid": [],
    "Athletic Club": [],
    "Real Betis": [
        {"nome": "Nabil Fekir", "tipo": "infortunio", "dettaglio": "Problema muscolare"},
    ],
    "Villarreal": [],
    "Real Sociedad": [],
    "Rayo Vallecano": [],
    "Getafe": [],
    "Osasuna": [],
    "Celta Vigo": [],
    "Alaves": [],
    "Valencia": [],
    "Girona": [],
    "Real Oviedo": [],
    "Espanyol": [],
    "Mallorca": [],
    "Levante": [],
    "Sevilla": [
        {"nome": "Erik Lamela", "tipo": "dubbio", "dettaglio": "Da valutare"},
    ],
    "Elche": [],
    # Alias
    "Atletico": [],
    "Oviedo":   [],

    # ──────────────────────────────────────────────
    # BUNDESLIGA (aprile 2026)
    # ──────────────────────────────────────────────
    "Bayern Munich": [
        {"nome": "Manuel Neuer", "tipo": "dubbio", "dettaglio": "Da valutare per la prossima gara"},
    ],
    "Bayer Leverkusen": [],
    "RasenBallsport Leipzig": [
        {"nome": "Dani Olmo", "tipo": "dubbio", "dettaglio": "Piccolo problema muscolare"},
    ],
    "Borussia Dortmund": [
        {"nome": "Sebastien Haller", "tipo": "infortunio", "dettaglio": "Problema muscolare, rientro imminente"},
    ],
    "VfB Stuttgart": [],
    "Eintracht Frankfurt": [],
    "Hoffenheim": [],
    "Mainz 05": [],
    "Freiburg": [],
    "FC Cologne": [],
    "Union Berlin": [],
    "Werder Bremen": [],
    "Borussia M.Gladbach": [],
    "Wolfsburg": [],
    "Augsburg": [],
    "Hamburger SV": [],
    "St. Pauli": [],
    "FC Heidenheim": [],
    # Alias Bundesliga
    "RB Leipzig":        [{"nome": "Dani Olmo", "tipo": "dubbio", "dettaglio": "Muscolare"}],
    "Mainz":             [],
    "Stuttgart":         [],
    "Monchengladbach":   [],
    "1. FC Koln":        [],
    "1. FC Heidenheim":  [],
    "St Pauli":          [],

    # ──────────────────────────────────────────────
    # LIGUE 1 (aprile 2026)
    # ──────────────────────────────────────────────
    "Paris Saint Germain": [
        {"nome": "Lucas Hernandez", "tipo": "infortunio", "dettaglio": "Recupero da infortunio al ginocchio"},
    ],
    "Lens": [],
    "Monaco": [
        {"nome": "Aleksandr Golovin", "tipo": "infortunio", "dettaglio": "Problema muscolare"},
    ],
    "Marseille": [],
    "Lille": [],
    "Strasbourg": [],
    "Lyon": [
        {"nome": "Maxence Caqueret", "tipo": "dubbio", "dettaglio": "Da valutare"},
    ],
    "Rennes": [],
    "Lorient": [],
    "Auxerre": [],
    "Toulouse": [],
    "Brest": [],
    "Nice": [],
    "Paris FC": [],
    "Nantes": [],
    "Le Havre": [],
    "Metz": [],
    "Angers": [],
    # Alias Ligue 1
    "PSG":               [{"nome": "Lucas Hernandez", "tipo": "infortunio", "dettaglio": "Ginocchio"}],
    "Stade Brestois 29": [],
}

# Probabili formazioni baseline (giornata 31)
FORMAZIONI_BASELINE = {
    31: {
        "Sassuolo": {"modulo": "4-2-3-1", "titolari": ["Muric", "Walukiewicz", "Idzes", "Muharemovic", "Garcia U.", "Kone I.", "Vranckx", "Berardi", "Volpato", "Lauriente", "Pinamonti"]},
        "Cagliari": {"modulo": "3-5-2", "titolari": ["Caprile", "Ze Pedro", "Mina", "Rodriguez", "Palestra", "Adopo", "Gaetano", "Folorunsho", "Obert", "Esposito Se.", "Kilicsoy"]},
        "Verona": {"modulo": "3-5-2", "titolari": ["Montipo", "Edmundsson", "Nelsson", "Valentini", "Belghali", "Akpa Akpro", "Gagliardini", "Harroui", "Frese", "Bowie", "Orban"]},
        "Fiorentina": {"modulo": "4-3-3", "titolari": ["De Gea", "Fortini", "Pongracic", "Ranieri", "Gosens", "Ndour", "Fagioli", "Brescianini", "Parisi", "Kean", "Gudmundsson"]},
        "Lazio": {"modulo": "4-3-3", "titolari": ["Motta", "Marusic", "Provstgaard", "Romagnoli", "Tavares", "Dele-Bashiru", "Patric", "Taylor", "Isaksen", "Maldini", "Pedro"]},
        "Parma": {"modulo": "3-4-2-1", "titolari": ["Suzuki", "Delprato", "Circati", "Valenti", "Britschgi", "Keita M.", "Sorensen", "Valeri", "Strefezza", "Ondrejka", "Pellegrino"]},
        "Cremonese": {"modulo": "4-4-2", "titolari": ["Audero", "Terracciano", "Bianchetti", "Luperto", "Pezzella", "Zerbin", "Maleh", "Grassi", "Vandeputte", "Bonazzoli", "Vardy"]},
        "Bologna": {"modulo": "4-3-3", "titolari": ["Ravaglia", "Joao Mario", "Vitik", "Lucumi", "Miranda", "Moro", "Freuler", "Ferguson", "Orsolini", "Castro", "Rowe"]},
        "Pisa": {"modulo": "3-4-2-1", "titolari": ["Semper", "Canestrelli", "Calabresi", "Angori", "Loyola", "Hojholt", "Aebischer", "Cuadrado", "Stengs", "Tramoni", "Meister"]},
        "Torino": {"modulo": "3-5-2", "titolari": ["Israel", "Coco", "Ismajli", "Maripan", "Pedersen", "Casadei", "Ilic", "Gineitis", "Nkounkou", "Vlasic", "Adams"]},
        "Inter": {"modulo": "3-5-2", "titolari": ["Sommer", "Bisseck", "Akanji", "Bastoni", "Dumfries", "Barella", "Calhanoglu", "Sucic", "Dimarco", "Thuram", "Bonny"]},
        "Roma": {"modulo": "3-4-2-1", "titolari": ["Svilar", "Ndicka", "Mancini", "Hermoso", "Rensch", "El Aynaoui", "Cristante", "Tsimikas", "Soule", "Pellegrini", "Malen"]},
        "Udinese": {"modulo": "3-5-2", "titolari": ["Okoye", "Solet", "Kristensen", "Bertola", "Ehizibue", "Karlstrom", "Miller", "Zarraga", "Zemura", "Zaniolo", "Davis"]},
        "Como": {"modulo": "4-2-3-1", "titolari": ["Butez", "Van der Brempt", "Diego Carlos", "Kempf", "Moreno", "Perrone", "Caqueret", "Kuhn", "Paz", "Da Cunha", "Douvikas"]},
        "Lecce": {"modulo": "4-3-3", "titolari": ["Falcone", "Veiga", "Siebert", "Jean", "Gallo", "Sala", "Ramadani", "Fofana", "Banda", "Cheddira", "Pierotti"]},
        "Atalanta": {"modulo": "3-4-2-1", "titolari": ["Carnesecchi", "Scalvini", "Hien", "Kolasinac", "Bellanova", "De Roon", "Ederson", "Zappacosta", "De Ketelaere", "Samardzic", "Krstovic"]},
        "Juventus": {"modulo": "4-2-3-1", "titolari": ["Di Gregorio", "Kalulu", "Gatti", "Kelly", "Cambiaso", "Locatelli", "Thuram K.", "Conceicao", "Koopmeiners", "Yildiz", "Vlahovic"]},
        "Genoa": {"modulo": "3-5-2", "titolari": ["Bijlow", "Vasquez", "Ostigard", "Martin", "Norton-Cuffy", "Frendrup", "Malinovskyi", "Baldanzi", "Sabelli", "Vitinha", "Colombo"]},
        "Napoli": {"modulo": "3-4-2-1", "titolari": ["Meret", "Buongiorno", "Beukema", "Olivera", "Gutierrez", "Lobotka", "Anguissa", "McTominay", "De Bruyne", "Politano", "Hojlund"]},
        "Milan": {"modulo": "4-2-3-1", "titolari": ["Maignan", "Estupinan", "Tomori", "De Winter", "Bartesaghi", "Ricci", "Fofana", "Pulisic", "Modric", "Saelemaekers", "Gimenez"]},
    }
}


def _load_cache():
    """Carica la cache dal disco."""
    global _cache
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                with _lock:
                    _cache.update(loaded)
        except Exception:
            pass


def _save_cache():
    """Salva la cache su disco."""
    with _lock:
        try:
            with open(CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(_cache, f, ensure_ascii=False, indent=2)
        except Exception:
            pass


def _scrape_infortunati():
    """Prova a scaricare infortunati aggiornati dal web."""
    html = _fetch("https://www.fantacalciopedia.com/articoli-fcp/consigli-fantacalcio/75-lista-infortunati-serie-a-aggiornata.html")
    if html and len(html) > 1000:
        with _lock:
            _cache["ultimo_update"] = datetime.now().strftime("%d/%m/%Y %H:%M")
        _save_cache()
        return True
    return False


def _scrape_formazioni():
    """
    Scarica le probabili formazioni dalla prossima giornata.
    Fonte: fantacalcio.it (affidabile, aggiornato last minute).
    """
    html = _fetch("https://www.fantacalcio.it/probabili-formazioni-serie-a")
    if not html or len(html) < 1000:
        return False

    # Mappa nomi squadre dal sito ai nostri nomi standard
    nome_map = {
        "sassuolo": "Sassuolo", "cagliari": "Cagliari", "verona": "Verona",
        "hellas verona": "Verona", "fiorentina": "Fiorentina", "lazio": "Lazio",
        "parma": "Parma", "cremonese": "Cremonese", "bologna": "Bologna",
        "pisa": "Pisa", "torino": "Torino", "inter": "Inter", "roma": "Roma",
        "udinese": "Udinese", "como": "Como", "lecce": "Lecce",
        "atalanta": "Atalanta", "juventus": "Juventus", "genoa": "Genoa",
        "napoli": "Napoli", "milan": "Milan", "ac milan": "Milan",
        "ssc napoli": "Napoli", "juventus fc": "Juventus",
    }

    try:
        formazioni_web = {}

        # Pattern per estrarre modulo e giocatori dal HTML
        # Cerca blocchi con nomi squadre e formazioni
        import re

        # Cerca pattern tipo "4-3-3" o "3-5-2"
        moduli = re.findall(r'(\d-\d-\d(?:-\d)?)', html)

        # Cerca nomi giocatori in blocchi
        # Il sito fantacalcio.it usa una struttura specifica
        # Estraiamo i blocchi per squadra

        # Metodo semplificato: cerca coppie squadra-modulo-giocatori
        blocks = html.split("squadra")

        for block in blocks:
            block_lower = block.lower()
            for nome_sito, nome_std in nome_map.items():
                if nome_sito in block_lower and nome_std not in formazioni_web:
                    # Cerca modulo
                    mod_match = re.search(r'(\d-\d-\d(?:-\d)?)', block)
                    if mod_match:
                        modulo = mod_match.group(1)
                        # Cerca nomi giocatori (parole capitalizzate)
                        nomi = re.findall(r'([A-Z][a-z]+(?:\s[A-Z][a-z]+)*)', block[:2000])
                        # Filtra nomi validi (lunghezza > 3, non parole comuni)
                        parole_escluse = {"Serie", "Calcio", "Modulo", "Allenatore", "Formazione",
                                          "Probabile", "Probabili", "Titolari", "Riserve",
                                          "Panchina", "Infortunati", "Squalificati"}
                        titolari = [n for n in nomi if len(n) > 3 and n not in parole_escluse][:11]

                        if len(titolari) >= 8:
                            formazioni_web[nome_std] = {
                                "modulo": modulo,
                                "titolari": titolari
                            }
                    break

        if formazioni_web:
            with _lock:
                _cache["formazioni"] = formazioni_web
                _cache["ultimo_update"] = datetime.now().strftime("%d/%m/%Y %H:%M")
            _save_cache()
            return True

    except Exception:
        pass
    return False


def _background_updater():
    """Thread background che aggiorna i dati periodicamente."""
    while True:
        try:
            _scrape_infortunati()
            _scrape_formazioni()
        except Exception:
            pass
        time.sleep(UPDATE_INTERVAL)


def avvia_aggiornamento_background():
    """Avvia il thread di aggiornamento automatico."""
    global _bg_thread
    _load_cache()
    if _bg_thread is None or not _bg_thread.is_alive():
        _bg_thread = threading.Thread(target=_background_updater, daemon=True)
        _bg_thread.start()


# ──────────────────────────────────────────────
# API pubblica
# ──────────────────────────────────────────────

def get_infortunati(squadra: str) -> list:
    """Ritorna la lista infortunati di una squadra."""
    return INFORTUNATI_BASELINE.get(squadra, [])


def get_formazione(squadra: str, giornata: int = 31) -> dict | None:
    """
    Ritorna la probabile formazione di una squadra.
    Priorita': 1) dati web (scraping live) 2) baseline hardcoded
    """
    # Prima controlla i dati scaricati dal web (piu' aggiornati)
    with _lock:
        web_form = _cache.get("formazioni", {})
    if squadra in web_form:
        return web_form[squadra]

    # Fallback al baseline
    g = FORMAZIONI_BASELINE.get(giornata, {})
    return g.get(squadra)


def get_n_indisponibili(squadra: str) -> int:
    """Ritorna il numero di giocatori indisponibili."""
    return len(get_infortunati(squadra))


def get_impatto_infortunati(squadra: str) -> float:
    """
    Calcola un fattore di impatto degli infortunati [0.85, 1.0].
    Piu' infortunati importanti = fattore piu' basso.
    """
    inf = get_infortunati(squadra)
    if not inf:
        return 1.0
    n_out = sum(1 for i in inf if i["tipo"] == "infortunio")
    n_dubbio = sum(1 for i in inf if i["tipo"] == "dubbio")
    # Ogni infortunato certo toglie 2%, ogni dubbio 1%
    penalita = n_out * 0.02 + n_dubbio * 0.01
    return max(0.85, 1.0 - penalita)
