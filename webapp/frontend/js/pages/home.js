// ── home.js - Rendering home page, hero, schedine, partite oggi ──

function pageHome(){
  return `<div class="hero" style="background:linear-gradient(135deg,rgba(13,27,42,.95),rgba(22,36,71,.9),rgba(13,59,30,.9)),url('/logo.png') center/300px no-repeat;position:relative">
    <img src="/logo.png" style="height:80px;margin-bottom:16px;filter:drop-shadow(0 4px 20px rgba(46,204,113,.4))">
    <h1>MatchIQ</h1>
    <p style="color:var(--green);font-size:1.2rem;font-weight:700;margin-bottom:8px">Simulatore Pronostici Calcistici</p>
    <p class="sub" style="font-size:1rem;max-width:550px;margin:0 auto 24px">L'intelligenza artificiale che analizza ogni partita per te.<br>Serie A + Premier League + La Liga + Bundesliga + Ligue 1 + UCL + UEL + UECL + Mondiali 2026.</p>
    <a href="#pronostici" class="btn btn-green" style="font-size:1.1rem;padding:16px 40px">Prova Gratis - Calcola Pronostico</a>
    <div style="margin-top:20px;padding:16px;background:rgba(31,52,96,.5);border-radius:12px;max-width:500px;margin-left:auto;margin-right:auto">
      <p style="color:var(--accent);font-weight:700;font-size:.9rem;margin-bottom:8px">Installa l'app sul tuo smartphone</p>
      <p style="color:var(--muted);font-size:.8rem;line-height:1.6">
        <strong style="color:var(--text)">iPhone:</strong> Apri Safari > Tocca l'icona Condividi (quadrato con freccia) > "Aggiungi alla schermata Home"<br>
        <strong style="color:var(--text)">Android:</strong> Apri Chrome > Tocca i 3 puntini in alto > "Aggiungi a schermata Home"
      </p>
      <p style="color:var(--muted);font-size:.75rem;margin-top:6px">Presto disponibile su App Store e Google Play</p>
    </div>
  </div>
  <div class="container">
    <div class="card" style="padding:28px;margin-bottom:24px;border-color:var(--accent);text-align:center">
      <h2 style="color:var(--green);margin-bottom:12px">Come funziona? Semplicissimo.</h2>
      <div class="grid3" style="margin-top:16px">
        <div style="text-align:center"><div style="font-size:2.5rem;margin-bottom:8px">1</div><strong>Scegli le squadre</strong><p style="color:var(--muted);font-size:.85rem;margin-top:4px">Seleziona la partita che ti interessa dal menu</p></div>
        <div style="text-align:center"><div style="font-size:2.5rem;margin-bottom:8px">2</div><strong>L'IA calcola tutto</strong><p style="color:var(--muted);font-size:.85rem;margin-top:4px">Analizza 8 fonti dati e 15 anni di storico in 2 secondi</p></div>
        <div style="text-align:center"><div style="font-size:2.5rem;margin-bottom:8px">3</div><strong>Ricevi il pronostico</strong><p style="color:var(--muted);font-size:.85rem;margin-top:4px">Ti dice il risultato piu' probabile con la % di successo</p></div>
      </div>
    </div>
    <div class="card" style="padding:24px;margin-bottom:24px;background:linear-gradient(135deg,#0d3b1e,#162447);border-color:var(--green)">
      <h2 style="text-align:center;color:var(--green);margin-bottom:12px">Non serve essere esperti!</h2>
      <p style="color:var(--text);font-size:1rem;line-height:1.8;text-align:center;max-width:700px;margin:0 auto">
        <strong style="color:var(--green)">MatchIQ</strong> fa tutto il lavoro per te. L'intelligenza artificiale analizza <strong>36.659 partite storiche</strong> di 8 competizioni, gli <strong>scontri diretti</strong>, la <strong>forma delle squadre</strong>, gli <strong>infortunati</strong>, le <strong>formazioni</strong> e le <strong>quote dei bookmaker</strong>. Tu devi solo leggere il risultato e decidere se seguire il consiglio.
      </p>
    </div>
    <h2 style="text-align:center;margin:24px 0 16px">I nostri numeri parlano chiaro</h2>
    <div class="grid3" style="margin-bottom:24px">
      <div class="card" style="text-align:center;border-color:var(--green)"><div id="home-stat-partite" style="font-size:2.5rem;font-weight:800;color:var(--green)">36.659</div><p style="color:var(--muted)">Partite analizzate</p></div>
      <div class="card" style="text-align:center;border-color:var(--accent)"><div id="home-stat-comp" style="font-size:2.5rem;font-weight:800;color:var(--accent)">9</div><p style="color:var(--muted)">Competizioni coperte</p><p style="color:var(--muted);font-size:.7rem;margin-top:4px">Serie A - Premier League - La Liga - Bundesliga - Ligue 1<br>Champions League - Europa League - Conference League<br>+ Mondiali 2026</p></div>
      <div class="card" style="text-align:center;border-color:var(--yellow)"><div id="home-stat-fonti" style="font-size:2.5rem;font-weight:800;color:var(--yellow)">8</div><p style="color:var(--muted)">Fonti dati combinate</p></div>
    </div>
    <h2 style="text-align:center;margin:24px 0 12px">Le nostre 8 fonti dati</h2>
    <div class="grid3">
      <div class="card" style="text-align:center"><div style="font-size:2rem">&#128202;</div><strong>15 anni di storico</strong><p style="color:var(--muted);font-size:.8rem">Forza attacco/difesa calcolata su migliaia di partite</p></div>
      <div class="card" style="text-align:center"><div style="font-size:2rem">&#128200;</div><strong>xG 2025-2026</strong><p style="color:var(--muted);font-size:.8rem">Expected Goals della stagione corrente</p></div>
      <div class="card" style="text-align:center"><div style="font-size:2rem">&#9876;</div><strong>Testa a testa H2H</strong><p style="color:var(--muted);font-size:.8rem">332 coppie di scontri diretti analizzati</p></div>
      <div class="card" style="text-align:center"><div style="font-size:2rem">&#128293;</div><strong>Forma pesata</strong><p style="color:var(--muted);font-size:.8rem">Ultime 15 partite con decay esponenziale</p></div>
      <div class="card" style="text-align:center"><div style="font-size:2rem">&#129518;</div><strong>Dixon-Coles + Ensemble</strong><p style="color:var(--muted);font-size:.8rem">3 modelli combinati per massima precisione</p></div>
      <div class="card" style="text-align:center"><div style="font-size:2rem">&#127973;</div><strong>Infortunati + Formazioni</strong><p style="color:var(--muted);font-size:.8rem">Aggiornamenti live ogni 30 minuti</p></div>
      <div class="card" style="text-align:center"><div style="font-size:2rem">&#127942;</div><strong>Classifica + Marcatori</strong><p style="color:var(--muted);font-size:.8rem">Posizione in classifica e top scorer</p></div>
      <div class="card" style="text-align:center"><div style="font-size:2rem">&#128176;</div><strong>Quote Bookmaker Live</strong><p style="color:var(--muted);font-size:.8rem">Media di 10+ bookmaker europei in tempo reale</p></div>
    </div>
    <div class="grid3">
      <div class="stat-box card"><div id="home-stat-1x2" class="num">54.8%</div><div class="lbl">1X2 (299 partite)</div></div>
      <div class="stat-box card"><div id="home-stat-gng" class="num">57.5%</div><div class="lbl">Goal/NoGoal</div></div>
      <div class="stat-box card" style="border-color:var(--green)"><div id="home-stat-alta" class="num" style="color:var(--green)">67.3%</div><div class="lbl">Pronostici Confidenza ALTA</div></div>
    </div>
    <div class="card" style="margin-top:16px;padding:20px;text-align:center;background:#0d1b2a;border-color:var(--accent)">
      <p style="color:var(--text);font-size:1rem;line-height:1.6">Questi numeri non sono inventati: sono il risultato di un <strong>backtesting su 299 partite reali</strong> della stagione 2025-2026. Quando l'IA ha confidenza Alta, centra il risultato 1X2 <strong style="color:var(--green)">2 volte su 3</strong>.</p>
    </div>
    <div class="card" style="margin-top:24px;padding:24px;border-color:var(--green)">
      ${userPlan==="pro"?'<div style="text-align:center;margin-bottom:12px"><span style="font-size:2rem">&#11088;</span><br><span style="color:var(--green);font-weight:800;font-size:1.1rem">Sei gia abbonato Pro!</span><br><span style="color:var(--muted);font-size:.9rem">Hai accesso completo a tutte le funzionalita</span></div>':''}
      <h2 style="text-align:center;color:var(--green)">${userPlan==="pro"?"Le tue funzionalita Pro":"Perche abbonarsi a Pro?"}</h2>
      <div class="grid2" style="margin-top:16px">
        <div>
          <p style="line-height:2;font-size:.95rem">
            <strong style="color:var(--green)">1.</strong> Il Pronostico del Giorno seleziona SOLO i pronostici con confidenza Alta<br>
            <strong style="color:var(--green)">2.</strong> Accesso a TUTTE le 8 giornate rimanenti con pronostici completi<br>
            <strong style="color:var(--green)">3.</strong> Classifica, marcatori e rose aggiornate in tempo reale<br>
            <strong style="color:var(--green)">4.</strong> Probabili formazioni e infortunati live aggiornati ogni 30 min
          </p>
        </div>
        <div>
          <p style="line-height:2;font-size:.95rem">
            <strong style="color:var(--green)">5.</strong> Over/Under, Goal/NoGoal e Risultato Esatto per ogni partita<br>
            <strong style="color:var(--green)">6.</strong> Marcatori consigliati dall'IA basati su xG e storico<br>
            <strong style="color:var(--green)">7.</strong> Badge SICURA sui pronostici con massima affidabilita'<br>
            <strong style="color:var(--green)">8.</strong> Notizie dal Calcio live
          </p>
        </div>
      </div>
      <div style="text-align:center;margin-top:16px">${userPlan==="pro"?'<span style="color:var(--green);font-weight:700">&#11088; Tutte le funzionalita sono attive sul tuo account</span>':'<button class="btn btn-green" style="font-size:1.1rem;padding:14px 40px" onclick="abbonarPro()">Abbonati a Pro  -  Solo 9.99&euro;/mese</button>'}</div>
    </div>
    <div id="partite-oggi-home"></div>
    <div id="partite-euro-home"></div>
    <div id="schedina-home"></div>
    <div id="schedina-pl-home"></div>
    <div id="schedina-ll-home"></div>
    <div id="schedina-bl-home"></div>
    <div id="schedina-l1-home"></div>
    <div class="card" style="margin-top:16px;padding:20px;text-align:center;background:linear-gradient(135deg,#1a237e,#0d3b1e);border-color:var(--accent);border-width:2px">
      <div style="font-size:2.5rem;margin-bottom:8px">&#127942;&#127758;</div>
      <h2 style="color:var(--accent);margin-bottom:8px">Mondiali 2026 - LIVE</h2>
      <p style="color:var(--text);font-size:.9rem;line-height:1.6">L'IA di MatchIQ analizza i <strong style="color:var(--green)">Mondiali FIFA 2026</strong> (USA, Canada, Messico).<br>48 nazionali, gironi live, pronostici per ogni partita.</p>
      <p style="color:var(--muted);font-size:.8rem;margin-top:8px">11 Giugno - 19 Luglio 2026</p>
      <a href="#mondiali" class="btn btn-green" style="margin-top:12px;display:inline-block">Vedi Gironi e Calendario &#127942;</a>
    </div>
  </div>`;
}

