/**
 * Identificativi squadre per i badge (loghi).
 * Copiati ESATTAMENTE dalla webapp (index.html righe 95-112) per garantire
 * le stesse immagini: https://media.api-sports.io/football/teams/{id}.png
 */

// Serie A
export const TEAM_IDS: Record<string, number> = {
  Inter: 505, Milan: 489, Napoli: 492, Como: 895, Juventus: 496, Roma: 497,
  Atalanta: 499, Lazio: 487, Bologna: 500, Sassuolo: 488, Udinese: 494, Parma: 523,
  Genoa: 495, Torino: 503, Cagliari: 490, Fiorentina: 502, Cremonese: 520,
  Lecce: 867, Verona: 504, Pisa: 801,
};

// Premier League
export const TEAM_IDS_PL: Record<string, number> = {
  Arsenal: 42, 'Aston Villa': 66, Bournemouth: 35, Brentford: 55, Brighton: 51,
  Burnley: 44, Chelsea: 49, 'Crystal Palace': 52, Everton: 45, Fulham: 36,
  Leeds: 63, Liverpool: 40, 'Man City': 50, 'Man United': 33, Newcastle: 34,
  'Nott. Forest': 65, Sunderland: 746, Tottenham: 47, 'West Ham': 48, Wolves: 39,
};

// La Liga
export const TEAM_IDS_LL: Record<string, number> = {
  Alaves: 542, 'Athletic Club': 531, 'Atletico Madrid': 530, Barcelona: 529,
  'Celta Vigo': 538, Elche: 797, Espanyol: 540, Getafe: 546, Girona: 547,
  Levante: 539, Mallorca: 798, Osasuna: 727, Oviedo: 718, 'Rayo Vallecano': 728,
  'Real Betis': 543, 'Real Madrid': 541, 'Real Sociedad': 548, Sevilla: 536,
  Valencia: 532, Villarreal: 533,
};

// Bundesliga
export const TEAM_IDS_BL: Record<string, number> = {
  Augsburg: 170, 'Bayern Munich': 157, 'Bayer Leverkusen': 168, 'Borussia Dortmund': 165,
  'Eintracht Frankfurt': 169, Freiburg: 160, 'Hamburger SV': 175, Heidenheim: 180,
  Hoffenheim: 167, '1. FC Koln': 192, Mainz: 164, Monchengladbach: 163,
  'RB Leipzig': 173, 'St Pauli': 186, Stuttgart: 172, 'Union Berlin': 182,
  'Werder Bremen': 162, Wolfsburg: 161,
};

// Ligue 1
export const TEAM_IDS_L1: Record<string, number> = {
  Angers: 76, Auxerre: 110, 'Le Havre': 1074, Lens: 116, Lille: 79, Lorient: 82,
  Lyon: 80, Marseille: 81, Metz: 112, Monaco: 91, Nantes: 83, Nice: 84,
  'Paris FC': 111, 'Paris Saint Germain': 85, Rennes: 94, 'Stade Brestois 29': 130,
  Strasbourg: 95, Toulouse: 96,
};

// Champions League
export const TEAM_IDS_UCL: Record<string, number> = {
  Ajax: 194, Arsenal: 42, Atalanta: 499, 'Athletic Club': 531, 'Atletico Madrid': 530,
  Barcelona: 529, 'Bayer Leverkusen': 168, 'Bayern Munchen': 157, Benfica: 211,
  'Bodo/Glimt': 327, 'Borussia Dortmund': 165, Chelsea: 49, 'Club Brugge KV': 569,
  'Eintracht Frankfurt': 169, 'FC Copenhagen': 400, Galatasaray: 645, Inter: 505,
  Juventus: 496, Liverpool: 40, 'Manchester City': 50, Marseille: 81, Monaco: 91,
  Napoli: 492, Newcastle: 34, 'Olympiakos Piraeus': 553, 'PSV Eindhoven': 197,
  Pafos: 3403, 'Paris Saint Germain': 85, Qarabag: 556, 'Real Madrid': 541,
  'Slavia Praha': 560, 'Sporting CP': 228, Tottenham: 47, 'Union St. Gilloise': 1393,
  Villarreal: 533,
};

