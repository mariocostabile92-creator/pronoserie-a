// ── profilo.js - Pagina login, registrazione, profilo utente, pronostici personali ──

function pageLogin(){
  if(userToken){
    return `<div class="container">
      <h1>Il tuo Account</h1>
      <div class="grid2" style="grid-template-columns:1fr 1fr;gap:16px">
        <div>
          <div class="card" style="padding:24px">
            <h3 style="margin-bottom:12px">Profilo</h3>
            <p style="color:var(--muted);margin:8px 0">Email</p>
            <p style="font-weight:700;font-size:1.1rem">${userEmail}</p>
            <p style="color:var(--muted);margin:12px 0 4px">Piano attuale</p>
            <p><span class="tag ${userPlan==="pro"?"tag-green":"tag-blue"}" style="font-size:1rem;padding:6px 20px">${userPlan==="pro"?"PRO":"FREE"}</span></p>
            ${userPlan!=="pro"?'<div style="margin-top:16px"><button class="btn btn-green" style="width:100%" onclick="abbonarPro()">Passa a Pro - 9.99&euro;/mese</button></div>':'<p style="color:var(--green);margin-top:16px;font-weight:700">Accesso completo attivo</p>'}
          </div>
          <div class="card" style="padding:24px;margin-top:16px">
            <h3 style="margin-bottom:12px">Pronostici utilizzati</h3>
            <p style="color:var(--muted)">Oggi: <strong style="color:var(--text)">${freeUsed}/${userPlan==="pro"?"Illimitati":FREE_LIMIT}</strong></p>
            ${userPlan!=="pro"?'<div class="bar" style="margin-top:8px"><div class="bar-fill" style="width:'+(freeUsed/FREE_LIMIT*100)+'%;background:var(--accent)"></div></div>':''}
          </div>
        </div>
        <div>
          <div class="card" style="padding:24px">
            <h3 style="margin-bottom:12px">Cambia Password</h3>
            <input id="old-pass" type="password" placeholder="Password attuale" style="width:100%;padding:10px;border-radius:8px;border:1px solid #1f3460;background:#0d1b2a;color:var(--text);margin-bottom:10px;font-size:.95rem">
            <input id="new-pass" type="password" placeholder="Nuova password (min 6 caratteri)" style="width:100%;padding:10px;border-radius:8px;border:1px solid #1f3460;background:#0d1b2a;color:var(--text);margin-bottom:10px;font-size:.95rem">
            <input id="new-pass2" type="password" placeholder="Conferma nuova password" style="width:100%;padding:10px;border-radius:8px;border:1px solid #1f3460;background:#0d1b2a;color:var(--text);margin-bottom:12px;font-size:.95rem">
            <button class="btn btn-blue" style="width:100%" onclick="doChangePassword()">Aggiorna Password</button>
            <div id="change-pass-msg" style="margin-top:8px;text-align:center"></div>
          </div>
          <div class="card" style="padding:24px;margin-top:16px;text-align:center">
            <button class="btn" style="background:var(--red);color:#fff;width:100%" onclick="doLogout()">Esci dall'account</button>
          </div>
        </div>
      </div>
      <div class="card" style="padding:20px;margin-top:16px;border-color:var(--accent)">
        <h3 style="color:var(--accent);margin-bottom:8px">I Miei Pronostici</h3>
        <p style="color:var(--muted);font-size:.85rem;margin-bottom:12px">Vedi il tuo storico, quanti ne hai azzeccati e le tue statistiche personali.</p>
        <a href="#miei" class="btn btn-blue" style="width:100%">Vedi i miei pronostici</a>
      </div>
      <div class="card" style="padding:20px;margin-top:16px;border-color:var(--green);background:linear-gradient(135deg,#0d3b1e,#162447)">
        <h3 style="color:var(--green);margin-bottom:8px">Invita un amico</h3>
        <p style="color:var(--muted);font-size:.85rem;margin-bottom:12px">Condividi il tuo link. Quando un amico si registra, ottieni <strong style="color:var(--green)">1 mese Pro gratis</strong>!</p>
        <div id="referral-section"><button class="btn btn-green" style="width:100%" onclick="loadReferralCode()">Ottieni il tuo link referral</button></div>
      </div>
    </div>`;
  }
  return `<div class="container">
    <div class="card" style="max-width:450px;margin:40px auto;padding:32px">
      <div style="display:flex;gap:0;margin-bottom:24px">
        <button id="tab-login" class="btn btn-blue" style="flex:1;border-radius:12px 0 0 12px" onclick="showLoginTab('login')">Accedi</button>
        <button id="tab-reg" class="btn" style="flex:1;border-radius:0 12px 12px 0;background:#1f3460;color:var(--muted)" onclick="showLoginTab('reg')">Registrati</button>
      </div>
      <div id="login-form">
        <input id="login-email" type="email" placeholder="Email" style="width:100%;padding:12px;border-radius:8px;border:1px solid #1f3460;background:#0d1b2a;color:var(--text);margin-bottom:12px;font-size:1rem">
        <div style="position:relative">
          <input id="login-pass" type="password" placeholder="Password" style="width:100%;padding:12px;border-radius:8px;border:1px solid #1f3460;background:#0d1b2a;color:var(--text);margin-bottom:8px;font-size:1rem;padding-right:60px">
          <button onclick="togglePass('login-pass',this)" style="position:absolute;right:8px;top:8px;background:none;border:none;color:var(--accent);cursor:pointer;font-size:.85rem">Mostra</button>
        </div>
        <div style="text-align:right;margin-bottom:12px"><a href="javascript:void(0)" onclick="showLoginTab('recover')" style="font-size:.85rem;color:var(--accent)">Password dimenticata?</a></div>
        <button class="btn btn-green" style="width:100%;font-size:1rem" onclick="doLogin()">Accedi</button>
      </div>
      <div id="reg-form" style="display:none">
        <input id="reg-email" type="email" placeholder="Email" style="width:100%;padding:12px;border-radius:8px;border:1px solid #1f3460;background:#0d1b2a;color:var(--text);margin-bottom:12px;font-size:1rem">
        <div style="position:relative">
          <input id="reg-pass" type="password" placeholder="Password (min 6 caratteri)" style="width:100%;padding:12px;border-radius:8px;border:1px solid #1f3460;background:#0d1b2a;color:var(--text);margin-bottom:16px;font-size:1rem;padding-right:60px">
          <button onclick="togglePass('reg-pass',this)" style="position:absolute;right:8px;top:8px;background:none;border:none;color:var(--accent);cursor:pointer;font-size:.85rem">Mostra</button>
        </div>
        <button class="btn btn-green" style="width:100%;font-size:1rem" onclick="doRegister()">Registrati Gratis</button>
      </div>
      <div id="recover-form" style="display:none">
        <p style="color:var(--muted);margin-bottom:16px;font-size:.9rem">Inserisci la tua email. Se l'account esiste, riceverai una nuova password.</p>
        <input id="recover-email" type="email" placeholder="La tua email" style="width:100%;padding:12px;border-radius:8px;border:1px solid #1f3460;background:#0d1b2a;color:var(--text);margin-bottom:12px;font-size:1rem">
        <button class="btn btn-blue" style="width:100%;font-size:1rem" onclick="doRecover()">Recupera Password</button>
        <div style="text-align:center;margin-top:12px"><a href="javascript:void(0)" onclick="showLoginTab('login')" style="font-size:.85rem;color:var(--accent)">&#8592; Torna al login</a></div>
      </div>
      <div id="auth-msg" style="margin-top:12px;text-align:center"></div>
    </div>
  </div>`;
}

