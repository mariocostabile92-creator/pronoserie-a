"""
scrape_understat.py
Scarica i dati xG REALI da Understat.com per le 5 leghe top europee.

Usa l'endpoint AJAX di Understat:
    https://understat.com/getLeagueData/{league}/{season}

La risposta e' JSON gzip-compresso con struttura:
    {
        "teams": {
            "id": {
                "id": "...",
                "title": "Nome Squadra",
                "history": [
                    {"h_a": "h", "xG": 1.23, "xGA": 0.85, ...},
                    ...
                ]
            }
        },
        "players": {...},
        "dates": {...}
    }

Uso:
    python scrape_understat.py

Output:
    - Dizionari Python pronti per season_2526.py
    - File xg_understat_cache.json con dati grezzi (cache)
    - Aggiornamento automatico di season_2526.py

Fonte: https://understat.com
"""

import urllib.request
import urllib.error
import json
import gzip
import re
import os
from datetime import datetime

# ──────────────────────────────────────────────
# Configurazione leghe Understat
# Chiave = nome usato nell'URL Understat
# Valore = codice lega interno al progetto
# ──────────────────────────────────────────────
UNDERSTAT_LEAGUES = {
    "EPL":        "E0",   # Premier League
    "La_liga":    "SP1",  # La Liga
    "Bundesliga": "D1",   # Bundesliga
    "Ligue_1":    "F1",   # Ligue 1
    "Serie_A":    "I1",   # Serie A (verifica/aggiornamento)
}

# Anno di inizio stagione (2025 = stagione 2025-26)
SEASON = 2025

# File di cache per salvare i risultati dello scraping
CACHE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "xg_understat_cache.json")

# File season da aggiornare
SEASON_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "season_2526.py")


def _fetch_league_data(understat_name: str, season: int) -> dict | None:
    """
    Scarica i dati JSON gzip-compressi dall'endpoint AJAX di Understat.

    URL: https://understat.com/getLeagueData/{league}/{season}

    Ritorna il dict con chiavi 'teams', 'players', 'dates', oppure None.
    """
    url = f"https://understat.com/getLeagueData/{understat_name}/{season}"
    print(f"  URL: {url}")

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "en-US,en;q=0.9",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": f"https://understat.com/league/{understat_name}/{season}",
    }

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw_bytes = resp.read()

        # Decomprime la risposta gzip
        try:
            decompressed = gzip.decompress(raw_bytes)
        except OSError:
            # Non e' gzip, usa i byte grezzi
            decompressed = raw_bytes

        text = decompressed.decode("utf-8", errors="replace")
        data = json.loads(text)
        return data

    except urllib.error.HTTPError as e:
        print(f"  [ERRORE HTTP {e.code}] {url}")
        return None
    except urllib.error.URLError as e:
        print(f"  [ERRORE URL] {e.reason}")
        return None
    except json.JSONDecodeError as e:
        print(f"  [ERRORE JSON] {e}")
        return None
    except Exception as e:
        print(f"  [ERRORE] {e}")
        return None


