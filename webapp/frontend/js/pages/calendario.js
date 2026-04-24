// ── calendario.js - Pagina calendario con risultati live e simulazione giornata ──

let _calRefreshTimer = null;

async function pageCalendario(){
  if(_calRefreshTimer){clearInterval(_calRefreshTimer);_calRefreshTimer=null}
  const leagueLabel = currentLeague==="premier-league"?"Campionato Inglese":currentLeague==="la-liga"?"Campionato Spagnolo":currentLeague==="bundesliga"?"Bundesliga":currentLeague==="ligue-1"?"Campionato Francese":currentLeague==="champions-league"?"Champions League":currentLeague==="europa-league"?"Europa League":currentLeague==="conference-league"?"Conference League":"Campionato Italiano";
  const calUrl = currentLeague==="serie-a" ? "/api/calendario" : "/api/"+currentLeague+"/calendario";
  const cal=await fetchAPI(calUrl, true);
  if(!cal||!cal.giornate||!cal.giornate.length)return `<div class="container">${leagueTabs()}<div class="card" style="color:var(--red)">Errore caricamento calendario.</div></div>`;

  const gc = String(cal.giornata_corrente || cal.giornate[0].giornata);
  const gCorrente = cal.giornate.find(x=>String(x.giornata)===gc) || cal.giornate[0];
  const completate = cal.giornate.filter(g=>g.stato==="completata");
  const prossime = cal.giornate.filter(g=>g.stato!=="completata" && String(g.giornata)!==gc);

  let html='<div class="container"><h1>Calendario '+leagueLabel+'</h1>';
  html+=leagueTabs();
  html+=`<p class="sub">${cal.live?'<span style="color:#e74c3c;font-weight:700">LIVE</span> - ':''}Giornata ${gc}${gCorrente.live?' in corso':''}</p>`;
  html+='<div class="grid-cal">';

  html+='<div>';
  html+=`<div class="card" style="${gCorrente.live?'border-color:#e74c3c;border-width:2px':''}">
    <div style="display:flex;align-items:center;justify-content:space-between">
      <h2 style="color:${gCorrente.live?'#e74c3c':'var(--green)'}">Giornata ${gc}</h2>
      ${gCorrente.live?'<span style="background:#e74c3c;color:#fff;padding:4px 12px;border-radius:10px;font-size:.75rem;font-weight:700;animation:pulse 1.5s infinite">LIVE</span>':''}
    </div>
    <p style="color:var(--muted);font-size:.85rem;margin-bottom:12px">${gCorrente.data||""}</p>`;

  if(userPlan==="pro" && !gCorrente.live && gCorrente.stato!=="completata"){
    html+=`<button class="btn btn-green" style="margin-bottom:12px;font-size:.9rem" onclick="simulaGiornata('${gc}')">Simula Pronostici Giornata</button>`;
  }

  gCorrente.partite.forEach(p=>{
    const hasResult = p.gol_h !== null && p.gol_h !== undefined;
    if(hasResult){
      const colH=p.gol_h>p.gol_a?"var(--green)":p.gol_h<p.gol_a?"var(--red)":"var(--yellow)";
      const colA=p.gol_a>p.gol_h?"var(--green)":p.gol_a<p.gol_h?"var(--red)":"var(--yellow)";
      let statusBadge="";
      if(p.live){statusBadge=`<span style="background:#e74c3c;color:#fff;padding:2px 6px;border-radius:6px;font-size:.65rem;font-weight:700;animation:pulse 1.5s infinite">${p.minuto||""}'</span>`}
      else if(p.status==="FT"){statusBadge='<span style="color:var(--muted);font-size:.65rem">FT</span>'}
      else if(p.status==="HT"){statusBadge='<span style="background:var(--yellow);color:#000;padding:2px 6px;border-radius:6px;font-size:.65rem;font-weight:700">INT</span>'}
      html+=`<div style="display:flex;align-items:center;padding:8px;border-bottom:1px solid #1f3460${p.live?';background:rgba(231,76,60,.08);border-radius:6px':''};cursor:${p.fixture_id?'pointer':'default'}" ${p.fixture_id?`onclick="showFixtureDetail(${p.fixture_id},'${p.home}','${p.away}')"`:''}>
        <span style="flex:1;text-align:right;font-weight:700;font-size:.9rem">${badge(p.home,18)}${p.home}</span>
        <div style="text-align:center;min-width:70px">
          <span style="font-size:1.1rem;font-weight:800"><span style="color:${colH}">${p.gol_h}</span> - <span style="color:${colA}">${p.gol_a}</span></span>
          <div>${statusBadge}</div>
        </div>
        <span style="flex:1;font-weight:700;font-size:.9rem">${p.away}${badge(p.away,18)}</span>
      </div>`;
    } else {
      html+=`<div class="match-btn" style="cursor:default"><span>${badge(p.home,18)}<strong>${p.home}</strong> <span style="color:var(--muted)">vs</span> <strong>${p.away}</strong>${badge(p.away,18)}</span></div>`;
    }
  });
  html+=`</div><div id="sim-result-main"></div>
    <div style="margin-top:16px;padding:14px;background:#0d1b2a;border-radius:10px;text-align:center">
      <p style="color:var(--muted);font-size:.9rem">Vuoi analizzare una singola partita nel dettaglio? Vai su <a href="#pronostici" style="color:var(--accent);font-weight:700">Pronostici</a> e calcola il pronostico della partita che ti interessa.</p>
    </div>
  </div>`;

  html+='<div>';

  const future = prossime.filter(g=>g.stato==="prossima");

  if(future.length>0){
    window._calFutureData = future;
    html+=`<div class="card" style="padding:12px">
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:10px">
        <h4 style="color:var(--muted);margin:0">Prossima giornata</h4>
        <select id="sel-giornata-cal" onchange="showGiornataCal()" style="min-height:40px;font-size:.9rem;padding:6px 10px;min-width:130px">
          ${future.map((g,i)=>`<option value="${i}" ${i>0&&userPlan!=="pro"?'disabled':''}>${'G.'+g.giornata+' - '+(g.data||'')}${i>0&&userPlan!=="pro"?' (PRO)':''}</option>`).join('')}
        </select>
      </div>
      <div id="giornata-cal-content">`;
    const g0 = future[0];
    g0.partite.forEach(p=>{
      html+=`<div style="display:flex;align-items:center;padding:8px 0;border-bottom:1px solid #1f3460">
        <span style="flex:1;text-align:right;font-size:.85rem;font-weight:600">${badge(p.home,16)}${p.home}</span>
        <span style="min-width:60px;text-align:center;color:var(--muted);font-size:.8rem">${p.ora||"vs"}</span>
        <span style="flex:1;font-size:.85rem;font-weight:600">${p.away}${badge(p.away,16)}</span>
      </div>`;
    });
    html+=`</div></div>`;
  }

  html+='</div></div>';

  if(cal.live){
    html+=`<div style="text-align:center;color:var(--muted);font-size:.8rem;margin-top:8px">Auto-aggiornamento ogni 60 secondi</div>`;
    _calRefreshTimer = setInterval(async()=>{
      if(location.hash!=="#calendario") return;
      const app=$("app");
      const result = await pageCalendario();
      if(result) app.innerHTML = result;
    }, 60000);
  }

  html+='</div>';
  return html;
}

