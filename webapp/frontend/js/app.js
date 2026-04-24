// ── app.js - Routing hash, state management, init, event listeners, constants ──

// ── COSTANTI SQUADRE ──
const SQ = ["Inter","Milan","Napoli","Como","Juventus","Roma","Atalanta","Lazio","Bologna","Sassuolo","Udinese","Parma","Genoa","Torino","Cagliari","Fiorentina","Cremonese","Lecce","Verona","Pisa"];
const SQ_PL = ["Arsenal","Aston Villa","Bournemouth","Brentford","Brighton","Burnley","Chelsea","Crystal Palace","Everton","Fulham","Leeds","Liverpool","Man City","Man United","Newcastle","Nott. Forest","Sunderland","Tottenham","West Ham","Wolves"];
const TEAM_IDS = {Inter:505,Milan:489,Napoli:492,Como:895,Juventus:496,Roma:497,Atalanta:499,Lazio:487,Bologna:500,Sassuolo:488,Udinese:494,Parma:523,Genoa:495,Torino:503,Cagliari:490,Fiorentina:502,Cremonese:520,Lecce:867,Verona:504,Pisa:801};
const TEAM_IDS_PL = {Arsenal:42,"Aston Villa":66,Bournemouth:35,Brentford:55,Brighton:51,Burnley:44,Chelsea:49,"Crystal Palace":52,Everton:45,Fulham:36,Leeds:63,Liverpool:40,"Man City":50,"Man United":33,Newcastle:34,"Nott. Forest":65,Sunderland:746,Tottenham:47,"West Ham":48,Wolves:39};
const SQ_LL = ["Alaves","Athletic Club","Atletico Madrid","Barcelona","Celta Vigo","Elche","Espanyol","Getafe","Girona","Levante","Mallorca","Osasuna","Oviedo","Rayo Vallecano","Real Betis","Real Madrid","Real Sociedad","Sevilla","Valencia","Villarreal"];
const TEAM_IDS_LL = {Alaves:542,"Athletic Club":531,"Atletico Madrid":530,Barcelona:529,"Celta Vigo":538,Elche:797,Espanyol:540,Getafe:546,Girona:547,Levante:539,Mallorca:798,Osasuna:727,Oviedo:718,"Rayo Vallecano":728,"Real Betis":543,"Real Madrid":541,"Real Sociedad":548,Sevilla:536,Valencia:532,Villarreal:533};
const SQ_UCL = ["Ajax","Arsenal","Atalanta","Athletic Club","Atletico Madrid","Barcelona","Bayer Leverkusen","Bayern Munchen","Benfica","Bodo/Glimt","Borussia Dortmund","Chelsea","Club Brugge KV","Eintracht Frankfurt","FC Copenhagen","Galatasaray","Inter","Juventus","Liverpool","Manchester City","Marseille","Monaco","Napoli","Newcastle","Olympiakos Piraeus","PSV Eindhoven","Pafos","Paris Saint Germain","Qarabag","Real Madrid","Slavia Praha","Sporting CP","Tottenham","Union St. Gilloise","Villarreal"];
const TEAM_IDS_UCL = {Ajax:194,Arsenal:42,Atalanta:499,"Athletic Club":531,"Atletico Madrid":530,Barcelona:529,"Bayer Leverkusen":168,"Bayern Munchen":157,Benfica:211,"Bodo/Glimt":327,"Borussia Dortmund":165,Chelsea:49,"Club Brugge KV":569,"Eintracht Frankfurt":169,"FC Copenhagen":400,Galatasaray:645,Inter:505,Juventus:496,Liverpool:40,"Manchester City":50,Marseille:81,Monaco:91,Napoli:492,Newcastle:34,"Olympiakos Piraeus":553,"PSV Eindhoven":197,Pafos:3403,"Paris Saint Germain":85,Qarabag:556,"Real Madrid":541,"Slavia Praha":560,"Sporting CP":228,Tottenham:47,"Union St. Gilloise":1393,Villarreal:533};
const SQ_UEL = ["AS Roma","Aston Villa","Bologna","Brann","Celta Vigo","Celtic","Dinamo Zagreb","FC Basel 1893","FC Midtjylland","FC Porto","FCSB","FK Crvena Zvezda","Fenerbahce","Ferencvarosi TC","Feyenoord","GO Ahead Eagles","Genk","Lille","Ludogorets","Lyon","Maccabi Tel Aviv","Malmo FF","Nice","Nottingham Forest","PAOK","Panathinaikos","Plzen","Rangers","Real Betis","Red Bull Salzburg","SC Braga","SC Freiburg","Sturm Graz","Utrecht","VfB Stuttgart"];
const TEAM_IDS_UEL = {"AS Roma":497,"Aston Villa":66,Bologna:500,Brann:319,"Celta Vigo":538,Celtic:247,"Dinamo Zagreb":620,"FC Basel 1893":551,"FC Midtjylland":397,"FC Porto":212,FCSB:559,"FK Crvena Zvezda":598,Fenerbahce:611,"Ferencvarosi TC":651,Feyenoord:209,"GO Ahead Eagles":410,Genk:742,Lille:79,Ludogorets:566,Lyon:80,"Maccabi Tel Aviv":604,"Malmo FF":375,Nice:84,"Nottingham Forest":65,PAOK:619,Panathinaikos:617,Plzen:567,Rangers:257,"Real Betis":543,"Red Bull Salzburg":571,"SC Braga":217,"SC Freiburg":160,"Sturm Graz":637,Utrecht:207,"VfB Stuttgart":172};
const SQ_BL = ["Augsburg","Bayern Munich","Bayer Leverkusen","Borussia Dortmund","Eintracht Frankfurt","Freiburg","Hamburger SV","Heidenheim","Hoffenheim","1. FC Koln","Mainz","Monchengladbach","RB Leipzig","St Pauli","Stuttgart","Union Berlin","Werder Bremen","Wolfsburg"];
const TEAM_IDS_BL = {Augsburg:170,"Bayern Munich":157,"Bayer Leverkusen":168,"Borussia Dortmund":165,"Eintracht Frankfurt":169,Freiburg:160,"Hamburger SV":175,Heidenheim:180,Hoffenheim:167,"1. FC Koln":192,Mainz:164,Monchengladbach:163,"RB Leipzig":173,"St Pauli":186,Stuttgart:172,"Union Berlin":182,"Werder Bremen":162,Wolfsburg:161};
const SQ_L1 = ["Angers","Auxerre","Le Havre","Lens","Lille","Lorient","Lyon","Marseille","Metz","Monaco","Nantes","Nice","Paris FC","Paris Saint Germain","Rennes","Stade Brestois 29","Strasbourg","Toulouse"];
const TEAM_IDS_L1 = {Angers:76,Auxerre:110,"Le Havre":1074,Lens:116,Lille:79,Lorient:82,Lyon:80,Marseille:81,Metz:112,Monaco:91,Nantes:83,Nice:84,"Paris FC":111,"Paris Saint Germain":85,Rennes:94,"Stade Brestois 29":130,Strasbourg:95,Toulouse:96};
const SQ_UECL = ["AEK Athens FC","AEK Larnaca","AZ Alkmaar","Aberdeen","BK Hacken","Breidablik","Celje","Crystal Palace","Drita","Dynamo Kyiv","FC Noah","FSV Mainz 05","Fiorentina","HNK Rijeka","Jagiellonia","KuPS","Lech Poznan","Legia Warszawa","Omonia Nicosia","Rapid Vienna","Rayo Vallecano","Shakhtar Donetsk","Shamrock Rovers","Slovan Bratislava","Sparta Praha","Strasbourg"];
const TEAM_IDS_UECL = {"AEK Athens FC":575,"AEK Larnaca":614,"AZ Alkmaar":201,Aberdeen:252,"BK Hacken":367,Breidablik:276,Celje:4360,"Crystal Palace":52,Drita:14281,"Dynamo Kyiv":572,"FC Noah":3684,"FSV Mainz 05":164,Fiorentina:502,"HNK Rijeka":561,Jagiellonia:336,KuPS:1165,"Lech Poznan":347,"Legia Warszawa":339,"Omonia Nicosia":3402,"Rapid Vienna":781,"Rayo Vallecano":728,"Shakhtar Donetsk":550,"Shamrock Rovers":652,"Slovan Bratislava":656,"Sparta Praha":628,Strasbourg:95};
const SQ_WC = ["USA","Messico","Canada","Brasile","Argentina","Uruguay","Colombia","Ecuador","Paraguay","Francia","Inghilterra","Germania","Spagna","Portogallo","Olanda","Belgio","Croazia","Svizzera","Svezia","Austria","Norvegia","Scozia","Rep. Ceca","Turchia","Bosnia","Giappone","Corea del Sud","Australia","Arabia Saudita","Qatar","Iran","Iraq","Giordania","Uzbekistan","Nuova Zelanda","Marocco","Senegal","Tunisia","Costa d'Avorio","Ghana","Egitto","Algeria","Sudafrica","Capo Verde","Congo DR","Haiti","Panama","Curacao"];
const TEAM_IDS_WC = {"USA":2384,"Messico":16,"Canada":1997,"Brasile":6,"Argentina":26,"Uruguay":27,"Colombia":1560,"Ecuador":2285,"Paraguay":28,"Francia":2,"Inghilterra":10,"Germania":25,"Spagna":9,"Portogallo":27,"Olanda":1118,"Belgio":1,"Croazia":3,"Svizzera":15,"Svezia":22,"Austria":775,"Norvegia":1090,"Scozia":1569,"Rep. Ceca":770,"Turchia":3589,"Bosnia":764,"Giappone":2232,"Corea del Sud":17,"Australia":20,"Arabia Saudita":23,"Qatar":1569,"Iran":22,"Iraq":2378,"Giordania":99,"Uzbekistan":2385,"Nuova Zelanda":1530,"Marocco":31,"Senegal":34,"Tunisia":28,"Costa d'Avorio":2282,"Ghana":867,"Egitto":3568,"Algeria":1538,"Sudafrica":1530,"Capo Verde":1535,"Congo DR":2286,"Haiti":2380,"Panama":2381,"Curacao":2382};