// Europa League
export const TEAM_IDS_UEL: Record<string, number> = {
  'AS Roma': 497, 'Aston Villa': 66, Bologna: 500, Brann: 319, 'Celta Vigo': 538,
  Celtic: 247, 'Dinamo Zagreb': 620, 'FC Basel 1893': 551, 'FC Midtjylland': 397,
  'FC Porto': 212, FCSB: 559, 'FK Crvena Zvezda': 598, Fenerbahce: 611,
  'Ferencvarosi TC': 651, Feyenoord: 209, 'GO Ahead Eagles': 410, Genk: 742,
  Lille: 79, Ludogorets: 566, Lyon: 80, 'Maccabi Tel Aviv': 604, 'Malmo FF': 375,
  Nice: 84, 'Nottingham Forest': 65, PAOK: 619, Panathinaikos: 617, Plzen: 567,
  Rangers: 257, 'Real Betis': 543, 'Red Bull Salzburg': 571, 'SC Braga': 217,
  'SC Freiburg': 160, 'Sturm Graz': 637, Utrecht: 207, 'VfB Stuttgart': 172,
};

// Conference League
export const TEAM_IDS_UECL: Record<string, number> = {
  'AEK Athens FC': 575, 'AEK Larnaca': 614, 'AZ Alkmaar': 201, Aberdeen: 252,
  'BK Hacken': 367, Breidablik: 276, Celje: 4360, 'Crystal Palace': 52, Drita: 14281,
  'Dynamo Kyiv': 572, 'FC Noah': 3684, 'FSV Mainz 05': 164, Fiorentina: 502,
  'HNK Rijeka': 561, Jagiellonia: 336, KuPS: 1165, 'Lech Poznan': 347,
  'Legia Warszawa': 339, 'Omonia Nicosia': 3402, 'Rapid Vienna': 781,
  'Rayo Vallecano': 728, 'Shakhtar Donetsk': 550, 'Shamrock Rovers': 652,
  'Slovan Bratislava': 656, 'Sparta Praha': 628, Strasbourg: 95,
};

// Mondiali 2026
export const TEAM_IDS_WC: Record<string, number> = {
  USA: 2384, Messico: 16, Canada: 1997, Brasile: 6, Argentina: 26, Uruguay: 27,
  Colombia: 1560, Ecuador: 2285, Paraguay: 28, Francia: 2, Inghilterra: 10,
  Germania: 25, Spagna: 9, Portogallo: 27, Olanda: 1118, Belgio: 1, Croazia: 3,
  Svizzera: 15, Svezia: 22, Austria: 775, Norvegia: 1090, Scozia: 1569,
  'Rep. Ceca': 770, Turchia: 3589, Bosnia: 764, Giappone: 2232, 'Corea del Sud': 17,
  Australia: 20, 'Arabia Saudita': 23, Qatar: 1569, Iran: 22, Iraq: 2378,
  Giordania: 99, Uzbekistan: 2385, 'Nuova Zelanda': 1530, Marocco: 31, Senegal: 34,
  Tunisia: 28, "Costa d'Avorio": 2282, Ghana: 867, Egitto: 3568, Algeria: 1538,
  Sudafrica: 1530, 'Capo Verde': 1535, 'Congo DR': 2286, Haiti: 2380, Panama: 2381,
  Curacao: 2382,
};

/**
 * Mappa unificata di TUTTI i TEAM_IDS (come nella webapp).
 * Identica alla funzione badge() di index.html:
 * const all = {...TEAM_IDS,...TEAM_IDS_PL,...TEAM_IDS_LL,...TEAM_IDS_BL,...TEAM_IDS_L1,
 *              ...TEAM_IDS_UCL,...TEAM_IDS_UEL,...TEAM_IDS_UECL,...TEAM_IDS_WC}
 */
export const ALL_TEAM_IDS: Record<string, number> = {
  ...TEAM_IDS,
  ...TEAM_IDS_PL,
  ...TEAM_IDS_LL,
  ...TEAM_IDS_BL,
  ...TEAM_IDS_L1,
  ...TEAM_IDS_UCL,
  ...TEAM_IDS_UEL,
  ...TEAM_IDS_UECL,
  ...TEAM_IDS_WC,
};

/**
 * Restituisce la URL del badge (logo) di una squadra.
 * Stessa URL usata dalla webapp: https://media.api-sports.io/football/teams/{id}.png
 * Restituisce null se la squadra non è nei TEAM_IDS.
 */
export function getTeamBadgeUrl(name: string): string | null {
  const id = ALL_TEAM_IDS[name];
  if (!id) return null;
  return `https://media.api-sports.io/football/teams/${id}.png`;
}