function showLoginTab(tab){
  $("login-form").style.display = tab==="login"?"block":"none";
  $("reg-form").style.display = tab==="reg"?"block":"none";
  $("recover-form").style.display = tab==="recover"?"block":"none";
  $("tab-login").style.background = tab==="login"?"var(--accent)":"#1f3460";
  $("tab-login").style.color = tab==="login"?"#fff":"var(--muted)";
  $("tab-reg").style.background = tab==="reg"?"var(--accent)":"#1f3460";
  $("tab-reg").style.color = tab==="reg"?"#fff":"var(--muted)";
  if($("auth-msg")) $("auth-msg").innerHTML = "";
}

function togglePass(id, btn){
  const inp = $(id);
  if(inp.type==="password"){inp.type="text";btn.textContent="Nascondi"}
  else{inp.type="password";btn.textContent="Mostra"}
}

async function doRecover(){
  const email=$("recover-email").value, msg=$("auth-msg");
  if(!email){msg.innerHTML='<span style="color:var(--red)">Inserisci la tua email</span>';return}
  msg.innerHTML='<div class="spinner" style="margin:8px auto"></div>';
  try{
    const d=await postAPI("/api/auth/reset-password",{email});
    msg.innerHTML='<span style="color:var(--green)">Password inviata!</span><br><div class="card" style="margin-top:12px;padding:16px;text-align:center"><p style="color:var(--text);font-weight:700">Controlla la tua email</p><p style="color:var(--muted);font-size:.85rem;margin-top:8px">Ti abbiamo inviato una password provvisoria a <strong>'+email+'</strong>.<br>Usala per accedere e poi cambiala dalle impostazioni del tuo account.</p><p style="color:var(--muted);font-size:.75rem;margin-top:8px">Non la trovi? Controlla anche la cartella spam.</p></div>';
  }catch(e){msg.innerHTML=`<span style="color:var(--red)">${e.message}</span>`}
}

