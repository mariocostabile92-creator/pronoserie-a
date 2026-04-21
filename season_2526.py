"""
season_2526.py
Dati reali della stagione Serie A 2025-2026.
Classifica, xG, calendario giornate 31-38.
Aggiornata alla 30a giornata (marzo 2026).
"""

# 20 squadre partecipanti Serie A 2025-2026
SQUADRE_2526 = [
    "Inter", "Milan", "Napoli", "Como", "Juventus", "Roma",
    "Atalanta", "Lazio", "Bologna", "Sassuolo", "Udinese",
    "Parma", "Genoa", "Torino", "Cagliari", "Fiorentina",
    "Cremonese", "Lecce", "Verona", "Pisa"
]

# Classifica reale dopo la 30a giornata
CLASSIFICA_REALE_30G = [
    {"Squadra": "Inter",       "Punti": 69, "G": 30, "V": 22, "N": 3,  "P": 5,  "GF": 66, "GS": 24, "DR": 42},
    {"Squadra": "Milan",       "Punti": 63, "G": 30, "V": 18, "N": 9,  "P": 3,  "GF": 47, "GS": 23, "DR": 24},
    {"Squadra": "Napoli",      "Punti": 62, "G": 30, "V": 19, "N": 5,  "P": 6,  "GF": 46, "GS": 30, "DR": 16},
    {"Squadra": "Como",        "Punti": 57, "G": 30, "V": 16, "N": 9,  "P": 5,  "GF": 53, "GS": 22, "DR": 31},
    {"Squadra": "Juventus",    "Punti": 54, "G": 30, "V": 15, "N": 9,  "P": 6,  "GF": 52, "GS": 29, "DR": 23},
    {"Squadra": "Roma",        "Punti": 54, "G": 30, "V": 17, "N": 3,  "P": 10, "GF": 40, "GS": 23, "DR": 17},
    {"Squadra": "Atalanta",    "Punti": 50, "G": 30, "V": 13, "N": 11, "P": 6,  "GF": 41, "GS": 27, "DR": 14},
    {"Squadra": "Lazio",       "Punti": 43, "G": 30, "V": 11, "N": 10, "P": 9,  "GF": 31, "GS": 28, "DR":  3},
    {"Squadra": "Bologna",     "Punti": 42, "G": 30, "V": 12, "N": 6,  "P": 12, "GF": 38, "GS": 36, "DR":  2},
    {"Squadra": "Sassuolo",    "Punti": 39, "G": 30, "V": 11, "N": 6,  "P": 13, "GF": 36, "GS": 40, "DR": -4},
    {"Squadra": "Udinese",     "Punti": 39, "G": 30, "V": 11, "N": 6,  "P": 13, "GF": 35, "GS": 42, "DR": -7},
    {"Squadra": "Parma",       "Punti": 34, "G": 30, "V": 8,  "N": 10, "P": 12, "GF": 21, "GS": 38, "DR":-17},
    {"Squadra": "Genoa",       "Punti": 33, "G": 30, "V": 8,  "N": 9,  "P": 13, "GF": 36, "GS": 42, "DR": -6},
    {"Squadra": "Torino",      "Punti": 33, "G": 30, "V": 9,  "N": 6,  "P": 15, "GF": 34, "GS": 53, "DR":-19},
    {"Squadra": "Cagliari",    "Punti": 30, "G": 30, "V": 7,  "N": 9,  "P": 14, "GF": 31, "GS": 42, "DR":-11},
    {"Squadra": "Fiorentina",  "Punti": 29, "G": 30, "V": 6,  "N": 11, "P": 13, "GF": 35, "GS": 44, "DR": -9},
    {"Squadra": "Cremonese",   "Punti": 27, "G": 30, "V": 6,  "N": 9,  "P": 15, "GF": 25, "GS": 44, "DR":-19},
    {"Squadra": "Lecce",       "Punti": 27, "G": 30, "V": 7,  "N": 6,  "P": 17, "GF": 21, "GS": 40, "DR":-19},
    {"Squadra": "Verona",      "Punti": 18, "G": 30, "V": 3,  "N": 9,  "P": 18, "GF": 22, "GS": 52, "DR":-30},
    {"Squadra": "Pisa",        "Punti": 18, "G": 30, "V": 2,  "N": 12, "P": 16, "GF": 23, "GS": 54, "DR":-31},
]

