"""
squads_2526.py
Rose complete e classifica marcatori Serie A 2025-2026.
Dati aggiornati a marzo 2026.
"""

# Classifica marcatori aggiornata alla 30a giornata
MARCATORI_2526 = [
    {"pos": 1,  "giocatore": "Lautaro Martinez",   "squadra": "Inter",       "gol": 14},
    {"pos": 2,  "giocatore": "Tasos Douvikas",      "squadra": "Como",        "gol": 11},
    {"pos": 3,  "giocatore": "Keinan Davis",        "squadra": "Udinese",     "gol": 10},
    {"pos": 4,  "giocatore": "Rasmus Hojlund",      "squadra": "Napoli",      "gol": 10},
    {"pos": 5,  "giocatore": "Kenan Yildiz",        "squadra": "Juventus",    "gol": 10},
    {"pos": 6,  "giocatore": "Nico Paz",            "squadra": "Como",        "gol": 10},
    {"pos": 7,  "giocatore": "Rafael Leao",         "squadra": "Milan",       "gol": 9},
    {"pos": 8,  "giocatore": "Hakan Calhanoglu",    "squadra": "Inter",       "gol": 8},
    {"pos": 9,  "giocatore": "Giovanni Simeone",    "squadra": "Torino",      "gol": 8},
    {"pos": 10, "giocatore": "Christian Pulisic",    "squadra": "Milan",       "gol": 8},
    {"pos": 11, "giocatore": "Gianluca Scamacca",   "squadra": "Atalanta",    "gol": 8},
    {"pos": 12, "giocatore": "Nikola Krstovic",     "squadra": "Atalanta",    "gol": 8},
    {"pos": 13, "giocatore": "Moise Kean",          "squadra": "Fiorentina",  "gol": 8},
    {"pos": 14, "giocatore": "Mateo Pellegrino",    "squadra": "Parma",       "gol": 8},
    {"pos": 15, "giocatore": "Domenico Berardi",    "squadra": "Sassuolo",    "gol": 7},
    {"pos": 16, "giocatore": "Nikola Vlasic",       "squadra": "Torino",      "gol": 7},
    {"pos": 17, "giocatore": "Scott McTominay",     "squadra": "Napoli",      "gol": 7},
    {"pos": 18, "giocatore": "Donyell Malen",       "squadra": "Roma",        "gol": 7},
    {"pos": 19, "giocatore": "Marcus Thuram",       "squadra": "Inter",       "gol": 7},
    {"pos": 20, "giocatore": "Andrea Pinamonti",    "squadra": "Sassuolo",    "gol": 7},
]

