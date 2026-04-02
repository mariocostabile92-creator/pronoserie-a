"""
train_ml_model.py
Allena un modello XGBoost sui 26 anni di dati Serie A.
Features: forza att/dif, xG, H2H, forma pesata, classifica, marcatori, infortunati.
Target: 1X2, Over/Under, Goal/NoGoal.
Esporta il modello e le statistiche pre-calcolate per la web app.
"""

import sys, os, json, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
import pandas as pd
from xgboost import XGBClassifier
import joblib

from data_loader import load_all_data
from stats_engine import get_team_stats, get_league_averages, get_h2h_stats, get_weighted_form
from season_2526 import SQUADRE_2526, XG_2526, CLASSIFICA_REALE_30G

print("=" * 60)
print("TRAINING MODELLO ML — PRONOSTICI SERIE A")
print("=" * 60)

# 1. Carica dati
print("\n1. Caricamento dati CSV...")
df = load_all_data()
print(f"   Partite totali: {len(df)}")

# 2. Calcola features per ogni partita
print("\n2. Feature engineering...")

features_list = []
labels_1x2 = []
labels_ou = []
labels_goal = []

medie = get_league_averages(df)

for idx, row in df.iterrows():
    if idx % 500 == 0:
        print(f"   Processate {idx}/{len(df)} partite...")
    
    home = row["HomeTeam"]
    away = row["AwayTeam"]
    gol_h = int(row["FTHG"])
    gol_a = int(row["FTAG"])
    ftr = row["FTR"]
    
    try:
        # Filtra solo partite PRIMA di questa per evitare data leakage
        df_before = df.loc[:idx-1] if idx > 50 else df.loc[:idx]
        if len(df_before) < 50:
            continue
        
        # Statistiche squadre (su dati precedenti)
        casa = df_before[df_before["HomeTeam"] == home]
        trasf = df_before[df_before["AwayTeam"] == away]
        
        if len(casa) < 3 or len(trasf) < 3:
            continue
        
        # Feature base
        mgf_casa = casa["FTHG"].mean()
        mgs_casa = casa["FTAG"].mean()
        mgf_trasf = trasf["FTAG"].mean()
        mgs_trasf = trasf["FTHG"].mean()
        
        media_gol_casa = df_before["FTHG"].mean()
        media_gol_trasf = df_before["FTAG"].mean()
        
        if media_gol_casa == 0 or media_gol_trasf == 0:
            continue
        
        forza_att_h = mgf_casa / media_gol_casa
        forza_dif_h = mgs_casa / media_gol_trasf
        forza_att_a = mgf_trasf / media_gol_trasf
        forza_dif_a = mgs_trasf / media_gol_casa
        
        # Lambda Poisson
        lambda_h = forza_att_h * forza_dif_a * media_gol_casa
        lambda_a = forza_att_a * forza_dif_h * media_gol_trasf
        
        # H2H
        h2h_mask = ((df_before["HomeTeam"]==home)&(df_before["AwayTeam"]==away))|((df_before["HomeTeam"]==away)&(df_before["AwayTeam"]==home))
        h2h = df_before[h2h_mask]
        h2h_n = len(h2h)
        h2h_adv = 0
        if h2h_n >= 3:
            h_wins = len(h2h[((h2h["HomeTeam"]==home)&(h2h["FTR"]=="H"))|((h2h["AwayTeam"]==home)&(h2h["FTR"]=="A"))])
            a_wins = len(h2h[((h2h["HomeTeam"]==away)&(h2h["FTR"]=="H"))|((h2h["AwayTeam"]==away)&(h2h["FTR"]=="A"))])
            h2h_adv = (h_wins - a_wins) / h2h_n
        
        # Forma recente (ultimi 5)
        home_recent = df_before[(df_before["HomeTeam"]==home)|(df_before["AwayTeam"]==home)].tail(5)
        away_recent = df_before[(df_before["HomeTeam"]==away)|(df_before["AwayTeam"]==away)].tail(5)
        
        def calc_form(matches, team):
            pts = 0
            for _, m in matches.iterrows():
                if m["HomeTeam"] == team:
                    pts += 3 if m["FTR"]=="H" else (1 if m["FTR"]=="D" else 0)
                else:
                    pts += 3 if m["FTR"]=="A" else (1 if m["FTR"]=="D" else 0)
            return pts / max(len(matches), 1)
        
        form_h = calc_form(home_recent, home)
        form_a = calc_form(away_recent, away)
        
        # Percentuali vittorie
        home_all = df_before[(df_before["HomeTeam"]==home)|(df_before["AwayTeam"]==home)]
        away_all = df_before[(df_before["HomeTeam"]==away)|(df_before["AwayTeam"]==away)]
        
        h_wins_pct = (len(casa[casa["FTR"]=="H"]) + len(df_before[(df_before["AwayTeam"]==home)&(df_before["FTR"]=="A")])) / max(len(home_all), 1)
        a_wins_pct = (len(trasf[trasf["FTR"]=="A"]) + len(df_before[(df_before["HomeTeam"]==away)&(df_before["FTR"]=="H")])) / max(len(away_all), 1)
        
        # Feature vector
        feat = [
            forza_att_h, forza_dif_h, forza_att_a, forza_dif_a,
            lambda_h, lambda_a,
            lambda_h - lambda_a,  # diff lambda
            mgf_casa, mgs_casa, mgf_trasf, mgs_trasf,
            h2h_adv, h2h_n,
            form_h, form_a, form_h - form_a,
            h_wins_pct, a_wins_pct,
            len(casa), len(trasf),  # n partite
        ]
        
        features_list.append(feat)
        
        # Labels
        labels_1x2.append(0 if ftr=="H" else (1 if ftr=="D" else 2))  # 0=Casa, 1=Pareggio, 2=Ospite
        labels_ou.append(1 if gol_h + gol_a > 2.5 else 0)  # 1=Over, 0=Under
        labels_goal.append(1 if gol_h >= 1 and gol_a >= 1 else 0)  # 1=Goal, 0=NoGoal
        
    except Exception:
        continue