// Aggiorna i numeri marketing della home con dati live dal backend (/api/stats/summary)
async function _loadHomeStats(){
  try {
    const s = await fetchAPI("/api/stats/summary");
    if(!s) return;
    // Aggiorna stat cards se presenti nel DOM
    const elPartite = document.getElementById("home-stat-partite");
    const elComp    = document.getElementById("home-stat-comp");
    const elFonti   = document.getElementById("home-stat-fonti");
    const el1x2     = document.getElementById("home-stat-1x2");
    const elGng     = document.getElementById("home-stat-gng");
    const elAlta    = document.getElementById("home-stat-alta");
    if(elPartite) elPartite.textContent = s.totale_partite ? s.totale_partite.toLocaleString("it-IT") : elPartite.textContent;
    if(elComp)    elComp.textContent    = s.competizioni_coperte || elComp.textContent;
    if(elFonti)   elFonti.textContent   = s.fonti_dati || elFonti.textContent;
    if(el1x2)     el1x2.textContent     = s.accuratezza_1x2 ? s.accuratezza_1x2 + "%" : el1x2.textContent;
    if(elAlta)    elAlta.textContent    = s.accuratezza_alta_confidenza ? s.accuratezza_alta_confidenza + "%" : elAlta.textContent;
  } catch(e) { console.warn("_loadHomeStats:", e); }
}