async function doLogin(){
  const email=$("login-email").value, pass=$("login-pass").value, msg=$("auth-msg");
  if(!email||!pass){msg.innerHTML='<span style="color:var(--red)">Compila tutti i campi</span>';return}
  msg.innerHTML='<div class="spinner" style="margin:8px auto"></div>';
  try{
    const d=await postAPI("/api/auth/login",{email,password:pass});
    userToken=d.access_token; userPlan=d.piano||"free"; userEmail=email;
    localStorage.setItem("userToken",userToken);
    localStorage.setItem("userPlan",userPlan);
    localStorage.setItem("userEmail",userEmail);
    updateNavAuth();
    location.hash="#home";
  }catch(e){msg.innerHTML=`<span style="color:var(--red)">${e.message}</span>`}
}

async function doRegister(){
  const email=$("reg-email").value, pass=$("reg-pass").value, msg=$("auth-msg");
  if(!email||pass.length<6){msg.innerHTML='<span style="color:var(--red)">Email e password (min 6 car.) richiesti</span>';return}
  msg.innerHTML='<div class="spinner" style="margin:8px auto"></div>';
  try{
    const d=await postAPI("/api/auth/register",{email,password:pass});
    userToken=d.access_token; userPlan=d.piano||"free"; userEmail=email;
    localStorage.setItem("userToken",userToken);
    localStorage.setItem("userPlan",userPlan);
    localStorage.setItem("userEmail",userEmail);
    const refCode = new URLSearchParams(window.location.search).get("ref") || localStorage.getItem("ref_code");
    if(refCode){try{await postAPI("/api/referral/apply",{code:refCode,email:email})}catch(e){} localStorage.removeItem("ref_code")}
    updateNavAuth();
    location.hash="#home";
  }catch(e){msg.innerHTML=`<span style="color:var(--red)">${e.message}</span>`}
}

