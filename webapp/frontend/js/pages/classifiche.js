// ── classifiche.js - Pagina classifiche e marcatori ──

async function pageClassifica(){
  const leagueLabel = currentLeague==="premier-league"?"Campionato Inglese":currentLeague==="la-liga"?"Campionato Spagnolo":currentLeague==="bundesliga"?"Bundesliga":currentLeague==="ligue-1"?"Campionato Francese":currentLeague==="champions-league"?"Champions League":currentLeague==="europa-league"?"Europa League":currentLeague==="conference-league"?"Conference League":"Campionato Italiano";
  if(userPlan!=="pro") return `<div class="container">${leagueTabs()}<div class="lock-msg card"><h2>Classifica ${leagueLabel}</h2><p style="margin:16px 0">La classifica completa e la classifica marcatori sono disponibili per gli utenti Pro</p><button class="btn btn-green" onclick="abbonarPro()">Abbonati a Pro  -  9.99&euro;/mese</button></div></div>`;
  const data=await fetchAPI("/api"+leagueApiPrefix()+"/classifica", true);
  if(!data||!data.classifica||data.classifica.length===0)return `<div class="container">${leagueTabs()}<div class="card" style="text-align:center;padding:32px"><h2>Classifica ${leagueLabel}</h2><p style="color:var(--muted);margin:16px 0">Dati in caricamento... Riprova tra qualche secondo.</p><button class="btn btn-blue" onclick="navigate()">Ricarica</button></div></div>`;
  const aggLive = data.live ? `<span style="color:var(--green);font-size:.85rem">Aggiornamento automatico: ${data.aggiornamento||""}</span>` : '<span style="color:var(--muted);font-size:.85rem">Dati base</span>';
  let html='<div class="container">'+leagueTabs()+'<h1>Classifica '+leagueLabel+'</h1><p class="sub">'+aggLive+'</p>';
  html+='<div class="grid-cal">';
  html+='<div class="card" style="overflow-x:auto;padding:8px"><h2 style="margin-bottom:8px;font-size:1.1rem">Classifica</h2>';
  html+=`<div style="display:flex;padding:4px 4px 6px;border-bottom:2px solid #1f3460;color:var(--muted);font-size:.65rem;font-weight:700"><span style="width:22px">#</span><span style="flex:1">Squadra</span><span style="width:22px">PG</span><span style="width:22px">V</span><span style="width:22px">N</span><span style="width:22px">P</span><span style="width:30px">DR</span><span style="width:28px;text-align:right">PT</span></div>`;
  (data.classifica||[]).forEach((r,i)=>{
    const c=i<4?"var(--green)":i<6?"var(--yellow)":i===6?"#9b59b6":i>=17?"var(--red)":"transparent";
    html+=`<div style="display:flex;align-items:center;padding:6px 4px;border-bottom:1px solid #1f3460;border-left:3px solid ${c}">
      <span style="width:22px;font-weight:700;color:var(--muted);font-size:.8rem">${i+1}</span>
      ${badge(r.Squadra,18)}
      <span style="flex:1;font-weight:700;font-size:.85rem">${r.Squadra}</span>
      <span style="width:22px;color:var(--muted);font-size:.75rem">${r.G}</span>
      <span style="width:22px;color:var(--green);font-size:.75rem">${r.V}</span>
      <span style="width:22px;color:var(--muted);font-size:.75rem">${r.N}</span>
      <span style="width:22px;color:var(--red);font-size:.75rem">${r.P}</span>
      <span style="width:30px;color:${r.DR>0?'var(--green)':r.DR<0?'var(--red)':'var(--muted)'};font-size:.75rem">${r.DR>0?'+':''}${r.DR}</span>
      <span style="width:28px;font-weight:800;font-size:.85rem;text-align:right">${r.Punti}</span>
    </div>`;
  });
  html+='<div style="margin-top:6px;display:flex;gap:8px;justify-content:center;font-size:.7rem;flex-wrap:wrap"><span style="color:var(--green)"> - &#9679; UCL</span><span style="color:var(--yellow)"> - &#9679; UEL</span><span style="color:#9b59b6"> - &#9679; Conf.</span><span style="color:var(--red)"> - &#9679; Retr.</span></div></div>';
  html+='</div>';
  html+='<div>';
  html+='<div class="card" style="padding:10px"><h3 style="margin-bottom:6px;font-size:1rem">Top 10 Marcatori</h3>';
  (data.marcatori||[]).slice(0,10).forEach(m=>{
    html+=`<div style="display:flex;align-items:center;padding:5px 4px;border-bottom:1px solid #1f3460"><span style="width:20px;font-weight:700;color:${m.pos<=3?"var(--green)":"var(--muted)"};font-size:.8rem">${m.pos}</span><span style="flex:1"><strong style="font-size:.85rem">${m.giocatore}</strong> <span style="color:var(--muted);font-size:.7rem">${badge(m.squadra,14)}${m.squadra}</span></span><span style="font-weight:800;color:var(--green);font-size:.9rem">${m.gol}</span></div>`;
  });
  html+='</div>';
  if(data.stats_squadre){
    const s=data.stats_squadre;
    html+='<div class="card" style="padding:10px;margin-top:10px"><h3 style="margin-bottom:8px;font-size:1rem">&#128200; Statistiche Squadre</h3>';
    html+=`<div style="display:flex;align-items:center;padding:5px 0;border-bottom:1px solid #1f3460"><span style="font-size:1.1rem;margin-right:6px">&#9917;</span><span style="flex:1;font-size:.8rem">Miglior attacco</span>${badge(s.miglior_attacco.squadra,14)}<span style="font-weight:700;color:var(--green);font-size:.85rem">${s.miglior_attacco.squadra}</span><span style="color:var(--muted);font-size:.75rem;margin-left:4px">(${s.miglior_attacco.gf} gol, ${s.miglior_attacco.media}/g)</span></div>`;
    html+=`<div style="display:flex;align-items:center;padding:5px 0;border-bottom:1px solid #1f3460"><span style="font-size:1.1rem;margin-right:6px">&#128737;</span><span style="flex:1;font-size:.8rem">Miglior difesa</span>${badge(s.miglior_difesa.squadra,14)}<span style="font-weight:700;color:var(--accent);font-size:.85rem">${s.miglior_difesa.squadra}</span><span style="color:var(--muted);font-size:.75rem;margin-left:4px">(${s.miglior_difesa.gs} subiti)</span></div>`;
    html+=`<div style="display:flex;align-items:center;padding:5px 0;border-bottom:1px solid #1f3460"><span style="font-size:1.1rem;margin-right:6px">&#129351;</span><span style="flex:1;font-size:.8rem">Clean sheet</span>${badge(s.piu_clean_sheet.squadra,14)}<span style="font-weight:700;color:var(--yellow);font-size:.85rem">${s.piu_clean_sheet.squadra}</span><span style="color:var(--muted);font-size:.75rem;margin-left:4px">(${s.piu_clean_sheet.clean_sheet})</span></div>`;
    if(s.miglior_forma){const fc={"W":"#2ecc71","D":"#f39c12","L":"#e74c3c"};const fh=(s.miglior_forma.form||"").split("").map(c=>`<span style="display:inline-block;width:14px;height:14px;background:${fc[c]||'#666'};color:#fff;font-size:.6rem;text-align:center;line-height:14px;border-radius:2px;margin:0 1px">${c}</span>`).join("");html+=`<div style="display:flex;align-items:center;padding:5px 0;border-bottom:1px solid #1f3460"><span style="font-size:1.1rem;margin-right:6px">&#128293;</span><span style="flex:1;font-size:.8rem">Miglior forma</span>${badge(s.miglior_forma.squadra,14)}<span style="font-weight:700;color:var(--green);font-size:.85rem;margin-right:4px">${s.miglior_forma.squadra}</span>${fh}</div>`;}
    html+=`<div style="display:flex;align-items:center;padding:5px 0"><span style="font-size:1.1rem;margin-right:6px">&#127968;</span><span style="flex:1;font-size:.8rem">Piu vittorie</span>${badge(s.miglior_casa.squadra,14)}<span style="font-weight:700;color:#9b59b6;font-size:.85rem">${s.miglior_casa.squadra}</span><span style="color:var(--muted);font-size:.75rem;margin-left:4px">(${s.miglior_casa.vittorie})</span></div>`;
    html+='</div>';
  }
  html+='</div></div></div>';
  return html;
}
