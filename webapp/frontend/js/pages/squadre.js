// ── squadre.js - Pagina squadre con rose, formazioni, infortunati ──

async function pageSquadre(){
  if(currentLeague==="champions-league"||currentLeague==="europa-league"||currentLeague==="conference-league") currentLeague="serie-a";
  const leagueLabel = currentLeague==="premier-league"?"Campionato Inglese":currentLeague==="la-liga"?"Campionato Spagnolo":currentLeague==="bundesliga"?"Bundesliga":currentLeague==="ligue-1"?"Campionato Francese":"Campionato Italiano";
  const squadreTabs = `<div style="display:flex;gap:0;margin-bottom:16px"><button style="flex:1;padding:8px;border:none;cursor:pointer;font-weight:700;font-size:.75rem;border-radius:10px 0 0 10px;${currentLeague==='serie-a'?'background:var(--green);color:#000':'background:#1f3460;color:var(--muted)'}" onclick="switchLeague('serie-a')">ITA</button><button style="flex:1;padding:8px;border:none;cursor:pointer;font-weight:700;font-size:.75rem;${currentLeague==='premier-league'?'background:var(--accent);color:#fff':'background:#1f3460;color:var(--muted)'}" onclick="switchLeague('premier-league')">ENG</button><button style="flex:1;padding:8px;border:none;cursor:pointer;font-weight:700;font-size:.75rem;${currentLeague==='la-liga'?'background:#f39c12;color:#000':'background:#1f3460;color:var(--muted)'}" onclick="switchLeague('la-liga')">ESP</button><button style="flex:1;padding:8px;border:none;cursor:pointer;font-weight:700;font-size:.75rem;${currentLeague==='bundesliga'?'background:#d50000;color:#fff':'background:#1f3460;color:var(--muted)'}" onclick="switchLeague('bundesliga')">GER</button><button style="flex:1;padding:8px;border:none;cursor:pointer;font-weight:700;font-size:.75rem;border-radius:0 10px 10px 0;${currentLeague==='ligue-1'?'background:#003189;color:#fff':'background:#1f3460;color:var(--muted)'}" onclick="switchLeague('ligue-1')">FRA</button></div>`;
  if(userPlan!=="pro") return `<div class="container">${squadreTabs}<div class="lock-msg card"><h2>Squadre ${leagueLabel}</h2><p style="margin:16px 0">Rose complete, probabili formazioni e infortunati live sono disponibili per gli utenti Pro</p><button class="btn btn-green" onclick="abbonarPro()">Abbonati a Pro  -  9.99&euro;/mese</button></div></div>`;
  return `<div class="container">
    ${squadreTabs}
    <h1>Squadre ${leagueLabel}</h1><p class="sub">Rose, formazioni e infortunati live</p>
    <select id="sel-sq" onchange="loadSq(this.value)" style="margin-bottom:16px">${opts()}</select>
    <div id="sq-det"><div class="spinner"></div></div>
  </div>`;
}