# Rose complete - 20 squadre Serie A 2025-2026
# Formato: (nome, ruolo, numero_maglia)
# Ruoli: P=Portiere, D=Difensore, C=Centrocampista, A=Attaccante
ROSE_2526 = {
    "Inter": [
        ("Yann Sommer", "P", 1), ("Josep Martinez", "P", 13), ("Raffaele Di Gennaro", "P", 12),
        ("Alessandro Bastoni", "D", 95), ("Yann Bisseck", "D", 31), ("Manuel Akanji", "D", 25),
        ("Stefan de Vrij", "D", 6), ("Francesco Acerbi", "D", 15), ("Federico Dimarco", "D", 32),
        ("Carlos Augusto", "D", 30), ("Denzel Dumfries", "D", 2), ("Matteo Darmian", "D", 36),
        ("Hakan Calhanoglu", "C", 20), ("Nicolo Barella", "C", 23), ("Petar Sucic", "C", 8),
        ("Davide Frattesi", "C", 16), ("Andy Diouf", "C", 17), ("Piotr Zielinski", "C", 7),
        ("Henrikh Mkhitaryan", "C", 22),
        ("Lautaro Martinez", "A", 10), ("Marcus Thuram", "A", 9), ("Pio Esposito", "A", 94),
        ("Ange-Yoan Bonny", "A", 14), ("Luis Henrique", "A", 11),
    ],
    "Milan": [
        ("Mike Maignan", "P", 16), ("Pietro Terracciano", "P", 1), ("Lorenzo Torriani", "P", 96),
        ("Strahinja Pavlovic", "D", 31), ("Koni De Winter", "D", 5), ("Fikayo Tomori", "D", 23),
        ("Matteo Gabbia", "D", 46), ("Davide Bartesaghi", "D", 33), ("Pervis Estupinan", "D", 2),
        ("Ardon Jashari", "C", 30), ("Samuele Ricci", "C", 4), ("Youssouf Fofana", "C", 19),
        ("Adrien Rabiot", "C", 12), ("Ruben Loftus-Cheek", "C", 8), ("Luka Modric", "C", 14),
        ("Rafael Leao", "A", 10), ("Christian Pulisic", "A", 11), ("Christopher Nkunku", "A", 18),
        ("Santiago Gimenez", "A", 7), ("Niclas Fullkrug", "A", 9), ("Alexis Saelemaekers", "A", 56),
    ],
    "Napoli": [
        ("Alex Meret", "P", 1), ("Nikita Contini", "P", 14), ("Vanja Milinkovic-Savic", "P", 32),
        ("Alessandro Buongiorno", "D", 4), ("Sam Beukema", "D", 31), ("Amir Rrahmani", "D", 13),
        ("Miguel Gutierrez", "D", 3), ("Mathias Olivera", "D", 17), ("Giovanni Di Lorenzo", "D", 22),
        ("Billy Gilmour", "C", 6), ("Stanislav Lobotka", "C", 68), ("Scott McTominay", "C", 8),
        ("Frank Anguissa", "C", 99), ("Kevin De Bruyne", "C", 11),
        ("Rasmus Hojlund", "A", 19), ("Romelu Lukaku", "A", 9), ("David Neres", "A", 7),
        ("Matteo Politano", "A", 21), ("Giovane", "A", 23), ("Alisson Santos", "A", 77),
    ],
    "Como": [
        ("Jean Butez", "P", 1), ("Noel Tornqvist", "P", 21),
        ("Diego Carlos", "D", 34), ("Marc Kempf", "D", 2), ("Edoardo Goldaniga", "D", 5),
        ("Alex Valle", "D", 3), ("Alberto Moreno", "D", 18), ("Ignace Van der Brempt", "D", 77),
        ("Mergim Vojvoda", "D", 31),
        ("Maximo Perrone", "C", 23), ("Lucas Da Cunha", "C", 33), ("Maxence Caqueret", "C", 6),
        ("Sergi Roberto", "C", 8), ("Nico Paz", "C", 10), ("Martin Baturina", "C", 20),
        ("Assane Diao", "A", 38), ("Nicolas Kuhn", "A", 19), ("Tasos Douvikas", "A", 11),
        ("Alvaro Morata", "A", 7), ("Jesus Rodriguez", "A", 17),
    ],
    "Juventus": [
        ("Michele Di Gregorio", "P", 16), ("Mattia Perin", "P", 1),
        ("Bremer", "D", 3), ("Pierre Kalulu", "D", 15), ("Lloyd Kelly", "D", 6),
        ("Federico Gatti", "D", 4), ("Andrea Cambiaso", "D", 27), ("Juan Cabal", "D", 32),
        ("Emil Holm", "D", 2),
        ("Manuel Locatelli", "C", 5), ("Khephren Thuram", "C", 19), ("Weston McKennie", "C", 22),
        ("Teun Koopmeiners", "C", 8), ("Filip Kostic", "C", 18),
        ("Dusan Vlahovic", "A", 9), ("Jonathan David", "A", 30), ("Lois Openda", "A", 20),
        ("Francisco Conceicao", "A", 7), ("Edon Zhegrova", "A", 11), ("Kenan Yildiz", "A", 10),
        ("Jeremy Boga", "A", 14),
    ],
    "Roma": [
        ("Mile Svilar", "P", 99), ("Pierluigi Gollini", "P", 95),
        ("Evan Ndicka", "D", 5), ("Gianluca Mancini", "D", 23), ("Mario Hermoso", "D", 22),
        ("Angelino", "D", 3), ("Konstantinos Tsimikas", "D", 12), ("Zeki Celik", "D", 19),
        ("Devyne Rensch", "D", 2),
        ("Bryan Cristante", "C", 4), ("Manu Kone", "C", 17), ("Neil El Aynaoui", "C", 8),
        ("Niccolo Pisilli", "C", 61), ("Lorenzo Pellegrini", "C", 7),
        ("Paulo Dybala", "A", 21), ("Donyell Malen", "A", 14), ("Evan Ferguson", "A", 11),
        ("Artem Dovbyk", "A", 9), ("Matias Soule", "A", 18), ("Stephan El Shaarawy", "A", 92),
        ("Brayan Zaragoza", "A", 97), ("Robinio Vaz", "A", 78),
    ],
    "Atalanta": [
        ("Marco Carnesecchi", "P", 29), ("Marco Sportiello", "P", 57),
        ("Giorgio Scalvini", "D", 42), ("Isak Hien", "D", 4), ("Odilon Kossounou", "D", 3),
        ("Sead Kolasinac", "D", 23), ("Berat Djimsiti", "D", 19),
        ("Ederson", "C", 13), ("Yunus Musah", "C", 6), ("Mario Pasalic", "C", 8),
        ("Marten de Roon", "C", 15), ("Raoul Bellanova", "C", 16), ("Davide Zappacosta", "C", 77),
        ("Charles De Ketelaere", "A", 17), ("Lazar Samardzic", "A", 10),
        ("Giacomo Raspadori", "A", 18), ("Gianluca Scamacca", "A", 9), ("Nikola Krstovic", "A", 90),
    ],
    "Lazio": [
        ("Ivan Provedel", "P", 94),
        ("Mario Gila", "D", 34), ("Alessio Romagnoli", "D", 13), ("Samuel Gigot", "D", 2),
        ("Nuno Tavares", "D", 17), ("Adam Marusic", "D", 77), ("Manuel Lazzari", "D", 29),
        ("Nicolo Rovella", "C", 6), ("Reda Belahyane", "C", 21), ("Kenneth Taylor", "C", 24),
        ("Fisayo Dele-Bashiru", "C", 7),
        ("Daniel Maldini", "A", 27), ("Mattia Zaccagni", "A", 10), ("Gustav Isaksen", "A", 18),
        ("Boulaye Dia", "A", 19), ("Pedro", "A", 9), ("Tijjani Noslin", "A", 14),
        ("Petar Ratkov", "A", 20), ("Adrian Przyborek", "A", 28),
    ],
    "Bologna": [
        ("Lukasz Skorupski", "P", 1), ("Federico Ravaglia", "P", 13),
        ("Jhon Lucumi", "D", 26), ("Martin Vitik", "D", 41), ("Nicolo Casale", "D", 16),
        ("Juan Miranda", "D", 33), ("Joao Mario", "D", 17), ("Lorenzo De Silvestri", "D", 29),
        ("Nikola Moro", "C", 6), ("Lewis Ferguson", "C", 19), ("Tommaso Pobega", "C", 4),
        ("Remo Freuler", "C", 8), ("Jens Odgaard", "C", 21),
        ("Santiago Castro", "A", 9), ("Thijs Dallinga", "A", 24), ("Riccardo Orsolini", "A", 7),
        ("Federico Bernardeschi", "A", 10), ("Jonathan Rowe", "A", 11),
    ],
    "Sassuolo": [
        ("Arijanet Muric", "P", 49), ("Stefano Turati", "P", 13),
        ("Jay Idzes", "D", 21), ("Josh Doig", "D", 3), ("Sebastian Walukiewicz", "D", 6),
        ("Filippo Romagna", "D", 19), ("Edoardo Pieragnolo", "D", 15),
        ("Luca Lipani", "C", 35), ("Daniel Boloca", "C", 11), ("Nemanja Matic", "C", 18),
        ("Ismael Kone", "C", 90), ("Kristian Thorstvedt", "C", 42),
        ("Domenico Berardi", "A", 25), ("Andrea Pinamonti", "A", 9),
        ("Armand Lauriente", "A", 45), ("Cristian Volpato", "A", 7),
    ],
    "Udinese": [
        ("Maduka Okoye", "P", 40), ("Razvan Sava", "P", 90),
        ("Oumar Solet", "D", 28), ("Thomas Kristensen", "D", 31), ("Nicolo Bertola", "D", 13),
        ("Christian Kabasele", "D", 27), ("Jordan Zemura", "D", 33), ("Alessandro Zanoli", "D", 59),
        ("Jesper Karlstrom", "C", 8), ("Lennon Miller", "C", 38), ("Oier Zarraga", "C", 6),
        ("Nicolò Zaniolo", "A", 10), ("Keinan Davis", "A", 9), ("Adam Buksa", "A", 18),
        ("Vakoun Bayo", "A", 15),
    ],
    "Parma": [
        ("Zion Suzuki", "P", 31),
        ("Alessandro Circati", "D", 39), ("Lautaro Valenti", "D", 5), ("Enrico Delprato", "D", 15),
        ("Emanuele Valeri", "D", 14), ("Franco Carboni", "D", 29),
        ("Mandela Keita", "C", 16), ("Adrian Bernabe", "C", 10), ("Hans Nicolussi Caviglia", "C", 41),
        ("Gaetano Oristanio", "C", 21),
        ("Gabriel Strefezza", "A", 7), ("Pontus Almqvist", "A", 11), ("Mateo Pellegrino", "A", 9),
    ],
    "Genoa": [
        ("Justin Bijlow", "P", 16), ("Nicola Leali", "P", 1),
        ("Johan Vasquez", "D", 22), ("Leo Ostigard", "D", 5), ("Aaron Martin", "D", 3),
        ("Brooke Norton-Cuffy", "D", 15), ("Stefano Sabelli", "D", 20),
        ("Morten Frendrup", "C", 32), ("Ruslan Malinovskyi", "C", 17), ("Tommaso Baldanzi", "C", 8),
        ("Mikael Ellertsson", "C", 77),
        ("Junior Messias", "A", 10), ("Lorenzo Colombo", "A", 29), ("Vitinha", "A", 9),
        ("Caleb Ekuban", "A", 18), ("Jeff Ekhator", "A", 21),
    ],
    "Torino": [
        ("Franco Israel", "P", 81), ("Alberto Paleari", "P", 1),
        ("Saul Coco", "D", 23), ("Ardian Ismajli", "D", 44), ("Guillermo Maripan", "D", 13),
        ("Cristiano Biraghi", "D", 34), ("Marcus Pedersen", "D", 16), ("Niels Nkounkou", "D", 25),
        ("Matteo Prati", "C", 4), ("Cesare Casadei", "C", 22), ("Ivan Ilic", "C", 8),
        ("Gvidas Gineitis", "C", 66), ("Valentino Lazaro", "C", 20),
        ("Nikola Vlasic", "A", 10), ("Che Adams", "A", 19), ("Giovanni Simeone", "A", 7),
        ("Zakaria Aboukhlal", "A", 17),
    ],
    "Cagliari": [
        ("Elia Caprile", "P", 1), ("Alen Sherri", "P", 12),
        ("Alberto Dossena", "D", 22), ("Yerry Mina", "D", 26), ("Adam Obert", "D", 33),
        ("Gabriele Zappa", "D", 28),
        ("Ibrahim Sulemana", "C", 25), ("Michel Adopo", "C", 8), ("Michael Folorunsho", "C", 90),
        ("Luca Mazzitelli", "C", 4), ("Gianluca Gaetano", "C", 10),
        ("Sebastiano Esposito", "A", 94), ("Semih Kilicsoy", "A", 9), ("Mattia Felici", "A", 17),
    ],
    "Fiorentina": [
        ("David de Gea", "P", 43), ("Oliver Christensen", "P", 53),
        ("Pietro Comuzzo", "D", 15), ("Luca Ranieri", "D", 6), ("Robin Gosens", "D", 21),
        ("Dodo", "D", 2), ("Tariq Lamptey", "D", 48), ("Fabiano Parisi", "D", 65),
        ("Rolando Mandragora", "C", 8), ("Nicolo Fagioli", "C", 44), ("Marco Brescianini", "C", 4),
        ("Jacopo Fazzini", "C", 22),
        ("Albert Gudmundsson", "A", 10), ("Moise Kean", "A", 9), ("Lucas Beltran", "A", 7),
        ("Riccardo Sottil", "A", 14), ("Jack Harrison", "A", 17),
    ],
    "Cremonese": [
        ("Emil Audero", "P", 1), ("Marco Silvestri", "P", 16),
        ("Giuseppe Pezzella", "D", 3), ("Sebastiano Luperto", "D", 5),
        ("Federico Baschirotto", "D", 6), ("Matteo Bianchetti", "D", 15),
        ("Tommaso Barbieri", "D", 4), ("Mikayil Faye", "D", 30),
        ("Morten Thorsby", "C", 2), ("Warren Bondo", "C", 38), ("Jari Vandeputte", "C", 27),
        ("Martin Payero", "C", 32), ("Alberto Grassi", "C", 33),
        ("Jamie Vardy", "A", 10), ("Milan Djuric", "A", 9), ("Alessio Zerbin", "A", 7),
        ("Antonio Sanabria", "A", 99), ("David Okereke", "A", 77),
    ],
    "Lecce": [
        ("Wladimiro Falcone", "P", 30), ("Christian Fruchtl", "P", 1),
        ("Gaspar", "D", 4), ("Antonino Gallo", "D", 25), ("Danilo Veiga", "D", 17),
        ("Ylber Ramadani", "C", 20), ("Medon Berisha", "C", 10), ("Lassana Coulibaly", "C", 29),
        ("Alex Sala", "C", 6), ("Filip Marchwinski", "C", 36),
        ("Lameck Banda", "A", 19), ("Francesco Camarda", "A", 22), ("Walid Cheddira", "A", 99),
        ("Konan N'Dri", "A", 11), ("Santiago Pierotti", "A", 50),
    ],
    "Verona": [
        ("Lorenzo Montipo", "P", 1), ("Simone Perilli", "P", 34),
        ("Victor Nelsson", "D", 15), ("Armel Bella-Kotchap", "D", 37),
        ("Domagoj Bradaric", "D", 12), ("Pol Lirola", "D", 14), ("Daniel Oyegoke", "D", 2),
        ("Sandi Lovric", "C", 4), ("Suat Serdar", "C", 8), ("Abdou Harroui", "C", 21),
        ("Roberto Gagliardini", "C", 63),
        ("Tomas Suslov", "A", 10), ("Thomas Henry", "A", 9), ("Casper Tengstedt", "A", 20),
        ("Ondrej Duda", "A", 27), ("Darko Lazovic", "A", 17),
    ],
    "Pisa": [
        ("Adrian Semper", "P", 1), ("Simone Scuffet", "P", 22),
        ("Simone Canestrelli", "D", 5), ("Arturo Calabresi", "D", 33),
        ("Felipe Loyola", "D", 35), ("Samuele Angori", "D", 3),
        ("Marius Marin", "C", 6), ("Malthe Hojholt", "C", 8), ("Michel Aebischer", "C", 20),
        ("Calvin Stengs", "C", 23), ("Juan Cuadrado", "C", 11),
        ("Henrik Meister", "A", 9), ("Matteo Tramoni", "A", 10),
        ("Samuel Iling-Junior", "A", 19), ("Stefano Moreo", "A", 32),
    ],
}

