"""
ml_ensemble.py
Ensemble GradientBoosting multi-lega: modello separato per ogni campionato.

DESIGN MULTI-LEGA:
- Per ogni lega viene allenato un modello indipendente (ml_model_<lega>.pkl)
- I dati storici vengono caricati dal CSV corretto per ogni lega
- Le feature includono xG, classifica reale e forma recente specifici per lega
- Se una lega ha meno di MIN_PARTITE_ML partite, usa il modello Serie A come fallback
- ml_model.pkl rimane aggiornato con il modello Serie A per compatibilita' backward

NOTA: predictor.py NON viene importato a livello di modulo per evitare
import circolare (predictor importa gia' da questo modulo a runtime).
"""

import sys
import os
import warnings
import pickle

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
warnings.filterwarnings("ignore")

import numpy as np
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import cross_val_score

from data_loader import load_all_data
from stats_engine import get_team_stats
from season_2526 import (
    SQUADRE_2526,
    get_risultati_stagione,
    get_xg,            get_xg_media_campionato,
    get_xg_pl,         get_xg_media_pl,
    get_xg_laliga,     get_xg_media_laliga,
    get_xg_bl,         get_xg_media_bl,
    get_xg_l1,         get_xg_media_l1,
    get_pts_per_squadra,
    get_forma_recente,
    get_team_ou_tendency,
)
from live_data import get_impatto_infortunati

# ─────────────────────────────────────────────────────────────────────────────
# Percorsi modelli
# ─────────────────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Modello generico (Serie A) - mantenuto per compatibilita' backward
MODEL_PATH = os.path.join(BASE_DIR, "ml_model.pkl")

# Numero minimo di partite per allenare un modello specifico
MIN_PARTITE_ML = 50

# Mapping lega -> funzioni xG (attacco, media campionato)
_LEGA_XG_FUNCS = {
    'serie-a':        (get_xg,       get_xg_media_campionato),
    'premier-league': (get_xg_pl,    get_xg_media_pl),
    'la-liga':        (get_xg_laliga, get_xg_media_laliga),
    'bundesliga':     (get_xg_bl,    get_xg_media_bl),
    'ligue-1':        (get_xg_l1,    get_xg_media_l1),
}

# Nomi feature (per leggibilita' del feature importance log)
FEATURE_NAMES = [
    "P1", "PX", "P2",                           # Prob Poisson
    "LamH", "LamA", "LamDiff",                  # Lambda Dixon-Coles
    "xGH", "xGA_avg", "xGAH", "xGAA", "xGDiff",# xG stagione corrente (per lega)
    "FAttC", "FDifC", "FAttT", "FDifT",         # Forza att/dif storica
    "FormaC", "FormaT", "FormaDiff",             # Forma pesata storica
    "PtsH", "PtsA", "PtsDiff",                  # Classifica reale (per lega)
    "FormaRecH", "FormaRecA", "FormaRecDiff",    # Forma recente ultime 5 (per lega)
    "H2Hadv", "H2Hn",                           # Head-to-Head
    "BK1", "BKX", "BK2",                        # Quote bookmaker
    "OUgolH", "OUgolA", "OUgolAvg",             # Tendenza O/U squadre
    "Conf", "GolAtt", "Ov25", "GoalSi",         # Indici extra
    "InjH", "InjA",                             # Infortunati
]


# ─────────────────────────────────────────────────────────────────────────────
# Utilita'
# ─────────────────────────────────────────────────────────────────────────────

def _get_model_path(league: str) -> str:
    """Percorso del file modello per la lega specificata."""
    return os.path.join(BASE_DIR, f"ml_model_{league}.pkl")


def _load_models(league: str) -> dict | None:
    """
    Carica i modelli per la lega specificata.
    Tenta prima il modello specifico per la lega, poi il fallback generico.
    Ritorna None se nessun modello e' disponibile.
    """
    # 1. Modello specifico per la lega
    path_lega = _get_model_path(league)
    if os.path.exists(path_lega):
        try:
            with open(path_lega, "rb") as f:
                return pickle.load(f)
        except Exception:
            pass

    # 2. Fallback: modello generico (Serie A)
    if os.path.exists(MODEL_PATH):
        try:
            with open(MODEL_PATH, "rb") as f:
                return pickle.load(f)
        except Exception:
            pass

    return None