def _calcola_xg_per_squadra(teams_data: dict) -> dict:
    """
    Calcola xG/pg e xGA/pg per ogni squadra, separati per casa e trasferta.

    teams_data: dict {id: {"title": nome, "history": [partite]}}
    Ogni partita ha: h_a ("h"=casa, "a"=trasferta), xG, xGA, scored, missed, etc.

    Ritorna: {nome_squadra: {
        xG_pg: float,         # xG medio per partita (tutte)
        xGA_pg: float,        # xGA medio per partita (tutte)
        xG_home_pg: float,    # xG medio nelle partite in casa
        xGA_home_pg: float,   # xGA medio nelle partite in casa
        xG_away_pg: float,    # xG medio nelle partite in trasferta
        xGA_away_pg: float,   # xGA medio nelle partite in trasferta
        n_home: int,          # partite giocate in casa
        n_away: int,          # partite giocate in trasferta
        n_tot: int,           # partite totali
    }}
    """
    risultato = {}

    for team_id, team_info in teams_data.items():
        nome = team_info.get("title", f"Team_{team_id}")
        history = team_info.get("history", [])

        if not history:
            continue

        # Separa partite casa ('h') e trasferta ('a')
        home_games = [m for m in history if m.get("h_a") == "h"]
        away_games = [m for m in history if m.get("h_a") == "a"]

        def media_campo(lst, campo):
            """Calcola la media di un campo numerico in una lista di partite."""
            valori = []
            for m in lst:
                v = m.get(campo)
                if v is not None:
                    try:
                        valori.append(float(v))
                    except (ValueError, TypeError):
                        pass
            return round(sum(valori) / len(valori), 3) if valori else 0.0

        n_home = len(home_games)
        n_away = len(away_games)
        n_tot = n_home + n_away

        if n_tot == 0:
            continue

        # xG creati: 'xG' = expected goals for (opportunita' create dalla squadra)
        # xGA subiti: 'xGA' = expected goals against (opportunita' create dagli avversari)
        xg_home_pg = media_campo(home_games, "xG")      # xG creati in casa
        xga_home_pg = media_campo(home_games, "xGA")    # xGA subiti in casa
        xg_away_pg = media_campo(away_games, "xG")      # xG creati in trasferta
        xga_away_pg = media_campo(away_games, "xGA")    # xGA subiti in trasferta

        # Media globale pesata per numero di partite
        xg_pg = round((xg_home_pg * n_home + xg_away_pg * n_away) / n_tot, 3)
        xga_pg = round((xga_home_pg * n_home + xga_away_pg * n_away) / n_tot, 3)

        risultato[nome] = {
            "xG_pg": xg_pg,
            "xGA_pg": xga_pg,
            "xG_home_pg": xg_home_pg,
            "xGA_home_pg": xga_home_pg,
            "xG_away_pg": xg_away_pg,
            "xGA_away_pg": xga_away_pg,
            "n_home": n_home,
            "n_away": n_away,
            "n_tot": n_tot,
        }

    return risultato


def scarica_xg_lega(understat_name: str, season: int = SEASON) -> dict | None:
    """
    Scarica e processa i dati xG per una lega da Understat.

    Args:
        understat_name: nome lega su Understat (es. 'EPL', 'La_liga')
        season: anno inizio stagione (es. 2025 per stagione 2025-26)

    Returns:
        Dizionario {nome_squadra: {xG_pg, xGA_pg, ...}} oppure None in caso di errore.
    """
    print(f"  Scarico {understat_name} stagione {season}/{season + 1}...")

    data = _fetch_league_data(understat_name, season)
    if not data:
        return None

    # La struttura e': {"teams": {...}, "players": {...}, "dates": {...}}
    teams_data = data.get("teams")
    if not teams_data:
        print(f"  [ERRORE] Chiave 'teams' non trovata. Chiavi disponibili: {list(data.keys())}")
        return None

    n_squadre = len(teams_data)
    print(f"  [OK] Trovate {n_squadre} squadre")

    # Calcola xG per squadra separati home/away
    xg_dict = _calcola_xg_per_squadra(teams_data)
    print(f"  [OK] Processate {len(xg_dict)} squadre con dati validi")

    # Mostra alcune statistiche di verifica
    if xg_dict:
        # Squadra con piu' xG
        top_atk = max(xg_dict.items(), key=lambda x: x[1]["xG_pg"])
        top_def = min(xg_dict.items(), key=lambda x: x[1]["xGA_pg"])
        print(f"  Miglior attacco xG: {top_atk[0]} ({top_atk[1]['xG_pg']} xG/pg)")
        print(f"  Miglior difesa xGA: {top_def[0]} ({top_def[1]['xGA_pg']} xGA/pg)")

    return xg_dict


def stampa_dizionario_python(nome_var: str, xg_dict: dict, commento: str = ""):
    """
    Stampa il dizionario xG in formato Python pronto per incollare in season_2526.py.
    """
    print(f"\n# {'─' * 58}")
    if commento:
        print(f"# {commento}")
    print(f"# Aggiornato: {datetime.now().strftime('%d/%m/%Y')}")
    print(f"{nome_var} = {{")
    for squadra in sorted(xg_dict.keys()):
        dati = xg_dict[squadra]
        xg = dati["xG_pg"]
        xga = dati["xGA_pg"]
        n = dati.get("n_tot", 0)
        print(f'    "{squadra}": {{"xG_pg": {xg}, "xGA_pg": {xga}}},  # {n}P')
    print("}")


