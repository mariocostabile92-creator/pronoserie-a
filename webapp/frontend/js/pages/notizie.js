// ── notizie.js - Pagina notizie live dal calcio ──

async function pageNotizie(){
  if(userPlan!=="pro") return `<div class="container"><div class="lock-msg card"><h2>Notizie dal Calcio</h2><p style="margin:16px 0">Le notizie live dal mondo del calcio sono disponibili per gli utenti Pro</p><button class="btn btn-green" onclick="abbonarPro()">Abbonati a Pro  -  9.99&euro;/mese</button></div></div>`;
  const data=await fetchAPI("/api/notizie");
  if(!data)return '<div class="container"><div class="card" style="color:var(--red)">Errore caricamento notizie</div></div>';
  let html='<div class="container"><h1>Notizie dal Calcio</h1><p class="sub">Aggiornamento live  -  '+( data.aggiornamento||"In tempo reale")+'</p>';
  (data.notizie||[]).forEach(n=>{
    html+=`<a href="${n.url||'#'}" ${n.url&&n.url.startsWith('http')?'target="_blank"':''} style="text-decoration:none"><div class="card" style="cursor:pointer;transition:.2s;padding:16px" onmouseover="this.style.borderColor='var(--accent)'" onmouseout="this.style.borderColor='#1f3460'"><h3 style="color:var(--text);font-size:1rem;margin-bottom:4px">${n.titolo}</h3><span style="color:var(--muted);font-size:.8rem">${n.fonte||"Serie A"}</span></div></a>`;
  });
  html+='</div>';
  return html;
}
