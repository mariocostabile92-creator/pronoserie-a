"""
league_mappings.py - Dizionari di mapping nomi squadre e team IDs per ogni campionato.
Estratto da api_server.py per separazione delle responsabilità.
"""

# Mapping nomi API Football -> nomi nostri (per ogni league)
PL_NOME_MAP = {
    "Manchester United": "Man United", "Manchester City": "Man City",
    "Newcastle United": "Newcastle", "Newcastle": "Newcastle",
    "AFC Bournemouth": "Bournemouth", "Bournemouth": "Bournemouth",
    "Wolverhampton Wanderers": "Wolves", "Wolves": "Wolves",
    "Nottingham Forest": "Nott. Forest",
    "Tottenham Hotspur": "Tottenham", "Tottenham": "Tottenham",
    "West Ham United": "West Ham", "West Ham": "West Ham",
    "Brighton and Hove Albion": "Brighton", "Brighton": "Brighton",
    "Crystal Palace": "Crystal Palace",
    "Arsenal": "Arsenal", "Liverpool": "Liverpool", "Chelsea": "Chelsea",
    "Aston Villa": "Aston Villa", "Fulham": "Fulham", "Everton": "Everton",
    "Brentford": "Brentford", "Burnley": "Burnley",
    "Leeds United": "Leeds", "Leeds": "Leeds",
    "Sunderland": "Sunderland",
}

PL_TEAM_IDS = {
    "Arsenal":42,"Aston Villa":66,"Bournemouth":35,"Brentford":55,"Brighton":51,
    "Burnley":44,"Chelsea":49,"Crystal Palace":52,"Everton":45,"Fulham":36,
    "Leeds":63,"Liverpool":40,"Man City":50,"Man United":33,"Newcastle":34,
    "Nott. Forest":65,"Sunderland":746,"Tottenham":47,"West Ham":48,"Wolves":39,
}

LL_NOME_MAP = {
    "FC Barcelona": "Barcelona", "Barcelona": "Barcelona",
    "Atletico Madrid": "Atletico Madrid", "Club Atletico de Madrid": "Atletico Madrid",
    "Athletic Club": "Athletic Club", "Athletic Bilbao": "Athletic Club",
    "Real Madrid": "Real Madrid",
    "Real Sociedad": "Real Sociedad",
    "Real Betis": "Real Betis",
    "Villarreal CF": "Villarreal", "Villarreal": "Villarreal",
    "Sevilla FC": "Sevilla", "Sevilla": "Sevilla",
    "Valencia CF": "Valencia", "Valencia": "Valencia",
    "RC Celta de Vigo": "Celta Vigo", "Celta Vigo": "Celta Vigo",
    "RCD Espanyol": "Espanyol", "Espanyol": "Espanyol",
    "Deportivo Alaves": "Alaves", "Alaves": "Alaves",
    "CA Osasuna": "Osasuna", "Osasuna": "Osasuna",
    "Getafe CF": "Getafe", "Getafe": "Getafe",
    "Girona FC": "Girona", "Girona": "Girona",
    "Rayo Vallecano": "Rayo Vallecano",
    "RCD Mallorca": "Mallorca", "Mallorca": "Mallorca",
    "Levante UD": "Levante", "Levante": "Levante",
    "Real Oviedo": "Oviedo", "Oviedo": "Oviedo",
    "Elche CF": "Elche", "Elche": "Elche",
}

LL_TEAM_IDS = {
    "Alaves":542,"Athletic Club":531,"Atletico Madrid":530,"Barcelona":529,
    "Celta Vigo":538,"Elche":797,"Espanyol":540,"Getafe":546,"Girona":547,
    "Levante":539,"Mallorca":798,"Osasuna":727,"Oviedo":718,
    "Rayo Vallecano":728,"Real Betis":543,"Real Madrid":541,
    "Real Sociedad":548,"Sevilla":536,"Valencia":532,"Villarreal":533,
}