GIORNATA_ATTUALE = 30
GIORNATE_TOTALI = 38
GIORNATE_RIMANENTI = GIORNATE_TOTALI - GIORNATA_ATTUALE

# ──────────────────────────────────────────────
# Expected Goals (xG) stagione 2025-2026 (Understat, 30 giornate)
# xG = gol attesi creati, xGA = gol attesi subiti
# xG_pg = xG per partita, xGA_pg = xGA per partita
# ──────────────────────────────────────────────
XG_2526 = {
    "Inter":       {"xG": 72.03, "xGA": 25.25, "xG_pg": 2.40, "xGA_pg": 0.84},
    "Milan":       {"xG": 55.04, "xGA": 33.57, "xG_pg": 1.83, "xGA_pg": 1.12},
    "Napoli":      {"xG": 46.76, "xGA": 32.87, "xG_pg": 1.56, "xGA_pg": 1.10},
    "Como":        {"xG": 53.85, "xGA": 32.35, "xG_pg": 1.80, "xGA_pg": 1.08},
    "Juventus":    {"xG": 59.20, "xGA": 29.01, "xG_pg": 1.97, "xGA_pg": 0.97},
    "Roma":        {"xG": 46.13, "xGA": 36.00, "xG_pg": 1.54, "xGA_pg": 1.20},
    "Atalanta":    {"xG": 55.80, "xGA": 41.49, "xG_pg": 1.86, "xGA_pg": 1.38},
    "Lazio":       {"xG": 36.40, "xGA": 40.17, "xG_pg": 1.21, "xGA_pg": 1.34},
    "Bologna":     {"xG": 40.07, "xGA": 41.58, "xG_pg": 1.34, "xGA_pg": 1.39},
    "Sassuolo":    {"xG": 35.68, "xGA": 48.83, "xG_pg": 1.19, "xGA_pg": 1.63},
    "Udinese":     {"xG": 35.73, "xGA": 46.83, "xG_pg": 1.19, "xGA_pg": 1.56},
    "Parma":       {"xG": 29.85, "xGA": 48.48, "xG_pg": 1.00, "xGA_pg": 1.62},
    "Genoa":       {"xG": 38.98, "xGA": 43.40, "xG_pg": 1.30, "xGA_pg": 1.45},
    "Torino":      {"xG": 39.93, "xGA": 47.21, "xG_pg": 1.33, "xGA_pg": 1.57},
    "Cagliari":    {"xG": 30.27, "xGA": 49.38, "xG_pg": 1.01, "xGA_pg": 1.65},
    "Fiorentina":  {"xG": 45.52, "xGA": 45.92, "xG_pg": 1.52, "xGA_pg": 1.53},
    "Cremonese":   {"xG": 30.99, "xGA": 56.14, "xG_pg": 1.03, "xGA_pg": 1.87},
    "Lecce":       {"xG": 27.84, "xGA": 50.03, "xG_pg": 0.93, "xGA_pg": 1.67},
    "Verona":      {"xG": 30.84, "xGA": 41.94, "xG_pg": 1.03, "xGA_pg": 1.40},
    "Pisa":        {"xG": 34.26, "xGA": 54.72, "xG_pg": 1.14, "xGA_pg": 1.82},
}