function showGiornataCal(){
  var sel=document.getElementById("sel-giornata-cal");
  if(!sel||!window._calFutureData)return;
  var g=window._calFutureData[parseInt(sel.value)];
  if(!g)return;
  var c=document.getElementById("giornata-cal-content");
  if(!c)return;
  var h="";
  g.partite.forEach(function(p){
    h+='<div style="display:flex;align-items:center;padding:8px 0;border-bottom:1px solid #1f3460">';
    h+='<span style="flex:1;text-align:right;font-size:.85rem;font-weight:600">'+badge(p.home,16)+p.home+'</span>';
    h+='<span style="min-width:60px;text-align:center;color:var(--muted);font-size:.8rem">'+(p.ora||"vs")+'</span>';
    h+='<span style="flex:1;font-size:.85rem;font-weight:600">'+p.away+badge(p.away,16)+'</span>';
    h+='</div>';
  });
  c.innerHTML=h;
}

async function simulaGiornata(gNum){
  const det=$("sim-result-main");
  if(!det)return;
  det.innerHTML='<div class="spinner"></div>';
  const calUrl = currentLeague==="serie-a" ? "/api/calendario" : "/api/"+currentLeague+"/calendario";
  const cal=await fetchAPI(calUrl);
  if(!cal)return;
  const g=cal.giornate.find(x=>String(x.giornata)===String(gNum));
  if(!g){det.innerHTML='<div class="card">Giornata non trovata</div>';return}
  const leagueLabel = currentLeague==="premier-league"?"Campionato Inglese":currentLeague==="la-liga"?"Campionato Spagnolo":currentLeague==="bundesliga"?"Bundesliga":currentLeague==="ligue-1"?"Campionato Francese":currentLeague==="champions-league"?"Champions League":currentLeague==="europa-league"?"Europa League":currentLeague==="conference-league"?"Conference League":"Campionato Italiano";

  const giocate = g.partite.filter(p=>p.gol_h!==null && p.gol_h!==undefined && (p.status==="FT"||p.status==="AET"||p.status==="PEN"));
  const daGiocareRaw = g.partite.filter(p=>!(p.gol_h!==null && p.gol_h!==undefined && (p.status==="FT"||p.status==="AET"||p.status==="PEN")));

  const isEuro = ["champions-league","europa-league","conference-league"].includes(currentLeague);
  let andata = [];
  let ritorno = [];
  if(isEuro){
    const seen = new Set();
    giocate.forEach(p=>{
      const key = [p.home, p.away].sort().join('|');
      seen.add(key);
      andata.push(p);
    });
    daGiocareRaw.forEach(p=>{
      const key = [p.home, p.away].sort().join('|');
      if(!seen.has(key)){
        seen.add(key);
        ritorno.push(p);
      } else {
        ritorno.push(p);
      }
    });
  } else {
    andata = giocate;
    ritorno = daGiocareRaw;
  }

  let html='<div class="container">';

  if(andata.length>0){
    html+=`<h3 style="margin-bottom:8px;color:var(--green)">${isEuro?'Andata':'Risultati'} - ${leagueLabel}</h3>`;
    html+='<div class="card" style="padding:8px;margin-bottom:12px">';
    andata.forEach(p=>{
      const cH=p.gol_h>p.gol_a?"var(--green)":p.gol_h<p.gol_a?"var(--red)":"var(--yellow)";
      const cA=p.gol_a>p.gol_h?"var(--green)":p.gol_a<p.gol_h?"var(--red)":"var(--yellow)";
      html+=`<div style="display:flex;align-items:center;padding:6px 0;border-bottom:1px solid #1f3460">
        <span style="flex:1;text-align:right;font-size:.85rem;font-weight:600">${badge(p.home,16)}${p.home}</span>
        <span style="min-width:60px;text-align:center;font-weight:800;font-size:1rem"><span style="color:${cH}">${p.gol_h}</span>-<span style="color:${cA}">${p.gol_a}</span></span>
        <span style="flex:1;font-size:.85rem;font-weight:600">${p.away}${badge(p.away,16)}</span>
      </div>`;
    });
    html+='</div>';
  }

  if(ritorno.length>0){
    html+=`<h3 style="margin-bottom:8px;color:var(--accent)">${isEuro?'Ritorno':'Pronostici'} - ${leagueLabel}</h3>`;
    html+='<div style="overflow-x:auto"><table style="width:100%;font-size:.75rem;white-space:nowrap"><thead><tr><th style="text-align:left">Partita</th><th>1</th><th>X</th><th>2</th><th>Tip</th><th>O/U</th><th>Goal</th><th>Doppio</th><th>Aff.</th></tr></thead><tbody>';
    for(const p of ritorno){
      const pronoUrl = "/api"+leagueApiPrefix()+"/pronostico/"+encodeURIComponent(p.home)+"/"+encodeURIComponent(p.away);
      const d=await fetchAPI(pronoUrl);
      if(!d)continue;
      const tipCol=d.suggerimento==="1"?"var(--green)":d.suggerimento==="X"?"var(--yellow)":"var(--red)";
      const ouLbl=d.over_25>50?"Over":"Under";
      const ouVal=d.over_25>50?d.over_25:d.under_25;
      const ouCol=ouVal>60?"var(--green)":ouVal>55?"#8bc34a":"var(--accent)";
      const glLbl=d.goal_si>50?"Si":"No";
      const glVal=d.goal_si>50?d.goal_si:d.goal_no;
      const glCol=glVal>60?"var(--green)":glVal>55?"#8bc34a":"var(--accent)";
      function pCol(v){return v>50?"var(--green)":v>35?"var(--yellow)":"var(--red)"}
      html+=`<tr style="border-bottom:1px solid #1f3460;cursor:pointer" onclick="showMatch('${p.home}','${p.away}')">
        <td style="text-align:left;padding:8px 4px"><strong>${p.home}</strong> - <strong>${p.away}</strong></td>
        <td style="color:${pCol(d.prob_1)};font-weight:${d.prob_1>40?'800':'400'}">${d.prob_1}%</td>
        <td style="color:${pCol(d.prob_x)};font-weight:${d.prob_x>30?'800':'400'}">${d.prob_x}%</td>
        <td style="color:${pCol(d.prob_2)};font-weight:${d.prob_2>40?'800':'400'}">${d.prob_2}%</td>
        <td><span style="color:${tipCol};font-weight:800">${d.suggerimento}</span>${d.sicura?'<span style="background:#ff6b35;color:#fff;font-size:.6rem;padding:1px 4px;border-radius:4px;margin-left:2px">!</span>':''}</td>
        <td><span style="color:${ouCol}">${ouLbl} ${ouVal}%</span></td>
        <td><span style="color:${glCol}">${glLbl} ${glVal}%</span></td>`;
      const tip = d.suggerimento;
      const ou = d.over_25>50 ? "Over" : "Under";
      const gl = d.goal_si>50 ? "Goal" : "NoGoal";
      const combos = [];
      if(tip!=="X"){
        combos.push({nome:tip+" + "+ou, prob: Math.min(d.suggerimento==="1"?d.prob_1:d.prob_2, d.over_25>50?d.over_25:d.under_25)});
        combos.push({nome:tip+" + "+gl, prob: Math.min(d.suggerimento==="1"?d.prob_1:d.prob_2, d.goal_si>50?d.goal_si:d.goal_no)});
      } else {
        combos.push({nome:"X + "+ou, prob: Math.min(d.prob_x, d.over_25>50?d.over_25:d.under_25)});
        combos.push({nome:"X + "+gl, prob: Math.min(d.prob_x, d.goal_si>50?d.goal_si:d.goal_no)});
      }
      combos.sort((a,b)=>b.prob-a.prob);
      const best = combos[0];
      const dCol = best.prob>60?"var(--green)":best.prob>50?"var(--yellow)":"var(--red)";
      html+=`<td><span style="color:${dCol};font-weight:700;font-size:.7rem">${best.nome}</span></td>
        <td><span style="color:${d.confidence_label==="Alta"?"var(--green)":d.confidence_label==="Media"?"var(--yellow)":"var(--red)"};font-weight:700">${Math.round((d.confidence||0)*100)}%</span></td>
      </tr>`;
    }
    html+='</tbody></table></div>';
  } else if(andata.length===0){
    html+='<div class="card" style="text-align:center;padding:16px;color:var(--muted)">Nessuna partita trovata per questa giornata</div>';
  }

  if(andata.length>0 && ritorno.length===0){
    html+='<div style="text-align:center;padding:12px;color:var(--muted);font-size:.85rem">Tutte le partite di questa giornata sono state giocate.</div>';
  }
  html+=`<div style="margin-top:10px;padding:10px;background:#0d1b2a;border-radius:8px;font-size:.7rem;color:var(--muted)">
    <strong style="color:var(--text)">Legenda:</strong>
    <span style="color:var(--green)">  - &#9679; Verde</span> = alta probabilita' (>50%)
    <span style="color:var(--yellow)">  - &#9679; Giallo</span> = media (35-50%)
    <span style="color:var(--red)">  - &#9679; Rosso</span> = bassa (<35%)
    | <strong>Tip</strong> = consiglio 1X2
    | <strong>O/U</strong> = Over/Under 2.5
    | <strong>Aff.</strong> = Affidabilita' del pronostico
    | <span style="background:#ff6b35;color:#fff;padding:0 4px;border-radius:3px">!</span> = pronostico SICURO
  </div>`;
  html+='</div>';
  det.innerHTML=html;
}