BL_NOME_MAP = {
    "1. FC Heidenheim 1846": "Heidenheim", "1. FC Heidenheim": "Heidenheim",
    "1. FC Köln": "1. FC Koln", "FC Köln": "1. FC Koln",
    "1899 Hoffenheim": "Hoffenheim", "TSG Hoffenheim": "Hoffenheim",
    "Bayern München": "Bayern Munich", "FC Bayern München": "Bayern Munich",
    "Borussia Mönchengladbach": "Monchengladbach",
    "FC Augsburg": "Augsburg", "FC St. Pauli": "St Pauli",
    "FSV Mainz 05": "Mainz", "1. FSV Mainz 05": "Mainz",
    "SC Freiburg": "Freiburg", "VfB Stuttgart": "Stuttgart",
    "VfL Wolfsburg": "Wolfsburg",
    "Bayer Leverkusen": "Bayer Leverkusen", "Borussia Dortmund": "Borussia Dortmund",
    "Eintracht Frankfurt": "Eintracht Frankfurt", "RB Leipzig": "RB Leipzig",
    "Union Berlin": "Union Berlin", "Werder Bremen": "Werder Bremen",
    "Hamburger SV": "Hamburger SV",
}

BL_TEAM_IDS = {
    "Heidenheim":180,"1. FC Koln":192,"Hoffenheim":167,
    "Bayer Leverkusen":168,"Bayern Munich":157,"Borussia Dortmund":165,
    "Monchengladbach":163,"Eintracht Frankfurt":169,"Augsburg":170,
    "St Pauli":186,"Mainz":164,"Hamburger SV":175,"RB Leipzig":173,
    "Freiburg":160,"Union Berlin":182,"Stuttgart":172,"Wolfsburg":161,
    "Werder Bremen":162,
}

L1_NOME_MAP = {
    "Paris Saint-Germain": "Paris Saint Germain", "PSG": "Paris Saint Germain",
    "Olympique de Marseille": "Marseille", "Marseille": "Marseille",
    "Olympique Lyonnais": "Lyon", "Lyon": "Lyon",
    "AS Monaco": "Monaco", "Monaco": "Monaco",
    "LOSC Lille": "Lille", "Lille": "Lille",
    "Stade Rennais FC": "Rennes", "Rennes": "Rennes",
    "RC Lens": "Lens", "Lens": "Lens",
    "OGC Nice": "Nice", "Nice": "Nice",
    "FC Nantes": "Nantes", "Nantes": "Nantes",
    "Stade Brestois 29": "Stade Brestois 29", "Brest": "Stade Brestois 29",
    "RC Strasbourg": "Strasbourg", "Strasbourg": "Strasbourg",
    "Toulouse FC": "Toulouse", "Toulouse": "Toulouse",
    "Le Havre AC": "Le Havre", "Le Havre": "Le Havre",
    "AJ Auxerre": "Auxerre", "Auxerre": "Auxerre",
    "SCO Angers": "Angers", "Angers": "Angers",
    "FC Lorient": "Lorient", "Lorient": "Lorient",
    "FC Metz": "Metz", "Metz": "Metz",
    "Paris FC": "Paris FC",
}

L1_TEAM_IDS = {
    "Paris Saint Germain": 85,
    "Marseille": 81,
    "Lyon": 80,
    "Monaco": 91,
    "Lille": 79,
    "Rennes": 94,
    "Lens": 116,
    "Nice": 84,
    "Nantes": 83,
    "Stade Brestois 29": 130,
    "Strasbourg": 95,
    "Toulouse": 96,
    "Le Havre": 1074,
    "Auxerre": 110,
    "Angers": 76,
    "Lorient": 82,
    "Metz": 112,
    "Paris FC": 111,
}