# ──────────────────────────────────────────────
# Expected Goals (xG) - Fonte: Understat, stagione 2025/2026
# (EPL) - Aggiornato: 21/04/2026
# ──────────────────────────────────────────────
XG_PL = {
    "Arsenal": {"xG_pg": 2.006, "xGA_pg": 0.881},  # 33P
    "Aston Villa": {"xG_pg": 1.454, "xGA_pg": 1.505},  # 33P
    "Bournemouth": {"xG_pg": 1.775, "xGA_pg": 1.524},  # 33P
    "Brentford": {"xG_pg": 1.788, "xGA_pg": 1.434},  # 33P
    "Brighton": {"xG_pg": 1.481, "xGA_pg": 1.416},  # 33P
    "Burnley": {"xG_pg": 0.98, "xGA_pg": 2.159},  # 33P
    "Chelsea": {"xG_pg": 2.034, "xGA_pg": 1.46},  # 33P
    "Crystal Palace": {"xG_pg": 1.657, "xGA_pg": 1.462},  # 32P
    "Everton": {"xG_pg": 1.314, "xGA_pg": 1.538},  # 33P
    "Fulham": {"xG_pg": 1.309, "xGA_pg": 1.609},  # 33P
    "Leeds": {"xG_pg": 1.572, "xGA_pg": 1.44},  # 33P
    "Liverpool": {"xG_pg": 1.806, "xGA_pg": 1.35},  # 33P
    "Manchester City": {"xG_pg": 2.049, "xGA_pg": 1.205},  # 32P
    "Manchester United": {"xG_pg": 1.837, "xGA_pg": 1.339},  # 33P
    "Newcastle United": {"xG_pg": 1.594, "xGA_pg": 1.535},  # 33P
    "Nottingham Forest": {"xG_pg": 1.204, "xGA_pg": 1.657},  # 33P
    "Sunderland": {"xG_pg": 1.114, "xGA_pg": 1.638},  # 33P
    "Tottenham": {"xG_pg": 1.199, "xGA_pg": 1.545},  # 33P
    "West Ham": {"xG_pg": 1.274, "xGA_pg": 1.794},  # 33P
    "Wolverhampton Wanderers": {"xG_pg": 0.935, "xGA_pg": 1.858},  # 33P
    # Alias nomi corti (football-data.co.uk)
    "Man City":     {"xG_pg": 2.049, "xGA_pg": 1.205},
    "Man United":   {"xG_pg": 1.837, "xGA_pg": 1.339},
    "Newcastle":    {"xG_pg": 1.594, "xGA_pg": 1.535},
    "Nott. Forest": {"xG_pg": 1.204, "xGA_pg": 1.657},
    "Wolves":       {"xG_pg": 0.935, "xGA_pg": 1.858},
}

def get_xg_pl(team_name: str) -> dict:
    """Ritorna xG per partita di una squadra PL. Supporta nomi Understat e nomi corti."""
    return XG_PL.get(team_name)

def get_xg_media_pl() -> dict:
    """Media xG del campionato PL (esclude alias duplicati usando valori unici)."""
    # Evita di contare doppioni degli alias: usa solo valori distinti
    seen = set()
    valori_unici = []
    for v in XG_PL.values():
        chiave = (v["xG_pg"], v["xGA_pg"])
        if chiave not in seen:
            seen.add(chiave)
            valori_unici.append(v)
    n = len(valori_unici)
    if n == 0:
        return {"xG_pg_medio": 1.35, "xGA_pg_medio": 1.35}
    return {
        "xG_pg_medio": round(sum(v["xG_pg"] for v in valori_unici) / n, 2),
        "xGA_pg_medio": round(sum(v["xGA_pg"] for v in valori_unici) / n, 2),
    }

# ──────────────────────────────────────────────
# Expected Goals (xG) - Fonte: Understat, stagione 2025/2026
# (La_liga) - Aggiornato: 21/04/2026
# ──────────────────────────────────────────────
XG_LALIGA = {
    "Alaves": {"xG_pg": 1.404, "xGA_pg": 1.472},  # 31P
    "Athletic Club": {"xG_pg": 1.52, "xGA_pg": 1.227},  # 31P
    "Atletico Madrid": {"xG_pg": 1.744, "xGA_pg": 1.298},  # 31P
    "Barcelona": {"xG_pg": 2.888, "xGA_pg": 1.4},  # 31P
    "Celta Vigo": {"xG_pg": 1.396, "xGA_pg": 1.38},  # 31P
    "Elche": {"xG_pg": 1.246, "xGA_pg": 1.957},  # 31P
    "Espanyol": {"xG_pg": 1.433, "xGA_pg": 1.689},  # 31P
    "Getafe": {"xG_pg": 0.91, "xGA_pg": 1.321},  # 31P
    "Girona": {"xG_pg": 1.314, "xGA_pg": 1.787},  # 31P
    "Levante": {"xG_pg": 1.495, "xGA_pg": 1.876},  # 31P
    "Mallorca": {"xG_pg": 1.221, "xGA_pg": 1.799},  # 31P
    "Osasuna": {"xG_pg": 1.326, "xGA_pg": 1.37},  # 31P
    "Rayo Vallecano": {"xG_pg": 1.512, "xGA_pg": 1.499},  # 31P
    "Real Betis": {"xG_pg": 1.63, "xGA_pg": 1.27},  # 31P
    "Real Madrid": {"xG_pg": 2.311, "xGA_pg": 1.168},  # 31P
    "Real Oviedo": {"xG_pg": 1.11, "xGA_pg": 1.744},  # 31P
    "Real Sociedad": {"xG_pg": 1.596, "xGA_pg": 1.523},  # 31P
    "Sevilla": {"xG_pg": 1.083, "xGA_pg": 1.721},  # 31P
    "Valencia": {"xG_pg": 1.394, "xGA_pg": 1.453},  # 31P
    "Villarreal": {"xG_pg": 1.784, "xGA_pg": 1.365},  # 31P
    # Alias nomi corti
    "Oviedo":           {"xG_pg": 1.11,  "xGA_pg": 1.744},
    "Atletico":         {"xG_pg": 1.744, "xGA_pg": 1.298},
}