def _build_features(pred: dict, hs: dict, aws: dict,
                    home: str, away: str,
                    bk: dict | None,
                    xg_home: dict | None, xg_away: dict | None,
                    pts_home: float, pts_away: float,
                    forma_rec_home: float, forma_rec_away: float) -> list:
    """
    Costruisce il vettore feature per una singola partita.

    Riceve tutti i dati pre-calcolati; non fa import da predictor per evitare
    dipendenze circolari.

    Parametri:
        pred:            output di get_prediction() (prob_1/x/2, lambda, ecc.)
        hs, aws:         statistiche squadra casa/ospite da get_team_stats()
        home, away:      nomi squadre
        bk:              dict quote bookmaker (o None)
        xg_home/away:    dict xG stagione corrente (o None)
        pts_home/away:   punti in classifica reale (specifici per lega)
        forma_rec_*:     forma recente ultime 5 (specifica per lega) [0..1]
    """
    ou_h = get_team_ou_tendency(home)
    ou_a = get_team_ou_tendency(away)

    # xG features (usa 1.3 come media neutra se non disponibili)
    xg_h_pg  = xg_home["xG_pg"]  if xg_home else 1.3
    xg_a_pg  = xg_away["xG_pg"]  if xg_away else 1.3
    xg_h_ga  = xg_home["xGA_pg"] if xg_home else 1.3
    xg_a_ga  = xg_away["xGA_pg"] if xg_away else 1.3

    features = [
        # Probabilita' Poisson + Dixon-Coles (gia' blendati con bookmaker)
        pred.get("prob_1", 33.3), pred.get("prob_x", 33.3), pred.get("prob_2", 33.3),
        # Lambda gol attesi
        pred.get("lambda_home", 1.3), pred.get("lambda_away", 1.1),
        pred.get("lambda_home", 1.3) - pred.get("lambda_away", 1.1),
        # xG stagione corrente (specifici per lega - segnale forte)
        xg_h_pg, xg_a_pg,
        xg_h_ga, xg_a_ga,
        xg_h_pg - xg_a_pg,
        # Forza att/dif storica (26 anni di dati CSV)
        hs.get("forza_att_casa", 1.0), hs.get("forza_dif_casa", 1.0),
        aws.get("forza_att_trasf", 1.0), aws.get("forza_dif_trasf", 1.0),
        # Forma pesata storica
        hs.get("forma_casa_pesata", 1.5),
        aws.get("forma_trasf_pesata", 1.5),
        hs.get("forma_casa_pesata", 1.5) - aws.get("forma_trasf_pesata", 1.5),
        # Classifica reale per lega (differenza punti come segnale di forza relativa)
        pts_home, pts_away, pts_home - pts_away,
        # Forma recente ultime 5 partite con decay (specifica per lega, range [0,1])
        forma_rec_home, forma_rec_away, forma_rec_home - forma_rec_away,
        # Head-to-Head storico
        hs["h2h"]["h2h_advantage"] if hs.get("h2h") else 0,
        hs["h2h"]["n_partite"]     if hs.get("h2h") else 0,
        # Quote bookmaker (segnale mercato molto informativo)
        bk["book_prob_1"] if bk else pred.get("prob_1", 33.3),
        bk["book_prob_x"] if bk else pred.get("prob_x", 33.3),
        bk["book_prob_2"] if bk else pred.get("prob_2", 33.3),
        # Tendenza Over/Under specifica per squadra
        ou_h.get("gol_pg", 2.5), ou_a.get("gol_pg", 2.5),
        (ou_h.get("gol_pg", 2.5) + ou_a.get("gol_pg", 2.5)) / 2,
        # Confidence e mercati extra
        pred.get("confidence", 0.5),
        pred.get("gol_attesi", 2.5),
        pred.get("over_25", 50.0),
        pred.get("goal_si", 50.0),
        # Infortunati (impatto sulla forza della squadra)
        pred.get("inj_home", 0), pred.get("inj_away", 0),
    ]
    return features


# ─────────────────────────────────────────────────────────────────────────────
# Training
# ─────────────────────────────────────────────────────────────────────────────