// ── STATE ──
let currentLeague = "serie-a";

// ── HELPER FUNCTIONS ──
function badge(name, size){
  size = size || 20;
  const all = {...TEAM_IDS,...TEAM_IDS_PL,...TEAM_IDS_LL,...TEAM_IDS_BL,...TEAM_IDS_L1,...TEAM_IDS_UCL,...TEAM_IDS_UEL,...TEAM_IDS_UECL,...TEAM_IDS_WC};
  const id = all[name];
  if(!id) return '';
  return `<img src="https://media.api-sports.io/football/teams/${id}.png" alt="${name}" style="width:${size}px;height:${size}px;vertical-align:middle;margin:0 4px">`;
}

function getSQ(){
  return currentLeague==="premier-league"?SQ_PL
    :currentLeague==="la-liga"?SQ_LL
    :currentLeague==="bundesliga"?SQ_BL
    :currentLeague==="ligue-1"?SQ_L1
    :currentLeague==="champions-league"?SQ_UCL
    :currentLeague==="europa-league"?SQ_UEL
    :currentLeague==="conference-league"?SQ_UECL
    :currentLeague==="mondiali-2026"?SQ_WC
    :SQ;
}

function opts(){return getSQ().map(s=>`<option value="${s}">${s}</option>`).join('')}
function leagueApiPrefix(){return currentLeague==="serie-a"?"":"/"+currentLeague}