def get_xg_laliga(team_name: str) -> dict:
    """Ritorna xG per partita di una squadra La Liga. Supporta nomi Understat e alias."""
    return XG_LALIGA.get(team_name)

def get_xg_media_laliga() -> dict:
    """Media xG del campionato La Liga (esclude alias duplicati)."""
    seen = set()
    valori_unici = []
    for v in XG_LALIGA.values():
        chiave = (v["xG_pg"], v["xGA_pg"])
        if chiave not in seen:
            seen.add(chiave)
            valori_unici.append(v)
    n = len(valori_unici)
    if n == 0:
        return {"xG_pg_medio": 1.35, "xGA_pg_medio": 1.35}
    return {
        "xG_pg_medio": round(sum(v["xG_pg"] for v in valori_unici) / n, 2),
        "xGA_pg_medio": round(sum(v["xGA_pg"] for v in valori_unici) / n, 2),
    }

# ──────────────────────────────────────────────
# Expected Goals (xG) - Fonte: Understat, stagione 2025/2026
# (Bundesliga) - Aggiornato: 21/04/2026
# ──────────────────────────────────────────────
XG_BL = {
    "Augsburg": {"xG_pg": 1.419, "xGA_pg": 2.012},  # 30P
    "Bayer Leverkusen": {"xG_pg": 2.142, "xGA_pg": 1.363},  # 30P
    "Bayern Munich": {"xG_pg": 3.195, "xGA_pg": 1.159},  # 30P
    "Borussia Dortmund": {"xG_pg": 1.932, "xGA_pg": 1.271},  # 30P
    "Borussia M.Gladbach": {"xG_pg": 1.388, "xGA_pg": 1.666},  # 30P
    "Eintracht Frankfurt": {"xG_pg": 1.508, "xGA_pg": 1.601},  # 30P
    "FC Cologne": {"xG_pg": 1.541, "xGA_pg": 1.808},  # 30P
    "FC Heidenheim": {"xG_pg": 1.341, "xGA_pg": 2.103},  # 30P
    "Freiburg": {"xG_pg": 1.518, "xGA_pg": 1.528},  # 30P
    "Hamburger SV": {"xG_pg": 1.269, "xGA_pg": 1.966},  # 30P
    "Hoffenheim": {"xG_pg": 1.834, "xGA_pg": 1.618},  # 30P
    "Mainz 05": {"xG_pg": 1.708, "xGA_pg": 1.748},  # 30P
    "RasenBallsport Leipzig": {"xG_pg": 2.177, "xGA_pg": 1.474},  # 30P
    "St. Pauli": {"xG_pg": 0.961, "xGA_pg": 1.848},  # 30P
    "Union Berlin": {"xG_pg": 1.392, "xGA_pg": 1.574},  # 30P
    "VfB Stuttgart": {"xG_pg": 1.978, "xGA_pg": 1.541},  # 30P
    "Werder Bremen": {"xG_pg": 1.286, "xGA_pg": 1.732},  # 30P
    "Wolfsburg": {"xG_pg": 1.418, "xGA_pg": 1.994},  # 30P
    # Alias nomi corti (football-data.co.uk)
    "1. FC Heidenheim":   {"xG_pg": 1.341, "xGA_pg": 2.103},
    "1. FC Koln":         {"xG_pg": 1.541, "xGA_pg": 1.808},
    "Monchengladbach":    {"xG_pg": 1.388, "xGA_pg": 1.666},
    "St Pauli":           {"xG_pg": 0.961, "xGA_pg": 1.848},
    "Mainz":              {"xG_pg": 1.708, "xGA_pg": 1.748},
    "RB Leipzig":         {"xG_pg": 2.177, "xGA_pg": 1.474},
    "Stuttgart":          {"xG_pg": 1.978, "xGA_pg": 1.541},
}