// Carica partite di oggi nella home
async function loadPartiteOggi(){
  const el=$("partite-oggi-home");
  if(!el)return;
  try{
    const cal=await fetchAPI("/api/calendario");
    if(!cal||!cal.giornate)return;
    const gc=cal.giornata_corrente;
    const g=cal.giornate.find(x=>x.giornata===gc);
    if(!g||!g.partite)return;
    const hasResults=g.partite.some(p=>p.gol_h!==null&&p.gol_h!==undefined);
    if(!hasResults&&!g.live)return;
    let html=`<div class="card" style="border-color:${g.live?'#e74c3c':'var(--accent)'}"><div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px"><h2>Giornata ${gc}</h2>${g.live?'<span style="background:#e74c3c;color:#fff;padding:4px 12px;border-radius:10px;font-size:.75rem;font-weight:700;animation:pulse 1.5s infinite">LIVE</span>':''}</div>`;
    g.partite.forEach(p=>{
      if(p.gol_h!==null&&p.gol_h!==undefined){
        const cH=p.gol_h>p.gol_a?"var(--green)":p.gol_h<p.gol_a?"var(--red)":"var(--yellow)";
        const cA=p.gol_a>p.gol_h?"var(--green)":p.gol_a<p.gol_h?"var(--red)":"var(--yellow)";
        let st=p.status==="FT"?"FT":p.live?(p.minuto+"'"):(p.status==="HT"?"INT":(p.ora||""));
        html+=`<div style="display:flex;align-items:center;padding:6px 0;border-bottom:1px solid #1f3460"><span style="flex:1;text-align:right;font-size:.9rem;font-weight:700">${badge(p.home,16)}${p.home}</span><div style="min-width:70px;text-align:center"><span style="font-weight:800;font-size:1.1rem"><span style="color:${cH}">${p.gol_h}</span>-<span style="color:${cA}">${p.gol_a}</span></span><div style="font-size:.65rem;color:var(--muted)">${st}</div></div><span style="flex:1;font-size:.9rem;font-weight:700">${p.away}${badge(p.away,16)}</span></div>`;
      } else {
        html+=`<div style="display:flex;align-items:center;padding:6px 0;border-bottom:1px solid #1f3460"><span style="flex:1;text-align:right;font-size:.85rem">${badge(p.home,16)}${p.home}</span><span style="min-width:70px;text-align:center;color:var(--muted);font-size:.8rem">${p.ora||"vs"}</span><span style="flex:1;font-size:.85rem">${p.away}${badge(p.away,16)}</span></div>`;
      }
    });
    html+=`</div>`;
    el.innerHTML=html;
  }catch(e){}
}