WC_NOME_MAP = {
    "United States": "USA", "USA": "USA",
    "England": "Inghilterra", "France": "Francia",
    "Germany": "Germania", "Spain": "Spagna",
    "Brazil": "Brasile", "Argentina": "Argentina",
    "Netherlands": "Olanda", "Belgium": "Belgio",
    "Portugal": "Portogallo", "Croatia": "Croazia",
    "Switzerland": "Svizzera", "Sweden": "Svezia",
    "South Korea": "Corea del Sud", "Japan": "Giappone",
    "Mexico": "Messico", "Canada": "Canada",
    "Australia": "Australia", "Morocco": "Marocco",
    "Senegal": "Senegal", "Tunisia": "Tunisia",
    "Ivory Coast": "Costa d'Avorio", "Ghana": "Ghana",
    "Egypt": "Egitto", "Algeria": "Algeria",
    "South Africa": "Sudafrica", "Cape Verde Islands": "Capo Verde",
    "Congo DR": "Congo DR", "Cameroon": "Camerun",
    "Saudi Arabia": "Arabia Saudita", "Qatar": "Qatar",
    "Iran": "Iran", "Iraq": "Iraq",
    "Jordan": "Giordania", "Uzbekistan": "Uzbekistan",
    "New Zealand": "Nuova Zelanda", "Haiti": "Haiti",
    "Panama": "Panama", "Paraguay": "Paraguay",
    "Uruguay": "Uruguay", "Colombia": "Colombia",
    "Ecuador": "Ecuador", "Bolivia": "Bolivia",
    "Türkiye": "Turchia", "Austria": "Austria",
    "Norway": "Norvegia", "Scotland": "Scozia",
    "Czech Republic": "Rep. Ceca", "Curaçao": "Curacao",
    "Bosnia & Herzegovina": "Bosnia",
}

WC_TEAM_IDS = {
    "USA": 2384, "Messico": 16, "Canada": 1997,
    "Brasile": 6, "Argentina": 26, "Uruguay": 27,
    "Colombia": 1560, "Ecuador": 2285, "Paraguay": 28,
    "Francia": 2, "Inghilterra": 10, "Germania": 25,
    "Spagna": 9, "Portogallo": 27, "Olanda": 1118,
    "Belgio": 1, "Croazia": 3, "Svizzera": 15,
    "Svezia": 22, "Austria": 775, "Norvegia": 1090,
    "Scozia": 1569, "Rep. Ceca": 770, "Turchia": 3589,
    "Bosnia": 764, "Giappone": 2232, "Corea del Sud": 17,
    "Australia": 20, "Arabia Saudita": 23, "Qatar": 1569,
    "Iran": 22, "Iraq": 2378, "Giordania": 99,
    "Uzbekistan": 2385, "Nuova Zelanda": 1530,
    "Marocco": 31, "Senegal": 34, "Tunisia": 28,
    "Costa d'Avorio": 2282, "Ghana": 867, "Egitto": 3568,
    "Algeria": 1538, "Sudafrica": 1530, "Capo Verde": 1535,
    "Congo DR": 2286, "Haiti": 2380, "Panama": 2381,
    "Curacao": 2382,
}

# Mapping nomi API Football -> nostri nomi (Serie A)
FOOTBALL_NOME_MAP = {
    "FC Internazionale Milano": "Inter", "Inter Milan": "Inter", "Inter": "Inter",
    "AC Milan": "Milan", "Milan": "Milan",
    "SSC Napoli": "Napoli", "Napoli": "Napoli",
    "Como 1907": "Como", "Como": "Como",
    "Juventus FC": "Juventus", "Juventus": "Juventus",
    "AS Roma": "Roma", "Roma": "Roma",
    "Atalanta BC": "Atalanta", "Atalanta": "Atalanta",
    "SS Lazio": "Lazio", "Lazio": "Lazio",
    "Bologna FC 1909": "Bologna", "Bologna": "Bologna",
    "US Sassuolo Calcio": "Sassuolo", "Sassuolo": "Sassuolo",
    "Udinese Calcio": "Udinese", "Udinese": "Udinese",
    "Parma Calcio 1913": "Parma", "Parma": "Parma",
    "Genoa CFC": "Genoa", "Genoa": "Genoa",
    "Torino FC": "Torino", "Torino": "Torino",
    "Cagliari Calcio": "Cagliari", "Cagliari": "Cagliari",
    "ACF Fiorentina": "Fiorentina", "Fiorentina": "Fiorentina",
    "US Cremonese": "Cremonese", "Cremonese": "Cremonese",
    "US Lecce": "Lecce", "Lecce": "Lecce",
    "Hellas Verona FC": "Verona", "Hellas Verona": "Verona", "Verona": "Verona",
    "AC Pisa 1909": "Pisa", "Pisa": "Pisa",
}

