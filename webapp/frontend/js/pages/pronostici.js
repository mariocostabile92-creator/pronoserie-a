// ── pronostici.js - Pagina pronostici, calcolo, risultati ──

function pagePronostici(){
  const leagueLabel = currentLeague==="premier-league"?"Campionato Inglese":currentLeague==="la-liga"?"Campionato Spagnolo":currentLeague==="bundesliga"?"Bundesliga":currentLeague==="ligue-1"?"Campionato Francese":currentLeague==="champions-league"?"Champions League":currentLeague==="europa-league"?"Europa League":currentLeague==="conference-league"?"Conference League":"Campionato Italiano";
  return `<div class="container">
    ${leagueTabs()}
    <div class="card" style="text-align:center;padding:32px">
      <h1>Calcola Pronostico - ${leagueLabel}</h1>
      <p class="sub">Scegli le squadre e scopri il pronostico dell'IA</p>
      <div style="display:flex;justify-content:center;align-items:center;gap:16px;flex-wrap:wrap;margin:24px 0">
        <div><label style="color:var(--green);font-weight:700">CASA</label><br><select id="sel-home">${opts()}</select></div>
        <span style="font-size:1.5rem;font-weight:800;color:var(--yellow)">VS</span>
        <div><label style="color:var(--red);font-weight:700">OSPITE</label><br><select id="sel-away">${opts()}</select></div>
      </div>
      <button class="btn btn-green" style="font-size:1.1rem;padding:16px 48px" onclick="calcPronostico()">CALCOLA PRONOSTICO</button>
    </div>
    <div class="card" style="padding:12px;margin-top:12px;background:#0d1b2a;border-color:var(--accent)">
      <div style="display:flex;align-items:center;justify-content:space-between;cursor:pointer" onclick="var d=document.getElementById('guida-pronostico');d.style.display=d.style.display==='none'?'block':'none'">
        <h4 style="color:var(--accent);margin:0;font-size:.9rem">Come leggere il pronostico</h4>
        <span style="color:var(--accent);font-size:1.2rem">&#9660;</span>
      </div>
      <div id="guida-pronostico" style="display:none;margin-top:12px">
        <div style="display:flex;gap:12px;flex-wrap:wrap;justify-content:center">
          <div style="text-align:center;flex:1;min-width:150px;padding:8px"><strong style="color:var(--text);font-size:.85rem">1 X 2</strong><p style="color:var(--muted);font-size:.75rem;margin-top:4px">1 = casa vince, X = pareggio, 2 = ospite vince</p></div>
          <div style="text-align:center;flex:1;min-width:150px;padding:8px"><strong style="color:var(--green);font-size:.85rem">Confidenza Alta</strong><p style="color:var(--muted);font-size:.75rem;margin-top:4px">Pronostico piu affidabile. G.31: 4/4 corretti</p></div>
          <div style="text-align:center;flex:1;min-width:150px;padding:8px"><strong style="color:var(--text);font-size:.85rem">Over/Under e Goal</strong><p style="color:var(--muted);font-size:.75rem;margin-top:4px">Over 2.5 = 3+ gol. Goal Si = entrambe segnano</p></div>
        </div>
        <p style="color:var(--muted);font-size:.75rem;text-align:center;margin-top:8px"><strong style="color:var(--yellow)">Consiglio:</strong> concentrati sui pronostici con confidenza Alta e probabilita sopra il 55%.</p>
      </div>
    </div>
    <div id="result"></div>
  </div>`;
}