def train_model(league: str = "serie-a") -> tuple:
    """
    Allena i modelli GradientBoosting (1X2, O/U, Goal) per la lega specificata.

    - Carica i dati storici corretti tramite LEGA_CONFIG
    - Estrae feature con xG, classifica e forma reali per la lega
    - Esegue k=5 cross-validation e logga l'accuratezza
    - Salva in ml_model_<lega>.pkl
    - Se < MIN_PARTITE_ML partite: copia il modello Serie A come fallback

    Ritorna: (models_dict, cv_score)  oppure (None, 0.0) se fallback
    """
    # Import locali per evitare import circolare a livello di modulo
    from predictor import get_prediction, _get_bookmaker_reference
    from optimize_weights import LEGA_CONFIG, get_partite_stagione_corrente

    print(f"\n{'='*55}")
    print(f"  TRAINING ML ENSEMBLE: {league.upper()}")
    print(f"{'='*55}")

    cfg = LEGA_CONFIG.get(league)
    if cfg is None:
        print(f"  [!] Lega '{league}' non supportata in LEGA_CONFIG.")
        return None, 0.0

    fn_xg, _ = _LEGA_XG_FUNCS.get(league, _LEGA_XG_FUNCS["serie-a"])

    # Carica storico CSV per la lega
    print(f"  Caricamento dati storici ({cfg['csv_code']})...")
    df = load_all_data(cfg["csv_code"])

    # Lista partite stagione corrente per questa lega
    if league == "serie-a":
        # Per Serie A usa get_risultati_stagione() con filtro SQUADRE_2526
        gs = get_risultati_stagione(df)
        partite = []
        for g in gs:
            for r in g["risultati"]:
                if r["home"] in SQUADRE_2526 and r["away"] in SQUADRE_2526:
                    partite.append(r)
    else:
        partite = get_partite_stagione_corrente(df)

    print(f"  Partite stagione corrente disponibili: {len(partite)}")

    # Controlla soglia minima per training specifico
    if len(partite) < MIN_PARTITE_ML:
        print(f"  [!] Meno di {MIN_PARTITE_ML} partite per '{league}'. "
              f"Copio modello Serie A come fallback.")
        sa_path = _get_model_path("serie-a")
        dest_path = _get_model_path(league)
        if os.path.exists(sa_path):
            with open(sa_path, "rb") as f:
                models = pickle.load(f)
            with open(dest_path, "wb") as f:
                pickle.dump(models, f)
            print(f"  [OK] Fallback salvato: {os.path.basename(dest_path)}")
        return None, 0.0

    # Classifica reale per la lega (punti -> forza relativa)
    pts_dict  = get_pts_per_squadra(league)
    media_pts = (sum(pts_dict.values()) / len(pts_dict)) if pts_dict else 40.0

    X_1x2, y_1x2 = [], []
    X_ou,  y_ou   = [], []
    X_goal, y_goal = [], []

    print(f"  Estrazione feature per {len(partite)} partite...")
    errori = 0
    for r in partite:
        home = r.get("home") or r.get("HomeTeam", "")
        away = r.get("away") or r.get("AwayTeam", "")
        if not home or not away:
            continue

        try:
            hs  = get_team_stats(df, home, opponent=away)
            aws = get_team_stats(df, away, opponent=home)

            # Predizione Dixon-Coles completa per la lega
            pred = get_prediction(hs, aws, df=df, league=league)

            # xG stagione corrente specifici per la lega
            xg_h = fn_xg(home)
            xg_a = fn_xg(away)

            # Classifica e forma recente (specifiche per la lega)
            pts_h = pts_dict.get(home, media_pts)
            pts_a = pts_dict.get(away, media_pts)
            forma_h = get_forma_recente(home, league)
            forma_a = get_forma_recente(away, league)

            # Quote bookmaker (segnale mercato)
            bk = _get_bookmaker_reference(df, home, away)

            feat = _build_features(
                pred, hs, aws, home, away,
                bk, xg_h, xg_a,
                pts_h, pts_a,
                forma_h, forma_a,
            )

            # Target 1X2 (H=0, D=1, A=2)
            ris = r.get("risultato") or r.get("FTR", "")
            m_target = {"H": 0, "D": 1, "A": 2}
            t = m_target.get(ris, -1)
            if t >= 0:
                X_1x2.append(feat)
                y_1x2.append(t)

            # Target O/U 2.5
            gh = int(r.get("gol_home") or r.get("FTHG", 0))
            ga = int(r.get("gol_away") or r.get("FTAG", 0))
            X_ou.append(feat)
            y_ou.append(1 if (gh + ga) > 2.5 else 0)

            # Target Goal/NoGoal
            X_goal.append(feat)
            y_goal.append(1 if (gh >= 1 and ga >= 1) else 0)

        except Exception:
            errori += 1
            continue

    if errori > 0:
        print(f"  [i] Partite saltate per errori: {errori}")

    X_1x2  = np.array(X_1x2)
    y_1x2  = np.array(y_1x2)
    X_ou   = np.array(X_ou)
    y_ou   = np.array(y_ou)
    X_goal = np.array(X_goal)
    y_goal = np.array(y_goal)

    print(f"  Partite con feature valide: {len(X_1x2)}")

    # Secondo controllo dopo l'estrazione (alcune partite potrebbero fallire)
    if len(X_1x2) < MIN_PARTITE_ML:
        print(f"  [!] Feature insufficienti ({len(X_1x2)} < {MIN_PARTITE_ML}). "
              f"Fallback su modello Serie A.")
        sa_path = _get_model_path("serie-a")
        dest_path = _get_model_path(league)
        if os.path.exists(sa_path) and league != "serie-a":
            with open(sa_path, "rb") as f:
                models = pickle.load(f)
            with open(dest_path, "wb") as f:
                pickle.dump(models, f)
        return None, 0.0

    # Numero fold CV: min(5, campioni/classe minima)
    n_cv = min(5, min(np.bincount(y_1x2)) if len(np.unique(y_1x2)) > 1 else 2)
    n_cv = max(n_cv, 2)

    # Parametri GBM (bilanciati per dataset multi-lega: 50-300 partite)
    gbm_params = dict(
        n_estimators=100, max_depth=3, learning_rate=0.1,
        min_samples_leaf=5, random_state=42, subsample=0.9,
    )

    print(f"\n  Allenamento 1X2  (k={n_cv} fold CV)...")
    model_1x2 = GradientBoostingClassifier(**gbm_params)
    cv_1x2 = cross_val_score(model_1x2, X_1x2, y_1x2, cv=n_cv, scoring="accuracy")
    print(f"    CV 1X2:  {cv_1x2.mean()*100:.1f}% (+/- {cv_1x2.std()*100:.1f}%)")
    model_1x2.fit(X_1x2, y_1x2)

    print(f"  Allenamento O/U  (k={n_cv} fold CV)...")
    model_ou = GradientBoostingClassifier(**gbm_params)
    cv_ou = cross_val_score(model_ou, X_ou, y_ou, cv=n_cv, scoring="accuracy")
    print(f"    CV O/U:  {cv_ou.mean()*100:.1f}% (+/- {cv_ou.std()*100:.1f}%)")
    model_ou.fit(X_ou, y_ou)

    print(f"  Allenamento Goal (k={n_cv} fold CV)...")
    model_goal = GradientBoostingClassifier(**gbm_params)
    cv_goal = cross_val_score(model_goal, X_goal, y_goal, cv=n_cv, scoring="accuracy")
    print(f"    CV Goal: {cv_goal.mean()*100:.1f}% (+/- {cv_goal.std()*100:.1f}%)")
    model_goal.fit(X_goal, y_goal)

    # Score complessivo pesato (stesso schema del backtesting)
    score_cv = (cv_1x2.mean() * 0.4 + cv_ou.mean() * 0.3 + cv_goal.mean() * 0.3) * 100
    print(f"\n  SCORE CV COMPLESSIVO ({league}): {score_cv:.1f}%")

    # Salva modello specifico per lega
    models = {
        "1x2":      model_1x2,
        "ou":       model_ou,
        "goal":     model_goal,
        "league":   league,
        "cv_score": round(score_cv, 2),
        "n_partite": len(X_1x2),
    }

    model_path = _get_model_path(league)
    with open(model_path, "wb") as f:
        pickle.dump(models, f)
    print(f"  [OK] Modello salvato: {os.path.basename(model_path)}")

    # Aggiorna ml_model.pkl (backward compat) se stiamo allenando Serie A
    if league == "serie-a":
        with open(MODEL_PATH, "wb") as f:
            pickle.dump(models, f)
        print(f"  [OK] Backward compat: ml_model.pkl aggiornato.")

    # Log feature importance top 10
    print(f"\n  Top 10 feature importance (1X2 - {league}):")
    imp  = model_1x2.feature_importances_
    top  = sorted(zip(FEATURE_NAMES, imp), key=lambda x: -x[1])[:10]
    for name, val in top:
        print(f"    {name:<16} {val:.3f}")

    return models, score_cv


