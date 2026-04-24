// ── pricing.js - Pagina pricing e piani ──

function pagePricing(){
  if(userPlan==="pro") return `<div class="container" style="text-align:center"><div class="card" style="padding:40px;border-color:var(--green)"><h1 style="color:var(--green)">Sei gia' Pro!</h1><p style="color:var(--muted);margin:16px 0;font-size:1.1rem">Hai accesso completo a tutte le funzionalita' di MatchIQ.</p><div style="font-size:3rem;margin:20px 0">&#11088;</div><p style="color:var(--text)">Il tuo abbonamento e' attivo. Grazie per il supporto!</p><a href="#home" class="btn btn-green" style="margin-top:20px">Torna alla Home</a></div></div>`;

  const features = [
    ["Pronostici al giorno", "2", "Illimitati"],
    ["Campionati", "Italiano + Inglese", "Italiano + Inglese"],
    ["Pronostico 1X2 con probabilita'", true, true],
    ["Over/Under e Goal/NoGoal", true, true],
    ["Risultato esatto", false, true],
    ["Simula Pronostici Giornata", false, true],
    ["Classifica + Marcatori live", false, true],
    ["Rose complete 40 squadre", false, true],
    ["Probabili formazioni live", false, true],
    ["Infortunati aggiornati", false, true],
    ["Pronostico del Giorno IA", "Solo 2 pronostici", "Completa (5 pronostici)"],
    ["Badge SICURA (confidenza Alta)", false, true],
    ["Notizie dal Calcio", false, true],
    ["Notifiche gol Telegram", false, true],
    ["Risultati Live con statistiche", false, true],
  ];

  let rows = "";
  features.forEach(([name, free, pro]) => {
    let freeVal, proVal;
    if(typeof free === "boolean") freeVal = free ? '<span style="color:var(--green)">&#10004;</span>' : '<span style="color:var(--red)">&#10006;</span>';
    else freeVal = `<span style="color:${free==='2'||free.includes('Solo')?'var(--yellow)':'var(--green)'}; font-weight:700;font-size:.85rem">${free}</span>`;
    if(typeof pro === "boolean") proVal = pro ? '<span style="color:var(--green)">&#10004;</span>' : '<span style="color:var(--red)">&#10006;</span>';
    else proVal = `<span style="color:var(--green);font-weight:700;font-size:.85rem">${pro}</span>`;
    rows += `<div style="display:flex;align-items:center;padding:10px 0;border-bottom:1px solid #1f3460"><span style="flex:2;font-size:.9rem;color:var(--text)">${name}</span><span style="flex:1;text-align:center">${freeVal}</span><span style="flex:1;text-align:center">${proVal}</span></div>`;
  });

  return `<div class="container" style="text-align:center">
    <h1>Piani e Prezzi</h1>
    <p class="sub">Scegli il piano adatto a te</p>
    <div style="max-width:750px;margin:24px auto">
      <div class="card" style="padding:0;overflow:hidden">
        <div style="display:flex;border-bottom:2px solid #1f3460">
          <div style="flex:2;padding:20px;text-align:left"><h3 style="color:var(--text)">Funzionalita'</h3></div>
          <div style="flex:1;padding:20px;text-align:center;background:#162447"><h3 style="color:var(--muted)">Free</h3><div style="font-size:1.5rem;font-weight:800;color:var(--muted)">0&euro;</div><p style="color:var(--muted);font-size:.75rem">per sempre</p></div>
          <div style="flex:1;padding:20px;text-align:center;background:linear-gradient(135deg,#0d3b1e,#162447);border-left:2px solid var(--green)"><div class="tag tag-green" style="font-size:.7rem;margin-bottom:4px">CONSIGLIATO</div><h3 style="color:var(--green)">Pro</h3><div style="font-size:1.5rem;font-weight:800;color:var(--green)">9.99&euro;</div><p style="color:var(--muted);font-size:.75rem">/mese</p></div>
        </div>
        <div style="padding:0 20px">${rows}</div>
        <div style="display:flex;border-top:2px solid #1f3460">
          <div style="flex:2"></div>
          <div style="flex:1;padding:20px;text-align:center"><a href="#pronostici" class="btn btn-blue" style="font-size:.9rem;padding:10px 20px">Inizia Gratis</a></div>
          <div style="flex:1;padding:20px;text-align:center;border-left:2px solid var(--green)"><button class="btn btn-green" style="font-size:.9rem;padding:10px 20px" onclick="abbonarPro()">Abbonati Pro</button></div>
        </div>
      </div>
    </div>
    <div class="card" style="max-width:750px;margin:20px auto;padding:20px;background:linear-gradient(135deg,#0d3b1e,#162447);border-color:var(--green)">
      <h3 style="color:var(--green);margin-bottom:8px">Perche' passare a Pro?</h3>
      <div class="grid3" style="margin-top:12px;gap:16px">
        <div style="text-align:center"><div style="font-size:2rem;margin-bottom:4px">&#127942;</div><strong style="font-size:.9rem">G.31: 8/10 azzeccati</strong><p style="color:var(--muted);font-size:.8rem">L'IA ha centrato l'80% dei pronostici</p></div>
        <div style="text-align:center"><div style="font-size:2rem;margin-bottom:4px">&#127919;</div><strong style="font-size:.9rem">Confidenza Alta: 100%</strong><p style="color:var(--muted);font-size:.8rem">4 pronostici sicuri su 4 corretti</p></div>
        <div style="text-align:center"><div style="font-size:2rem;margin-bottom:4px">&#9889;</div><strong style="font-size:.9rem">Pronostici illimitati</strong><p style="color:var(--muted);font-size:.8rem">Analizza tutte le partite che vuoi</p></div>
      </div>
      <div style="text-align:center;margin-top:16px"><button class="btn btn-green" style="font-size:1.1rem;padding:14px 40px" onclick="abbonarPro()">Abbonati a Pro - Solo 9.99&euro;/mese</button></div>
    </div>
  </div>`;
}
