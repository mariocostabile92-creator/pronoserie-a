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
# SQUADRE (rose, formazioni, infortunati)
# ─────────────────────────────
ALLENATORI = {"Inter":"Cristian Chivu","Milan":"Massimiliano Allegri","Napoli":"Antonio Conte","Como":"Cesc Fabregas","Juventus":"Luciano Spalletti","Roma":"Gian Piero Gasperini","Atalanta":"Raffaele Palladino","Lazio":"Maurizio Sarri","Bologna":"Vincenzo Italiano","Sassuolo":"Fabio Grosso","Udinese":"Kosta Runjaic","Parma":"Carlos Cuesta","Genoa":"Patrick Vieira","Torino":"Roberto D'Aversa","Cagliari":"Fabio Pisacane","Fiorentina":"Paolo Vanoli","Cremonese":"Davide Nicola","Lecce":"Eusebio Di Francesco","Verona":"Paolo Sammarco","Pisa":"Oscar Hiljemark"}

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
    "Inter":[("Sommer","P",1),("Martinez J.","P",13),("Bastoni","D",95),("Bisseck","D",31),("Akanji","D",25),("De Vrij","D",6),("Acerbi","D",15),("Dimarco","D",32),("Dumfries","D",2),("Darmian","D",36),("Calhanoglu","C",20),("Barella","C",23),("Sucic","C",8),("Frattesi","C",16),("Zielinski","C",7),("Mkhitaryan","C",22),("Lautaro Martinez","A",10),("Thuram","A",9),("Bonny","A",14),("Luis Henrique","A",11)],
    "Milan":[("Maignan","P",16),("Terracciano","P",1),("Pavlovic","D",31),("De Winter","D",5),("Tomori","D",23),("Gabbia","D",46),("Estupinan","D",2),("Bartesaghi","D",33),("Ricci","C",4),("Fofana","C",19),("Rabiot","C",12),("Loftus-Cheek","C",8),("Modric","C",14),("Jashari","C",30),("Leao","A",10),("Pulisic","A",11),("Nkunku","A",18),("Gimenez","A",7),("Fullkrug","A",9),("Saelemaekers","A",56)],
    "Napoli":[("Meret","P",1),("Contini","P",14),("Buongiorno","D",4),("Beukema","D",31),("Rrahmani","D",13),("Gutierrez","D",3),("Olivera","D",17),("Di Lorenzo","D",22),("Gilmour","C",6),("Lobotka","C",68),("McTominay","C",8),("Anguissa","C",99),("De Bruyne","C",11),("Hojlund","A",19),("Lukaku","A",9),("Neres","A",7),("Politano","A",21),("Giovane","A",23),("Alisson Santos","A",77)],
    "Juventus":[("Di Gregorio","P",16),("Perin","P",1),("Bremer","D",3),("Kalulu","D",15),("Kelly","D",6),("Gatti","D",4),("Cambiaso","D",27),("Holm","D",2),("Locatelli","C",5),("Thuram K.","C",19),("McKennie","C",22),("Koopmeiners","C",8),("Vlahovic","A",9),("David","A",30),("Openda","A",20),("Conceicao","A",7),("Yildiz","A",10),("Boga","A",14)],
    "Roma":[("Svilar","P",99),("Gollini","P",95),("Ndicka","D",5),("Mancini","D",23),("Hermoso","D",22),("Angelino","D",3),("Tsimikas","D",12),("Celik","D",19),("Rensch","D",2),("Cristante","C",4),("Kone","C",17),("El Aynaoui","C",8),("Pisilli","C",61),("Pellegrini","C",7),("Dybala","A",21),("Malen","A",14),("Ferguson","A",11),("Dovbyk","A",9),("Soule","A",18),("El Shaarawy","A",92),("Zaragoza","A",97),("Vaz","A",78)],
    "Atalanta":[("Carnesecchi","P",29),("Sportiello","P",57),("Scalvini","D",42),("Hien","D",4),("Kossounou","D",3),("Kolasinac","D",23),("Djimsiti","D",19),("Ederson","C",13),("Musah","C",6),("Pasalic","C",8),("De Roon","C",15),("Bellanova","C",16),("Zappacosta","C",77),("De Ketelaere","A",17),("Samardzic","A",10),("Raspadori","A",18),("Scamacca","A",9),("Krstovic","A",90)],
    "Lazio":[("Provedel","P",94),("Motta","P",40),("Gila","D",34),("Romagnoli","D",13),("Gigot","D",2),("Tavares","D",17),("Marusic","D",77),("Lazzari","D",29),("Rovella","C",6),("Belahyane","C",21),("Taylor","C",24),("Dele-Bashiru","C",7),("Maldini","A",27),("Zaccagni","A",10),("Isaksen","A",18),("Dia","A",19),("Pedro","A",9),("Noslin","A",14),("Ratkov","A",20)],
    "Bologna":[("Skorupski","P",1),("Ravaglia","P",13),("Lucumi","D",26),("Vitik","D",41),("Casale","D",16),("Miranda","D",33),("Joao Mario","D",17),("Moro","C",6),("Ferguson L.","C",19),("Pobega","C",4),("Freuler","C",8),("Odgaard","C",21),("Castro","A",9),("Dallinga","A",24),("Orsolini","A",7),("Bernardeschi","A",10),("Rowe","A",11)],
    "Sassuolo":[("Muric","P",49),("Turati","P",13),("Idzes","D",21),("Doig","D",3),("Walukiewicz","D",6),("Romagna","D",19),("Pieragnolo","D",15),("Lipani","C",35),("Boloca","C",11),("Matic","C",18),("Kone","C",90),("Thorstvedt","C",42),("Berardi","A",25),("Pinamonti","A",9),("Lauriente","A",45),("Volpato","A",7)],
    "Udinese":[("Okoye","P",40),("Sava","P",90),("Solet","D",28),("Kristensen","D",31),("Bertola","D",13),("Kabasele","D",27),("Zemura","D",33),("Zanoli","D",59),("Karlstrom","C",8),("Miller","C",38),("Zarraga","C",6),("Zaniolo","A",10),("Davis","A",9),("Buksa","A",18)],
    "Parma":[("Suzuki","P",31),("Circati","D",39),("Valenti","D",5),("Delprato","D",15),("Valeri","D",14),("Carboni","D",29),("Keita","C",16),("Bernabe","C",10),("Nicolussi Caviglia","C",41),("Oristanio","C",21),("Strefezza","A",7),("Almqvist","A",11),("Pellegrino","A",9)],
    "Genoa":[("Bijlow","P",16),("Leali","P",1),("Vasquez","D",22),("Ostigard","D",5),("Martin","D",3),("Norton-Cuffy","D",15),("Sabelli","D",20),("Frendrup","C",32),("Malinovskyi","C",17),("Baldanzi","C",8),("Ellertsson","C",77),("Messias","A",10),("Colombo","A",29),("Vitinha","A",9),("Ekuban","A",18)],
    "Torino":[("Israel","P",81),("Paleari","P",1),("Coco","D",23),("Ismajli","D",44),("Maripan","D",13),("Biraghi","D",34),("Pedersen","D",16),("Nkounkou","D",25),("Prati","C",4),("Casadei","C",22),("Ilic","C",8),("Gineitis","C",66),("Lazaro","C",20),("Vlasic","A",10),("Adams","A",19),("Simeone","A",7)],
    "Cagliari":[("Caprile","P",1),("Sherri","P",12),("Dossena","D",22),("Mina","D",26),("Obert","D",33),("Zappa","D",28),("Sulemana","C",25),("Adopo","C",8),("Folorunsho","C",90),("Mazzitelli","C",4),("Gaetano","C",10),("Esposito","A",94),("Kilicsoy","A",9),("Felici","A",17)],
    "Fiorentina":[("De Gea","P",43),("Christensen","P",53),("Comuzzo","D",15),("Ranieri","D",6),("Gosens","D",21),("Dodo","D",2),("Lamptey","D",48),("Parisi","D",65),("Mandragora","C",8),("Fagioli","C",44),("Brescianini","C",4),("Fazzini","C",22),("Gudmundsson","A",10),("Kean","A",9),("Beltran","A",7),("Harrison","A",17)],
    "Cremonese":[("Audero","P",1),("Silvestri","P",16),("Pezzella","D",3),("Luperto","D",5),("Baschirotto","D",6),("Bianchetti","D",15),("Barbieri","D",4),("Faye","D",30),("Thorsby","C",2),("Bondo","C",38),("Vandeputte","C",27),("Payero","C",32),("Grassi","C",33),("Vardy","A",10),("Djuric","A",9),("Zerbin","A",7),("Sanabria","A",99)],
    "Lecce":[("Falcone","P",30),("Fruchtl","P",1),("Gaspar","D",4),("Gallo","D",25),("Veiga","D",17),("Ramadani","C",20),("Berisha","C",10),("Coulibaly","C",29),("Sala","C",6),("Marchwinski","C",36),("Banda","A",19),("Camarda","A",22),("Cheddira","A",99),("Pierotti","A",50)],
    "Verona":[("Montipo","P",1),("Perilli","P",34),("Nelsson","D",15),("Bella-Kotchap","D",37),("Bradaric","D",12),("Lirola","D",14),("Oyegoke","D",2),("Lovric","C",4),("Serdar","C",8),("Harroui","C",21),("Gagliardini","C",63),("Suslov","A",10),("Henry","A",9),("Tengstedt","A",20),("Duda","A",27)],
    "Pisa":[("Semper","P",1),("Scuffet","P",22),("Canestrelli","D",5),("Calabresi","D",33),("Loyola","D",35),("Angori","D",3),("Marin","C",6),("Hojholt","C",8),("Aebischer","C",20),("Stengs","C",23),("Cuadrado","C",11),("Meister","A",9),("Tramoni","A",10),("Iling-Junior","A",19),("Moreo","A",32)],
    "Como":[("Butez","P",1),("Tornqvist","P",21),("Diego Carlos","D",34),("Kempf","D",2),("Goldaniga","D",5),("Valle","D",3),("Moreno","D",18),("Van der Brempt","D",77),("Vojvoda","D",31),("Perrone","C",23),("Da Cunha","C",33),("Caqueret","C",6),("Sergi Roberto","C",8),("Paz","C",10),("Baturina","C",20),("Diao","A",38),("Kuhn","A",19),("Douvikas","A",11),("Morata","A",7)],
}

@app.get("/api/squadra/{nome}")
async def squadra(nome: str):
    n = nome.strip().title()
    return {
        "nome": n,
        "allenatore": ALLENATORI.get(n, "N/D"),
        "formazione": FORMAZIONI.get(n),
        "infortunati": INFORTUNATI.get(n, []),
        "rosa": [{"nome":g[0],"ruolo":g[1],"numero":g[2]} for g in ROSE.get(n, [])],
    }

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