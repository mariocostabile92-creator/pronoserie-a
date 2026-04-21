import axios from 'axios';

// URL base del backend: configurabile tramite variabile d'ambiente Expo
const API_BASE_URL = process.env.EXPO_PUBLIC_API_URL || 'https://matchiq.it.com/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// ===== AUTH TOKEN =====

/**
 * Imposta o rimuove il token JWT nell'header Authorization di tutte le richieste.
 * Chiamato dall'AuthContext ogni volta che il token cambia.
 */
export const setAuthToken = (token: string | null) => {
  if (token) {
    api.defaults.headers.common['Authorization'] = `Bearer ${token}`;
  } else {
    delete api.defaults.headers.common['Authorization'];
  }
};

// ===== AUTH =====

/** Login: restituisce access_token e piano */
export const loginUser = (email: string, password: string) =>
  api.post<{ access_token: string; piano: string }>('/auth/login', { email, password });

/** Registrazione: restituisce access_token e piano */
export const registerUser = (email: string, password: string) =>
  api.post<{ access_token: string; piano: string }>('/auth/register', { email, password });

/** Info utente corrente (piano e email) */
export const getMe = () =>
  api.get<{ email: string; piano: string }>('/payments/check-plan');

/** Codice referral dell'utente autenticato */
export const getReferralCode = () =>
  api.get<{ code: string; link: string; completati: number; in_attesa: number }>('/referral/my-code');

// Alias backward-compat (usati altrove nel codice)
export const login = (email: string, password: string) =>
  api.post('/auth/login', { email, password });

export const register = (email: string, password: string) =>
  api.post('/auth/register', { email, password });

// ===== PRONOSTICI =====
export const getPrediction = (home: string, away: string, league: string = 'serie_a') =>
  api.get(`/pronostico/${home}/${away}`);

export const getDailyTips = (league: string = 'serie_a') => {
  // Mappa lega → endpoint schedina
  const endpoints: Record<string, string> = {
    serie_a: '/schedina',
    premier: '/schedina-pl',
    la_liga: '/schedina-ll',
    bundesliga: '/schedina-bl',
    ligue_1: '/schedina-l1',
  };
  return api.get(endpoints[league] || '/schedina');
};

// ===== CALENDARIO =====
export const getCalendar = (league: string = 'serie_a', day?: number) =>
  api.get(`/${league}/calendario`, { params: { day } });

// ===== CLASSIFICA =====
export const getStandings = (league: string = 'serie_a') =>
  api.get(`/${league}/classifica`);

// ===== RISULTATI LIVE =====
export const getLiveResults = (league?: string) =>
  api.get('/risultati', { params: { league } });

export const getMatchDetails = (matchId: string) =>
  api.get(`/fixture/${matchId}`);

// ===== SQUADRE =====
export const getTeamRoster = (team: string, league: string = 'serie_a') =>
  api.get(`/squadra/${team}`);

// ===== CLASSIFICA LEGA =====
// league: 'serie-a' | 'premier-league' | 'la-liga' | 'bundesliga' | 'ligue-1'
// La Serie A usa /classifica (senza prefisso), le altre leghe usano /{league}/classifica
// (identico alla webapp: leagueApiPrefix() restituisce "" per serie-a)
export const getClassifica = (league: string) =>
  league === 'serie-a'
    ? api.get('/classifica')
    : api.get(`/${league}/classifica`);

// ===== CALENDARIO LEGA =====
// Restituisce giornate con partite programmate e risultati
// La Serie A usa /calendario (senza prefisso), le altre leghe usano /{league}/calendario
export const getCalendario = (league: string) =>
  league === 'serie-a'
    ? api.get('/calendario')
    : api.get(`/${league}/calendario`);

// ===== SCHEDINA / SIMULA GIORNATA =====
// Restituisce i pronostici IA per la giornata corrente della lega selezionata
// Usato dal bottone "Simula Giornata" nel calendario, identico alla webapp
const SCHEDINA_ENDPOINTS: Record<string, string> = {
  'serie-a':        '/schedina',
  'premier-league': '/schedina-pl',
  'la-liga':        '/schedina-ll',
  'bundesliga':     '/schedina-bl',
  'ligue-1':        '/schedina-l1',
};
export const getSchedina = (league: string) =>
  api.get(SCHEDINA_ENDPOINTS[league] || '/schedina');

// ===== DETTAGLIO FIXTURE =====
// Restituisce eventi, score e info della partita
export const getFixtureDetail = (id: number | string) =>
  api.get(`/fixture/${id}`);

// ===== DETTAGLIO SQUADRA =====
// Restituisce rosa, formazione, infortunati e allenatore di una squadra
export const getSquadra = (nome: string) =>
  api.get(`/squadra/${encodeURIComponent(nome)}`);