// Carica partite PL nella home
async function loadPartitePL(){
  const el=$("partite-pl-home");
  if(!el)return;
  try{
    const cal=await fetchAPI("/api/premier-league/calendario");
    if(!cal||!cal.giornate)return;
    const gc=cal.giornata_corrente;
    const g=cal.giornate.find(x=>String(x.giornata)===String(gc));
    if(!g||!g.partite)return;
    const oldLeague = currentLeague;
    currentLeague = "premier-league";
    let html=`<div class="card" style="border-color:var(--accent)"><div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px"><h2>Campionato Inglese - G.${gc}</h2>${g.live?'<span style="background:#e74c3c;color:#fff;padding:4px 12px;border-radius:10px;font-size:.75rem;font-weight:700;animation:pulse 1.5s infinite">LIVE</span>':''}</div>`;
    g.partite.forEach(p=>{
      if(p.gol_h!==null&&p.gol_h!==undefined){
        const cH=p.gol_h>p.gol_a?"var(--green)":p.gol_h<p.gol_a?"var(--red)":"var(--yellow)";
        const cA=p.gol_a>p.gol_h?"var(--green)":p.gol_a<p.gol_h?"var(--red)":"var(--yellow)";
        let st=p.status==="FT"?"FT":p.live?(p.minuto+"'"):(p.status==="HT"?"INT":(p.ora||""));
        html+=`<div style="display:flex;align-items:center;padding:6px 0;border-bottom:1px solid #1f3460"><span style="flex:1;text-align:right;font-size:.9rem;font-weight:700">${badge(p.home,16)}${p.home}</span><div style="min-width:70px;text-align:center"><span style="font-weight:800;font-size:1.1rem"><span style="color:${cH}">${p.gol_h}</span>-<span style="color:${cA}">${p.gol_a}</span></span><div style="font-size:.65rem;color:var(--muted)">${st}</div></div><span style="flex:1;font-size:.9rem;font-weight:700">${p.away}${badge(p.away,16)}</span></div>`;
      } else {
        html+=`<div style="display:flex;align-items:center;padding:6px 0;border-bottom:1px solid #1f3460"><span style="flex:1;text-align:right;font-size:.85rem">${badge(p.home,16)}${p.home}</span><span style="min-width:70px;text-align:center;color:var(--muted);font-size:.8rem">${p.ora||"vs"}</span><span style="flex:1;font-size:.85rem">${p.away}${badge(p.away,16)}</span></div>`;
      }
    });
    html+=`</div>`;
    el.innerHTML=html;
    currentLeague = oldLeague;
  }catch(e){currentLeague="serie-a"}
}