def get_xg_bl(team_name: str) -> dict:
    """Ritorna xG per partita di una squadra Bundesliga. Supporta nomi Understat e alias."""
    return XG_BL.get(team_name)

def get_xg_media_bl() -> dict:
    """Media xG del campionato Bundesliga (esclude alias duplicati)."""
    seen = set()
    valori_unici = []
    for v in XG_BL.values():
        chiave = (v["xG_pg"], v["xGA_pg"])
        if chiave not in seen:
            seen.add(chiave)
            valori_unici.append(v)
    n = len(valori_unici)
    if n == 0:
        return {"xG_pg_medio": 1.5, "xGA_pg_medio": 1.5}
    return {
        "xG_pg_medio": round(sum(v["xG_pg"] for v in valori_unici) / n, 2),
        "xGA_pg_medio": round(sum(v["xGA_pg"] for v in valori_unici) / n, 2),
    }

# ──────────────────────────────────────────────
# Expected Goals (xG) - Fonte: Understat, stagione 2025/2026
# (Ligue_1) - Aggiornato: 21/04/2026
# ──────────────────────────────────────────────
XG_L1 = {
    "Angers": {"xG_pg": 0.948, "xGA_pg": 1.683},  # 30P
    "Auxerre": {"xG_pg": 1.181, "xGA_pg": 1.414},  # 30P
    "Brest": {"xG_pg": 1.386, "xGA_pg": 1.578},  # 29P
    "Le Havre": {"xG_pg": 1.106, "xGA_pg": 1.654},  # 30P
    "Lens": {"xG_pg": 2.199, "xGA_pg": 1.317},  # 29P
    "Lille": {"xG_pg": 1.73, "xGA_pg": 1.208},  # 30P
    "Lorient": {"xG_pg": 1.407, "xGA_pg": 1.529},  # 30P
    "Lyon": {"xG_pg": 1.588, "xGA_pg": 1.405},  # 30P
    "Marseille": {"xG_pg": 2.004, "xGA_pg": 1.392},  # 30P
    "Metz": {"xG_pg": 0.966, "xGA_pg": 1.927},  # 30P
    "Monaco": {"xG_pg": 1.89, "xGA_pg": 1.513},  # 30P
    "Nantes": {"xG_pg": 1.052, "xGA_pg": 1.609},  # 29P
    "Nice": {"xG_pg": 1.359, "xGA_pg": 1.822},  # 30P
    "Paris FC": {"xG_pg": 1.394, "xGA_pg": 1.723},  # 30P
    "Paris Saint Germain": {"xG_pg": 2.285, "xGA_pg": 0.899},  # 28P
    "Rennes": {"xG_pg": 1.604, "xGA_pg": 1.651},  # 30P
    "Strasbourg": {"xG_pg": 1.681, "xGA_pg": 1.331},  # 29P
    "Toulouse": {"xG_pg": 1.353, "xGA_pg": 1.366},  # 30P
    # Alias nomi alternativi
    "Stade Brestois 29":  {"xG_pg": 1.386, "xGA_pg": 1.578},
    "PSG":                {"xG_pg": 2.285, "xGA_pg": 0.899},
}

def get_xg_l1(team_name: str) -> dict:
    """Ritorna xG per partita di una squadra Ligue 1. Supporta nomi Understat e alias."""
    return XG_L1.get(team_name)

def get_xg_media_l1() -> dict:
    """Media xG del campionato Ligue 1 (esclude alias duplicati)."""
    seen = set()
    valori_unici = []
    for v in XG_L1.values():
        chiave = (v["xG_pg"], v["xGA_pg"])
        if chiave not in seen:
            seen.add(chiave)
            valori_unici.append(v)
    n = len(valori_unici)
    if n == 0:
        return {"xG_pg_medio": 1.35, "xGA_pg_medio": 1.35}
    return {
        "xG_pg_medio": round(sum(v["xG_pg"] for v in valori_unici) / n, 2),
        "xGA_pg_medio": round(sum(v["xGA_pg"] for v in valori_unici) / n, 2),
    }