# Allenatori 2025-2026 (aggiornati al 30/03/2026)
ALLENATORI_2526 = {
    "Inter": "Cristian Chivu",
    "Milan": "Massimiliano Allegri",
    "Napoli": "Antonio Conte",
    "Como": "Cesc Fabregas",
    "Juventus": "Luciano Spalletti",
    "Roma": "Gian Piero Gasperini",
    "Atalanta": "Raffaele Palladino",
    "Lazio": "Maurizio Sarri",
    "Bologna": "Vincenzo Italiano",
    "Sassuolo": "Fabio Grosso",
    "Udinese": "Kosta Runjaic",
    "Parma": "Carlos Cuesta",
    "Genoa": "Patrick Vieira",
    "Torino": "Roberto D'Aversa",
    "Cagliari": "Fabio Pisacane",
    "Fiorentina": "Paolo Vanoli",
    "Cremonese": "Davide Nicola",
    "Lecce": "Eusebio Di Francesco",
    "Verona": "Paolo Sammarco",
    "Pisa": "Oscar Hiljemark",
}


def get_rosa(squadra: str) -> list:
    """Ritorna la rosa di una squadra come lista di tuple (nome, ruolo, numero)."""
    return ROSE_2526.get(squadra, [])


def get_marcatori():
    """Ritorna la classifica marcatori."""
    return MARCATORI_2526


def get_allenatore(squadra: str) -> str:
    """Ritorna il nome dell'allenatore."""
    return ALLENATORI_2526.get(squadra, "N/D")


def get_giocatori_per_ruolo(squadra: str) -> dict:
    """Ritorna i giocatori raggruppati per ruolo."""
    rosa = get_rosa(squadra)
    gruppi = {"P": [], "D": [], "C": [], "A": []}
    for nome, ruolo, num in rosa:
        if ruolo in gruppi:
            gruppi[ruolo].append((nome, num))
    return gruppi
