// ── risultati.js - Risultati live, storico partite, dettaglio fixture ──

let _liveRefreshTimer = null;
let _viewingFixtureDetail = false;

function showStoricoRis(){
  var sel=document.getElementById("sel-storico-ris");
  if(!sel||!window._risultatiStorico)return;
  var idx=parseInt(sel.value);
  if(isNaN(idx))return;
  var g=window._risultatiStorico[idx];
  if(!g)return;
  var c=document.getElementById("storico-ris-content");
  if(!c)return;
  var h="";
  g.partite.forEach(function(p){
    var cH=p.gol_h>p.gol_a?"var(--green)":p.gol_h<p.gol_a?"var(--red)":"var(--yellow)";
    var cA=p.gol_a>p.gol_h?"var(--green)":p.gol_a<p.gol_h?"var(--red)":"var(--yellow)";
    h+='<div style="padding:4px 0;border-bottom:1px solid #1f3460;cursor:pointer" onclick="showFixtureDetail('+(p.fixture_id||0)+',\''+(p.home||'')+ '\',\''+(p.away||'')+'\')"> ';
    h+='<div style="display:flex;align-items:center;gap:2px">';
    h+='<span style="flex:1;text-align:right;font-size:.8rem;font-weight:600">'+badge(p.home,14)+p.home+'</span>';
    h+='<span style="min-width:50px;text-align:center;font-weight:800;font-size:.9rem"><span style="color:'+cH+'">'+p.gol_h+'</span>-<span style="color:'+cA+'">'+p.gol_a+'</span></span>';
    h+='<span style="flex:1;font-size:.8rem;font-weight:600">'+p.away+badge(p.away,14)+'</span>';
    h+='</div></div>';
  });
  c.innerHTML=h;
}