X = np.array(features_list)
y_1x2 = np.array(labels_1x2)
y_ou = np.array(labels_ou)
y_goal = np.array(labels_goal)

print(f"   Partite con features valide: {len(X)}")
print(f"   Distribuzione 1X2: Casa={sum(y_1x2==0)}, Pareggio={sum(y_1x2==1)}, Ospite={sum(y_1x2==2)}")

# 3. Training
print("\n3. Training XGBoost...")

# Modello 1X2
model_1x2 = XGBClassifier(
    n_estimators=300, max_depth=5, learning_rate=0.08,
    subsample=0.8, colsample_bytree=0.8,
    eval_metric="mlogloss", random_state=42
)
model_1x2.fit(X, y_1x2)

# Modello Over/Under
model_ou = XGBClassifier(
    n_estimators=200, max_depth=4, learning_rate=0.1,
    eval_metric="logloss", random_state=42
)
model_ou.fit(X, y_ou)

# Modello Goal/NoGoal
model_goal = XGBClassifier(
    n_estimators=200, max_depth=4, learning_rate=0.1,
    eval_metric="logloss", random_state=42
)
model_goal.fit(X, y_goal)

# 4. Valutazione
print("\n4. Valutazione accuratezza...")
from sklearn.model_selection import cross_val_score

# Cross-validation su tutto il dataset
cv_1x2 = cross_val_score(model_1x2, X, y_1x2, cv=5, scoring="accuracy")
cv_ou = cross_val_score(model_ou, X, y_ou, cv=5, scoring="accuracy")
cv_goal = cross_val_score(model_goal, X, y_goal, cv=5, scoring="accuracy")

print(f"   1X2:       {cv_1x2.mean()*100:.1f}% (+/- {cv_1x2.std()*100:.1f}%)")
print(f"   Over/Under: {cv_ou.mean()*100:.1f}% (+/- {cv_ou.std()*100:.1f}%)")
print(f"   Goal/NoGoal: {cv_goal.mean()*100:.1f}% (+/- {cv_goal.std()*100:.1f}%)")

