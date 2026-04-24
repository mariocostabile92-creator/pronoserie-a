// ── fantacalcio.js - Pagina fantacalcio con consigli IA ──

async function pageFantacalcio(){
  if(userPlan!=="pro") return `<div class="container"><div class="lock-msg card" style="text-align:center;padding:32px">
    <div style="font-size:3rem;margin-bottom:12px">&#9917;</div>
    <h2 style="color:var(--green)">Fantacalcio IA</h2>
    <p style="color:var(--muted);margin:16px 0">L'IA ti dice chi schierare, chi evitare e i probabili marcatori della giornata.</p>
    <button class="btn btn-green" onclick="abbonarPro()">Sblocca con Pro - 9.99&euro;/mese</button>
  </div></div>`;

  const fcLeagues = [
    {key:"serie-a",label:"ITA",col:"var(--green)"},
    {key:"premier-league",label:"ENG",col:"var(--accent)"},
    {key:"la-liga",label:"ESP",col:"var(--red)"},
    {key:"bundesliga",label:"GER",col:"var(--yellow)"},
    {key:"ligue-1",label:"FRA",col:"#4a86c8"}
  ];
  const fcTabsHtml = '<div style="display:flex;gap:0;margin-bottom:16px;border-radius:10px;overflow:hidden">' +
    fcLeagues.map(l=>`<button style="flex:1;padding:5px;border:none;cursor:pointer;font-weight:600;font-size:.6rem;${currentLeague===l.key?'background:'+l.col+';color:#fff':'background:#1f3460;color:var(--muted)'}" onclick="switchLeague('${l.key}')">${l.label}</button>`).join('') + '</div>';

  let gc = 32;
  try {
    const calUrl = currentLeague==="serie-a" ? "/api/calendario" : "/api/"+currentLeague+"/calendario";
    const cal = await fetchAPI(calUrl);
    if(cal) gc = cal.giornata_corrente || 32;
  } catch(e){}

  const leagueLabel = currentLeague==="premier-league"?"Campionato Inglese":currentLeague==="la-liga"?"Campionato Spagnolo":currentLeague==="bundesliga"?"Bundesliga":currentLeague==="ligue-1"?"Campionato Francese":"Campionato Italiano";
  const apiUrl = currentLeague==="serie-a" ? "/api/fantacalcio/consigli/"+gc : "/api/"+currentLeague+"/fantacalcio/consigli/"+gc;
  const data = await fetchAPI(apiUrl, true);
  if(!data || !data.consigli) return '<div class="container">'+fcTabsHtml+'<div class="card" style="color:var(--red)">Errore caricamento consigli fantacalcio</div></div>';

  const c = data.consigli;
  const st = data.squadra_tipo;
  let html='<div class="container">';
  html+='<h1>&#9917; Fantacalcio IA</h1>';
  html+=fcTabsHtml;
  html+=`<p class="sub">${leagueLabel} - Giornata ${data.giornata} ${data.data||""}</p>`;

  if(st && st.portiere){
    html+=`<div class="card" style="padding:16px;margin-bottom:16px;border:2px solid var(--green);background:linear-gradient(135deg,#0a2e1a 0%,#162447 100%)">
      <h2 style="color:var(--green);margin-bottom:12px;text-align:center">&#11088; Squadra Tipo - Modulo ${st.modulo}</h2>
      <div style="background:linear-gradient(to bottom,#1a5e34,#2d8a4e,#1a5e34);border-radius:12px;padding:20px 10px;text-align:center;position:relative;min-height:260px">`;
    html+=`<div style="margin-bottom:16px"><span class="player-dot" style="background:#f39c12">${st.portiere.giocatore}${st.capitano===st.portiere.giocatore?' &#169;':''}</span></div>`;
    html+='<div style="display:flex;justify-content:center;gap:6px;flex-wrap:wrap;margin-bottom:16px">';
    (st.difensori||[]).forEach(d=>{html+=`<span class="player-dot">${d.giocatore}${st.capitano===d.giocatore?' &#169;':''}</span>`;});
    html+='</div>';
    html+='<div style="display:flex;justify-content:center;gap:6px;flex-wrap:wrap;margin-bottom:16px">';
    (st.centrocampisti||[]).forEach(d=>{html+=`<span class="player-dot" style="background:var(--green);color:#000">${d.giocatore}${st.capitano===d.giocatore?' &#169;':''}</span>`;});
    html+='</div>';
    html+='<div style="display:flex;justify-content:center;gap:6px;flex-wrap:wrap">';
    (st.attaccanti||[]).forEach(d=>{html+=`<span class="player-dot" style="background:var(--red)">${d.giocatore}${st.capitano===d.giocatore?' &#169;':''}</span>`;});
    html+='</div>';
    html+=`</div>`;
    if(st.panchina && st.panchina.length>0){
      html+='<div style="margin-top:10px;text-align:center"><span style="color:var(--muted);font-size:.8rem">Panchina: </span>';
      st.panchina.forEach(p=>{html+=`<span style="color:var(--muted);font-size:.8rem;margin:0 4px">${p.giocatore} ${badge(p.squadra,12)}</span>`;});
      html+='</div>';
    }
    if(st.capitano){
      html+=`<div style="text-align:center;margin-top:8px"><span style="color:var(--yellow);font-size:.85rem;font-weight:700">&#169; Capitano: ${st.capitano}</span></div>`;
    }
    html+='</div>';
  }

  const ruoli = [
    {key:"portieri",nome:"Portieri",icon:"&#129351;",col:"var(--accent)"},
    {key:"difensori",nome:"Difensori",icon:"&#128737;",col:"var(--green)"},
    {key:"centrocampisti",nome:"Centrocampisti",icon:"&#127939;",col:"var(--yellow)"},
    {key:"attaccanti",nome:"Attaccanti",icon:"&#9917;",col:"var(--red)"}
  ];

  ruoli.forEach(r=>{
    const lista = c[r.key] || [];
    if(lista.length===0) return;
    html+=`<div class="card" style="padding:12px;margin-bottom:10px;border-left:3px solid ${r.col}">
      <h3 style="color:${r.col};margin-bottom:8px">${r.icon} ${r.nome} consigliati</h3>`;
    lista.forEach(p=>{
      const stars = p.rating >= 8 ? "&#11088;&#11088;&#11088;" : p.rating >= 6 ? "&#11088;&#11088;" : "&#11088;";
      const titIcon = p.tit_status==="TITOLARE"||p.tit_prob>=90 ? '<span style="color:#2ecc71;font-size:.7rem;font-weight:700"> &#9679; TIT</span>' :
                      p.tit_status==="PROBABILE"||p.tit_prob>=50 ? '<span style="color:#f39c12;font-size:.7rem;font-weight:700"> &#9679; PROB</span>' :
                      '<span style="color:#e74c3c;font-size:.7rem;font-weight:700"> &#9679; PANCA</span>';
      const formaIcon = p.forma_trend==="crescita" ? '<span style="color:#2ecc71">&#8599;</span>' :
                        p.forma_trend==="calo" ? '<span style="color:#e74c3c">&#8600;</span>' : '<span style="color:#f39c12">&#8594;</span>';
      let statsLine = '';
      if(p.media) statsLine += `Media ${p.media} | `;
      if(p.gol) statsLine += `${p.gol}&#9917; `;
      if(p.assist) statsLine += `${p.assist}&#127775; `;
      if(p.rigori) statsLine += `| Rig: ${p.rigori} `;
      statsLine += `| Forma ${formaIcon}`;

      html+=`<div style="display:flex;align-items:center;justify-content:space-between;padding:6px 0;border-bottom:1px solid #1f3460">
        <div style="flex:1">
          <strong style="font-size:.9rem">${p.giocatore||p.squadra}</strong> ${badge(p.squadra,14)}${titIcon}
          <br><span style="color:var(--accent);font-size:.7rem">${statsLine}</span>
          <br><span style="color:var(--muted);font-size:.75rem">${p.motivazione}</span>
        </div>
        <div style="text-align:right;min-width:60px">
          <span style="font-size:.8rem">${stars}</span>
          <br><span style="color:${r.col};font-weight:800;font-size:.9rem">${p.rating}/10</span>
        </div>
      </div>`;
    });
    html+='</div>';
  });

  const evitare = c.evitare || [];
  if(evitare.length > 0){
    html+=`<div class="card" style="padding:12px;margin-bottom:10px;border-left:3px solid var(--red);background:rgba(231,76,60,.05)">
      <h3 style="color:var(--red);margin-bottom:8px">&#9888; Chi evitare</h3>`;
    evitare.forEach(p=>{
      const icon = p.tipo==="infortunato" ? "&#129657;" : "&#128308;";
      html+=`<div style="display:flex;align-items:center;padding:4px 0;border-bottom:1px solid #1f3460;font-size:.85rem">
        <span style="min-width:20px">${icon}</span>
        <div style="flex:1">
          <strong>${p.giocatore||p.squadra}</strong> ${badge(p.squadra||"",14)}
          <br><span style="color:var(--red);font-size:.75rem">${p.motivazione}</span>
        </div>
      </div>`;
    });
    html+='</div>';
  }

  html+=`<div class="card" style="text-align:center;padding:16px;background:#0d1b2a;border-color:var(--accent)">
    <p style="color:var(--muted);font-size:.85rem">Consigli basati su: statistiche live API Football, probabili formazioni, pronostici IA, forma recente.</p>
    <p style="color:var(--muted);font-size:.7rem;margin-top:4px">Aggiornamento automatico ogni 5 minuti</p>
  </div>`;

  html+='</div>';
  return html;
}