def train_all_leagues() -> dict:
    """
    Allena modelli ML per tutte e 5 le leghe supportate.
    Serie A viene allenata per prima (usata come fallback per le altre).
    Ritorna un dict {league_id: cv_score}.
    """
    LEGHE = ["serie-a", "premier-league", "la-liga", "bundesliga", "ligue-1"]
    risultati = {}

    for lega in LEGHE:
        try:
            _, score = train_model(lega)
            risultati[lega] = score
        except Exception as e:
            print(f"  [ERRORE] {lega}: {e}")
            risultati[lega] = None

    return risultati


# ─────────────────────────────────────────────────────────────────────────────
# Inferenza (chiamata da predictor.py a runtime)
# ─────────────────────────────────────────────────────────────────────────────

def predict_ml(home: str, away: str,
               pred: dict, hs: dict, aws: dict,
               df, league: str = "serie-a",
               bk: dict | None = None) -> dict | None:
    """
    Genera predizioni ML per una partita usando il modello specifico per la lega.

    Parametri:
        home, away:  nomi squadre
        pred:        output di get_prediction() (prob_1/x/2, lambda, confidence, ecc.)
                     deve essere calcolato PRIMA di chiamare questa funzione
        hs, aws:     statistiche squadra casa/ospite da get_team_stats()
        df:          dataframe storico
        league:      id lega (es. 'serie-a', 'premier-league', ...)
        bk:          dict quote bookmaker (pre-calcolato, opzionale)

    Ritorna:
        dict con ml_prob_1/x/2, ml_over_25, ml_goal_si
        None se il modello non e' disponibile o c'e' un errore
    """
    models = _load_models(league)
    if models is None:
        return None

    try:
        fn_xg = _LEGA_XG_FUNCS.get(league, _LEGA_XG_FUNCS["serie-a"])[0]
        xg_h = fn_xg(home)
        xg_a = fn_xg(away)

        pts_dict  = get_pts_per_squadra(league)
        media_pts = (sum(pts_dict.values()) / len(pts_dict)) if pts_dict else 40.0
        pts_h = pts_dict.get(home, media_pts)
        pts_a = pts_dict.get(away, media_pts)

        forma_h = get_forma_recente(home, league)
        forma_a = get_forma_recente(away, league)

        # Calcola bk solo se non passato esternamente (evita doppio calcolo)
        if bk is None and df is not None:
            try:
                from predictor import _get_bookmaker_reference
                bk = _get_bookmaker_reference(df, home, away)
            except Exception:
                bk = None

        feat = _build_features(
            pred, hs, aws, home, away,
            bk, xg_h, xg_a,
            pts_h, pts_a,
            forma_h, forma_a,
        )

        X = np.array([feat])

        # Predizione 1X2
        proba_1x2   = models["1x2"].predict_proba(X)[0]
        classes_1x2 = models["1x2"].classes_
        prob_map = {int(c): float(p) for c, p in zip(classes_1x2, proba_1x2)}
        ml_prob_1 = prob_map.get(0, 0.333) * 100  # 0=Home
        ml_prob_x = prob_map.get(1, 0.333) * 100  # 1=Draw
        ml_prob_2 = prob_map.get(2, 0.334) * 100  # 2=Away

        # Predizione O/U 2.5
        ou_proba   = models["ou"].predict_proba(X)[0]
        ou_classes = models["ou"].classes_
        ou_map = {int(c): float(p) for c, p in zip(ou_classes, ou_proba)}
        ml_over_25 = ou_map.get(1, 0.5) * 100  # 1=Over

        # Predizione Goal/NoGoal
        goal_proba   = models["goal"].predict_proba(X)[0]
        goal_classes = models["goal"].classes_
        goal_map = {int(c): float(p) for c, p in zip(goal_classes, goal_proba)}
        ml_goal_si = goal_map.get(1, 0.5) * 100  # 1=GoalSi

        # Lega effettivamente usata (potrebbe essere il fallback Serie A)
        lega_usata = models.get("league", league)

        return {
            "ml_prob_1":    round(ml_prob_1, 1),
            "ml_prob_x":    round(ml_prob_x, 1),
            "ml_prob_2":    round(ml_prob_2, 1),
            "ml_over_25":   round(ml_over_25, 1),
            "ml_goal_si":   round(ml_goal_si, 1),
            "ml_league":    lega_usata,
            "ml_cv_score":  models.get("cv_score"),
            "ml_n_partite": models.get("n_partite"),
        }

    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Entry point standalone
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Training ML ensemble multi-lega"
    )
    parser.add_argument(
        "--lega", type=str, default="serie-a",
        choices=["serie-a", "premier-league", "la-liga",
                 "bundesliga", "ligue-1", "tutte"],
        help="Lega da allenare (default: serie-a; 'tutte' per tutte le leghe)"
    )
    args = parser.parse_args()

    if args.lega == "tutte":
        print("Alleno modelli ML per tutte le leghe...\n")
        risultati = train_all_leagues()
        print(f"\n{'='*55}")
        print("RIEPILOGO TRAINING ML MULTI-LEGA")
        print(f"{'='*55}")
        for lg, sc in risultati.items():
            if sc:
                print(f"  {lg:<20}  score CV: {sc:.1f}%")
            else:
                print(f"  {lg:<20}  fallback Serie A")
    else:
        models, score = train_model(args.lega)
        if models:
            print(f"\n[OK] Training completato. Score CV: {score:.1f}%")
        else:
            print(f"\n[i] Usato fallback Serie A per {args.lega}.")