# ──────────────────────────────────────────────
# Calendario ufficiale giornate 31-38
# Fonte: legaseriea.it + transfermarkt.it
# ──────────────────────────────────────────────
CALENDARIO_31_38 = {
    31: {
        "data": "4-6 aprile 2026",
        "partite": [
            ("Sassuolo", "Cagliari"), ("Verona", "Fiorentina"), ("Lazio", "Parma"),
            ("Cremonese", "Bologna"), ("Pisa", "Torino"), ("Inter", "Roma"),
            ("Udinese", "Como"), ("Lecce", "Atalanta"), ("Juventus", "Genoa"),
            ("Napoli", "Milan"),
        ]
    },
    32: {
        "data": "10-13 aprile 2026",
        "partite": [
            ("Roma", "Pisa"), ("Cagliari", "Cremonese"), ("Torino", "Verona"),
            ("Milan", "Udinese"), ("Atalanta", "Juventus"), ("Genoa", "Sassuolo"),
            ("Parma", "Napoli"), ("Bologna", "Lecce"), ("Como", "Inter"),
            ("Fiorentina", "Lazio"),
        ]
    },
    33: {
        "data": "17-20 aprile 2026",
        "partite": [
            ("Sassuolo", "Como"), ("Inter", "Cagliari"), ("Udinese", "Parma"),
            ("Napoli", "Lazio"), ("Roma", "Atalanta"), ("Cremonese", "Torino"),
            ("Verona", "Milan"), ("Pisa", "Genoa"), ("Juventus", "Bologna"),
            ("Lecce", "Fiorentina"),
        ]
    },
    34: {
        "data": "24-27 aprile 2026",
        "partite": [
            ("Napoli", "Cremonese"), ("Parma", "Pisa"), ("Bologna", "Roma"),
            ("Verona", "Lecce"), ("Fiorentina", "Sassuolo"), ("Genoa", "Como"),
            ("Torino", "Inter"), ("Milan", "Juventus"), ("Cagliari", "Atalanta"),
            ("Lazio", "Udinese"),
        ]
    },
    35: {
        "data": "2-4 maggio 2026",
        "partite": [
            ("Atalanta", "Genoa"), ("Bologna", "Cagliari"), ("Como", "Napoli"),
            ("Cremonese", "Lazio"), ("Inter", "Parma"), ("Juventus", "Verona"),
            ("Pisa", "Lecce"), ("Roma", "Fiorentina"), ("Sassuolo", "Milan"),
            ("Udinese", "Torino"),
        ]
    },
    36: {
        "data": "8-10 maggio 2026",
        "partite": [
            ("Cagliari", "Udinese"), ("Cremonese", "Pisa"), ("Fiorentina", "Genoa"),
            ("Lazio", "Inter"), ("Lecce", "Juventus"), ("Milan", "Atalanta"),
            ("Napoli", "Bologna"), ("Parma", "Roma"), ("Torino", "Sassuolo"),
            ("Verona", "Como"),
        ]
    },
    37: {
        "data": "15-17 maggio 2026",
        "partite": [
            ("Atalanta", "Bologna"), ("Cagliari", "Torino"), ("Como", "Parma"),
            ("Genoa", "Milan"), ("Inter", "Verona"), ("Juventus", "Fiorentina"),
            ("Pisa", "Napoli"), ("Roma", "Lazio"), ("Sassuolo", "Lecce"),
            ("Udinese", "Cremonese"),
        ]
    },
    38: {
        "data": "24 maggio 2026",
        "partite": [
            ("Bologna", "Inter"), ("Cremonese", "Como"), ("Fiorentina", "Atalanta"),
            ("Lazio", "Pisa"), ("Lecce", "Genoa"), ("Milan", "Cagliari"),
            ("Napoli", "Udinese"), ("Parma", "Sassuolo"), ("Torino", "Juventus"),
            ("Verona", "Roma"),
        ]
    },
}


def get_classifica_reale():
    """Ritorna la classifica reale come lista ordinata per punti."""
    return sorted(CLASSIFICA_REALE_30G, key=lambda x: (-x["Punti"], -x["DR"], -x["GF"]))


def get_xg(squadra: str) -> dict | None:
    """Ritorna i dati xG della squadra."""
    return XG_2526.get(squadra)