def _genera_blocco_python(nome_var: str, xg_dict: dict, understat_name: str) -> str:
    """
    Genera il testo Python completo per un dizionario xG, con commenti.
    """
    righe = []
    data_oggi = datetime.now().strftime("%d/%m/%Y")
    righe.append(f"# {'─' * 46}")
    righe.append(
        f"# Expected Goals (xG) - Fonte: Understat, stagione {SEASON}/{SEASON + 1}"
    )
    righe.append(f"# ({understat_name}) - Aggiornato: {data_oggi}")
    righe.append(f"# {'─' * 46}")
    righe.append(f"{nome_var} = {{")
    for squadra in sorted(xg_dict.keys()):
        dati = xg_dict[squadra]
        xg = dati["xG_pg"]
        xga = dati["xGA_pg"]
        n = dati.get("n_tot", 0)
        righe.append(f'    "{squadra}": {{"xG_pg": {xg}, "xGA_pg": {xga}}},  # {n}P')
    righe.append("}")
    return "\n".join(righe)


def aggiorna_season_2526(tutti_i_dati: dict) -> bool:
    """
    Aggiorna automaticamente season_2526.py con i dati xG scaricati da Understat.
    Sostituisce i blocchi XG_PL, XG_LALIGA, XG_BL, XG_L1.
    XG_2526 (Serie A) viene aggiornato solo se presente nei dati scaricati.

    Usa regex multi-riga per trovare e sostituire ciascun dizionario.

    Returns: True se il file e' stato modificato, False altrimenti.
    """
    if not os.path.exists(SEASON_FILE):
        print(f"  [ERRORE] {SEASON_FILE} non trovato!")
        return False

    with open(SEASON_FILE, "r", encoding="utf-8") as f:
        contenuto = f.read()

    # Mappa: nome variabile Python -> chiave Understat nei dati scaricati
    aggiornamenti = [
        ("XG_PL",     "EPL"),
        ("XG_LALIGA", "La_liga"),
        ("XG_BL",     "Bundesliga"),
        ("XG_L1",     "Ligue_1"),
        # Serie A: aggiorna solo se esplicitamente richiesto
        # ("XG_2526", "Serie_A"),
    ]

    modificato = False

    for nome_var, understat_key in aggiornamenti:
        if understat_key not in tutti_i_dati:
            print(f"  [SKIP] {nome_var}: dati {understat_key} non scaricati")
            continue

        xg_dict = tutti_i_dati[understat_key].get("squadre", {})
        if not xg_dict:
            print(f"  [SKIP] {nome_var}: dizionario vuoto")
            continue

        nuovo_blocco = _genera_blocco_python(nome_var, xg_dict, understat_key)

        # Pattern regex per trovare l'intero blocco del dizionario nel file
        # Cerca da qualsiasi riga di commento precedente fino alla chiusura }
        # Il dizionario e' delimitato da NOME_VAR = { ... }
        # Usiamo un pattern che cattura il blocco completo con commenti header
        pattern = (
            r'(?:# ─+\n(?:#[^\n]*\n)*)?'  # commenti opzionali prima
            rf'{re.escape(nome_var)}\s*=\s*\{{'  # apertura dizionario
            r'[^}]*(?:\{[^}]*\}[^}]*)*'          # contenuto (con sotto-dict)
            r'\}'                                  # chiusura
        )

        match = re.search(pattern, contenuto, re.DOTALL)
        if match:
            contenuto = contenuto[:match.start()] + nuovo_blocco + contenuto[match.end():]
            print(f"  [OK] {nome_var} aggiornato ({len(xg_dict)} squadre, Understat reale)")
            modificato = True
        else:
            # Fallback: cerca solo la definizione del dizionario senza commenti
            pattern2 = (
                rf'{re.escape(nome_var)}\s*=\s*\{{'
                r'[^}]*(?:\{[^}]*\}[^}]*)*'
                r'\}'
            )
            match2 = re.search(pattern2, contenuto, re.DOTALL)
            if match2:
                contenuto = contenuto[:match2.start()] + nuovo_blocco + contenuto[match2.end():]
                print(f"  [OK] {nome_var} aggiornato (fallback, {len(xg_dict)} squadre)")
                modificato = True
            else:
                print(f"  [ERRORE] {nome_var} non trovato in {SEASON_FILE}")

    if modificato:
        with open(SEASON_FILE, "w", encoding="utf-8") as f:
            f.write(contenuto)
        print(f"\n  [OK] {SEASON_FILE} aggiornato con successo!")
    else:
        print(f"\n  [INFO] Nessuna modifica applicata a season_2526.py")

    return modificato