async function loadReferralCode(){
  const el=$("referral-section");
  if(!el)return;
  el.innerHTML='<div class="spinner" style="margin:8px auto"></div>';
  try{
    const d=await fetchAPI("/api/referral/my-code");
    if(!d||!d.code){el.innerHTML='<p style="color:var(--red)">Errore. Riprova.</p>';return}
    el.innerHTML=`
      <div style="background:#0d1b2a;padding:12px;border-radius:8px;margin-bottom:8px">
        <p style="color:var(--muted);font-size:.75rem;margin-bottom:4px">Il tuo codice:</p>
        <p style="font-size:1.3rem;font-weight:800;color:var(--green);text-align:center;letter-spacing:3px">${d.code}</p>
      </div>
      <div style="background:#0d1b2a;padding:10px;border-radius:8px;margin-bottom:10px">
        <p style="color:var(--muted);font-size:.7rem;margin-bottom:4px">Il tuo link:</p>
        <input id="ref-link" value="${d.link}" readonly style="width:100%;font-size:.75rem;padding:8px;background:#162447;border:1px solid var(--accent);color:var(--text);border-radius:6px;min-height:40px" onclick="this.select();document.execCommand('copy')">
        <button class="btn btn-blue" style="width:100%;margin-top:6px;font-size:.8rem;min-height:40px" onclick="navigator.clipboard.writeText('${d.link}');this.textContent='Copiato!'">Copia link</button>
      </div>
      <div style="display:flex;gap:12px;text-align:center">
        <div style="flex:1;background:#0d1b2a;padding:8px;border-radius:8px"><div style="font-size:1.2rem;font-weight:800;color:var(--green)">${d.completati}</div><div style="font-size:.7rem;color:var(--muted)">Amici iscritti</div></div>
        <div style="flex:1;background:#0d1b2a;padding:8px;border-radius:8px"><div style="font-size:1.2rem;font-weight:800;color:var(--accent)">${d.in_attesa}</div><div style="font-size:.7rem;color:var(--muted)">In attesa</div></div>
      </div>`;
  }catch(e){el.innerHTML='<p style="color:var(--red)">Errore: '+e.message+'</p>'}
}

async function doChangePassword(){
  const old_p=$("old-pass").value, new_p=$("new-pass").value, new_p2=$("new-pass2").value, msg=$("change-pass-msg");
  if(!old_p||!new_p){msg.innerHTML='<span style="color:var(--red)">Compila tutti i campi</span>';return}
  if(new_p.length<6){msg.innerHTML='<span style="color:var(--red)">Min 6 caratteri</span>';return}
  if(new_p!==new_p2){msg.innerHTML='<span style="color:var(--red)">Le password non coincidono</span>';return}
  msg.innerHTML='<div class="spinner" style="margin:4px auto"></div>';
  try{
    await postAPI("/api/auth/change-password",{old_password:old_p,new_password:new_p});
    msg.innerHTML='<span style="color:var(--green)">Password aggiornata!</span>';
    $("old-pass").value=""; $("new-pass").value=""; $("new-pass2").value="";
  }catch(e){msg.innerHTML=`<span style="color:var(--red)">${e.message}</span>`}
}

function doLogout(){
  userToken=""; userPlan="free"; userEmail=""; freeUsed=0;
  localStorage.removeItem("userToken");
  localStorage.removeItem("userPlan");
  localStorage.removeItem("userEmail");
  localStorage.setItem("freeUsed","0");
  updateNavAuth();
  location.hash="#home";
}