function leagueTabs(){
  return `<div style="display:flex;gap:0;margin-bottom:16px;flex-wrap:wrap">
    <button style="flex:1;padding:5px;border:none;cursor:pointer;font-weight:600;font-size:.6rem;border-radius:10px 0 0 10px;${currentLeague==='serie-a'?'background:var(--green);color:#000':'background:#1f3460;color:var(--muted)'}" onclick="switchLeague('serie-a')">ITA</button>
    <button style="flex:1;padding:5px;border:none;cursor:pointer;font-weight:600;font-size:.6rem;${currentLeague==='premier-league'?'background:var(--accent);color:#fff':'background:#1f3460;color:var(--muted)'}" onclick="switchLeague('premier-league')">ENG</button>
    <button style="flex:1;padding:5px;border:none;cursor:pointer;font-weight:600;font-size:.6rem;${currentLeague==='la-liga'?'background:#f39c12;color:#000':'background:#1f3460;color:var(--muted)'}" onclick="switchLeague('la-liga')">ESP</button>
    <button style="flex:1;padding:5px;border:none;cursor:pointer;font-weight:600;font-size:.6rem;${currentLeague==='bundesliga'?'background:#d50000;color:#fff':'background:#1f3460;color:var(--muted)'}" onclick="switchLeague('bundesliga')">GER</button>
    <button style="flex:1;padding:5px;border:none;cursor:pointer;font-weight:600;font-size:.6rem;${currentLeague==='ligue-1'?'background:#003189;color:#fff':'background:#1f3460;color:var(--muted)'}" onclick="switchLeague('ligue-1')">FRA</button>
    <button style="flex:1;padding:5px;border:none;cursor:pointer;font-weight:600;font-size:.6rem;${currentLeague==='champions-league'?'background:#1a237e;color:#fff':'background:#1f3460;color:var(--muted)'}" onclick="switchLeague('champions-league')">UCL</button>
    <button style="flex:1;padding:5px;border:none;cursor:pointer;font-weight:600;font-size:.6rem;${currentLeague==='europa-league'?'background:#ff6f00;color:#fff':'background:#1f3460;color:var(--muted)'}" onclick="switchLeague('europa-league')">UEL</button>
    <button style="flex:1;padding:5px;border:none;cursor:pointer;font-weight:600;font-size:.6rem;${currentLeague==='conference-league'?'background:#4caf50;color:#fff':'background:#1f3460;color:var(--muted)'}" onclick="switchLeague('conference-league')">UECL</button>
    <button style="flex:1;padding:5px;border:none;cursor:pointer;font-weight:600;font-size:.6rem;border-radius:0 10px 10px 0;${currentLeague==='mondiali-2026'?'background:#f39c12;color:#000':'background:#1f3460;color:var(--muted)'}" onclick="switchLeague('mondiali-2026')">&#127942;WC</button>
  </div>`;
}

