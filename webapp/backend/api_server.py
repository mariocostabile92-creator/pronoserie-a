"""
api_server.py - VERSIONE FINALE STABILE
Compatibile con frontend PronoSerie A
Fix calendario + fallback + debug + Railway ready
"""

import sys
import os

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

# ─────────────────────────────
# FRONTEND
# ─────────────────────────────
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")

@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse("/app")

@app.get("/app", include_in_schema=False)
@app.get("/app/{path:path}", include_in_schema=False)
async def serve_app(path: str = ""):
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

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

    # Fallback con Poisson + xG inline (funziona SEMPRE)
    from scipy.stats import poisson as pdist
    XG = {
        "Inter":{"xG":2.40,"xGA":0.84},"Milan":{"xG":1.83,"xGA":1.12},"Napoli":{"xG":1.56,"xGA":1.10},
        "Como":{"xG":1.80,"xGA":1.08},"Juventus":{"xG":1.97,"xGA":0.97},"Roma":{"xG":1.54,"xGA":1.20},
        "Atalanta":{"xG":1.86,"xGA":1.38},"Lazio":{"xG":1.21,"xGA":1.34},"Bologna":{"xG":1.34,"xGA":1.39},
        "Sassuolo":{"xG":1.19,"xGA":1.63},"Udinese":{"xG":1.19,"xGA":1.56},"Parma":{"xG":1.00,"xGA":1.62},
        "Genoa":{"xG":1.30,"xGA":1.45},"Torino":{"xG":1.33,"xGA":1.57},"Cagliari":{"xG":1.01,"xGA":1.65},
        "Fiorentina":{"xG":1.52,"xGA":1.53},"Cremonese":{"xG":1.03,"xGA":1.87},"Lecce":{"xG":0.93,"xGA":1.67},
        "Verona":{"xG":1.03,"xGA":1.40},"Pisa":{"xG":1.14,"xGA":1.82},
    }
    h = home.strip().title()
    a = away.strip().title()
    xh = XG.get(h, {"xG":1.3,"xGA":1.3})
    xa = XG.get(a, {"xG":1.3,"xGA":1.3})
    avg = sum(v["xGA"] for v in XG.values()) / len(XG)
    lh = max(0.3, min(xh["xG"] * (xa["xGA"] / avg), 5.0))
    la = max(0.3, min(xa["xG"] * (xh["xGA"] / avg), 5.0))

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
    tot = p1 + px + p2
    if tot > 0: p1/=tot; px/=tot; p2/=tot

    ov25 = sum(pdist.pmf(i,lh)*pdist.pmf(j,la) for i in range(11) for j in range(11) if i+j>2.5)
    gsi = sum(pdist.pmf(i,lh)*pdist.pmf(j,la) for i in range(1,11) for j in range(1,11))
    scores = sorted([{"score":f"{i}-{j}","prob":round(pdist.pmf(i,lh)*pdist.pmf(j,la)*100,1)} for i in range(6) for j in range(6)], key=lambda x:-x["prob"])

    mp = max(p1, px, p2)
    sg = "1" if mp==p1 else ("X" if mp==px else "2")
    sl = "Vittoria Casa" if sg=="1" else ("Pareggio" if sg=="X" else "Vittoria Ospite")
    sp = sorted([p1,px,p2], reverse=True)
    cf = min((sp[0]-sp[1])/0.4, 1.0)*0.7+0.3
    cl = "Alta" if cf>=0.65 else ("Media" if cf>=0.4 else "Bassa")

    return {
        "prob_1":round(p1*100,1),"prob_x":round(px*100,1),"prob_2":round(p2*100,1),
        "quota_1":round(1.05/p1,2) if p1>0 else 99,"quota_x":round(1.05/px,2) if px>0 else 99,"quota_2":round(1.05/p2,2) if p2>0 else 99,
        "suggerimento":sg,"sugg_label":sl,"confidence":round(cf,3),"confidence_label":cl,
        "over_25":round(ov25*100,1),"under_25":round((1-ov25)*100,1),
        "goal_si":round(gsi*100,1),"goal_no":round((1-gsi)*100,1),
        "gol_attesi":round(lh+la,2),"risultati_esatti":scores[:5],
    }

# ─────────────────────────────
# AUTH
# ─────────────────────────────
@app.post("/api/auth/register")
async def register(data: dict):
    email = data["email"].lower().strip()

    if get_user_by_email(email):
        raise HTTPException(409, "Email già registrata")

    user = create_user(email, hash_password(data["password"]))
    token = create_token({"sub": str(user["id"])})

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
    conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (hash_password(new_pass), user["id"]))
    conn.commit()
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
        "risultati_esatti": raw.get("risultati_esatti", [])
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
    try:
        return get_classifica_reale()
    except Exception as e:
        print("❌ ERRORE CLASSIFICA:", e)
        return {}

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