async function pageMyPredictions(){
  if(!userToken) return '<div class="container"><div class="card" style="text-align:center;padding:24px"><h2>Accedi per vedere i tuoi pronostici</h2><a href="#login" class="btn btn-green" style="margin-top:12px">Accedi</a></div></div>';
  try{await postAPI("/api/user/verify-predictions",{})}catch(e){}
  const data = await fetchAPI("/api/user/my-predictions");
  if(!data) return '<div class="container"><div class="card" style="color:var(--red)">Errore caricamento</div></div>';
  const s = data.stats || {};
  let html='<div class="container"><h1>I Miei Pronostici</h1><p class="sub">Il tuo storico personale</p>';
  html+=`<div class="grid3" style="margin-bottom:16px">
    <div class="card" style="text-align:center;padding:12px"><div style="font-size:1.8rem;font-weight:800;color:var(--green)">${s.totale||0}</div><div style="color:var(--muted);font-size:.8rem">Pronostici fatti</div></div>
    <div class="card" style="text-align:center;padding:12px"><div style="font-size:1.8rem;font-weight:800;color:var(--accent)">${s.acc_1x2||0}%</div><div style="color:var(--muted);font-size:.8rem">1X2 azzeccati</div></div>
    <div class="card" style="text-align:center;padding:12px"><div style="font-size:1.8rem;font-weight:800;color:var(--yellow)">${s.verificati||0}</div><div style="color:var(--muted);font-size:.8rem">Verificati</div></div>
  </div>`;
  if(s.verificati>0){
    html+=`<div class="card" style="padding:10px;margin-bottom:12px"><div style="display:flex;gap:16px;justify-content:center;font-size:.85rem">
      <span>1X2: <strong style="color:var(--green)">${s.ok_1x2}/${s.verificati}</strong></span>
      <span>O/U: <strong style="color:var(--accent)">${s.ok_ou}/${s.verificati}</strong></span>
      <span>Goal: <strong style="color:var(--yellow)">${s.ok_goal}/${s.verificati}</strong></span>
    </div></div>`;
  }
  if(data.predictions && data.predictions.length>0){
    data.predictions.forEach(p=>{
      const ver = p.verificato;
      const col = ver ? (p.corretto?"var(--green)":"var(--red)") : "var(--muted)";
      const segno = ver ? (p.corretto?"&#10004;":"&#10006;") : "&#9201;";
      html+=`<div class="card" style="padding:8px;margin-bottom:6px;border-left:3px solid ${col}">
        <div style="display:flex;align-items:center;justify-content:space-between">
          <div style="font-size:.85rem"><strong>${p.home}</strong> vs <strong>${p.away}</strong>
            <br><span style="color:var(--muted);font-size:.75rem">${p.confidence||""} | ${p.over_under||""} | ${p.goal||""}</span>
          </div>
          <div style="text-align:right">
            <span style="font-size:1.1rem;font-weight:800;color:${col}">${segno} ${p.pronostico}</span>
            ${ver?`<br><span style="font-size:.75rem;color:var(--muted)">${p.gol_h_reale}-${p.gol_a_reale} (${p.risultato_reale})</span>`:'<br><span style="font-size:.7rem;color:var(--muted)">In attesa</span>'}
          </div>
        </div>
      </div>`;
    });
  } else {
    html+='<div class="card" style="text-align:center;padding:20px;color:var(--muted)"><p>Non hai ancora salvato nessun pronostico.</p><a href="#pronostici" class="btn btn-blue" style="margin-top:8px">Calcola il primo pronostico</a></div>';
  }
  html+='</div>';
  return html;
}

async function saveLastPrediction(){
  if(!window._lastPrediction) return;
  const msg=$("save-pred-msg");
  if(msg) msg.innerHTML='<span style="color:var(--muted)">Salvataggio...</span>';
  try{
    await postAPI("/api/user/save-prediction", window._lastPrediction);
    if(msg) msg.innerHTML='<span style="color:var(--green)">Salvato! <a href="#miei" style="color:var(--accent)">Vedi i tuoi pronostici</a></span>';
  }catch(e){if(msg) msg.innerHTML='<span style="color:var(--red)">Errore: '+e.message+'</span>'}
}

async function saveMyPrediction(home,away,tip,prob,conf,ou,goal){
  const msg=$("save-pred-msg");
  if(msg) msg.innerHTML='<span style="color:var(--muted)">Salvataggio...</span>';
  try{
    await postAPI("/api/user/save-prediction",{home:home,away:away,pronostico:tip,prob:prob,confidence:conf,over_under:ou,goal:goal,league:currentLeague});
    if(msg) msg.innerHTML='<span style="color:var(--green)">Salvato! Vai su <a href="#miei" style="color:var(--accent)">I Miei Pronostici</a> per vederlo.</span>';
  }catch(e){if(msg) msg.innerHTML='<span style="color:var(--red)">Errore: '+e.message+'</span>'}
}