// ===== NOTIZIE CALCISTICHE =====
// Risposta: { notizie: [{ titolo, fonte, url }], aggiornamento }
export const getNotizie = () =>
  api.get('/notizie');

// ===== ACCURATEZZA MODELLO =====
// Risposta: { giornate: [...], totale: { partite, acc_1x2, acc_ou, acc_goal, acc_alta, tot_alta } }
export const getAccuratezza = () =>
  api.get('/accuratezza');

// ===== PRONOSTICI PERSONALI UTENTE =====

/** Recupera i pronostici salvati dall'utente (richiede autenticazione) */
export const getMyPredictions = () =>
  api.get<{
    predictions: Array<{
      id: number;
      league: string;
      home: string;
      away: string;
      pronostico: string;
      prob: number;
      confidence: string;
      over_under: string;
      goal: string;
      created_at: string;
      match_date: string;
      verificato: boolean;
      corretto: boolean | null;
      risultato_reale: string | null;
      gol_h_reale: number | null;
      gol_a_reale: number | null;
    }>;
    stats: {
      totale: number;
      verificati: number;
      ok_1x2: number;
      ok_ou: number;
      ok_goal: number;
      acc_1x2: number;
      acc_ou: number;
      acc_goal: number;
    };
  }>('/user/my-predictions');

/** Salva un pronostico per l'utente autenticato */
export const savePrediction = (data: {
  league?: string;
  home: string;
  away: string;
  pronostico: string;
  prob?: number;
  confidence?: string;
  over_under?: string;
  goal?: string;
  match_date?: string;
}) =>
  api.post<{ status: string }>('/user/save-prediction', data);

// ===== REFERRAL =====

/** Applica il codice referral di un amico */
export const applyReferral = (code: string, email: string) =>
  api.post<{ status: string; reward?: string }>('/referral/apply', { code, email });

// ===== FANTACALCIO =====

/** Consigli IA per la giornata di fantacalcio (Serie A) */
export const getFantacalcioConsigli = (giornata: number) =>
  api.get<{
    giornata: number;
    data: string;
    consigli: {
      portieri: Array<{ giocatore: string; squadra: string; rating: number; avversario: string; motivazione: string }>;
      difensori: Array<{ giocatore: string; squadra: string; rating: number; avversario: string; motivazione: string }>;
      centrocampisti: Array<{ giocatore: string; squadra: string; rating: number; avversario: string; motivazione: string }>;
      attaccanti: Array<{ giocatore: string; squadra: string; rating: number; avversario: string; motivazione: string }>;
      evitare: Array<{ giocatore: string; squadra: string; motivazione: string; tipo: string }>;
    };
    squadra_tipo: {
      portieri: Array<{ nome: string; squadra: string }>;
      difensori: Array<{ nome: string; squadra: string }>;
      centrocampisti: Array<{ nome: string; squadra: string }>;
      attaccanti: Array<{ nome: string; squadra: string }>;
      panchina: Array<{ nome: string; squadra: string }>;
      capitano: { nome: string; squadra: string } | null;
    };
    error?: string;
  }>(`/fantacalcio/consigli/${giornata}`);

// ===== MONDIALI 2026 =====

/** Gironi e partite del Mondiale 2026 */
export const getMondialiGironi = () =>
  api.get<{
    gironi: Record<string, Array<{
      squadra: string;
      punti: number;
      vinte: number;
      pareggiate: number;
      perse: number;
      gol_fatti: number;
      gol_subiti: number;
    }>>;
    partite_gironi: Record<string, Array<{
      home: string;
      away: string;
      round: string;
      status: string;
      gol_h: number | null;
      gol_a: number | null;
    }>>;
    fasi_finale: Record<string, Array<any>>;
    totale_partite: number;
  }>('/mondiali-2026/gironi');

/** Pronostico per una partita del Mondiale usando il motore generico */
export const getMondialiPronostico = (home: string, away: string) =>
  api.get(`/pronostico/${encodeURIComponent(home)}/${encodeURIComponent(away)}`);

// ===== PAGAMENTI & ABBONAMENTO =====

/** Controlla piano attuale dell'utente (alias di getMe) */
export const checkPlan = () =>
  api.get<{ piano: string; email: string }>('/payments/check-plan');

/** Crea sessione checkout Stripe per upgrade Pro (richiede autenticazione) */
export const createCheckout = () =>
  api.post<{ checkout_url: string }>('/payments/checkout');

// ===== PUSH NOTIFICATIONS =====

/**
 * Registra il push token Expo nel backend.
 * Endpoint da implementare lato backend: POST /api/push/register
 * Per ora l'infrastruttura è pronta ma il backend non ha ancora l'endpoint.
 */
export const registerPushToken = (token: string) =>
  api.post('/push/register', { token });

export default api;
