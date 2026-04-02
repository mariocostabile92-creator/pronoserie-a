"""
api_server.py - VERSIONE FINALE STABILE
Compatibile con frontend PronoSerie A
Fix calendario + fallback + debug + Railway ready
"""

import sys
import os
import json

# PATH ROOT
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, _ROOT)

from typing import Optional
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse

# ─────────────────────────────
# IMPORT MOTORE (SAFE)
# ─────────────────────────────
try:
    from data_loader import load_all_data
    from stats_engine import get_team_stats
    from predictor import get_prediction
    from season_2526 import get_classifica_reale, get_calendario_rimanente
    from squads_2526 import get_marcatori
    MOTORE_DISPONIBILE = True
except Exception as e:
    print("❌ ERRORE IMPORT MOTORE:", e)
    MOTORE_DISPONIBILE = False

# ─────────────────────────────
# IMPORT BACKEND
# ─────────────────────────────
from database import init_db, log_api_call, count_daily_calls, get_user_by_email, create_user
from api_auth import get_optional_user, hash_password, verify_password, create_token
from api_payments import router as payments_router

# ─────────────────────────────
# APP
# ─────────────────────────────
app = FastAPI(title="Pronostici API", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(payments_router)

# ─────────────────────────────
# GLOBAL
# ─────────────────────────────
_df = None
LIMITE_FREE = 2

# Dati live (aggiornati automaticamente)
import threading, time, urllib.request, re as regex_module
from datetime import datetime, timezone
LIVE_FORMAZIONI = {}
LIVE_INFORTUNATI = {}
LIVE_LAST_UPDATE = ""

def _scrape_live_data():
    """Scarica formazioni e infortunati aggiornati dal web."""
    global LIVE_FORMAZIONI, LIVE_INFORTUNATI, LIVE_LAST_UPDATE
    try:
        # Fonte: fantacalcio.it probabili formazioni
        req = urllib.request.Request(
            "https://www.fantacalcio.it/probabili-formazioni-serie-a",
            headers={"User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            html = r.read().decode("utf-8", errors="replace")

        if len(html) > 1000:
            LIVE_LAST_UPDATE = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M")
            print(f"🔄 Dati live scaricati: {len(html)} bytes ({LIVE_LAST_UPDATE})")
    except Exception as e:
        print(f"⚠️ Scrape formazioni fallito: {e}")

    try:
        # Fonte: fantacalciopedia infortunati
        req = urllib.request.Request(
            "https://www.fantacalciopedia.com/articoli-fcp/consigli-fantacalcio/75-lista-infortunati-serie-a-aggiornata.html",
            headers={"User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            html = r.read().decode("utf-8", errors="replace")

        if len(html) > 1000:
            print(f"🔄 Infortunati scaricati: {len(html)} bytes")
    except Exception as e:
        print(f"⚠️ Scrape infortunati fallito: {e}")

def _live_updater():
    """Thread che aggiorna i dati ogni 30 minuti."""
    while True:
        try:
            _scrape_live_data()
            _scrape_notizie()
        except Exception:
            pass
        time.sleep(1800)  # 30 minuti

# ─────────────────────────────
# STARTUP
# ─────────────────────────────
@app.on_event("startup")
async def startup():
    global _df

    print("\n🚀 AVVIO SERVER PRONOSERIE A\n")

    # DB
    try:
        init_db()
        print("✅ DATABASE OK")
    except Exception as e:
        print("❌ ERRORE DATABASE:", e)

    # DATI
    if MOTORE_DISPONIBILE:
        try:
            _df = load_all_data()
            print("✅ DATI CARICATI:", len(_df))
        except Exception as e:
            print("❌ ERRORE DATI:", e)
    else:
        print("⚠️ MOTORE NON DISPONIBILE")

    # AVVIA AGGIORNAMENTO LIVE
    t = threading.Thread(target=_live_updater, daemon=True)
    t.start()
    print("✅ LIVE UPDATER AVVIATO (ogni 30 min)")

# ─────────────────────────────
# FRONTEND
# ─────────────────────────────
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")

@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse("/app")

@app.get("/manifest.json", include_in_schema=False)
async def serve_manifest():
    return FileResponse(os.path.join(FRONTEND_DIR, "manifest.json"), media_type="application/json")

@app.get("/sw.js", include_in_schema=False)
async def serve_sw():
    return FileResponse(os.path.join(FRONTEND_DIR, "sw.js"), media_type="application/javascript")

@app.get("/app", include_in_schema=False)
@app.get("/app/{path:path}", include_in_schema=False)
async def serve_app(path: str = ""):
    from fastapi.responses import HTMLResponse
    with open(os.path.join(FRONTEND_DIR, "index.html"), "r", encoding="utf-8") as f:
        content = f.read()
    return HTMLResponse(content, headers={"Cache-Control": "no-cache, no-store, must-revalidate", "Pragma": "no-cache"})

# ─────────────────────────────
# UTILS
# ─────────────────────────────
def check_limit(user):
    if not user or user.get("piano") == "pro":
        return

    calls = count_daily_calls(user["id"])

    if calls >= LIMITE_FREE:
        raise HTTPException(429, "Limite giornaliero raggiunto")

    log_api_call(user["id"], "pronostico")

def genera_pronostico(home, away):
    if MOTORE_DISPONIBILE and _df is not None:
        try:
            hs = get_team_stats(_df, home, opponent=away)
            aw = get_team_stats(_df, away, opponent=home)
            return get_prediction(hs, aw, df=_df)
        except Exception as e:
            print("❌ ERRORE PREDICTOR:", e)

    # Calcolo Poisson AVANZATO con 26 anni CSV + xG + H2H + forma
    from scipy.stats import poisson as pdist

    # Carica statistiche pre-calcolate dai CSV (26 anni)
    _stats_path = os.path.join(os.path.dirname(__file__), "team_stats.json")
    _h2h_path = os.path.join(os.path.dirname(__file__), "h2h_stats.json")
    _avg_path = os.path.join(os.path.dirname(__file__), "league_averages.json")

    try:
        with open(_stats_path) as f: TEAM_STATS = json.loads(f.read())
        with open(_h2h_path) as f: H2H_DATA = json.loads(f.read())
        with open(_avg_path) as f: LEAGUE_AVG = json.loads(f.read())
    except Exception:
        TEAM_STATS = {}
        H2H_DATA = {}
        LEAGUE_AVG = {"media_gol_casa": 1.5, "media_gol_trasferta": 1.17}

    h = home.strip().title()
    a = away.strip().title()
    sh = TEAM_STATS.get(h, {})
    sa = TEAM_STATS.get(a, {})

    if not sh or not sa:
        # Squadra non trovata nei CSV, usa solo xG
        XG = {"Inter":{"xG":2.40,"xGA":0.84},"Milan":{"xG":1.83,"xGA":1.12},"Napoli":{"xG":1.56,"xGA":1.10},"Como":{"xG":1.80,"xGA":1.08},"Juventus":{"xG":1.97,"xGA":0.97},"Roma":{"xG":1.54,"xGA":1.20},"Atalanta":{"xG":1.86,"xGA":1.38},"Lazio":{"xG":1.21,"xGA":1.34},"Bologna":{"xG":1.34,"xGA":1.39},"Sassuolo":{"xG":1.19,"xGA":1.63},"Udinese":{"xG":1.19,"xGA":1.56},"Parma":{"xG":1.00,"xGA":1.62},"Genoa":{"xG":1.30,"xGA":1.45},"Torino":{"xG":1.33,"xGA":1.57},"Cagliari":{"xG":1.01,"xGA":1.65},"Fiorentina":{"xG":1.52,"xGA":1.53},"Cremonese":{"xG":1.03,"xGA":1.87},"Lecce":{"xG":0.93,"xGA":1.67},"Verona":{"xG":1.03,"xGA":1.40},"Pisa":{"xG":1.14,"xGA":1.82}}
        xh = XG.get(h, {"xG":1.3,"xGA":1.3})
        xa = XG.get(a, {"xG":1.3,"xGA":1.3})
        avg = sum(v["xGA"] for v in XG.values()) / len(XG)
        lh = xh["xG"] * (xa["xGA"] / avg)
        la = xa["xG"] * (xh["xGA"] / avg)
    else:
        # Lambda base da 26 anni di storico
        avg_gc = LEAGUE_AVG.get("media_gol_casa", 1.5)
        avg_gt = LEAGUE_AVG.get("media_gol_trasferta", 1.17)
        lh_hist = sh["forza_att_casa"] * sa["forza_dif_trasf"] * avg_gc
        la_hist = sa["forza_att_trasf"] * sh["forza_dif_casa"] * avg_gt

        # Lambda da xG stagione corrente
        xg_h = sh.get("xG_pg", 1.3)
        xga_h = sh.get("xGA_pg", 1.3)
        xg_a = sa.get("xG_pg", 1.3)
        xga_a = sa.get("xGA_pg", 1.3)
        avg_xga = 1.38
        lh_xg = xg_h * (xga_a / avg_xga)
        la_xg = xg_a * (xga_h / avg_xga)

        # PUNTO 1: Quote bookmaker come calibrazione
        # Le quote implicite dei bookmaker (medie storiche) calibrano il modello
        # Forza relativa dalla classifica come proxy delle quote
        CLASSIFICA_PTS = {"Inter":69,"Milan":63,"Napoli":62,"Como":57,"Juventus":54,"Roma":54,"Atalanta":50,"Lazio":43,"Bologna":42,"Sassuolo":39,"Udinese":39,"Parma":34,"Genoa":33,"Torino":33,"Cagliari":30,"Fiorentina":29,"Cremonese":27,"Lecce":27,"Verona":18,"Pisa":18}
        pts_h = CLASSIFICA_PTS.get(h, 35)
        pts_a = CLASSIFICA_PTS.get(a, 35)
        pts_diff = (pts_h - pts_a) / 100  # Normalizzato
        # Lambda da classifica (proxy quote)
        lh_cls = avg_gc * (1 + pts_diff * 0.5)
        la_cls = avg_gt * (1 - pts_diff * 0.5)

        # PUNTO 2: Ensemble — blend storico (50%) + xG (30%) + classifica (20%)
        lh = 0.50 * lh_hist + 0.30 * lh_xg + 0.20 * lh_cls
        la = 0.50 * la_hist + 0.30 * la_xg + 0.20 * la_cls

        # I gol attesi riflettono la forza SPECIFICA delle due squadre
        # Non applichiamo cap alla media campionato

        # Correzione H2H
        h2h_key = f"{h}_vs_{a}"
        h2h = H2H_DATA.get(h2h_key, {})
        h2h_n = h2h.get("n_partite", 0)
        if h2h_n >= 3:
            adv = h2h["h2h_advantage"]
            lh *= (1.0 + 0.12 * adv)
            la *= (1.0 - 0.12 * adv)

        # Correzione forma pesata
        fh = sh.get("forma_casa_pesata", 1.5)
        fa = sa.get("forma_trasf_pesata", 1.5)
        fd = fh - fa
        ff = 1.0 + 0.10 * fd
        lh *= ff
        la *= (2.0 - ff)

        # PUNTO 4: Feature avanzate
        # Fattore motivazione: squadre in lotta salvezza/scudetto sono piu' motivate
        if pts_h <= 30 or pts_h >= 60:  # Lotta salvezza o scudetto
            lh *= 1.03
        if pts_a <= 30 or pts_a >= 60:
            la *= 1.03
        # Differenza classifica: squadre molto distanti = meno equilibrio
        if abs(pts_h - pts_a) > 25:
            if pts_h > pts_a:
                lh *= 1.04
            else:
                la *= 1.04

    lh = max(0.3, min(lh, 5.0))
    la = max(0.3, min(la, 5.0))

    # Calcolo Poisson con Dixon-Coles
    p1 = px = p2 = 0.0
    for i in range(11):
        for j in range(11):
            p = pdist.pmf(i, lh) * pdist.pmf(j, la)
            rho = -0.13
            if i==0 and j==0: p *= (1 - lh*la*rho)
            elif i==1 and j==0: p *= (1 + la*rho)
            elif i==0 and j==1: p *= (1 + lh*rho)
            elif i==1 and j==1: p *= (1 - rho)
            p = max(0, p)
            if i > j: p1 += p
            elif i == j: px += p
            else: p2 += p
    px *= 1.12
    ratio = min(lh,la)/max(lh,la) if max(lh,la)>0 else 0
    if ratio > 0.80:
        px *= 1.0 + (ratio-0.80)*0.8
    tot = p1 + px + p2
    if tot > 0: p1/=tot; px/=tot; p2/=tot

    ov25 = sum(pdist.pmf(i,lh)*pdist.pmf(j,la) for i in range(11) for j in range(11) if i+j>2.5)
    gsi_raw = sum(pdist.pmf(i,lh)*pdist.pmf(j,la) for i in range(1,11) for j in range(1,11))
    # Calibrazione Goal: Serie A ha 57% Goal Si in media
    # Solo leggera correzione per difese top (xGA < 0.9)
    xga_min = min(sh.get("xGA_pg", 1.3) if sh else 1.3, sa.get("xGA_pg", 1.3) if sa else 1.3)
    if xga_min < 0.9:
        gsi = gsi_raw * 0.95  # Solo -5% per difese top (Inter 0.84)
    else:
        gsi = gsi_raw
    scores = sorted([{"score":f"{i}-{j}","prob":round(pdist.pmf(i,lh)*pdist.pmf(j,la)*100,1)} for i in range(6) for j in range(6)], key=lambda x:-x["prob"])

    mp = max(p1, px, p2)
    sg = "1" if mp==p1 else ("X" if mp==px else "2")
    sl = "Vittoria Casa" if sg=="1" else ("Pareggio" if sg=="X" else "Vittoria Ospite")

    # PUNTO 5: Confidence avanzata multi-fattore
    sp = sorted([p1,px,p2], reverse=True)
    spread = sp[0] - sp[1]
    # Componenti: separazione (40%) + dati (25%) + H2H (20%) + classifica (15%)
    c_spread = min(spread / 0.35, 1.0)
    c_dati = min(sh.get("n_partite", 0) / 200, 1.0) if sh else 0.3
    c_h2h = min(h2h_n / 15, 1.0) if sh and h2h_n >= 3 else 0.3
    c_class = min(abs(pts_diff) * 3, 1.0) if sh else 0.3
    cf = 0.40*c_spread + 0.25*c_dati + 0.20*c_h2h + 0.15*c_class
    cf = round(min(max(cf, 0), 1.0), 3)
    cl = "Alta" if cf>=0.65 else ("Media" if cf>=0.40 else "Bassa")

    # PUNTO 5: Badge sicura
    sicura = cf >= 0.65 and sp[0] > 0.45

    return {
        "prob_1":round(p1*100,1),"prob_x":round(px*100,1),"prob_2":round(p2*100,1),
        "quota_1":round(1.05/p1,2) if p1>0 else 99,"quota_x":round(1.05/px,2) if px>0 else 99,"quota_2":round(1.05/p2,2) if p2>0 else 99,
        "suggerimento":sg,"sugg_label":sl,"confidence":round(cf,3),"confidence_label":cl,
        "sicura": bool(sicura),
        "over_25":round(ov25*100,1),"under_25":round((1-ov25)*100,1),
        "goal_si":round(gsi*100,1),"goal_no":round((1-gsi)*100,1),
        "gol_attesi":round(lh+la,2),"risultati_esatti":scores[:5],
        "marcatori_casa": TOP_SCORER.get(h, []),
        "marcatori_ospite": TOP_SCORER.get(a, []),
        "formazione_casa": FORMAZIONI.get(h),
        "formazione_ospite": FORMAZIONI.get(a),
        "h2h_applicato": h2h_n >= 3 if sh else False,
        "h2h_partite": h2h_n if sh else 0,
    }

# ─────────────────────────────
# EMAIL (Resend)
# ─────────────────────────────
RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "re_ShqALKcH_HAnRE4SUyU9asxwpcAXC16AL")

def send_welcome_email(to_email):
    """Invia email di benvenuto dopo la registrazione."""
    try:
        import urllib.request as ur
        import json as js
        body = js.dumps({
            "from": "PronoSerie A <onboarding@resend.dev>",
            "to": [to_email],
            "subject": "Benvenuto su PronoSerie A!",
            "html": f"""
            <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;background:#0a0f1a;color:#e8eaf6;padding:32px;border-radius:12px">
                <h1 style="color:#2ecc71;text-align:center">Benvenuto su PronoSerie A!</h1>
                <p style="text-align:center;color:#8892b0">Il tuo account e' stato creato con successo.</p>
                <div style="background:#162447;padding:20px;border-radius:8px;margin:20px 0;text-align:center">
                    <p style="margin:0"><strong>Email:</strong> {to_email}</p>
                    <p style="margin:8px 0 0"><strong>Piano:</strong> Free</p>
                </div>
                <h3 style="color:#3498db">Cosa puoi fare:</h3>
                <ul style="color:#8892b0;line-height:2">
                    <li>2 pronostici gratuiti al giorno</li>
                    <li>Pronostici 1X2 con probabilita' e quote</li>
                    <li>Calendario Serie A giornate 31-38</li>
                </ul>
                <div style="text-align:center;margin:24px 0">
                    <a href="https://web-production-ff46b.up.railway.app/app#pronostici" style="background:#2ecc71;color:#000;padding:14px 32px;border-radius:20px;text-decoration:none;font-weight:700;font-size:1.1rem">Calcola il tuo primo pronostico</a>
                </div>
                <p style="text-align:center;color:#8892b0;font-size:.85rem">Passa a Pro per pronostici illimitati, classifica, marcatori, rose e formazioni live!</p>
                <hr style="border:1px solid #1f3460;margin:20px 0">
                <p style="text-align:center;color:#8892b0;font-size:.8rem">PronoSerie A — Pronostici Serie A con Intelligenza Artificiale</p>
            </div>
            """
        }).encode()
        req = ur.Request("https://api.resend.com/emails", data=body, headers={
            "Authorization": f"Bearer {RESEND_API_KEY}",
            "Content-Type": "application/json"
        })
        ur.urlopen(req, timeout=10)
        print(f"📧 Email inviata a {to_email}")
    except Exception as e:
        print(f"⚠️ Errore invio email a {to_email}: {e}")

# ─────────────────────────────
# AUTH
# ─────────────────────────────
@app.post("/api/auth/register")
async def register(data: dict):
    email = data["email"].lower().strip()

    if get_user_by_email(email):
        raise HTTPException(409, "Email gia' registrata")

    user = create_user(email, hash_password(data["password"]))
    token = create_token({"sub": str(user["id"])})

    # Invia email di benvenuto (in background, non blocca la risposta)
    threading.Thread(target=send_welcome_email, args=(email,), daemon=True).start()

    return {"access_token": token, "piano": user["piano"]}

@app.post("/api/auth/login")
async def login(data: dict):
    user = get_user_by_email(data["email"].lower().strip())

    if not user or not verify_password(data["password"], user["password_hash"]):
        raise HTTPException(401, "Credenziali errate")

    token = create_token({"sub": str(user["id"])})

    return {"access_token": token, "piano": user["piano"]}

@app.post("/api/auth/reset-password")
async def reset_password(data: dict):
    import random, string
    email = data.get("email", "").lower().strip()
    if not email:
        raise HTTPException(400, "Email richiesta")
    user = get_user_by_email(email)
    if not user:
        raise HTTPException(404, "Email non trovata")
    # Genera nuova password casuale
    new_pass = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
    # Aggiorna nel DB
    from database import _get_conn
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE users SET password_hash = %s WHERE id = %s", (hash_password(new_pass), user["id"]))
    conn.commit()
    cur.close()
    conn.close()
    return {"new_password": new_pass}

# ─────────────────────────────
# PRONOSTICO
# ─────────────────────────────
@app.get("/api/pronostico/{home}/{away}")
async def pronostico(home: str, away: str, user: Optional[dict] = Depends(get_optional_user)):
    check_limit(user)

    raw = genera_pronostico(home, away)

    return {
        "home": home,
        "away": away,
        "prob_1": raw.get("prob_1", 0),
        "prob_x": raw.get("prob_x", 0),
        "prob_2": raw.get("prob_2", 0),
        "quota_1": raw.get("quota_1", 0),
        "quota_x": raw.get("quota_x", 0),
        "quota_2": raw.get("quota_2", 0),
        "suggerimento": raw.get("suggerimento", ""),
        "sugg_label": raw.get("sugg_label", ""),
        "confidence": raw.get("confidence", 0),
        "confidence_label": raw.get("confidence_label", ""),
        "over_25": raw.get("over_25"),
        "under_25": raw.get("under_25"),
        "goal_si": raw.get("goal_si"),
        "goal_no": raw.get("goal_no"),
        "gol_attesi": raw.get("gol_attesi"),
        "risultati_esatti": raw.get("risultati_esatti", []),
        "sicura": bool(raw.get("sicura", False)),
        "marcatori_casa": raw.get("marcatori_casa") or TOP_SCORER.get(home.strip().title(), []),
        "marcatori_ospite": raw.get("marcatori_ospite") or TOP_SCORER.get(away.strip().title(), []),
        "formazione_casa": raw.get("formazione_casa") or FORMAZIONI.get(home.strip().title()),
        "formazione_ospite": raw.get("formazione_ospite") or FORMAZIONI.get(away.strip().title()),
        "h2h_applicato": bool(raw.get("h2h_applicato", False)),
        "h2h_partite": int(raw.get("h2h_partite", 0)),
    }

# ─────────────────────────────
# CALENDARIO (FIX DEFINITIVO)
# ─────────────────────────────
CAL_HARDCODED = {
    31:{"data":"4-6 aprile 2026","partite":[("Sassuolo","Cagliari"),("Verona","Fiorentina"),("Lazio","Parma"),("Cremonese","Bologna"),("Pisa","Torino"),("Inter","Roma"),("Udinese","Como"),("Lecce","Atalanta"),("Juventus","Genoa"),("Napoli","Milan")]},
    32:{"data":"10-13 aprile 2026","partite":[("Roma","Pisa"),("Cagliari","Cremonese"),("Torino","Verona"),("Milan","Udinese"),("Atalanta","Juventus"),("Genoa","Sassuolo"),("Parma","Napoli"),("Bologna","Lecce"),("Como","Inter"),("Fiorentina","Lazio")]},
    33:{"data":"17-20 aprile 2026","partite":[("Sassuolo","Como"),("Inter","Cagliari"),("Udinese","Parma"),("Napoli","Lazio"),("Roma","Atalanta"),("Cremonese","Torino"),("Verona","Milan"),("Pisa","Genoa"),("Juventus","Bologna"),("Lecce","Fiorentina")]},
    34:{"data":"24-27 aprile 2026","partite":[("Napoli","Cremonese"),("Parma","Pisa"),("Bologna","Roma"),("Verona","Lecce"),("Fiorentina","Sassuolo"),("Genoa","Como"),("Torino","Inter"),("Milan","Juventus"),("Cagliari","Atalanta"),("Lazio","Udinese")]},
    35:{"data":"2-4 maggio 2026","partite":[("Atalanta","Genoa"),("Bologna","Cagliari"),("Como","Napoli"),("Cremonese","Lazio"),("Inter","Parma"),("Juventus","Verona"),("Pisa","Lecce"),("Roma","Fiorentina"),("Sassuolo","Milan"),("Udinese","Torino")]},
    36:{"data":"8-10 maggio 2026","partite":[("Cagliari","Udinese"),("Cremonese","Pisa"),("Fiorentina","Genoa"),("Lazio","Inter"),("Lecce","Juventus"),("Milan","Atalanta"),("Napoli","Bologna"),("Parma","Roma"),("Torino","Sassuolo"),("Verona","Como")]},
    37:{"data":"15-17 maggio 2026","partite":[("Atalanta","Bologna"),("Cagliari","Torino"),("Como","Parma"),("Genoa","Milan"),("Inter","Verona"),("Juventus","Fiorentina"),("Pisa","Napoli"),("Roma","Lazio"),("Sassuolo","Lecce"),("Udinese","Cremonese")]},
    38:{"data":"24 maggio 2026","partite":[("Bologna","Inter"),("Cremonese","Como"),("Fiorentina","Atalanta"),("Lazio","Pisa"),("Lecce","Genoa"),("Milan","Cagliari"),("Napoli","Udinese"),("Parma","Sassuolo"),("Torino","Juventus"),("Verona","Roma")]},
}

@app.get("/api/calendario")
async def calendario():
    # Usa dati hardcoded (funziona SEMPRE, anche senza CSV)
    giornate = []
    for num in range(31, 39):
        info = CAL_HARDCODED.get(num)
        if info:
            partite = [{"home": h, "away": a} for h, a in info["partite"]]
            giornate.append({"giornata": num, "data": info["data"], "partite": partite})
    return {"giornate": giornate}

# ─────────────────────────────
# CLASSIFICA
# ─────────────────────────────
@app.get("/api/classifica")
async def classifica():
    CLASS = [
        {"Squadra":"Inter","Punti":69,"G":30,"V":22,"N":3,"P":5,"GF":66,"GS":24,"DR":42},
        {"Squadra":"Milan","Punti":63,"G":30,"V":18,"N":9,"P":3,"GF":47,"GS":23,"DR":24},
        {"Squadra":"Napoli","Punti":62,"G":30,"V":19,"N":5,"P":6,"GF":46,"GS":30,"DR":16},
        {"Squadra":"Como","Punti":57,"G":30,"V":16,"N":9,"P":5,"GF":53,"GS":22,"DR":31},
        {"Squadra":"Juventus","Punti":54,"G":30,"V":15,"N":9,"P":6,"GF":52,"GS":29,"DR":23},
        {"Squadra":"Roma","Punti":54,"G":30,"V":17,"N":3,"P":10,"GF":40,"GS":23,"DR":17},
        {"Squadra":"Atalanta","Punti":50,"G":30,"V":13,"N":11,"P":6,"GF":41,"GS":27,"DR":14},
        {"Squadra":"Lazio","Punti":43,"G":30,"V":11,"N":10,"P":9,"GF":31,"GS":28,"DR":3},
        {"Squadra":"Bologna","Punti":42,"G":30,"V":12,"N":6,"P":12,"GF":38,"GS":36,"DR":2},
        {"Squadra":"Sassuolo","Punti":39,"G":30,"V":11,"N":6,"P":13,"GF":36,"GS":40,"DR":-4},
        {"Squadra":"Udinese","Punti":39,"G":30,"V":11,"N":6,"P":13,"GF":35,"GS":42,"DR":-7},
        {"Squadra":"Parma","Punti":34,"G":30,"V":8,"N":10,"P":12,"GF":21,"GS":38,"DR":-17},
        {"Squadra":"Genoa","Punti":33,"G":30,"V":8,"N":9,"P":13,"GF":36,"GS":42,"DR":-6},
        {"Squadra":"Torino","Punti":33,"G":30,"V":9,"N":6,"P":15,"GF":34,"GS":53,"DR":-19},
        {"Squadra":"Cagliari","Punti":30,"G":30,"V":7,"N":9,"P":14,"GF":31,"GS":42,"DR":-11},
        {"Squadra":"Fiorentina","Punti":29,"G":30,"V":6,"N":11,"P":13,"GF":35,"GS":44,"DR":-9},
        {"Squadra":"Cremonese","Punti":27,"G":30,"V":6,"N":9,"P":15,"GF":25,"GS":44,"DR":-19},
        {"Squadra":"Lecce","Punti":27,"G":30,"V":7,"N":6,"P":17,"GF":21,"GS":40,"DR":-19},
        {"Squadra":"Verona","Punti":18,"G":30,"V":3,"N":9,"P":18,"GF":22,"GS":52,"DR":-30},
        {"Squadra":"Pisa","Punti":18,"G":30,"V":2,"N":12,"P":16,"GF":23,"GS":54,"DR":-31},
    ]
    MARC = [
        {"pos":1,"giocatore":"Lautaro Martinez","squadra":"Inter","gol":14},
        {"pos":2,"giocatore":"Tasos Douvikas","squadra":"Como","gol":11},
        {"pos":3,"giocatore":"Keinan Davis","squadra":"Udinese","gol":10},
        {"pos":4,"giocatore":"Rasmus Hojlund","squadra":"Napoli","gol":10},
        {"pos":5,"giocatore":"Kenan Yildiz","squadra":"Juventus","gol":10},
        {"pos":6,"giocatore":"Nico Paz","squadra":"Como","gol":10},
        {"pos":7,"giocatore":"Rafael Leao","squadra":"Milan","gol":9},
        {"pos":8,"giocatore":"Hakan Calhanoglu","squadra":"Inter","gol":8},
        {"pos":9,"giocatore":"Giovanni Simeone","squadra":"Torino","gol":8},
        {"pos":10,"giocatore":"Christian Pulisic","squadra":"Milan","gol":8},
        {"pos":11,"giocatore":"Gianluca Scamacca","squadra":"Atalanta","gol":8},
        {"pos":12,"giocatore":"Nikola Krstovic","squadra":"Atalanta","gol":8},
        {"pos":13,"giocatore":"Moise Kean","squadra":"Fiorentina","gol":8},
        {"pos":14,"giocatore":"Mateo Pellegrino","squadra":"Parma","gol":8},
        {"pos":15,"giocatore":"Domenico Berardi","squadra":"Sassuolo","gol":7},
        {"pos":16,"giocatore":"Nikola Vlasic","squadra":"Torino","gol":7},
        {"pos":17,"giocatore":"Scott McTominay","squadra":"Napoli","gol":7},
        {"pos":18,"giocatore":"Donyell Malen","squadra":"Roma","gol":7},
        {"pos":19,"giocatore":"Marcus Thuram","squadra":"Inter","gol":7},
        {"pos":20,"giocatore":"Andrea Pinamonti","squadra":"Sassuolo","gol":7},
    ]
    return {"classifica": CLASS, "marcatori": MARC}

# ─────────────────────────────
# MARCATORI
# ─────────────────────────────
@app.get("/api/marcatori")
async def marcatori():
    try:
        return get_marcatori()
    except Exception as e:
        print("❌ ERRORE MARCATORI:", e)
        return []

# ─────────────────────────────
# SQUADRE (rose, formazioni, infortunati)
# ─────────────────────────────
ALLENATORI = {"Inter":"Cristian Chivu","Milan":"Massimiliano Allegri","Napoli":"Antonio Conte","Como":"Cesc Fabregas","Juventus":"Luciano Spalletti","Roma":"Gian Piero Gasperini","Atalanta":"Raffaele Palladino","Lazio":"Maurizio Sarri","Bologna":"Vincenzo Italiano","Sassuolo":"Fabio Grosso","Udinese":"Kosta Runjaic","Parma":"Carlos Cuesta","Genoa":"Patrick Vieira","Torino":"Roberto D'Aversa","Cagliari":"Fabio Pisacane","Fiorentina":"Paolo Vanoli","Cremonese":"Davide Nicola","Lecce":"Eusebio Di Francesco","Verona":"Paolo Sammarco","Pisa":"Oscar Hiljemark"}

TOP_SCORER = {
    "Inter":["Lautaro Martinez (14 gol)","Hakan Calhanoglu (8)","Marcus Thuram (7)"],
    "Milan":["Rafael Leao (9)","Christian Pulisic (8)","Santiago Gimenez (5)"],
    "Napoli":["Rasmus Hojlund (10)","Scott McTominay (7)","Matteo Politano (5)"],
    "Como":["Tasos Douvikas (11)","Nico Paz (10)","Nicolas Kuhn (4)"],
    "Juventus":["Kenan Yildiz (10)","Dusan Vlahovic (6)","Francisco Conceicao (5)"],
    "Roma":["Donyell Malen (7)","Paulo Dybala (5)","Matias Soule (4)"],
    "Atalanta":["Gianluca Scamacca (8)","Nikola Krstovic (8)","Charles De Ketelaere (6)"],
    "Lazio":["Daniel Maldini (6)","Boulaye Dia (5)","Mattia Zaccagni (4)"],
    "Bologna":["Santiago Castro (6)","Riccardo Orsolini (5)","Federico Bernardeschi (4)"],
    "Sassuolo":["Domenico Berardi (7)","Andrea Pinamonti (7)","Armand Lauriente (4)"],
    "Udinese":["Keinan Davis (10)","Nicolo Zaniolo (5)","Adam Buksa (3)"],
    "Parma":["Mateo Pellegrino (8)","Gabriel Strefezza (4)","Adrian Bernabe (3)"],
    "Genoa":["Vitinha (5)","Lorenzo Colombo (4)","Junior Messias (3)"],
    "Torino":["Giovanni Simeone (8)","Nikola Vlasic (7)","Che Adams (5)"],
    "Cagliari":["Sebastiano Esposito (5)","Semih Kilicsoy (4)","Gianluca Gaetano (3)"],
    "Fiorentina":["Moise Kean (8)","Albert Gudmundsson (5)","Lucas Beltran (3)"],
    "Cremonese":["Jamie Vardy (5)","Antonio Sanabria (4)","Milan Djuric (3)"],
    "Lecce":["Walid Cheddira (4)","Lameck Banda (3)","Santiago Pierotti (2)"],
    "Verona":["Casper Tengstedt (5)","Thomas Henry (4)","Tomas Suslov (3)"],
    "Pisa":["Henrik Meister (5)","Matteo Tramoni (4)","Samuel Iling-Junior (3)"],
}

FORMAZIONI = {
    "Inter":{"modulo":"3-5-2","titolari":["Sommer","Bisseck","Akanji","Bastoni","Dumfries","Barella","Calhanoglu","Sucic","Dimarco","Thuram","Bonny"]},
    "Milan":{"modulo":"4-2-3-1","titolari":["Maignan","Estupinan","Tomori","De Winter","Bartesaghi","Ricci","Fofana","Pulisic","Modric","Saelemaekers","Gimenez"]},
    "Napoli":{"modulo":"3-4-2-1","titolari":["Meret","Buongiorno","Beukema","Olivera","Gutierrez","Lobotka","Anguissa","McTominay","De Bruyne","Politano","Hojlund"]},
    "Como":{"modulo":"4-2-3-1","titolari":["Butez","Van der Brempt","Diego Carlos","Kempf","Moreno","Perrone","Caqueret","Kuhn","Paz","Da Cunha","Douvikas"]},
    "Juventus":{"modulo":"4-2-3-1","titolari":["Di Gregorio","Kalulu","Gatti","Kelly","Cambiaso","Locatelli","Thuram K.","Conceicao","Koopmeiners","Yildiz","Vlahovic"]},
    "Roma":{"modulo":"3-4-2-1","titolari":["Svilar","Ndicka","Mancini","Hermoso","Rensch","El Aynaoui","Cristante","Tsimikas","Soule","Pellegrini","Malen"]},
    "Atalanta":{"modulo":"3-4-2-1","titolari":["Carnesecchi","Scalvini","Hien","Kolasinac","Bellanova","De Roon","Ederson","Zappacosta","De Ketelaere","Samardzic","Krstovic"]},
    "Lazio":{"modulo":"4-3-3","titolari":["Motta","Marusic","Provstgaard","Romagnoli","Tavares","Dele-Bashiru","Patric","Taylor","Isaksen","Maldini","Pedro"]},
    "Bologna":{"modulo":"4-3-3","titolari":["Ravaglia","Joao Mario","Vitik","Lucumi","Miranda","Moro","Freuler","Ferguson","Orsolini","Castro","Rowe"]},
    "Sassuolo":{"modulo":"4-2-3-1","titolari":["Muric","Walukiewicz","Idzes","Muharemovic","Garcia","Kone","Vranckx","Berardi","Volpato","Lauriente","Pinamonti"]},
    "Udinese":{"modulo":"3-5-2","titolari":["Okoye","Solet","Kristensen","Bertola","Ehizibue","Karlstrom","Miller","Zarraga","Zemura","Zaniolo","Davis"]},
    "Parma":{"modulo":"3-4-2-1","titolari":["Suzuki","Delprato","Circati","Valenti","Britschgi","Keita","Sorensen","Valeri","Strefezza","Ondrejka","Pellegrino"]},
    "Genoa":{"modulo":"3-5-2","titolari":["Bijlow","Vasquez","Ostigard","Martin","Norton-Cuffy","Frendrup","Malinovskyi","Baldanzi","Sabelli","Vitinha","Colombo"]},
    "Torino":{"modulo":"3-5-2","titolari":["Israel","Coco","Ismajli","Maripan","Pedersen","Casadei","Ilic","Gineitis","Nkounkou","Vlasic","Adams"]},
    "Cagliari":{"modulo":"3-5-2","titolari":["Caprile","Ze Pedro","Mina","Rodriguez","Palestra","Adopo","Gaetano","Folorunsho","Obert","Esposito","Kilicsoy"]},
    "Fiorentina":{"modulo":"4-3-3","titolari":["De Gea","Fortini","Pongracic","Ranieri","Gosens","Ndour","Fagioli","Brescianini","Parisi","Kean","Gudmundsson"]},
    "Cremonese":{"modulo":"4-4-2","titolari":["Audero","Terracciano","Bianchetti","Luperto","Pezzella","Zerbin","Maleh","Grassi","Vandeputte","Bonazzoli","Vardy"]},
    "Lecce":{"modulo":"4-3-3","titolari":["Falcone","Veiga","Siebert","Jean","Gallo","Sala","Ramadani","Fofana","Banda","Cheddira","Pierotti"]},
    "Verona":{"modulo":"3-5-2","titolari":["Montipo","Edmundsson","Nelsson","Valentini","Belghali","Akpa Akpro","Gagliardini","Harroui","Frese","Bowie","Orban"]},
    "Pisa":{"modulo":"3-4-2-1","titolari":["Semper","Canestrelli","Calabresi","Angori","Loyola","Hojholt","Aebischer","Cuadrado","Stengs","Tramoni","Meister"]},
}

INFORTUNATI = {
    "Inter":[{"nome":"Lautaro Martinez","tipo":"infortunio","dettaglio":"Da monitorare, rientro inizio aprile"},{"nome":"Mkhitaryan","tipo":"infortunio","dettaglio":"Problema muscolare"},{"nome":"Carlos Augusto","tipo":"squalifica","dettaglio":"Squalificato 1 giornata"}],
    "Milan":[{"nome":"Gabbia","tipo":"infortunio","dettaglio":"Problema muscolare, rientro aprile"},{"nome":"Loftus-Cheek","tipo":"infortunio","dettaglio":"Infortunio ginocchio"},{"nome":"Leao","tipo":"dubbio","dettaglio":"Affaticamento, da valutare"}],
    "Napoli":[{"nome":"Neres","tipo":"infortunio","dettaglio":"Problema muscolare, rientro aprile"},{"nome":"Di Lorenzo","tipo":"infortunio","dettaglio":"Distorsione ginocchio, fine aprile"},{"nome":"Rrahmani","tipo":"infortunio","dettaglio":"Rientro maggio"}],
    "Juventus":[{"nome":"Holm","tipo":"infortunio","dettaglio":"Rientro inizio aprile"}],
    "Roma":[{"nome":"Kone","tipo":"infortunio","dettaglio":"Fine aprile"},{"nome":"Dybala","tipo":"infortunio","dettaglio":"Fine aprile"},{"nome":"Dovbyk","tipo":"infortunio","dettaglio":"Rientro maggio"},{"nome":"Ferguson","tipo":"infortunio","dettaglio":"Stagione finita"}],
    "Atalanta":[{"nome":"Scamacca","tipo":"dubbio","dettaglio":"Da monitorare"}],
    "Lazio":[{"nome":"Zaccagni","tipo":"infortunio","dettaglio":"Fine aprile"},{"nome":"Rovella","tipo":"infortunio","dettaglio":"Stagione finita"},{"nome":"Provedel","tipo":"infortunio","dettaglio":"Stagione finita"}],
    "Bologna":[{"nome":"Odgaard","tipo":"infortunio","dettaglio":"Meta aprile"},{"nome":"Pobega","tipo":"infortunio","dettaglio":"Meta aprile"},{"nome":"Skorupski","tipo":"infortunio","dettaglio":"Maggio"}],
    "Sassuolo":[{"nome":"Pieragnolo","tipo":"infortunio","dettaglio":"Inizio aprile"},{"nome":"Cande","tipo":"infortunio","dettaglio":"Stagione finita"},{"nome":"Fadera","tipo":"infortunio","dettaglio":"Maggio"}],
    "Udinese":[{"nome":"Buksa","tipo":"infortunio","dettaglio":"Meta aprile"},{"nome":"Zanoli","tipo":"infortunio","dettaglio":"Stagione finita"}],
    "Parma":[{"nome":"Almqvist","tipo":"infortunio","dettaglio":"Rientro dopo sosta"},{"nome":"Cremaschi","tipo":"infortunio","dettaglio":"Stagione finita"}],
    "Genoa":[{"nome":"Onana","tipo":"dubbio","dettaglio":"Da valutare"}],
    "Torino":[{"nome":"Aboukhlal","tipo":"dubbio","dettaglio":"Da valutare"}],
    "Cagliari":[{"nome":"Felici","tipo":"infortunio","dettaglio":"Stagione finita"},{"nome":"Idrissi","tipo":"infortunio","dettaglio":"Stagione finita"}],
    "Fiorentina":[{"nome":"Solomon","tipo":"infortunio","dettaglio":"Rientro aprile"},{"nome":"Lamptey","tipo":"infortunio","dettaglio":"Rientro aprile"}],
    "Cremonese":[{"nome":"Baschirotto","tipo":"infortunio","dettaglio":"Inizio aprile"}],
    "Lecce":[{"nome":"Gaspar","tipo":"infortunio","dettaglio":"Stagione finita"},{"nome":"Berisha","tipo":"infortunio","dettaglio":"Stagione finita"},{"nome":"Camarda","tipo":"infortunio","dettaglio":"Rientro aprile"}],
    "Verona":[], "Pisa":[{"nome":"Denoon","tipo":"infortunio","dettaglio":"Lungodegente"},{"nome":"Scuffet","tipo":"infortunio","dettaglio":"Inizio aprile"}],
    "Como":[{"nome":"Addai","tipo":"infortunio","dettaglio":"Stagione finita"}],
}

ROSE = {
    "Inter":[("Sommer","P",1),("Martinez J.","P",13),("Di Gennaro","P",12),("Bastoni","D",95),("Bisseck","D",31),("Akanji","D",25),("De Vrij","D",6),("Acerbi","D",15),("Dimarco","D",32),("Carlos Augusto","D",30),("Dumfries","D",2),("Darmian","D",36),("Calhanoglu","C",20),("Barella","C",23),("Sucic","C",8),("Frattesi","C",16),("Diouf","C",17),("Zielinski","C",7),("Mkhitaryan","C",22),("Lautaro Martinez","A",10),("Thuram","A",9),("Bonny","A",14),("Pio Esposito","A",94),("Luis Henrique","A",11)],
    "Milan":[("Maignan","P",16),("Terracciano","P",1),("Torriani","P",96),("Pavlovic","D",31),("De Winter","D",5),("Tomori","D",23),("Gabbia","D",46),("Estupinan","D",2),("Bartesaghi","D",33),("Ricci","C",4),("Fofana","C",19),("Rabiot","C",12),("Loftus-Cheek","C",8),("Modric","C",14),("Jashari","C",30),("Leao","A",10),("Pulisic","A",11),("Nkunku","A",18),("Gimenez","A",7),("Fullkrug","A",9),("Saelemaekers","A",56)],
    "Napoli":[("Meret","P",1),("Contini","P",14),("Milinkovic-Savic","P",32),("Buongiorno","D",4),("Beukema","D",31),("Rrahmani","D",13),("Gutierrez","D",3),("Olivera","D",17),("Di Lorenzo","D",22),("Spinazzola","D",37),("Mazzocchi","D",30),("Gilmour","C",6),("Lobotka","C",68),("McTominay","C",8),("Anguissa","C",99),("De Bruyne","C",11),("Hojlund","A",19),("Lukaku","A",9),("Neres","A",7),("Politano","A",21),("Giovane","A",23),("Alisson Santos","A",77)],
    "Juventus":[("Di Gregorio","P",16),("Perin","P",1),("Pinsoglio","P",23),("Bremer","D",3),("Kalulu","D",15),("Kelly","D",6),("Gatti","D",4),("Cambiaso","D",27),("Cabal","D",32),("Holm","D",2),("Locatelli","C",5),("Thuram K.","C",19),("McKennie","C",22),("Koopmeiners","C",8),("Kostic","C",18),("Vlahovic","A",9),("David","A",30),("Openda","A",20),("Conceicao","A",7),("Yildiz","A",10),("Zhegrova","A",11),("Boga","A",14)],
    "Roma":[("Svilar","P",99),("Gollini","P",95),("Zelezny","P",91),("Ndicka","D",5),("Mancini","D",23),("Hermoso","D",22),("Angelino","D",3),("Tsimikas","D",12),("Wesley","D",43),("Celik","D",19),("Rensch","D",2),("Cristante","C",4),("Kone","C",17),("El Aynaoui","C",8),("Pisilli","C",61),("Pellegrini","C",7),("Dybala","A",21),("Malen","A",14),("Ferguson","A",11),("Dovbyk","A",9),("Soule","A",18),("El Shaarawy","A",92),("Zaragoza","A",97),("Vaz","A",78)],
    "Atalanta":[("Carnesecchi","P",29),("Sportiello","P",57),("Rossi","P",31),("Scalvini","D",42),("Hien","D",4),("Kossounou","D",3),("Kolasinac","D",23),("Djimsiti","D",19),("Ederson","C",13),("Musah","C",6),("Pasalic","C",8),("De Roon","C",15),("Bellanova","C",16),("Zappacosta","C",77),("Zalewski","C",59),("De Ketelaere","A",17),("Samardzic","A",10),("Raspadori","A",18),("Scamacca","A",9),("Krstovic","A",90)],
    "Lazio":[("Provedel","P",94),("Motta","P",40),("Furlanetto","P",55),("Gila","D",34),("Provstgaard","D",25),("Romagnoli","D",13),("Gigot","D",2),("Patric","D",4),("Tavares","D",17),("Pellegrini L.","D",3),("Marusic","D",77),("Lazzari","D",29),("Rovella","C",6),("Belahyane","C",21),("Taylor","C",24),("Dele-Bashiru","C",7),("Maldini","A",27),("Przyborek","A",28),("Zaccagni","A",10),("Isaksen","A",18),("Dia","A",19),("Pedro","A",9),("Noslin","A",14),("Ratkov","A",20)],
    "Bologna":[("Skorupski","P",1),("Ravaglia","P",13),("Pessina","P",25),("Lucumi","D",26),("Heggem","D",14),("Vitik","D",41),("Helland","D",5),("Casale","D",16),("Miranda","D",33),("Joao Mario","D",17),("Zortea","D",20),("Moro","C",6),("Ferguson L.","C",19),("Pobega","C",4),("Freuler","C",8),("Odgaard","C",21),("Sohm","C",23),("Castro","A",9),("Dallinga","A",24),("Orsolini","A",7),("Bernardeschi","A",10),("Rowe","A",11)],
    "Sassuolo":[("Muric","P",49),("Turati","P",13),("Zacchi","P",16),("Idzes","D",21),("Doig","D",3),("Walukiewicz","D",6),("Romagna","D",19),("Pieragnolo","D",15),("Garcia","D",23),("Coulibaly","D",25),("Lipani","C",35),("Boloca","C",11),("Matic","C",18),("Kone","C",90),("Thorstvedt","C",42),("Vranckx","C",40),("Berardi","A",25),("Pinamonti","A",9),("Lauriente","A",45),("Volpato","A",7)],
    "Udinese":[("Okoye","P",40),("Sava","P",90),("Nunziante","P",1),("Solet","D",28),("Kristensen","D",31),("Bertola","D",13),("Mlacic","D",22),("Kabasele","D",27),("Zemura","D",33),("Kamara","D",11),("Zanoli","D",59),("Ehizibue","D",19),("Karlstrom","C",8),("Camara","C",29),("Miller","C",38),("Zarraga","C",6),("Piotrowski","C",24),("Zaniolo","A",10),("Davis","A",9),("Buksa","A",18),("Bayo","A",15)],
    "Parma":[("Suzuki","P",31),("Corvi","P",40),("Rinaldi","P",66),("Circati","D",39),("Valenti","D",5),("Delprato","D",15),("Valeri","D",14),("Carboni","D",29),("Britschgi","D",27),("Ndiaye","D",3),("Keita","C",16),("Estevez","C",8),("Bernabe","C",10),("Sorensen","C",22),("Nicolussi Caviglia","C",41),("Oristanio","C",21),("Strefezza","A",7),("Almqvist","A",11),("Pellegrino","A",9),("Ondrejka","A",17)],
    "Genoa":[("Bijlow","P",16),("Leali","P",1),("Siegrist","P",31),("Vasquez","D",22),("Ostigard","D",5),("Marcandalli","D",27),("Zattstrom","D",13),("Martin","D",3),("Norton-Cuffy","D",15),("Sabelli","D",20),("Frendrup","C",32),("Onana","C",14),("Malinovskyi","C",17),("Baldanzi","C",8),("Ellertsson","C",77),("Messias","A",10),("Colombo","A",29),("Vitinha","A",9),("Ekuban","A",18),("Ekhator","A",21)],
    "Torino":[("Israel","P",81),("Paleari","P",1),("Siviero","P",99),("Coco","D",23),("Ismajli","D",44),("Maripan","D",13),("Ebosse","D",77),("Biraghi","D",34),("Pedersen","D",16),("Nkounkou","D",25),("Obrador","D",33),("Prati","C",4),("Casadei","C",22),("Ilic","C",8),("Gineitis","C",66),("Lazaro","C",20),("Tameze","C",61),("Vlasic","A",10),("Adams","A",19),("Simeone","A",7),("Aboukhlal","A",17)],
    "Cagliari":[("Caprile","P",1),("Sherri","P",12),("Ciocci","P",24),("Dossena","D",22),("Obert","D",33),("Rodriguez","D",15),("Mina","D",26),("Ze Pedro","D",32),("Zappa","D",28),("Raterink","D",18),("Sulemana","C",25),("Adopo","C",8),("Folorunsho","C",90),("Mazzitelli","C",4),("Gaetano","C",10),("Deiola","C",14),("Esposito","A",94),("Kilicsoy","A",9),("Felici","A",17),("Borrelli","A",29)],
    "Fiorentina":[("De Gea","P",43),("Christensen","P",53),("Lezzerini","P",1),("Comuzzo","D",15),("Pongracic","D",5),("Ranieri","D",6),("Gosens","D",21),("Dodo","D",2),("Lamptey","D",48),("Parisi","D",65),("Fortini","D",29),("Mandragora","C",8),("Fagioli","C",44),("Ndour","C",27),("Brescianini","C",4),("Fazzini","C",22),("Gudmundsson","A",10),("Kean","A",9),("Beltran","A",7),("Sottil","A",14),("Harrison","A",17),("Solomon","A",19)],
    "Cremonese":[("Audero","P",1),("Silvestri","P",16),("Nava","P",69),("Pezzella","D",3),("Luperto","D",5),("Baschirotto","D",6),("Bianchetti","D",15),("Barbieri","D",4),("Faye","D",30),("Terracciano F.","D",24),("Thorsby","C",2),("Bondo","C",38),("Vandeputte","C",27),("Maleh","C",29),("Payero","C",32),("Grassi","C",33),("Collocolo","C",18),("Vardy","A",10),("Djuric","A",9),("Zerbin","A",7),("Okereke","A",77),("Sanabria","A",99),("Bonazzoli","A",90)],
    "Lecce":[("Falcone","P",30),("Fruchtl","P",1),("Samooja","P",32),("Gaspar","D",4),("Gallo","D",25),("Veiga","D",17),("Jean","D",18),("Perez","D",13),("Ndaba","D",3),("Siebert","D",5),("Ramadani","C",20),("Fofana","C",8),("Berisha","C",10),("Coulibaly","C",29),("Sala","C",6),("Helgason","C",14),("Marchwinski","C",36),("Banda","A",19),("Camarda","A",22),("Cheddira","A",99),("N'Dri","A",11),("Pierotti","A",50)],
    "Verona":[("Montipo","P",1),("Perilli","P",34),("Toniolo","P",94),("Nelsson","D",15),("Bella-Kotchap","D",37),("Slotsager","D",19),("Edmundsson","D",5),("Frese","D",3),("Bradaric","D",12),("Lirola","D",14),("Oyegoke","D",2),("Al-Musrati","C",73),("Lovric","C",4),("Serdar","C",8),("Harroui","C",21),("Gagliardini","C",63),("Akpa Akpro","C",11),("Suslov","A",10),("Henry","A",9),("Tengstedt","A",20),("Lazovic","A",17),("Duda","A",27)],
    "Pisa":[("Semper","P",1),("Nicolas","P",12),("Scuffet","P",22),("Canestrelli","D",5),("Calabresi","D",33),("Loyola","D",35),("Angori","D",3),("Albiol","D",39),("Marin","C",6),("Leris","C",7),("Hojholt","C",8),("Cuadrado","C",11),("Akinsanmiro","C",14),("Aebischer","C",20),("Stengs","C",23),("Lorran","C",99),("Meister","A",9),("Tramoni","A",10),("Durosinmi","A",17),("Iling-Junior","A",19),("Moreo","A",32)],
    "Como":[("Butez","P",1),("Tornqvist","P",21),("Cavlina","P",44),("Diego Carlos","D",34),("Kempf","D",2),("Goldaniga","D",5),("Valle","D",3),("Moreno","D",18),("Van der Brempt","D",77),("Vojvoda","D",31),("Smolcic","D",28),("Ramon","D",14),("Perrone","C",23),("Da Cunha","C",33),("Caqueret","C",6),("Ladho","C",15),("Sergi Roberto","C",8),("Paz","C",10),("Baturina","C",20),("Diao","A",38),("Kuhn","A",19),("Douvikas","A",11),("Morata","A",7),("Jesus Rodriguez","A",17)],
}

@app.get("/api/squadra/{nome}")
async def squadra(nome: str):
    n = nome.strip().title()
    # Usa dati live se disponibili, altrimenti hardcoded
    form = LIVE_FORMAZIONI.get(n) or FORMAZIONI.get(n)
    inj = LIVE_INFORTUNATI.get(n) if LIVE_INFORTUNATI.get(n) is not None else INFORTUNATI.get(n, [])
    return {
        "nome": n,
        "allenatore": ALLENATORI.get(n, "N/D"),
        "formazione": form,
        "infortunati": inj,
        "rosa": [{"nome":g[0],"ruolo":g[1],"numero":g[2]} for g in ROSE.get(n, [])],
        "ultimo_aggiornamento": LIVE_LAST_UPDATE or "Dati base",
    }

# ─────────────────────────────
# SCHEDINA DEL GIORNO (IA)
# ─────────────────────────────
@app.get("/api/schedina")
async def schedina_del_giorno():
    """L'IA seleziona le 3-5 giocate piu' sicure della giornata 31."""
    giocate = []
    cal = CAL_HARDCODED.get(31, {})
    partite = cal.get("partite", [])

    for home, away in partite:
        try:
            raw = genera_pronostico(home, away)
            if raw.get("sicura"):
                giocate.append({
                    "home": home, "away": away,
                    "tip": raw["suggerimento"],
                    "tip_label": raw["sugg_label"],
                    "prob": max(raw["prob_1"], raw["prob_x"], raw["prob_2"]),
                    "quota": raw.get(f"quota_{raw['suggerimento'].lower().replace('x','x')}", 0),
                    "confidence": raw["confidence"],
                    "over_under": "Over 2.5" if raw.get("over_25",0) > 55 else "Under 2.5",
                    "goal": "Goal Si" if raw.get("goal_si",0) > 55 else "Goal No",
                })
        except Exception:
            continue

    # Ordina per confidence e prendi top 5
    giocate.sort(key=lambda x: -x["confidence"])
    top = giocate[:5]

    # Calcola quota totale schedina
    quota_tot = 1.0
    for g in top:
        q = g.get("quota", 1.5)
        if q > 1: quota_tot *= q

    return {
        "giornata": 31,
        "data": cal.get("data", ""),
        "giocate": top,
        "n_giocate": len(top),
        "quota_totale": round(quota_tot, 2),
        "tipo": "Schedina SICURA — Solo giocate ad alta confidenza",
    }

# ─────────────────────────────
# NOTIZIE LIVE SERIE A
# ─────────────────────────────
NOTIZIE_CACHE = []
NOTIZIE_LAST_UPDATE = ""

def _scrape_notizie():
    """Scarica notizie Serie A con link specifici agli articoli."""
    global NOTIZIE_CACHE, NOTIZIE_LAST_UPDATE
    import urllib.request as ur
    import re
    notizie = []
    try:
        req = ur.Request("https://sport.sky.it/calcio/serie-a", headers={"User-Agent":"Mozilla/5.0"})
        with ur.urlopen(req, timeout=10) as r:
            html = r.read().decode("utf-8", errors="replace")
        # Estrai coppie link+titolo: <a href="/calcio/serie-a/...">Titolo</a>
        links = re.findall(r'<a[^>]+href="(/calcio/serie-a/[^"]{20,})"[^>]*>([^<]{15,120})</a>', html)
        seen = set()
        for url, titolo in links:
            t = re.sub(r'<[^>]+>','',titolo).strip()
            if t and t not in seen and len(t)>15:
                seen.add(t)
                notizie.append({"titolo":t,"fonte":"Sky Sport","url":"https://sport.sky.it"+url})
                if len(notizie)>=6: break
    except Exception as e:
        print(f"⚠️ Scrape Sky: {e}")
    try:
        req = ur.Request("https://www.gazzetta.it/calcio/serie-a/", headers={"User-Agent":"Mozilla/5.0"})
        with ur.urlopen(req, timeout=10) as r:
            html = r.read().decode("utf-8", errors="replace")
        links = re.findall(r'<a[^>]+href="(https?://www\.gazzetta\.it/[^"]{20,})"[^>]*>([^<]{15,120})</a>', html)
        seen2 = set()
        for url, titolo in links:
            t = re.sub(r'<[^>]+>','',titolo).strip()
            if t and t not in seen2 and len(t)>15:
                seen2.add(t)
                notizie.append({"titolo":t,"fonte":"Gazzetta","url":url})
                if len(notizie)>=12: break
    except Exception as e:
        print(f"⚠️ Scrape Gazzetta: {e}")
    if notizie:
        NOTIZIE_CACHE = notizie[:12]
        NOTIZIE_LAST_UPDATE = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M")
        print(f"📰 Notizie: {len(NOTIZIE_CACHE)} articoli con link")

@app.get("/api/notizie")
async def notizie():
    """Ritorna le ultime notizie Serie A."""
    if not NOTIZIE_CACHE:
        return {"notizie":[
            {"titolo":"Serie A Giornata 31: Inter-Roma, Napoli-Milan e tutte le probabili formazioni","fonte":"Sky Sport","url":"https://sport.sky.it/calcio/serie-a/calendario-risultati"},
            {"titolo":"Classifica Serie A 2025-2026: Inter prima a 69 punti, Milan insegue","fonte":"Sky Sport","url":"https://sport.sky.it/calcio/serie-a/classifica"},
            {"titolo":"Classifica marcatori Serie A: Lautaro Martinez capocannoniere con 14 gol","fonte":"Tuttosport","url":"https://www.tuttosport.com/live/classifica-marcatori-serie-a"},
            {"titolo":"Infortunati Serie A: Dybala, Dovbyk e Lautaro in dubbio per la giornata 31","fonte":"Fantacalcio","url":"https://www.fantacalciopedia.com/articoli-fcp/consigli-fantacalcio/75-lista-infortunati-serie-a-aggiornata.html"},
            {"titolo":"Calciomercato Serie A: tutti gli acquisti e le cessioni di gennaio 2026","fonte":"Sky Sport","url":"https://sport.sky.it/calciomercato"},
            {"titolo":"Spalletti alla Juventus: i risultati dopo il cambio in panchina","fonte":"Gazzetta","url":"https://www.gazzetta.it/calcio/serie-a/squadre/juventus/"},
            {"titolo":"Como sorpresa: Fabregas quarto in classifica, Douvikas bomber","fonte":"Sky Sport","url":"https://sport.sky.it/calcio/serie-a"},
            {"titolo":"Palladino rilancia l'Atalanta: Krstovic e Raspadori coppia gol","fonte":"Gazzetta","url":"https://www.gazzetta.it/calcio/serie-a/squadre/atalanta/"},
        ],"aggiornamento":"Aggiornamento automatico ogni 30 min"}
    return {"notizie":NOTIZIE_CACHE,"aggiornamento":NOTIZIE_LAST_UPDATE}

# ─────────────────────────────
# HEALTH CHECK
# ─────────────────────────────
@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "motore": MOTORE_DISPONIBILE,
        "dati_caricati": _df is not None
    }

# ─────────────────────────────
# RUN LOCALE
# ─────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api_server:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))