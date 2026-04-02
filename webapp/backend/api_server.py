"""
api_server.py
Versione completa FIXATA per frontend + Railway
"""

import sys
import os

# ─────────────────────────────────────────────
# PATH PROJECT ROOT
# ─────────────────────────────────────────────
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, _ROOT)

from typing import Optional
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse

# ─────────────────────────────────────────────
# IMPORT MOTORE
# ─────────────────────────────────────────────
try:
    from data_loader import load_all_data
    from stats_engine import get_team_stats
    from predictor import get_prediction
    from season_2526 import (
        get_classifica_reale,
        get_calendario_rimanente,
        GIORNATA_ATTUALE,
    )
    from squads_2526 import get_marcatori
    MOTORE_DISPONIBILE = True
except Exception as e:
    print("Errore motore:", e)
    MOTORE_DISPONIBILE = False

# ─────────────────────────────────────────────
# IMPORT BACKEND
# ─────────────────────────────────────────────
from database import init_db, log_api_call, count_daily_calls, get_user_by_email, create_user
from api_auth import get_current_user, get_optional_user, hash_password, verify_password, create_token
from api_models import *
from api_payments import router as payments_router

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
app = FastAPI(title="Pronostici Serie A API", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(payments_router)

LIMITE_FREE = 2
_df = None


# ─────────────────────────────────────────────
# STARTUP
# ─────────────────────────────────────────────
@app.on_event("startup")
async def startup():
    global _df

    print("🚀 Avvio server...")

    try:
        init_db()
        print("✅ Database pronto")
    except Exception as e:
        print("❌ DB error:", e)

    if MOTORE_DISPONIBILE:
        try:
            _df = load_all_data()
            print("✅ Dati caricati")
        except Exception as e:
            print("❌ Errore dati:", e)


# ─────────────────────────────────────────────
# FRONTEND SERVE
# ─────────────────────────────────────────────
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")

@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse("/app")

@app.get("/app", include_in_schema=False)
@app.get("/app/{path:path}", include_in_schema=False)
async def serve_app(path: str = ""):
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))


# ─────────────────────────────────────────────
# UTILS
# ─────────────────────────────────────────────
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
        except:
            pass

    # fallback
    return {
        "prob_1": 34,
        "prob_x": 33,
        "prob_2": 33,
        "quota_1": 2.2,
        "quota_x": 3.1,
        "quota_2": 2.9,
        "suggerimento": "1",
        "sugg_label": "Fallback",
        "confidence": 0.5,
        "confidence_label": "Media",
    }


# ─────────────────────────────────────────────
# AUTH
# ─────────────────────────────────────────────
@app.post("/api/auth/register")
async def register(data: UserRegister):
    email = data.email.lower()

    if get_user_by_email(email):
        raise HTTPException(409, "Email già registrata")

    user = create_user(email, hash_password(data.password))
    token = create_token({"sub": str(user["id"])})

    return {"access_token": token, "piano": user["piano"]}


@app.post("/api/auth/login")
async def login(data: UserLogin):
    user = get_user_by_email(data.email.lower())

    if not user or not verify_password(data.password, user["password_hash"]):
        raise HTTPException(401, "Credenziali errate")

    token = create_token({"sub": str(user["id"])})

    return {"access_token": token, "piano": user["piano"]}


# ─────────────────────────────────────────────
# PRONOSTICO (compatibile frontend)
# ─────────────────────────────────────────────
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


# ─────────────────────────────────────────────
# CALENDARIO (FIX ERRORE 404)
# ─────────────────────────────────────────────
@app.get("/api/calendario")
async def calendario():
    try:
        if not MOTORE_DISPONIBILE:
            return {"giornate": []}

        cal = get_calendario_rimanente()

        return {
            "giornate": [
                {
                    "giornata": g["giornata"],
                    "data": g.get("data", ""),
                    "partite": [
                        {"home": p["home"], "away": p["away"]}
                        for p in g["partite"]
                    ]
                }
                for g in cal
            ]
        }

    except Exception as e:
        raise HTTPException(500, str(e))


# ─────────────────────────────────────────────
# CLASSIFICA
# ─────────────────────────────────────────────
@app.get("/api/classifica")
async def classifica():
    try:
        return get_classifica_reale()
    except Exception as e:
        raise HTTPException(500, str(e))


# ─────────────────────────────────────────────
# MARCATORI
# ─────────────────────────────────────────────
@app.get("/api/marcatori")
async def marcatori():
    try:
        return get_marcatori()
    except Exception as e:
        raise HTTPException(500, str(e))


# ─────────────────────────────────────────────
# HEALTH
# ─────────────────────────────────────────────
@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "motore": MOTORE_DISPONIBILE,
        "dati": _df is not None
    }


# ─────────────────────────────────────────────
# RUN LOCALE
# ─────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api_server:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))