// Carica partite europee in evidenza (UCL/UEL/UECL di oggi/domani)
async function loadPartiteEuro(){
  const el=$("partite-euro-home");
  if(!el)return;
  try{
    const comps=[{key:"champions-league",name:"Champions League",col:"#1a237e"},{key:"europa-league",name:"Europa League",col:"#ff6f00"},{key:"conference-league",name:"Conference League",col:"#4caf50"}];
    let html="";
    for(const comp of comps){
      const cal=await fetchAPI("/api/"+comp.key+"/calendario");
      if(!cal||!cal.giornate)continue;
      const gc=cal.giornata_corrente;
      const g=cal.giornate.find(x=>String(x.giornata)===String(gc));
      if(!g||!g.partite)continue;
      const future=g.partite.filter(p=>!(p.gol_h!==null&&p.gol_h!==undefined&&(p.status==="FT"||p.status==="AET"||p.status==="PEN")));
      if(future.length===0)continue;
      const oldL=currentLeague; currentLeague=comp.key;
      html+=`<div class="card" style="border-color:${comp.col};border-width:2px;margin-bottom:10px">
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px">
          <h3 style="color:${comp.col};font-size:1rem;margin:0">${comp.name} - ${gc}</h3>
          ${g.live?'<span style="background:#e74c3c;color:#fff;padding:3px 10px;border-radius:8px;font-size:.7rem;font-weight:700;animation:pulse 1.5s infinite">LIVE</span>':''}
        </div>`;
      future.slice(0,6).forEach(p=>{
        if(p.gol_h!==null&&p.gol_h!==undefined&&p.live){
          const cH=p.gol_h>p.gol_a?"var(--green)":p.gol_h<p.gol_a?"var(--red)":"var(--yellow)";
          const cA=p.gol_a>p.gol_h?"var(--green)":p.gol_a<p.gol_h?"var(--red)":"var(--yellow)";
          html+=`<div style="display:flex;align-items:center;padding:5px 0;border-bottom:1px solid #1f3460;background:rgba(231,76,60,.06)"><span style="flex:1;text-align:right;font-size:.8rem;font-weight:600">${badge(p.home,14)}${p.home}</span><div style="min-width:55px;text-align:center"><span style="font-weight:800"><span style="color:${cH}">${p.gol_h}</span>-<span style="color:${cA}">${p.gol_a}</span></span><div style="font-size:.6rem;color:#e74c3c">${p.minuto||""}'</div></div><span style="flex:1;font-size:.8rem;font-weight:600">${p.away}${badge(p.away,14)}</span></div>`;
        } else {
          html+=`<div style="display:flex;align-items:center;padding:5px 0;border-bottom:1px solid #1f3460"><span style="flex:1;text-align:right;font-size:.8rem">${badge(p.home,14)}${p.home}</span><span style="min-width:55px;text-align:center;color:var(--muted);font-size:.75rem">${p.ora||"vs"}</span><span style="flex:1;font-size:.8rem">${p.away}${badge(p.away,14)}</span></div>`;
        }
      });
      html+='</div>';
      currentLeague=oldL;
    }
    if(html) el.innerHTML=html;
  }catch(e){}
}

