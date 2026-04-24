// ── accuratezza.js - Dashboard accuratezza pronostici ──

async function pageAccuratezza(){
  const data = await fetchAPI("/api/accuratezza", true);
  if(!data || !data.giornate) return '<div class="container"><div class="card" style="text-align:center;padding:32px"><div class="spinner"></div><p style="color:var(--muted);margin-top:12px">Calcolo accuratezza in corso... Potrebbe richiedere qualche secondo.</p></div></div>';
  const t = data.totale || {};
  let html = '<div class="container">';
  html += '<h1>Dashboard Accuratezza</h1><p class="sub">Pronostici IA vs Risultati Reali - Aggiornamento automatico</p>';

  html += `<div class="grid3" style="margin-bottom:16px">
    <div class="card" style="text-align:center;padding:16px;border-color:var(--green)">
      <div style="font-size:2rem;font-weight:800;color:var(--green)">${t.acc_1x2||0}%</div>
      <div style="color:var(--muted);font-size:.8rem">1X2 (${t.partite||0} partite)</div>
    </div>
    <div class="card" style="text-align:center;padding:16px">
      <div style="font-size:2rem;font-weight:800;color:var(--accent)">${t.acc_ou||0}%</div>
      <div style="color:var(--muted);font-size:.8rem">Over/Under</div>
    </div>
    <div class="card" style="text-align:center;padding:16px;border-color:var(--green)">
      <div style="font-size:2rem;font-weight:800;color:var(--green)">${t.acc_alta||0}%</div>
      <div style="color:var(--muted);font-size:.8rem">Confidenza Alta (${t.tot_alta||0})</div>
    </div>
  </div>`;

  data.giornate.forEach(g => {
    const colAcc = g.acc_1x2 >= 70 ? "var(--green)" : g.acc_1x2 >= 50 ? "var(--yellow)" : "var(--red)";
    const campCol = g.league_key === "premier-league" ? "var(--accent)" : g.league_key === "la-liga" ? "#f39c12" : "var(--green)";
    html += `<div class="card" style="padding:10px;margin-bottom:8px">
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:6px;cursor:pointer" onclick="var d=this.nextElementSibling;d.style.display=d.style.display==='none'?'block':'none'">
        <div>
          <span style="color:${campCol};font-weight:700;font-size:.85rem">${g.campionato}</span>
          <span style="color:var(--muted);font-size:.8rem"> - G.${g.giornata}</span>
        </div>
        <div style="display:flex;align-items:center;gap:10px">
          <span style="color:${colAcc};font-weight:800;font-size:1.1rem">${g.ok_1x2}/${g.totale}</span>
          <span style="color:${colAcc};font-weight:700;font-size:.9rem">${g.acc_1x2}%</span>
          <span style="color:var(--muted);font-size:1rem">&#9660;</span>
        </div>
      </div>
      <div style="display:none">`;
    g.dettagli.forEach(d => {
      const col = d.corretto ? "var(--green)" : "var(--red)";
      const segno = d.corretto ? "&#10004;" : "&#10006;";
      html += `<div style="display:flex;align-items:center;padding:4px 0;border-bottom:1px solid #1f3460;font-size:.8rem">
        <span style="color:${col};min-width:20px;font-weight:700">${segno}</span>
        <span style="flex:1">${d.home} ${d.gol_h}-${d.gol_a} ${d.away}</span>
        <span style="color:${col};min-width:60px;text-align:right">IA: ${d.pronostico}</span>
        ${d.confidenza==="Alta"?'<span style="color:var(--green);font-size:.65rem;margin-left:4px">ALTA</span>':''}
      </div>`;
    });
    html += `<div style="display:flex;gap:12px;margin-top:6px;font-size:.75rem;color:var(--muted)">
      <span>O/U: ${g.acc_ou}%</span><span>Goal: ${g.acc_goal}%</span>
      ${g.tot_alta>0?`<span style="color:var(--green)">Alta: ${g.ok_alta}/${g.tot_alta} (${g.acc_alta}%)</span>`:''}
    </div></div></div>`;
  });

  html += `<div class="card" style="text-align:center;padding:16px;background:linear-gradient(135deg,#0d3b1e,#162447);border-color:var(--green)">
    <p style="color:var(--text);font-size:.9rem">Questi risultati sono <strong>calcolati in tempo reale</strong> confrontando i pronostici dell'IA con i risultati effettivi delle partite.</p>
    <a href="#pronostici" class="btn btn-green" style="margin-top:12px">Calcola il prossimo pronostico</a>
  </div>`;

  html += '</div>';
  return html;
}