async function pageRisultati(){
  const leagueLabel = currentLeague==="premier-league"?"Campionato Inglese":currentLeague==="la-liga"?"Campionato Spagnolo":currentLeague==="bundesliga"?"Bundesliga":currentLeague==="ligue-1"?"Campionato Francese":currentLeague==="champions-league"?"Champions League":currentLeague==="europa-league"?"Europa League":currentLeague==="conference-league"?"Conference League":"Campionato Italiano";
  if(userPlan!=="pro") return `<div class="container">${leagueTabs()}<div class="lock-msg card"><h2>Risultati Live ${leagueLabel}</h2><p style="margin:16px 0">I risultati live e lo storico delle partite sono disponibili per gli utenti Pro</p><button class="btn btn-green" onclick="abbonarPro()">Abbonati a Pro - 9.99&euro;/mese</button></div></div>`;
  if(_liveRefreshTimer){clearInterval(_liveRefreshTimer);_liveRefreshTimer=null}
  const data=await fetchAPI("/api"+leagueApiPrefix()+"/risultati", true);
  if(!data||!data.giornate)return `<div class="container">${leagueTabs()}<div class="card" style="color:var(--red)">Errore caricamento risultati</div></div>`;
  const hasLive = data.live;
  let html='<div class="container">';
  html+=leagueTabs();
  html+=`<div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;margin-bottom:8px">
    <div><h1 style="margin-bottom:4px">Risultati Live ${leagueLabel}</h1><p class="sub" style="margin-bottom:0">Aggiornamento: ${data.aggiornamento||"In tempo reale"}</p></div>
    <div style="display:flex;align-items:center;gap:12px">
      ${hasLive?'<div style="display:flex;align-items:center;gap:6px;background:#e74c3c;padding:6px 16px;border-radius:20px;animation:pulse 1.5s infinite"><div style="width:10px;height:10px;border-radius:50%;background:#fff"></div><span style="color:#fff;font-weight:800;font-size:.9rem">LIVE</span></div>':'<span style="color:var(--muted);font-size:.85rem">Nessuna partita in corso</span>'}
      <button class="btn btn-blue" style="padding:8px 16px;font-size:.85rem" onclick="refreshRisultati()">Aggiorna</button>
    </div>
  </div>`;

  const completate = data.giornate.filter(g=>!g.live);
  const liveG = data.giornate.filter(g=>g.live);
  const ultimaComp = completate.length>0 ? completate[0] : null;
  const storico = completate.slice(1);

  window._risultatiStorico = storico;

  function rp(partite){
    let h="";
    partite.forEach(p=>{
      const cH=p.gol_h>p.gol_a?"var(--green)":p.gol_h<p.gol_a?"var(--red)":"var(--yellow)";
      const cA=p.gol_a>p.gol_h?"var(--green)":p.gol_a<p.gol_h?"var(--red)":"var(--yellow)";
      let sb="";
      if(p.live)sb=`<span style="background:#e74c3c;color:#fff;padding:1px 5px;border-radius:4px;font-size:.6rem;font-weight:700">${p.minuto||""}'</span>`;
      else if(p.status==="FT")sb='<span style="color:var(--muted);font-size:.6rem">FT</span>';
      else sb=`<span style="color:var(--muted);font-size:.6rem">${p.ora||p.status_it||""}</span>`;
      const mH=p.marcatori_home||[], mA=p.marcatori_away||[];
      h+=`<div style="padding:6px 2px;border-bottom:1px solid #1f3460;cursor:pointer" onclick="showFixtureDetail(${p.fixture_id||0},'${(p.home||'').replace(/'/g,'')}','${(p.away||'').replace(/'/g,'')}')">
        <div style="display:flex;align-items:center;gap:2px">
          <span style="flex:1;text-align:right;font-weight:600;font-size:.8rem">${badge(p.home,16)}${p.home}</span>
          <div style="text-align:center;min-width:55px"><span style="font-size:1rem;font-weight:800"><span style="color:${cH}">${p.gol_h!=null?p.gol_h:''}</span>${p.gol_h!=null?'-':'vs'}<span style="color:${cA}">${p.gol_a!=null?p.gol_a:''}</span></span><div>${sb}</div></div>
          <span style="flex:1;font-weight:600;font-size:.8rem">${p.away}${badge(p.away,16)}</span>
        </div>
        ${mH.length||mA.length?`<div style="display:flex;gap:8px;margin-top:2px;font-size:.65rem;justify-content:center"><span style="color:var(--muted)">${mH.join(', ')}</span><span style="color:var(--muted)">${mA.join(', ')}</span></div>`:''}
      </div>`;
    });
    return h;
  }

  html+='<div class="grid-cal">';

  if(liveG.length>0){
    const lg=liveG[0];
    html+=`<div><div class="card" style="padding:10px;border-color:#e74c3c;border-width:2px">
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:6px">
        <h3 style="margin:0;font-size:1rem">G.${lg.giornata} <span style="color:var(--muted);font-size:.75rem">${lg.data||""}</span></h3>
        <span style="background:#e74c3c;color:#fff;padding:2px 8px;border-radius:6px;font-size:.7rem;font-weight:700;animation:pulse 1.5s infinite">LIVE</span>
      </div>
      ${rp(lg.partite)}
    </div></div>`;
  } else {
    html+=`<div><div class="card" style="padding:16px;text-align:center">
      <h3 style="color:var(--accent)">Prossima giornata</h3>
      <p style="color:var(--muted);font-size:.85rem">Nessuna partita in corso. Consulta il <a href="#calendario" style="color:var(--accent)">Calendario</a> per le prossime partite.</p>
    </div></div>`;
  }

  html+='<div>';
  if(ultimaComp){
    html+=`<div class="card" style="padding:10px">
      <h3 style="margin:0 0 6px;font-size:1rem">G.${ultimaComp.giornata} <span style="color:var(--muted);font-size:.75rem">${ultimaComp.data||""}</span> <span style="color:var(--green);font-size:.65rem">COMPLETATA</span></h3>
      ${rp(ultimaComp.partite)}
    </div>`;
  }
  if(storico.length>0){
    html+=`<div class="card" style="padding:10px;margin-top:8px">
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:6px">
        <h4 style="color:var(--muted);margin:0;font-size:.85rem">Storico</h4>
        <select id="sel-storico-ris" onchange="showStoricoRis()" style="min-height:38px;font-size:.8rem;padding:4px 6px;min-width:110px">
          <option value="">Seleziona...</option>
          ${storico.map((g,i)=>`<option value="${i}">G.${g.giornata}</option>`).join('')}
        </select>
      </div>
      <div id="storico-ris-content"></div>
    </div>`;
  }
  html+='</div></div>';

  if(hasLive){
    _liveRefreshTimer = setInterval(()=>{refreshRisultati()}, 60000);
  }
  return html;
}

async function refreshRisultati(){
  const app=$("app");
  if(!app || !location.hash.includes("risultati") || _viewingFixtureDetail) return;
  const result = await pageRisultati();
  if(result) app.innerHTML = result;
}

async function backToRisultati(){
  _viewingFixtureDetail = false;
  const app=$("app");
  app.innerHTML='<div class="spinner"></div>';
  const result = await pageRisultati();
  if(result) app.innerHTML = result;
}