// Carica schedina Serie A nella home
async function loadSchedina(){
  const el=$("schedina-home");
  if(!el)return;
  try{
    const controller = new AbortController();
    const timeoutId = setTimeout(()=>controller.abort(), 8000);
    const headers = {};
    if(userToken) headers["Authorization"] = "Bearer " + userToken;
    const r = await fetch(API+"/api/schedina?_t="+Date.now(), {headers, signal:controller.signal});
    clearTimeout(timeoutId);
    if(!r.ok) return;
    const d = await r.json();
    if(!d||!d.giocate||!d.giocate.length)return;
    const oldL = currentLeague;
    currentLeague = "serie-a";
    let html='<div class="card" style="border-color:var(--green);border-width:2px"><h2 style="color:var(--green);text-align:center;font-size:1.1rem">Pronostico del Giorno - Campionato Italiano G.'+d.giornata+'</h2><p style="text-align:center;color:var(--muted);margin-bottom:12px;font-size:.8rem">'+d.tipo+'</p>';
    const maxShow = userPlan==="pro" ? d.giocate.length : 2;
    d.giocate.slice(0,maxShow).forEach((g,i)=>{
      html+=`<div style="display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid #1f3460"><div style="font-size:.85rem">${badge(g.home,16)}<strong>${g.home}</strong> vs <strong>${g.away}</strong>${badge(g.away,16)}<br><span style="color:var(--muted);font-size:.7rem">Conf. ${Math.round(g.confidence*100)}% | ${g.over_under} | ${g.goal}</span></div><div style="text-align:right"><span class="tag tag-green" style="font-size:.9rem;padding:4px 12px">${g.tip}</span><br><span style="color:var(--muted);font-size:.75rem">Quota ${g.quota}</span></div></div>`;
    });
    if(userPlan!=="pro"&&d.giocate.length>2){
      html+=`<div style="text-align:center;padding:16px;color:var(--muted)"><p>+ ${d.giocate.length-2} altri pronostici SICURI</p><button class="btn btn-green" style="margin-top:8px" onclick="abbonarPro()">Sblocca tutto con Pro  -  9.99&euro;/mese</button></div>`;
    }
    if(userPlan==="pro"){
      html+=`<div style="text-align:center;margin-top:10px;padding:10px;background:#0d1b2a;border-radius:8px"><span style="color:var(--muted);font-size:.8rem">Quota totale:</span> <span style="font-size:1.3rem;font-weight:800;color:var(--green)">${d.quota_totale}</span></div>`;
    }
    html+='</div>';
    el.innerHTML=html;
    currentLeague = oldL;
  }catch(e){}
}

// Carica schedina PL nella home
async function loadSchedinaPL(){
  const el=$("schedina-pl-home");
  if(!el)return;
  try{
    const controller = new AbortController();
    const timeoutId = setTimeout(()=>controller.abort(), 10000);
    const headers = {};
    if(userToken) headers["Authorization"] = "Bearer " + userToken;
    const r = await fetch(API+"/api/schedina-pl?_t="+Date.now(), {headers, signal:controller.signal});
    clearTimeout(timeoutId);
    if(!r.ok) return;
    const d = await r.json();
    if(!d||!d.giocate||!d.giocate.length)return;
    const oldLeague = currentLeague;
    currentLeague = "premier-league";
    let html='<div class="card" style="border-color:var(--accent);border-width:2px"><h2 style="color:var(--accent);text-align:center">Pronostico del Giorno - Campionato Inglese G.'+d.giornata+'</h2><p style="text-align:center;color:var(--muted);margin-bottom:16px">'+d.tipo+'</p>';
    const maxShow = userPlan==="pro" ? d.giocate.length : 2;
    d.giocate.slice(0,maxShow).forEach((g,i)=>{
      html+=`<div style="display:flex;justify-content:space-between;align-items:center;padding:10px 0;border-bottom:1px solid #1f3460"><div>${badge(g.home,18)}<strong>${g.home}</strong> vs <strong>${g.away}</strong>${badge(g.away,18)}<br><span style="color:var(--muted);font-size:.8rem">Conf. ${Math.round(g.confidence*100)}% | ${g.over_under} | ${g.goal}</span></div><div style="text-align:right"><span class="tag tag-blue" style="font-size:1rem;padding:6px 16px">${g.tip}</span><br><span style="color:var(--muted);font-size:.85rem">Quota ${g.quota}</span></div></div>`;
    });
    if(userPlan!=="pro"&&d.giocate.length>2){
      html+=`<div style="text-align:center;padding:16px;color:var(--muted)"><p>+ ${d.giocate.length-2} altri pronostici</p><button class="btn btn-green" style="margin-top:8px" onclick="abbonarPro()">Sblocca tutto con Pro</button></div>`;
    }
    if(userPlan==="pro"){
      html+=`<div style="text-align:center;margin-top:16px;padding:16px;background:#0d1b2a;border-radius:8px"><span style="color:var(--muted)">Quota totale:</span><br><span style="font-size:2rem;font-weight:800;color:var(--accent)">${d.quota_totale}</span></div>`;
    }
    html+='</div>';
    el.innerHTML=html;
    currentLeague = oldLeague;
  }catch(e){}
}

