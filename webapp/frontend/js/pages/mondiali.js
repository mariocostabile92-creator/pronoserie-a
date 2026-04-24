// ── mondiali.js - Pagina Mondiali 2026 con gironi e fasi finali ──

async function pageMondiali(){
  const data = await fetchAPI("/api/mondiali-2026/gironi", true);
  if(!data || !data.gironi) return '<div class="container"><div class="card" style="color:var(--red)">Errore caricamento dati Mondiali 2026</div></div>';

  const gironi = data.gironi;
  const partite_g = data.partite_gironi || {};
  const fasi = data.fasi_finale || {};
  const letters = Object.keys(gironi).sort();

  let html='<div class="container">';
  html+='<h1 style="text-align:center">&#127942; FIFA World Cup 2026</h1>';
  html+='<p class="sub" style="text-align:center">USA - Canada - Messico | 11 giugno - 19 luglio 2026</p>';
  html+=`<p style="text-align:center;color:var(--green);font-weight:700;margin-bottom:16px">${data.totale_partite || 72} partite | 48 squadre | 12 gironi</p>`;

  html+='<div style="display:flex;flex-wrap:wrap;gap:2px;margin-bottom:16px;justify-content:center">';
  letters.forEach((g,i)=>{
    const active = i===0;
    html+=`<button class="wc-tab" data-girone="${g}" style="padding:6px 10px;border:none;cursor:pointer;font-weight:700;font-size:.75rem;border-radius:6px;${active?'background:var(--green);color:#000':'background:#1f3460;color:var(--muted)'}" onclick="showWCGirone('${g}')">${g}</button>`;
  });
  html+='</div>';

  letters.forEach((g,i)=>{
    const squadre = gironi[g] || [];
    const partite = partite_g[g] || [];
    const display = i===0 ? 'block' : 'none';

    html+=`<div id="wc-girone-${g}" class="wc-girone-panel" style="display:${display}">`;
    html+=`<div class="card" style="padding:12px;margin-bottom:10px;border-left:3px solid var(--green)">`;
    html+=`<h3 style="color:var(--green);margin-bottom:10px">Girone ${g}</h3>`;

    html+='<table style="width:100%;font-size:.8rem;border-collapse:collapse">';
    html+='<tr style="color:var(--muted);border-bottom:1px solid #1f3460"><th style="text-align:left;padding:4px">Pos</th><th style="text-align:left">Squadra</th><th>G</th><th>V</th><th>P</th><th>S</th><th>GF</th><th>GS</th><th>Diff</th><th style="font-weight:800">Pt</th></tr>';
    squadre.forEach((s,idx)=>{
      const rowColor = idx < 2 ? 'color:#2ecc71' : idx === 2 ? 'color:#f39c12' : 'color:var(--text)';
      const bg = idx < 2 ? 'background:rgba(46,204,113,.08)' : idx === 2 ? 'background:rgba(243,156,18,.05)' : '';
      html+=`<tr style="${rowColor};${bg};border-bottom:1px solid #0d1b2a">
        <td style="padding:4px;font-weight:700">${s.pos}</td>
        <td style="font-weight:600">${s.squadra}</td>
        <td style="text-align:center">${s.g}</td>
        <td style="text-align:center">${s.v}</td>
        <td style="text-align:center">${s.p}</td>
        <td style="text-align:center">${s.s}</td>
        <td style="text-align:center">${s.gf}</td>
        <td style="text-align:center">${s.gs}</td>
        <td style="text-align:center">${s.diff>0?'+':''}${s.diff}</td>
        <td style="text-align:center;font-weight:800;font-size:1rem">${s.punti}</td>
      </tr>`;
    });
    html+='</table>';
    html+='<div style="margin-top:6px;font-size:.7rem"><span style="color:#2ecc71">&#9632;</span> Qualificate &nbsp;<span style="color:#f39c12">&#9632;</span> Possibile miglior terza</div>';
    html+='</div>';

    if(partite.length > 0){
      html+=`<div class="card" style="padding:12px;margin-bottom:10px">`;
      html+=`<h4 style="color:var(--accent);margin-bottom:8px">Partite Girone ${g}</h4>`;
      partite.forEach(p=>{
        const score = p.gol_h !== null ? `${p.gol_h} - ${p.gol_a}` : 'vs';
        const statusLabel = p.status === 'FT' ? '<span style="color:#2ecc71;font-size:.7rem"> FT</span>' :
                           p.status === 'NS' ? `<span style="color:var(--muted);font-size:.7rem"> ${p.data} ${p.ora}</span>` :
                           `<span style="color:#e74c3c;font-size:.7rem"> LIVE</span>`;
        html+=`<div style="display:flex;align-items:center;justify-content:space-between;padding:6px 0;border-bottom:1px solid #0d1b2a;cursor:pointer" onclick="switchLeague('mondiali-2026');navigate('pronostici')">
          <span style="flex:1;text-align:right;font-size:.85rem;font-weight:600">${p.home}</span>
          <span style="min-width:60px;text-align:center;font-weight:800;font-size:.9rem;color:var(--green)">${score}</span>
          <span style="flex:1;text-align:left;font-size:.85rem;font-weight:600">${p.away}</span>
          ${statusLabel}
        </div>`;
      });
      html+='</div>';
    }

    html+='</div>';
  });

  const fasiKeys = Object.keys(fasi);
  if(fasiKeys.length > 0){
    html+=`<div class="card" style="padding:12px;margin-top:16px;border-left:3px solid var(--accent)">`;
    html+=`<h3 style="color:var(--accent);margin-bottom:10px">&#127942; Fase a eliminazione diretta</h3>`;
    fasiKeys.forEach(fase=>{
      html+=`<h4 style="color:var(--yellow);margin:10px 0 6px">${fase}</h4>`;
      fasi[fase].forEach(p=>{
        const score = p.gol_h !== null ? `${p.gol_h} - ${p.gol_a}` : 'vs';
        html+=`<div style="display:flex;align-items:center;justify-content:space-between;padding:6px 0;border-bottom:1px solid #0d1b2a">
          <span style="flex:1;text-align:right;font-size:.85rem;font-weight:600">${p.home}</span>
          <span style="min-width:60px;text-align:center;font-weight:800;font-size:.9rem;color:var(--accent)">${score}</span>
          <span style="flex:1;text-align:left;font-size:.85rem;font-weight:600">${p.away}</span>
          <span style="color:var(--muted);font-size:.7rem">${p.data}</span>
        </div>`;
      });
    });
    html+='</div>';
  }

  html+=`<div class="card" style="text-align:center;padding:12px;margin-top:16px;background:#0d1b2a">
    <p style="color:var(--muted);font-size:.75rem">Dati aggiornati live da API Football. Clicca su una partita per il pronostico IA.</p>
  </div>`;

  html+='</div>';
  return html;
}

function showWCGirone(g){
  document.querySelectorAll('.wc-girone-panel').forEach(el=>el.style.display='none');
  document.querySelectorAll('.wc-tab').forEach(el=>{el.style.background='#1f3460';el.style.color='var(--muted)';});
  const panel = document.getElementById('wc-girone-'+g);
  if(panel) panel.style.display='block';
  const tab = document.querySelector(`.wc-tab[data-girone="${g}"]`);
  if(tab){tab.style.background='var(--green)';tab.style.color='#000';}
}