# Team IDs per API Football (Serie A)
_TEAM_IDS = {
    "Inter":505,"Milan":489,"Napoli":492,"Como":895,"Juventus":496,
    "Roma":497,"Atalanta":499,"Lazio":487,"Bologna":500,"Sassuolo":488,
    "Udinese":494,"Parma":523,"Genoa":495,"Torino":503,"Cagliari":490,
    "Fiorentina":502,"Cremonese":520,"Lecce":867,"Verona":504,"Pisa":801,
}

_RUOLO_MAP = {"Goalkeeper":"P","Defender":"D","Midfielder":"C","Attacker":"A"}

# Tutti i team IDs delle squadre europee (UCL/UEL/UECL)
_ALL_EURO_IDS = {
    "Ajax":194,"Arsenal":42,"Atalanta":499,"Athletic Club":531,"Atletico Madrid":530,
    "Barcelona":529,"Bayer Leverkusen":168,"Bayern Munchen":157,"Bayern München":157,
    "Benfica":211,"Bodo/Glimt":327,"Borussia Dortmund":165,"Chelsea":49,
    "Club Brugge KV":569,"Eintracht Frankfurt":169,"FC Copenhagen":400,"Galatasaray":645,
    "Inter":505,"Juventus":496,"Liverpool":40,"Manchester City":50,"Marseille":81,
    "Monaco":91,"Napoli":492,"Newcastle":34,"Olympiakos Piraeus":553,"PSV Eindhoven":197,
    "Pafos":3403,"Paris Saint Germain":85,"Qarabag":556,"Real Madrid":541,
    "Slavia Praha":560,"Sporting CP":228,"Tottenham":47,"Union St. Gilloise":1393,
    "Villarreal":533,"AS Roma":497,"Aston Villa":66,"Bologna":500,"Brann":319,
    "Celta Vigo":538,"Celtic":247,"Dinamo Zagreb":620,"FC Basel 1893":551,
    "FC Midtjylland":397,"FC Porto":212,"FCSB":559,"FK Crvena Zvezda":598,
    "Fenerbahce":611,"Fenerbahçe":611,"Ferencvarosi TC":651,"Feyenoord":209,
    "GO Ahead Eagles":410,"Genk":742,"Lille":79,"Ludogorets":566,"Lyon":80,
    "Maccabi Tel Aviv":604,"Malmo FF":375,"Nice":84,"Nottingham Forest":65,
    "PAOK":619,"Panathinaikos":617,"Plzen":567,"Rangers":257,"Real Betis":543,
    "Red Bull Salzburg":571,"SC Braga":217,"SC Freiburg":160,"Sturm Graz":637,
    "Utrecht":207,"VfB Stuttgart":172,"BSC Young Boys":565,"Shakhtar Donetsk":550,
    "AEK Athens FC":575,"AEK Larnaca":614,"AZ Alkmaar":201,"Aberdeen":252,
    "BK Hacken":367,"Breidablik":276,"Celje":4360,"Crystal Palace":52,"Drita":14281,
    "Dynamo Kyiv":572,"FC Noah":3684,"FSV Mainz 05":164,"Fiorentina":502,
    "HNK Rijeka":561,"Jagiellonia":336,"KuPS":1165,"Lech Poznan":347,
    "Legia Warszawa":339,"Omonia Nicosia":3402,"Rapid Vienna":781,"Rayo Vallecano":728,
    "Shamrock Rovers":652,"Slovan Bratislava":656,"Sparta Praha":628,"Strasbourg":95,
}