async function calcPronostico(){
  const h=$("sel-home").value, a=$("sel-away").value, res=$("result");
  if(h===a){res.innerHTML='<div class="card" style="color:var(--red)">Scegli due squadre diverse!</div>';return}
  if(userPlan!=="pro" && freeUsed>=FREE_LIMIT){
    res.innerHTML='<div class="card" style="text-align:center;padding:32px"><h2 style="color:var(--yellow)">Hai usato i tuoi 2 pronostici gratuiti!</h2><p style="color:var(--muted);margin:16px 0">Passa a Pro per pronostici illimitati, Over/Under, Goal, Risultato Esatto e molto altro.</p><button class="btn btn-green" style="font-size:1.1rem;padding:14px 40px" onclick="abbonarPro()">Abbonati a Pro  -  9.99&euro;/mese</button></div>';
    return;
  }
  res.innerHTML='<div class="spinner"></div>';
  const d=await fetchAPI("/api"+leagueApiPrefix()+"/pronostico/"+encodeURIComponent(h)+"/"+encodeURIComponent(a));
  if(!d){res.innerHTML='<div class="card" style="color:var(--red)">Errore. Riprova tra qualche secondo.</div>';return}
  const best=d.suggerimento||"?";
  const cc=d.confidence_label==="Alta"?"var(--green)":d.confidence_label==="Media"?"var(--yellow)":"var(--red)";
  const cp=Math.round((d.confidence||0.5)*100);
  let extra="";
  if(d.over_25){
    const ouVal=Math.max(d.over_25,d.under_25);
    const ouLbl=d.over_25>50?"Over 2.5":"Under 2.5";
    const ouCol=ouVal>60?"var(--green)":ouVal>55?"#8bc34a":"var(--accent)";
    const glVal=Math.max(d.goal_si,d.goal_no);
    const glLbl=d.goal_si>50?"Goal Si":"Goal No";
    const glCol=glVal>60?"var(--green)":glVal>55?"#8bc34a":"var(--accent)";
    extra=`<div class="grid3" style="margin:16px 0">
      <div class="card" style="text-align:center;padding:12px"><strong>${ouLbl}</strong><br><span style="font-size:1.3rem;font-weight:700;color:${ouCol}">${ouVal}%</span></div>
      <div class="card" style="text-align:center;padding:12px"><strong>${glLbl}</strong><br><span style="font-size:1.3rem;font-weight:700;color:${glCol}">${glVal}%</span></div>
      <div class="card" style="text-align:center;padding:12px"><strong>Gol Attesi</strong><br><span style="font-size:1.3rem;font-weight:700;color:${d.gol_attesi>2.5?'var(--green)':'var(--accent)'}">${d.gol_attesi||"-"}</span></div>
    </div>`;
    if(d.risultati_esatti&&d.risultati_esatti.length){
      extra+=`<div style="margin-top:16px"><h4 style="color:var(--accent);margin-bottom:8px">Risultato Esatto Piu' Probabile</h4><div class="grid3" style="gap:8px">`;
      d.risultati_esatti.slice(0,3).forEach((r,i)=>{
        const bg=i===0?"var(--green)":i===1?"var(--accent)":"var(--muted)";
        extra+=`<div style="text-align:center;padding:12px;background:#0d1b2a;border-radius:10px;border:2px solid ${bg}"><div style="font-size:1.8rem;font-weight:800;color:${bg}">${r.score}</div><div style="color:var(--muted);font-size:.85rem">${r.prob}%</div></div>`;
      });
      extra+=`</div>`;
      if(d.risultati_esatti.length>3){
        extra+=`<div style="display:flex;gap:8px;margin-top:6px;justify-content:center">`;
        d.risultati_esatti.slice(3,5).forEach(r=>{
          extra+=`<span style="color:var(--muted);font-size:.85rem">${r.score} (${r.prob}%)</span>`;
        });
        extra+=`</div>`;
      }
      extra+=`</div>`;
    }
    const ouTip=d.over_25>50?"Over 2.5":"Under 2.5";
    const ouProb=Math.max(d.over_25,d.under_25);
    const glTip=d.goal_si>50?"Goal Si":"Goal No";
    const glProb=Math.max(d.goal_si,d.goal_no);
    const giocate=[
      {nome:`1X2: ${best}`,prob:Math.max(d.prob_1,d.prob_x,d.prob_2),quota:best==="1"?d.quota_1:best==="X"?d.quota_x:d.quota_2},
      {nome:ouTip,prob:ouProb,quota:ouProb>55?1.85:2.10},
      {nome:glTip,prob:glProb,quota:glProb>55?1.75:2.00},
    ];
    giocate.sort((a,b)=>b.prob-a.prob);
    extra+=`<div style="margin-top:16px;padding:16px;background:linear-gradient(135deg,#0d3b1e,#162447);border-radius:12px;border:2px solid var(--green)">
      <h4 style="color:var(--green);margin-bottom:8px;text-align:center">Pronostico Migliore Consigliato dall'IA</h4>
      <div style="text-align:center"><span style="font-size:1.5rem;font-weight:800;color:var(--green)">${giocate[0].nome}</span><br><span style="color:var(--muted)">Probabilita': ${giocate[0].prob}% | Quota ~${giocate[0].quota}</span></div>
      <div style="display:flex;justify-content:center;gap:12px;margin-top:8px;flex-wrap:wrap">
        ${giocate.slice(1).map(g=>`<span style="color:var(--muted);font-size:.85rem">${g.nome}: ${g.prob}%</span>`).join(" | ")}
      </div>
    </div>`;
    if(d.marcatori_casa||d.marcatori_ospite){
      extra+=`<div style="margin-top:12px;padding:12px;background:#0d1b2a;border-radius:8px"><h4 style="color:var(--green);margin-bottom:8px">Probabili Marcatori</h4>`;
      if(d.marcatori_casa&&d.marcatori_casa.length)extra+=`<p style="color:var(--text);font-size:.9rem"><strong style="color:var(--green)">${h}:</strong> ${d.marcatori_casa.join(" &middot; ")}</p>`;
      if(d.marcatori_ospite&&d.marcatori_ospite.length)extra+=`<p style="color:var(--text);font-size:.9rem;margin-top:4px"><strong style="color:var(--red)">${a}:</strong> ${d.marcatori_ospite.join(" &middot; ")}</p>`;
      extra+=`</div>`;
    }
    if(userToken){
      const ouTxt = d.over_25>50?'Over 2.5':'Under 2.5';
      const glTxt = d.goal_si>50?'Goal Si':'Goal No';
      window._lastPrediction = {home:h, away:a, pronostico:best, prob:Math.max(d.prob_1,d.prob_x,d.prob_2), confidence:d.confidence_label, over_under:ouTxt, goal:glTxt, league:currentLeague};
      extra+=`<div style="margin-top:12px;text-align:center">
        <button class="btn btn-green" style="font-size:.9rem;padding:10px 24px" onclick="saveLastPrediction()">
          Salva nel tuo storico
        </button>
        <div id="save-pred-msg" style="margin-top:6px;font-size:.8rem"></div>
      </div>`;
    }
    if(d.formazione_casa||d.formazione_ospite){
      extra+=`<div style="margin-top:12px;padding:16px;background:#0d1b2a;border-radius:8px"><h4 style="color:var(--accent);margin-bottom:12px">Probabili Formazioni</h4>`;
      [["casa",h,d.formazione_casa,"var(--green)"],[" ospite",a,d.formazione_ospite,"var(--red)"]].forEach(([tipo,nome,form,col])=>{
        if(form){
          extra+=`<div style="margin-bottom:12px"><strong style="color:${col};font-size:1rem">${nome} (${form.modulo})</strong><div style="background:#2d8a4e;border-radius:8px;padding:12px;margin-top:6px;text-align:center">`;
          form.titolari.forEach(g=>{
            extra+=`<span style="display:inline-block;background:${col};color:#fff;padding:3px 10px;border-radius:12px;font-size:.75rem;margin:2px;font-weight:600">${g}</span>`;
          });
          extra+=`</div></div>`;
        }
      });
      extra+=`</div>`;
    }
  }
  if(userPlan!=="pro"){freeUsed++;localStorage.setItem("freeUsed",freeUsed)}
  const remaining = userPlan==="pro" ? "" : `<p style="color:var(--muted);text-align:center;margin-top:12px;font-size:.85rem">Pronostici gratuiti rimanenti: ${Math.max(0,FREE_LIMIT-freeUsed)}/${FREE_LIMIT}</p>`;
  res.innerHTML=`<div class="card">
    <h2 style="text-align:center">${badge(h,28)}${h} vs ${a}${badge(a,28)}</h2>
    <div style="text-align:center;margin:16px 0;padding:16px;background:linear-gradient(135deg,#0d3b1e,#162447);border-radius:12px;border:2px solid var(--green)">
      <div style="font-size:.85rem;color:var(--muted);margin-bottom:4px">Consiglio MatchIQ</div>
      <span style="font-size:1.8rem;font-weight:800;color:var(--green)">${best}</span>
      <span style="font-size:1.1rem;color:var(--text);margin-left:8px">${d.sugg_label||""}</span>
      ${d.sicura?' <span class="tag" style="background:#ff6b35;color:#fff;font-size:.8rem;padding:4px 12px;margin-left:8px">SICURA</span>':''}
      <div style="margin-top:8px"><span style="color:${cc};font-weight:700">Affidabilita: ${d.confidence_label} (${cp}%)</span></div>
      <div class="bar" style="max-width:250px;margin:6px auto 0"><div class="bar-fill" style="width:${cp}%;background:${cc}"></div></div>
    </div>
    <div class="grid3" style="margin:16px 0">
      <div class="box1x2 ${best==="1"?"best":""}"><div style="color:var(--green);font-weight:700">1 Casa</div><div class="pct">${d.prob_1}%</div><div class="quota">Quota ${d.quota_1}</div></div>
      <div class="box1x2 ${best==="X"?"best":""}"><div style="color:var(--yellow);font-weight:700">X Pareggio</div><div class="pct">${d.prob_x}%</div><div class="quota">Quota ${d.quota_x}</div></div>
      <div class="box1x2 ${best==="2"?"best":""}"><div style="color:var(--red);font-weight:700">2 Ospite</div><div class="pct">${d.prob_2}%</div><div class="quota">Quota ${d.quota_2}</div></div>
    </div>
    ${extra}
    ${remaining}
  </div>`;
}