def get_xg_media_campionato() -> dict:
    """Calcola la media xG del campionato."""
    vals = list(XG_2526.values())
    n = len(vals)
    return {
        "xG_pg_medio": sum(v["xG_pg"] for v in vals) / n,
        "xGA_pg_medio": sum(v["xGA_pg"] for v in vals) / n,
    }


def get_calendario_rimanente() -> dict:
    """Ritorna il calendario delle giornate 31-38."""
    return CALENDARIO_31_38


def genera_partite_rimanenti() -> list:
    """Ritorna tutte le partite rimanenti come lista piatta di tuple (home, away)."""
    tutte = []
    for g in range(31, 39):
        if g in CALENDARIO_31_38:
            tutte.extend(CALENDARIO_31_38[g]["partite"])
    return tutte


def get_risultati_stagione(df) -> list:
    """
    Estrae i risultati della stagione 2025-2026 dai dati CSV.
    Raggruppa per settimana (una giornata di Serie A si gioca su venerdi-lunedi).
    Ritorna lista di dict con giornata, data, partite e risultati.
    """
    import pandas as pd

    if df is None or len(df) == 0:
        return []

    # Filtra solo partite con squadre della stagione corrente
    mask = df["HomeTeam"].isin(SQUADRE_2526) & df["AwayTeam"].isin(SQUADRE_2526)
    stagione = df[mask].copy()

    # Filtra per date 2025-2026
    if "Date" not in stagione.columns:
        return []

    stagione = stagione.dropna(subset=["Date"])
    stagione = stagione[stagione["Date"] >= "2025-08-01"]
    stagione = stagione[stagione["Date"] <= "2026-06-01"]

    # Rimuovi duplicati
    stagione = stagione.drop_duplicates(subset=["Date", "HomeTeam", "AwayTeam"], keep="first")
    stagione = stagione.sort_values("Date").reset_index(drop=True)

    if len(stagione) == 0:
        return []

    # Raggruppa per settimana ISO (le giornate cadono nella stessa settimana)
    stagione["week"] = stagione["Date"].dt.isocalendar().week.astype(int)
    stagione["year"] = stagione["Date"].dt.year

    giornate = []
    g_num = 0
    for (year, week), gruppo in stagione.groupby(["year", "week"]):
        if len(gruppo) < 3:
            continue  # Salta settimane con poche partite (probabili turni infrasettimanali parziali)
        g_num += 1
        if g_num > 30:
            break

        data_str = ""
        try:
            data_str = gruppo["Date"].iloc[0].strftime("%d/%m/%Y")
        except Exception:
            pass

        risultati = []
        for _, m in gruppo.iterrows():
            risultati.append({
                "home": str(m.get("HomeTeam", "")),
                "away": str(m.get("AwayTeam", "")),
                "gol_home": int(m.get("FTHG", 0)),
                "gol_away": int(m.get("FTAG", 0)),
                "risultato": str(m.get("FTR", "")),
            })

        giornate.append({
            "giornata": g_num,
            "data": data_str,
            "risultati": risultati,
        })

    return giornate


def get_team_ou_tendency(team_name: str) -> dict:
    """
    Ritorna la tendenza Over/Under della squadra nella stagione corrente.
    Basato su gol reali (GF+GS dalla classifica).
    """
    for r in CLASSIFICA_REALE_30G:
        if r["Squadra"] == team_name:
            g = r["G"]
            if g == 0:
                return {"gol_pg": 2.6, "over_pct": 50}
            gol_pg = (r["GF"] + r["GS"]) / g
            # % partite con 3+ gol totali (stimata dalla media)
            over_pct = min(80, max(20, 50 + (gol_pg - 2.6) * 20))
            return {"gol_pg": round(gol_pg, 2), "over_pct": round(over_pct, 1)}
    return {"gol_pg": 2.6, "over_pct": 50}


def get_season_avg_goals() -> float:
    """Media gol per partita della stagione corrente (dalla classifica reale)."""
    tot_gol = sum(r["GF"] for r in CLASSIFICA_REALE_30G)
    tot_partite = sum(r["G"] for r in CLASSIFICA_REALE_30G) / 2  # Ogni partita conta 2 volte
    if tot_partite == 0:
        return 2.6
    return round(tot_gol / tot_partite, 2)