async function showMatch(h,a){
  const app=$("app");
  if(userPlan!=="pro" && freeUsed>=FREE_LIMIT){
    app.innerHTML='<div class="container"><div class="card" style="text-align:center;padding:32px"><h2 style="color:var(--yellow)">Hai usato i tuoi 2 pronostici gratuiti!</h2><p style="color:var(--muted);margin:16px 0">Passa a Pro per pronostici illimitati su tutte le partite e giornate.</p><button class="btn btn-green" style="font-size:1.1rem;padding:14px 40px" onclick="abbonarPro()">Abbonati a Pro  -  9.99&euro;/mese</button><br><br><a href="javascript:void(0)" onclick="location.hash=\'\';setTimeout(()=>location.hash=\'#calendario\',50)" style="color:var(--accent)">&#8592; Torna al Calendario</a></div></div>';
    return;
  }
  app.innerHTML='<div class="spinner"></div>';
  const d=await fetchAPI("/api"+leagueApiPrefix()+"/pronostico/"+encodeURIComponent(h)+"/"+encodeURIComponent(a));
  if(!d){app.innerHTML='<div class="container"><div class="card" style="color:var(--red)">Errore calcolo pronostico. <a href="#calendario">Torna</a></div></div>';return}
  if(userPlan!=="pro"){freeUsed++;localStorage.setItem("freeUsed",freeUsed)}
  const best=d.suggerimento||"?";
  const cp=Math.round((d.confidence||0.5)*100);
  const cc=d.confidence_label==="Alta"?"var(--green)":d.confidence_label==="Media"?"var(--yellow)":"var(--red)";
  let extra="";
  if(d.over_25){
    const ouV=Math.max(d.over_25,d.under_25);const ouC=ouV>60?"var(--green)":ouV>55?"#8bc34a":"var(--accent)";
    const glV=Math.max(d.goal_si,d.goal_no);const glC=glV>60?"var(--green)":glV>55?"#8bc34a":"var(--accent)";
    extra=`<div class="grid3" style="margin:16px 0">
      <div class="card" style="text-align:center;padding:12px"><strong>${d.over_25>50?"Over":"Under"} 2.5</strong><br><span style="font-size:1.2rem;font-weight:700;color:${ouC}">${ouV}%</span></div>
      <div class="card" style="text-align:center;padding:12px"><strong>${d.goal_si>50?"Goal Si":"Goal No"}</strong><br><span style="font-size:1.2rem;font-weight:700;color:${glC}">${glV}%</span></div>
      <div class="card" style="text-align:center;padding:12px"><strong>Gol Attesi</strong><br><span style="font-size:1.2rem;font-weight:700;color:${d.gol_attesi>2.5?'var(--green)':'var(--accent)'}">${d.gol_attesi||"-"}</span></div>
    </div>`;
    if(d.risultati_esatti&&d.risultati_esatti.length){
      extra+=`<div class="grid3" style="gap:8px;margin-top:8px">`;
      d.risultati_esatti.slice(0,3).forEach((r,i)=>{
        const bg=i===0?"var(--green)":i===1?"var(--accent)":"var(--muted)";
        extra+=`<div style="text-align:center;padding:10px;background:#0d1b2a;border-radius:8px;border:2px solid ${bg}"><div style="font-size:1.5rem;font-weight:800;color:${bg}">${r.score}</div><div style="color:var(--muted);font-size:.8rem">${r.prob}%</div></div>`;
      });
      extra+=`</div>`;
    }
  }
  app.innerHTML=`<div class="container">
    <a href="javascript:void(0)" onclick="location.hash='';setTimeout(()=>location.hash='#calendario',50)" style="color:var(--accent);display:inline-block;margin-bottom:16px">&#8592; Torna al Calendario</a>
    <div class="card" style="text-align:center">
      <h1>${badge(h,30)}${h} vs ${a}${badge(a,30)}</h1>
      <div class="grid3" style="margin:20px 0">
        <div class="box1x2 ${best==="1"?"best":""}"><div style="color:var(--green)">1</div><div class="pct">${d.prob_1}%</div><div class="quota">Q. ${d.quota_1}</div></div>
        <div class="box1x2 ${best==="X"?"best":""}"><div style="color:var(--yellow)">X</div><div class="pct">${d.prob_x}%</div><div class="quota">Q. ${d.quota_x}</div></div>
        <div class="box1x2 ${best==="2"?"best":""}"><div style="color:var(--red)">2</div><div class="pct">${d.prob_2}%</div><div class="quota">Q. ${d.quota_2}</div></div>
      </div>
      <span class="tag tag-green" style="font-size:1rem;padding:8px 20px">Consiglio: ${best}  -  ${d.sugg_label||""}</span>
      <div style="margin:12px 0"><span style="color:${cc};font-weight:700">Affidabilita': ${d.confidence_label} (${cp}%)</span></div>
      ${extra}
    </div>
  </div>`;
}