score_tot = cv_1x2.mean()*0.4 + cv_ou.mean()*0.3 + cv_goal.mean()*0.3
print(f"\n   SCORE COMPLESSIVO: {score_tot*100:.1f}%")

# 5. Calcola statistiche per ogni squadra (per la web app)
print("\n5. Calcolo statistiche per web app...")
stats_export = {}
for sq in SQUADRE_2526:
    try:
        s = get_team_stats(df, sq)
        xg = XG_2526.get(sq, {})
        stats_export[sq] = {
            "forza_att_casa": round(s["forza_att_casa"], 4),
            "forza_dif_casa": round(s["forza_dif_casa"], 4),
            "forza_att_trasf": round(s["forza_att_trasf"], 4),
            "forza_dif_trasf": round(s["forza_dif_trasf"], 4),
            "mgf_casa": round(s["mgf_casa"], 3),
            "mgs_casa": round(s["mgs_casa"], 3),
            "mgf_trasf": round(s["mgf_trasf"], 3),
            "mgs_trasf": round(s["mgs_trasf"], 3),
            "forma_pesata": round(s.get("forma_pesata", 1.5), 3),
            "forma_casa_pesata": round(s.get("forma_casa_pesata", 1.5), 3),
            "forma_trasf_pesata": round(s.get("forma_trasf_pesata", 1.5), 3),
            "perc_vittorie": round(s["perc_vittorie"], 1),
            "n_partite": s["n_partite"],
            "xG_pg": xg.get("xG_pg", 1.3),
            "xGA_pg": xg.get("xGA_pg", 1.3),
        }
    except Exception as e:
        print(f"   Errore {sq}: {e}")

# 6. Salva modelli e statistiche
print("\n6. Salvataggio modelli...")
output_dir = os.path.join(os.path.dirname(__file__), "webapp", "backend")

joblib.dump(model_1x2, os.path.join(output_dir, "model_1x2.joblib"))
joblib.dump(model_ou, os.path.join(output_dir, "model_ou.joblib"))
joblib.dump(model_goal, os.path.join(output_dir, "model_goal.joblib"))

with open(os.path.join(output_dir, "team_stats.json"), "w") as f:
    json.dump(stats_export, f, indent=2)

# Salva medie campionato
with open(os.path.join(output_dir, "league_averages.json"), "w") as f:
    json.dump({
        "media_gol_casa": round(medie["media_gol_casa"], 4),
        "media_gol_trasferta": round(medie["media_gol_trasferta"], 4),
    }, f)

# H2H pre-calcolati per le squadre 2025-26
print("   Calcolo H2H...")
h2h_export = {}
for h in SQUADRE_2526:
    for a in SQUADRE_2526:
        if h != a:
            h2h = get_h2h_stats(df, h, a)
            if h2h:
                h2h_export[f"{h}_vs_{a}"] = {
                    "h2h_advantage": h2h["h2h_advantage"],
                    "n_partite": h2h["n_partite"],
                }

with open(os.path.join(output_dir, "h2h_stats.json"), "w") as f:
    json.dump(h2h_export, f, indent=2)

print(f"\n   Modelli salvati in: {output_dir}")
print(f"   - model_1x2.joblib ({os.path.getsize(os.path.join(output_dir, 'model_1x2.joblib'))//1024} KB)")
print(f"   - model_ou.joblib")
print(f"   - model_goal.joblib")
print(f"   - team_stats.json ({len(stats_export)} squadre)")
print(f"   - h2h_stats.json ({len(h2h_export)} coppie)")
print(f"   - league_averages.json")

print("\n" + "=" * 60)
print(f"TRAINING COMPLETATO!")
print(f"Accuratezza 1X2: {cv_1x2.mean()*100:.1f}%")
print(f"Accuratezza O/U: {cv_ou.mean()*100:.1f}%")
print(f"Accuratezza Goal: {cv_goal.mean()*100:.1f}%")
print(f"SCORE TOTALE: {score_tot*100:.1f}%")
print("=" * 60)