async function showFixtureDetail(fixtureId, home, away){
  if(!fixtureId) return;
  _viewingFixtureDetail = true;
  const app=$("app");
  app.innerHTML='<div class="container"><div class="spinner"></div><p style="text-align:center;color:var(--muted);margin-top:12px">Caricamento dettagli partita...</p></div>';

  const d = await fetchAPI("/api/fixture/"+fixtureId, true);
  if(!d || !d.home){
    app.innerHTML='<div class="container"><div class="card" style="color:var(--red)">Errore caricamento dettagli. <a href="#risultati" style="color:var(--accent)">Torna</a></div></div>';
    return;
  }

  const colH=d.gol_h>d.gol_a?"var(--green)":d.gol_h<d.gol_a?"var(--red)":"var(--yellow)";
  const colA=d.gol_a>d.gol_h?"var(--green)":d.gol_a<d.gol_h?"var(--red)":"var(--yellow)";
  const isLive=d.live;
  const st=d.stats||{};
  const ev=d.eventi||[];
  const fm=d.formazioni||{};

  let html='<div class="container">';
  html+=`<a href="javascript:void(0)" onclick="backToRisultati()" style="color:var(--accent);display:inline-block;margin-bottom:12px">&larr; Torna ai Risultati</a>`;

  html+=`<div class="card" style="text-align:center;padding:24px${isLive?';border-color:#e74c3c;border-width:2px':''}">
    ${isLive?'<div style="margin-bottom:8px"><span style="background:#e74c3c;color:#fff;padding:4px 16px;border-radius:12px;font-weight:700;animation:pulse 1.5s infinite">LIVE '+(d.minuto||"")+"'"+'</span></div>':''}
    <div style="display:flex;align-items:center;justify-content:center;gap:20px;margin:12px 0">
      <div style="flex:1;text-align:right"><h2 style="margin:0;font-size:1.4rem">${badge(d.home,32)}${d.home}</h2></div>
      <div style="text-align:center">
        <span style="font-size:2.5rem;font-weight:800"><span style="color:${colH}">${d.gol_h}</span> - <span style="color:${colA}">${d.gol_a}</span></span>
        <div style="color:var(--muted);font-size:.8rem;margin-top:4px">${d.status_it||d.status}${d.primo_tempo?' | 1T: '+d.primo_tempo:''}</div>
      </div>
      <div style="flex:1"><h2 style="margin:0;font-size:1.4rem">${d.away}${badge(d.away,32)}</h2></div>
    </div>
    ${d.stadio?'<div style="color:var(--muted);font-size:.8rem">'+d.stadio+(d.citta?' - '+d.citta:'')+(d.arbitro?' | Arbitro: '+d.arbitro:'')+'</div>':''}
  </div>`;

  if(ev.length>0){
    html+=`<div class="card"><h3 style="margin-bottom:8px">Cronologia</h3>`;
    ev.forEach(e=>{
      const isHome=e.squadra==="home";
      let icon="", color="var(--text)", label="";
      if(e.tipo==="Goal"){icon="&#9917;";color="var(--green)";label=e.dettaglio==="Penalty"?" (R)":e.dettaglio==="Own Goal"?" (aut.)":""}
      else if(e.tipo==="Card"&&e.dettaglio==="Yellow Card"){icon="&#128993;";color="var(--yellow)"}
      else if(e.tipo==="Card"&&e.dettaglio==="Red Card"){icon="&#128308;";color="var(--red)"}
      else if(e.tipo==="subst"){icon="&#128260;";color="var(--accent)"}
      else if(e.tipo==="Var"){icon="&#128250;";color="var(--muted)"}
      else{icon="&#128204;"}

      let detail = `<strong>${e.giocatore}</strong>${label}`;
      if(e.tipo==="subst" && e.assist){
        detail = `<strong style="color:var(--green)">${e.giocatore}</strong> <span style="color:var(--red);font-size:.7rem">&#9660; ${e.assist}</span>`;
      } else if(e.tipo==="Goal" && e.assist){
        detail = `<strong>${e.giocatore}</strong>${label} <span style="color:var(--muted);font-size:.7rem">(${e.assist})</span>`;
      }

      html+=`<div style="display:flex;align-items:center;padding:6px 0;border-bottom:1px solid #1f3460;font-size:.8rem;gap:4px">
        <span style="min-width:32px;text-align:center;color:var(--muted);font-weight:700;font-size:.7rem">${e.minuto}</span>
        <span style="min-width:20px;text-align:center;font-size:.85rem">${icon}</span>
        <div style="flex:1;color:${color};line-height:1.3">${detail}</div>
      </div>`;
    });
    html+=`</div>`;
  }

  if(Object.keys(st).length>0){
    html+=`<div class="card"><h3 style="margin-bottom:16px">Statistiche</h3>
    <div style="display:flex;justify-content:space-between;margin-bottom:12px;padding:0 8px">
      <span style="font-weight:700;color:var(--green)">${badge(d.home,20)}${d.home}</span>
      <span style="font-weight:700;color:var(--red)">${d.away}${badge(d.away,20)}</span>
    </div>`;

    const statRows=[
      ["possesso","Possesso"],["tiri_porta","Tiri in porta"],["tiri","Tiri totali"],
      ["tiri_fuori","Tiri fuori"],["tiri_bloccati","Tiri bloccati"],
      ["corner","Corner"],["falli","Falli"],["fuorigioco","Fuorigioco"],
      ["gialli","Gialli"],["rossi","Rossi"],["parate","Parate"],
      ["passaggi","Passaggi"],["passaggi_riusciti","Passaggi riusciti"],
      ["passaggi_pct","Precisione pass."],["xg","xG"]
    ];

    statRows.forEach(([key,label])=>{
      const vh=st[key+"_home"], va=st[key+"_away"];
      if(vh==null&&va==null) return;
      const numH=parseFloat(vh)||0, numA=parseFloat(va)||0;
      const total=numH+numA||1;
      const pctH=key==="possesso"?(parseInt(vh)||50):Math.round(numH/total*100);
      const pctA=key==="possesso"?(parseInt(va)||50):Math.round(numA/total*100);
      const betterH=numH>numA, betterA=numA>numH;

      html+=`<div style="padding:8px;border-bottom:1px solid rgba(31,52,96,.5)">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px">
          <span style="font-size:.95rem;font-weight:${betterH?'800':'400'};color:${betterH?'var(--green)':'var(--text)'};min-width:50px">${vh!=null?vh:'-'}</span>
          <span style="font-size:.75rem;color:var(--muted);text-transform:uppercase;letter-spacing:.5px">${label}</span>
          <span style="font-size:.95rem;font-weight:${betterA?'800':'400'};color:${betterA?'var(--green)':'var(--text)'};min-width:50px;text-align:right">${va!=null?va:'-'}</span>
        </div>
        <div style="display:flex;height:6px;border-radius:3px;overflow:hidden;gap:2px">
          <div style="width:${pctH}%;background:${betterH?'var(--green)':'#2a3f5f'};border-radius:3px;transition:width .5s"></div>
          <div style="width:${pctA}%;background:${betterA?'var(--red)':'#2a3f5f'};border-radius:3px;transition:width .5s"></div>
        </div>
      </div>`;
    });
    html+=`</div>`;
  }

  if(fm.home||fm.away){
    html+=`<div class="card"><h3 style="margin-bottom:12px">Formazioni</h3><div class="grid2">`;
    ["home","away"].forEach(side=>{
      const f=fm[side];
      if(!f) return;
      const nome=side==="home"?d.home:d.away;
      const col=side==="home"?"var(--green)":"var(--red)";
      html+=`<div>
        <h4 style="color:${col};margin-bottom:6px">${nome} (${f.modulo})</h4>
        <p style="color:var(--muted);font-size:.75rem;margin-bottom:8px">All. ${f.allenatore}</p>
        <div style="background:#2d8a4e;border-radius:8px;padding:10px;text-align:center;margin-bottom:8px">
          ${f.titolari.map(g=>'<span style="display:inline-block;background:'+col+';color:#fff;padding:2px 8px;border-radius:10px;font-size:.7rem;margin:2px;font-weight:600">'+g+'</span>').join('')}
        </div>
        ${f.panchina&&f.panchina.length?'<p style="color:var(--muted);font-size:.7rem">Panchina: '+f.panchina.join(', ')+'</p>':''}
      </div>`;
    });
    html+=`</div></div>`;
  }

  if(isLive){
    html+=`<div style="text-align:center;color:var(--muted);font-size:.8rem;margin-top:8px">Aggiornamento automatico ogni 30 secondi</div>`;
    setTimeout(()=>{
      if(location.hash==="#risultati") showFixtureDetail(fixtureId,home,away);
    }, 30000);
  }

  html+='</div>';
  app.innerHTML=html;
}