// Carica schedina La Liga nella home
async function loadSchedinaLL(){
  const el=$("schedina-ll-home");
  if(!el)return;
  try{
    const controller = new AbortController();
    const timeoutId = setTimeout(()=>controller.abort(), 10000);
    const headers = {};
    if(userToken) headers["Authorization"] = "Bearer " + userToken;
    const r = await fetch(API+"/api/schedina-ll?_t="+Date.now(), {headers, signal:controller.signal});
    clearTimeout(timeoutId);
    if(!r.ok) return;
    const d = await r.json();
    if(!d||!d.giocate||!d.giocate.length)return;
    const oldLeague = currentLeague;
    currentLeague = "la-liga";
    let html='<div class="card" style="border-color:#f39c12;border-width:2px"><h2 style="color:#f39c12;text-align:center;font-size:1.1rem">Pronostico del Giorno - Campionato Spagnolo G.'+d.giornata+'</h2><p style="text-align:center;color:var(--muted);margin-bottom:12px;font-size:.8rem">'+d.tipo+'</p>';
    const maxShow = userPlan==="pro" ? d.giocate.length : 2;
    d.giocate.slice(0,maxShow).forEach((g,i)=>{
      html+=`<div style="display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid #1f3460"><div style="font-size:.85rem">${badge(g.home,16)}<strong>${g.home}</strong> vs <strong>${g.away}</strong>${badge(g.away,16)}<br><span style="color:var(--muted);font-size:.7rem">Conf. ${Math.round(g.confidence*100)}%${g.over_under?' | '+g.over_under:''}${g.goal?' | '+g.goal:''}</span></div><div style="text-align:right"><span class="tag" style="background:#f39c12;color:#000;font-size:.9rem;padding:4px 12px">${g.tip}</span><br><span style="color:var(--muted);font-size:.7rem">Quota ${g.quota}</span></div></div>`;
    });
    if(userPlan!=="pro"&&d.giocate.length>2){
      html+=`<div style="text-align:center;padding:12px;color:var(--muted);font-size:.8rem"><p>+ ${d.giocate.length-2} altri pronostici</p><button class="btn btn-green" style="margin-top:6px;font-size:.8rem;padding:8px 16px" onclick="abbonarPro()">Sblocca con Pro</button></div>`;
    }
    if(userPlan==="pro"&&d.quota_totale){
      html+=`<div style="text-align:center;margin-top:10px;padding:10px;background:#0d1b2a;border-radius:8px"><span style="color:var(--muted);font-size:.8rem">Quota totale:</span> <span style="font-size:1.3rem;font-weight:800;color:#f39c12">${d.quota_totale}</span></div>`;
    }
    html+='</div>';
    el.innerHTML=html;
    currentLeague = oldLeague;
  }catch(e){}
}