function switchLeague(l){currentLeague=l;navigate()}

// Carica squadre attive live per competizioni europee
async function loadActiveTeams(){
  if(!["champions-league","europa-league","conference-league"].includes(currentLeague)) return;
  try{
    const d = await fetchAPI("/api/"+currentLeague+"/squadre-attive");
    if(d && d.squadre && d.squadre.length>0){
      if(currentLeague==="champions-league") window._SQ_UCL_LIVE = d.squadre;
      else if(currentLeague==="europa-league") window._SQ_UEL_LIVE = d.squadre;
      else window._SQ_UECL_LIVE = d.squadre;
      const selH = document.getElementById("sel-home");
      const selA = document.getElementById("sel-away");
      if(selH && selA){
        const opts = d.squadre.map(s=>'<option value="'+s+'">'+s+'</option>').join('');
        selH.innerHTML = opts;
        selA.innerHTML = opts;
      }
    }
  }catch(e){}
}

// ── ROUTER ──
const routes = {
  home: pageHome,
  mondiali: pageMondiali,
  fantacalcio: pageFantacalcio,
  pronostici: pagePronostici,
  calendario: pageCalendario,
  classifica: pageClassifica,
  squadre: pageSquadre,
  notizie: pageNotizie,
  risultati: pageRisultati,
  pricing: pagePricing,
  login: pageLogin,
  privacy: pagePrivacy,
  termini: pageTermini,
  accuratezza: pageAccuratezza,
  miei: pageMyPredictions
};

async function navigate(){
  const hash = (location.hash || "#home").replace("#","");
  if(hash!=="risultati" && typeof _liveRefreshTimer !== "undefined" && _liveRefreshTimer){clearInterval(_liveRefreshTimer);_liveRefreshTimer=null}
  if(hash!=="calendario" && typeof _calRefreshTimer !== "undefined" && _calRefreshTimer){clearInterval(_calRefreshTimer);_calRefreshTimer=null}
  if(typeof _viewingFixtureDetail !== "undefined") _viewingFixtureDetail = false;
  const page = routes[hash] || routes.home;
  document.querySelectorAll(".nav a:not(#nav-auth)").forEach(a=>a.classList.toggle("active",a.getAttribute("href")==="#"+hash));
  const app = $("app");
  try{
    const result = page();
    if(result && typeof result.then === "function"){app.innerHTML='<div class="spinner"></div>';app.innerHTML=await result}
    else{app.innerHTML = result}
  }catch(e){app.innerHTML='<div class="container card" style="color:var(--red)">Errore: '+e.message+'</div>'}
  const ft = $("app-footer"); if(ft) ft.style.display = "block";
  if(hash==="squadre" && userPlan==="pro") setTimeout(()=>loadSq(getSQ()[0]),200);
  if(hash==="pronostici" && ["champions-league","europa-league","conference-league"].includes(currentLeague)) setTimeout(()=>loadActiveTeams(),500);
  if(hash==="home"){
    setTimeout(()=>loadPartiteOggi(),500);
    setTimeout(()=>loadPartiteEuro(),1500);
    setTimeout(()=>loadSchedina(),2000);
    setTimeout(()=>loadSchedinaPL(),3000);
    setTimeout(()=>loadSchedinaLL(),4000);
    setTimeout(()=>loadSchedinaBL(),5000);
    setTimeout(()=>loadSchedinaL1(),6000);
    setTimeout(()=>{fetchAPI("/api/classifica")},5000);
    setTimeout(()=>_loadHomeStats(),800);
  }
  updateNavAuth();
}

