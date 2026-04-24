// ── api.js - Tutte le chiamate fetch/API, cache client, token handling ──

const API = window.location.origin;

// Stato utente (condiviso tra moduli)
let userPlan = localStorage.getItem("userPlan") || "free";
let userToken = localStorage.getItem("userToken") || "";
let userEmail = localStorage.getItem("userEmail") || "";
let freeUsed = parseInt(localStorage.getItem("freeUsed")||"0");
const FREE_LIMIT = 2;

// Cache API per evitare chiamate ripetute
const _apiCache = {};
const CACHE_TTL = 300000; // 5 minuti

async function fetchAPI(ep, noCache) {
  if(!noCache && _apiCache[ep] && (Date.now()-_apiCache[ep].t < CACHE_TTL)){
    return _apiCache[ep].d;
  }
  try {
    const sep = ep.includes("?") ? "&" : "?";
    const headers = {};
    if(userToken) headers["Authorization"] = "Bearer " + userToken;
    const r = await fetch(API+ep+sep+"_t="+Date.now(), {headers});
    if(!r.ok) throw new Error(r.status);
    const data = await r.json();
    _apiCache[ep]={d:data,t:Date.now()};
    return data;
  } catch(e) { console.error("API:",ep,e); return null; }
}

async function postAPI(ep, body) {
  try {
    const headers = {"Content-Type":"application/json"};
    if(userToken) headers["Authorization"] = "Bearer " + userToken;
    const r = await fetch(API+ep, {method:"POST", headers, body:JSON.stringify(body)});
    if(!r.ok) { const err = await r.json().catch(()=>({})); throw new Error(err.detail||r.status); }
    return await r.json();
  } catch(e) { throw e; }
}

function $(id){return document.getElementById(id)}

// Carica configurazione dinamica (team IDs, leghe) dal backend
async function loadConfig(){
  try {
    const cfg = await fetchAPI("/api/config");
    if(!cfg) return;
    // Aggiorna le costanti globali con i dati del backend
    if(cfg.serie_a_team_ids) Object.assign(TEAM_IDS, cfg.serie_a_team_ids);
    if(cfg.leagues){
      cfg.leagues.forEach(lg => {
        if(lg.key === "premier-league" && lg.team_ids) Object.assign(TEAM_IDS_PL, lg.team_ids);
        if(lg.key === "la-liga"        && lg.team_ids) Object.assign(TEAM_IDS_LL, lg.team_ids);
        if(lg.key === "bundesliga"     && lg.team_ids) Object.assign(TEAM_IDS_BL, lg.team_ids);
        if(lg.key === "ligue-1"        && lg.team_ids) Object.assign(TEAM_IDS_L1, lg.team_ids);
        if(lg.key === "mondiali-2026"  && lg.team_ids) Object.assign(TEAM_IDS_WC, lg.team_ids);
      });
    }
  } catch(e) { console.warn("loadConfig:", e); }
}