def carica_cache() -> dict:
    """Carica i dati dalla cache JSON se esiste."""
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"  [ATTENZIONE] Cache corrotta o non leggibile: {e}")
    return {}


def salva_cache(dati: dict):
    """Salva i dati nella cache JSON per evitare download ripetuti."""
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(dati, f, indent=2, ensure_ascii=False)
        print(f"[OK] Cache salvata: {CACHE_FILE}")
    except Exception as e:
        print(f"[ERRORE] Impossibile salvare cache: {e}")


def main():
    """Funzione principale: scarica xG da Understat e aggiorna season_2526.py."""
    print("=" * 70)
    print("SCRAPER xG UNDERSTAT - Stagione 2025-2026")
    print(f"Data esecuzione: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print(f"Endpoint: https://understat.com/getLeagueData/{{league}}/{{season}}")
    print("=" * 70)

    tutti_i_dati = {}
    errori = []

    # Leghe da scaricare
    leghe = [
        ("EPL",        "XG_PL",     "Premier League"),
        ("La_liga",    "XG_LALIGA", "La Liga"),
        ("Bundesliga", "XG_BL",     "Bundesliga"),
        ("Ligue_1",    "XG_L1",     "Ligue 1"),
        ("Serie_A",    "XG_2526",   "Serie A (verifica)"),
    ]

    for understat_name, var_name, descr in leghe:
        print(f"\n{'─' * 50}")
        print(f"[{descr}] -> {var_name}")
        print(f"{'─' * 50}")

        xg_dict = scarica_xg_lega(understat_name, SEASON)

        if xg_dict:
            tutti_i_dati[understat_name] = {
                "var_name": var_name,
                "descrizione": descr,
                "squadre": xg_dict,
                "aggiornato": datetime.now().isoformat(),
                "n_squadre": len(xg_dict),
            }
            stampa_dizionario_python(
                var_name,
                xg_dict,
                f"Expected Goals (xG) {descr} - Fonte: Understat, stagione {SEASON}/{SEASON + 1}"
            )
        else:
            errori.append(understat_name)
            print(f"  [SKIP] Nessun dato per {understat_name}")

    # Salva cache
    print(f"\n{'=' * 70}")
    print("SALVATAGGIO CACHE")
    salva_cache(tutti_i_dati)

    # Aggiorna season_2526.py automaticamente
    # NOTA: l'aggiornamento automatico e' disabilitato per sicurezza.
    # Usa i dizionari stampati sopra per aggiornare manualmente season_2526.py,
    # oppure usa il modulo da auto_update.py che gestisce il processo in modo controllato.
    # if tutti_i_dati:
    #     print(f"\n{'=' * 70}")
    #     print("AGGIORNAMENTO season_2526.py")
    #     aggiorna_season_2526(tutti_i_dati)

    # Report finale
    print(f"\n{'=' * 70}")
    print("RIEPILOGO")
    print(f"  Leghe OK: {len(tutti_i_dati)}/{len(leghe)}")
    if errori:
        print(f"  Leghe con errori: {', '.join(errori)}")
    print(f"  Cache: {CACHE_FILE}")
    print("=" * 70)

    if errori:
        print(
            "\n[NOTA] Per le leghe con errori, i valori precedenti in season_2526.py"
            "\n       rimangono invariati. Riprova piu' tardi."
        )

    return len(errori) == 0


if __name__ == "__main__":
    ok = main()
    if not ok:
        import sys
        sys.exit(1)