async function loadSq(nome){
  const det=$("sq-det"); if(!det)return;
  det.innerHTML='<div class="spinner"></div>';
  const d=await fetchAPI("/api/squadra/"+encodeURIComponent(nome));
  if(!d){det.innerHTML='<div class="card" style="color:var(--red)">Errore</div>';return}
  let html='<div class="grid2">';
  html+='<div>';
  html+=`<div class="card"><h2>${badge(d.nome||nome,28)}${d.nome||nome}</h2><p style="color:var(--muted)">Allenatore: <strong>${d.allenatore||"N/D"}</strong></p>${d.ultimo_aggiornamento?`<p style="color:var(--muted);font-size:.8rem;margin-top:4px">Aggiornamento: ${d.ultimo_aggiornamento}</p>`:''}</div>`;
  if(d.formazione&&d.formazione.titolari){
    const tit=d.formazione.titolari;
    const mod=d.formazione.modulo||"4-4-2";
    const modNums=(mod.match(/\d/g)||[]).map(Number);
    const rows=[[1]];
    modNums.forEach(n=>rows.push([n]));
    const nRows=rows.length;
    function getRuolo(ri){
      if(ri===0) return "P";
      if(ri===nRows-1) return "A";
      if(ri===1) return "D";
      return "C";
    }
    const ruoliCol={"P":"#f39c12","D":"#3498db","C":"#2ecc71","A":"#e74c3c"};
    const ruoliLbl={"P":"POR","D":"DIF","C":"CC","A":"ATT"};

    let pitchRows=[];
    let idx=0;
    rows.forEach((row,ri)=>{
      let cells=[];
      for(let c=0;c<row[0];c++){
        if(idx<tit.length){
          const nome=tit[idx];
          const cognome=nome.split(" ").pop();
          const ruolo=getRuolo(ri);
          cells.push({cognome, ruolo});
          idx++;
        }
      }
      pitchRows.push(cells);
    });

    pitchRows.reverse();

    let pitchHtml='';
    pitchRows.forEach(cells=>{
      pitchHtml+=`<div style="display:flex;justify-content:center;gap:12px;margin:8px 0">`;
      cells.forEach(c=>{
        const col=ruoliCol[c.ruolo]||"#3498db";
        const lbl=ruoliLbl[c.ruolo]||"";
        pitchHtml+=`<div style="text-align:center;min-width:55px"><div style="background:${col};color:#fff;width:34px;height:34px;border-radius:50%;display:inline-flex;align-items:center;justify-content:center;font-size:.65rem;font-weight:800;border:2px solid rgba(255,255,255,.4)">${lbl}</div><div style="color:#fff;font-size:.65rem;font-weight:600;margin-top:2px;text-shadow:0 1px 2px rgba(0,0,0,.5)">${c.cognome}</div></div>`;
      });
      pitchHtml+='</div>';
    });

    html+=`<div class="card"><h3>Probabile Formazione (${mod})</h3>
      <div class="pitch" style="margin-top:8px;padding:20px 12px;min-height:320px;display:flex;flex-direction:column;justify-content:space-between">
        ${pitchHtml}
      </div>
    </div>`;
  }
  if(d.infortunati&&d.infortunati.length>0){
    html+=`<div class="card" style="border-color:var(--red)"><h3 style="color:var(--red)">&#127973; Indisponibili (${d.infortunati.length})</h3>`;
    d.infortunati.forEach(inj=>{
      const c=inj.tipo==="infortunio"?"var(--red)":"var(--yellow)";
      html+=`<div style="padding:6px 0;border-bottom:1px solid #1f3460"><span style="color:${c};font-weight:700">${inj.tipo==="infortunio"?"X":"?"} ${inj.nome}</span><br><span style="color:var(--muted);font-size:.85rem">${inj.dettaglio||""}</span></div>`;
    });
    html+='</div>';
  }
  html+='</div>';
  html+='<div>';
  if(d.rosa){
    const ruoli={P:{n:"Portieri",c:"var(--yellow)"},D:{n:"Difensori",c:"var(--accent)"},C:{n:"Centrocampisti",c:"var(--green)"},A:{n:"Attaccanti",c:"var(--red)"}};
    for(const[r,info]of Object.entries(ruoli)){
      const gg=d.rosa.filter(g=>g.ruolo===r);
      if(!gg.length)continue;
      html+=`<div class="card" style="padding:12px"><h3 style="color:${info.c}">${info.n}</h3>`;
      gg.forEach(g=>{
        const ini=(g.nome||"").split(" ").map(w=>w[0]||"").join("").slice(0,2).toUpperCase();
        html+=`<div style="display:flex;align-items:center;padding:4px 0;border-bottom:1px solid #1f3460"><div style="width:28px;height:28px;border-radius:50%;background:${info.c};display:flex;align-items:center;justify-content:center;font-size:.6rem;font-weight:800;color:#fff;margin-right:6px;flex-shrink:0">${ini}</div><span style="width:26px;font-weight:700;color:${info.c};font-size:.8rem">${g.numero}</span><span style="font-size:.85rem">${g.nome}</span></div>`;
      });
      html+='</div>';
    }
  }
  html+='</div></div>';
  det.innerHTML=html;
}