async function loadSchedinaBL(){
  const el=$("schedina-bl-home"); if(!el)return;
  try{ const c=new AbortController(); const t=setTimeout(()=>c.abort(),10000); const h={}; if(userToken) h["Authorization"]="Bearer "+userToken;
    const r=await fetch(API+"/api/schedina-bl?_t="+Date.now(),{headers:h,signal:c.signal}); clearTimeout(t); if(!r.ok)return; const d=await r.json(); if(!d||!d.giocate||!d.giocate.length)return;
    const ol=currentLeague; currentLeague="bundesliga";
    let html='<div class="card" style="border-color:#d50000;border-width:2px"><h2 style="color:#d50000;text-align:center;font-size:1.1rem">Pronostico del Giorno - Bundesliga G.'+d.giornata+'</h2><p style="text-align:center;color:var(--muted);margin-bottom:12px;font-size:.8rem">'+d.tipo+'</p>';
    const ms=userPlan==="pro"?d.giocate.length:2; d.giocate.slice(0,ms).forEach(g=>{
      html+=`<div style="display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid #1f3460"><div style="font-size:.85rem">${badge(g.home,16)}<strong>${g.home}</strong> vs <strong>${g.away}</strong>${badge(g.away,16)}<br><span style="color:var(--muted);font-size:.7rem">Conf. ${Math.round(g.confidence*100)}%${g.over_under?' | '+g.over_under:''}${g.goal?' | '+g.goal:''}</span></div><div style="text-align:right"><span class="tag" style="background:#d50000;color:#fff;font-size:.9rem;padding:4px 12px">${g.tip}</span><br><span style="color:var(--muted);font-size:.7rem">Quota ${g.quota}</span></div></div>`;
    }); if(userPlan!=="pro"&&d.giocate.length>2) html+=`<div style="text-align:center;padding:12px;color:var(--muted);font-size:.8rem"><p>+ ${d.giocate.length-2} altri pronostici</p><button class="btn btn-green" style="margin-top:6px;font-size:.8rem;padding:8px 16px" onclick="abbonarPro()">Sblocca con Pro</button></div>`;
    if(userPlan==="pro"&&d.quota_totale) html+=`<div style="text-align:center;margin-top:10px;padding:10px;background:#0d1b2a;border-radius:8px"><span style="color:var(--muted);font-size:.8rem">Quota totale:</span> <span style="font-size:1.3rem;font-weight:800;color:#d50000">${d.quota_totale}</span></div>`;
    html+='</div>'; el.innerHTML=html; currentLeague=ol;
  }catch(e){}
}

async function loadSchedinaL1(){
  const el=$("schedina-l1-home"); if(!el)return;
  try{ const c=new AbortController(); const t=setTimeout(()=>c.abort(),10000); const h={}; if(userToken) h["Authorization"]="Bearer "+userToken;
    const r=await fetch(API+"/api/schedina-l1?_t="+Date.now(),{headers:h,signal:c.signal}); clearTimeout(t); if(!r.ok)return; const d=await r.json(); if(!d||!d.giocate||!d.giocate.length)return;
    const ol=currentLeague; currentLeague="ligue-1";
    let html='<div class="card" style="border-color:#003189;border-width:2px"><h2 style="color:#003189;text-align:center;font-size:1.1rem">Pronostico del Giorno - Ligue 1 G.'+d.giornata+'</h2><p style="text-align:center;color:var(--muted);margin-bottom:12px;font-size:.8rem">'+d.tipo+'</p>';
    const ms=userPlan==="pro"?d.giocate.length:2; d.giocate.slice(0,ms).forEach(g=>{
      html+=`<div style="display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid #1f3460"><div style="font-size:.85rem">${badge(g.home,16)}<strong>${g.home}</strong> vs <strong>${g.away}</strong>${badge(g.away,16)}<br><span style="color:var(--muted);font-size:.7rem">Conf. ${Math.round(g.confidence*100)}%${g.over_under?' | '+g.over_under:''}${g.goal?' | '+g.goal:''}</span></div><div style="text-align:right"><span class="tag" style="background:#003189;color:#fff;font-size:.9rem;padding:4px 12px">${g.tip}</span><br><span style="color:var(--muted);font-size:.7rem">Quota ${g.quota}</span></div></div>`;
    }); if(userPlan!=="pro"&&d.giocate.length>2) html+=`<div style="text-align:center;padding:12px;color:var(--muted);font-size:.8rem"><p>+ ${d.giocate.length-2} altri pronostici</p><button class="btn btn-green" style="margin-top:6px;font-size:.8rem;padding:8px 16px" onclick="abbonarPro()">Sblocca con Pro</button></div>`;
    if(userPlan==="pro"&&d.quota_totale) html+=`<div style="text-align:center;margin-top:10px;padding:10px;background:#0d1b2a;border-radius:8px"><span style="color:var(--muted);font-size:.8rem">Quota totale:</span> <span style="font-size:1.3rem;font-weight:800;color:#003189">${d.quota_totale}</span></div>`;
    html+='</div>'; el.innerHTML=html; currentLeague=ol;
  }catch(e){}
}