function updateNavAuth(){
  const el = $("nav-auth");
  if(!el) return;
  if(userToken){
    el.innerHTML = userPlan==="pro"?"&#11088; Pro":"&#128100; Free";
    el.style.background = userPlan==="pro"?"var(--green)":"#1f3460";
    el.style.color = userPlan==="pro"?"#000":"var(--text)";
  }else{
    el.innerHTML = "&#128100; Accedi";
    el.style.background = "#1f3460";
    el.style.color = "var(--muted)";
  }
}

// ── STRIPE CHECKOUT ──
async function abbonarPro(){
  const btn = event.target;
  btn.textContent = "Caricamento...";
  btn.disabled = true;
  try {
    const ep = userEmail ? `/api/payments/checkout-direct?email=${encodeURIComponent(userEmail)}` : "/api/payments/checkout-direct";
    const d = await fetchAPI(ep);
    if(d && d.checkout_url){
      window.location.href = d.checkout_url;
    } else {
      alert("Errore nella creazione del pagamento. Riprova.");
      btn.textContent = "Abbonati Ora";
      btn.disabled = false;
    }
  } catch(e) {
    alert("Errore connessione. Riprova.");
    btn.textContent = "Abbonati Ora";
    btn.disabled = false;
  }
}

// ── GESTIONE RITORNO DA STRIPE ──
async function checkPaidReturn(){
  if(window.location.search.includes("paid=1")){
    if(userToken && userEmail){
      try{ await postAPI("/api/payments/activate-pro", {email: userEmail}); }catch(e){}
      userPlan = "pro";
      localStorage.setItem("userPlan","pro");
      freeUsed = 0;
      localStorage.setItem("freeUsed","0");
      updateNavAuth();
      history.replaceState(null,"","/app#home");
      alert("Pagamento completato! Ora hai accesso Pro illimitato.");
    } else {
      localStorage.setItem("stripe_paid","1");
      history.replaceState(null,"","/app#login");
      location.hash = "#login";
      alert("Pagamento ricevuto! Accedi con la tua email per attivare il piano Pro.");
    }
  }
  if(localStorage.getItem("stripe_paid")==="1" && userToken && userEmail){
    try{
      const r = await postAPI("/api/payments/activate-pro", {email: userEmail});
      if(r.piano==="pro"){
        userPlan = "pro";
        localStorage.setItem("userPlan","pro");
        localStorage.removeItem("stripe_paid");
        updateNavAuth();
      }
    }catch(e){}
  }
}

// ── INIT ──
window.addEventListener("hashchange", navigate);
if(!location.hash) location.hash = "#home";

// Salva codice referral se presente nell'URL
const _refParam = new URLSearchParams(window.location.search).get("ref");
if(_refParam) localStorage.setItem("ref_code", _refParam);

navigate();
checkPaidReturn();
loadConfig();

// PWA Service Worker + Push Notifications
if('serviceWorker' in navigator){
  navigator.serviceWorker.register('/sw.js').then(async reg=>{
    setTimeout(async()=>{
      if(Notification.permission==='default' && userToken){
        const p = await Notification.requestPermission();
        if(p==='granted'){
          try{
            const vapid = await fetchAPI("/api/push/vapid-key");
            if(vapid && vapid.publicKey){
              const sub = await reg.pushManager.subscribe({
                userVisibleOnly: true,
                applicationServerKey: Uint8Array.from(atob(vapid.publicKey.replace(/-/g,'+').replace(/_/g,'/').padEnd(vapid.publicKey.length+(4-vapid.publicKey.length%4)%4,'=')), c=>c.charCodeAt(0))
              });
              await postAPI("/api/push/subscribe", {subscription: sub.toJSON()});
              console.log('Push subscription attiva');
            }
          }catch(e){console.log('Push setup error:',e)}
        }
      }
    }, 5000);
  }).catch(()=>{});
}
