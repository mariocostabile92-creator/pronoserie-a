
## Confronto approcci

Ho analizzato 3 piani alternativi. La mia sintesi finale adotta:

| Aspetto | Scelta | Motivo |
|---|---|---|
| H2H | Integrato in `get_team_stats()` con parametro `opponent=None` (Plan 3) | Pulito, retrocompatibile, dati accessibili ovunque |
| Quote | Tutte le colonne disponibili (Plan 3) | Più robusto: media su più bookmaker |
| Forma pesata | Decay esponenziale alpha=0.10, n=15, separata casa/trasferta (Plan 1) | Più preciso di una forma unica |
| Dixon-Coles | rho=-0.13 come costante, clamp min 0 (Plan 2+3) | Standard letteratura, sicuro |
| Blending modello+bookmaker | No blending, solo confronto visivo (Plan 2+3) | Più trasparente per l'utente |
| Confidence | 4 componenti pesate, colore incluso (Plan 3) | Output più pratico per UI |
| H2H in league.py | Solo pronostici singoli, non stagione completa (Plan 2) | Evita rallentamenti |

---

## Step di implementazione

### Step 0 — `data_loader.py` — Parsing numerico quote
- Dopo la riga 78 (conversione FTHG/FTAG), aggiungere conversione `to_numeric` per **tutte** le colonne quote: `WHH, WHD, WHA, GBH, GBD, GBA, IWH, IWD, IWA, LBH, LBD, LBA, SBH, SBD, SBA`
- Aggiungere ordinamento `pd.to_datetime(Date)` + `sort_values("Date")` per garantire ordine temporale

### Step 1 — `stats_engine.py` — Nuova funzione `get_h2h_stats(df, home, away)`
- Filtra partite dove `(HomeTeam==home AND AwayTeam==away) OR (HomeTeam==away AND AwayTeam==home)`
- Calcola: `n_partite, vittorie_home, pareggi, vittorie_away, media_gol_home, media_gol_away`
- Calcola `h2h_advantage = (vittorie_home - vittorie_away) / n` in [-1, 1]
- Se < 3 scontri diretti: ritorna `None`
- Include `ultimi_5_h2h` con punteggi (es. "Juve 2-1 Inter")

### Step 2 — `stats_engine.py` — Nuova funzione `get_weighted_form(df, team, n=15)`
- Ordina partite per data (recenti prima)
- Pesi: `w_i = exp(-0.10 * i)` dove i=0 e' la piu' recente
- Calcola media punti pesata: V=3, P=1, S=0
- Risultato normalizzato in [0, 3]
- Include `forma_casa_pesata` e `forma_trasf_pesata` separati

### Step 3 — `stats_engine.py` — Estensione `get_team_stats(df, team, opponent=None)`
- Aggiungere parametro opzionale `opponent=None`
- Chiamare `get_weighted_form()` e aggiungere: `forma_pesata`, `forma_casa_pesata`, `forma_trasf_pesata`
- Se `opponent` specificato: chiamare `get_h2h_stats()` e aggiungere chiave `"h2h"` al dizionario (o `None`)
- Mantenere `forma_recente` (ultimi 5) per retrocompatibilita'

### Step 4 — `predictor.py` — Costanti e Dixon-Coles
- Aggiungere costanti modulo: `ALPHA_H2H = 0.08`, `ALPHA_FORMA = 0.06`, `DIXON_COLES_RHO = -0.13`, `MARGINE_BK = 1.05`
- Nuova funzione `_dixon_coles_tau(i, j, lambda_h, lambda_a, rho)`
- Aggiornare `calcola_probabilita()` per applicare tau alla matrice Poisson
- Clamp `max(0, p * tau)` per evitare probabilita' negative
- Normalizzare dopo la correzione

### Step 5 — `predictor.py` — Integrazione H2H e Forma nei lambda
- In `get_prediction()`, dopo il calcolo base di lambda:
  - Se H2H disponibile: `lambda_home *= (1.0 + ALPHA_H2H * h2h_advantage)`
  - Forma: `forma_factor = 1.0 + ALPHA_FORMA * (forma_pesata_home - forma_pesata_away)`, applicare a entrambi i lambda
- Clamp finale [0.3, 5.0] invariato

### Step 6 — `predictor.py` — Confronto bookmaker
- Nuova funzione `_get_bookmaker_reference(df, home, away)`
- Cerca ultima partita H2H con quote disponibili
- Usa media di TUTTE le quote presenti (WH, GB, IW, LB, SB)
- Converte in prob. implicite normalizzate (rimuovendo overround)
- Ritorna `None` se nessuna quota disponibile

### Step 7 — `predictor.py` — Indice confidence
- Nuova funzione `_calcola_confidence(probs, n_home, n_away, h2h, bk_probs)`
- 4 componenti pesate:
  - Separazione probabilita' (40%): distanza tra prob max e seconda
  - Volume dati (25%): min(n_partite, 200) / 200
  - H2H (20%): n_h2h / 15 se disponibile, 0.3 altrimenti
  - Convergenza forma (15%): vicinanza forme delle due squadre alla previsione
- Output: `confidence` [0,1], `confidence_label` ("Alta"/"Media"/"Bassa"), `confidence_color`

### Step 8 — `predictor.py` — Aggiornamento firma `get_prediction()`
- Nuovo parametro: `df=None`
- Aggiungere al dizionario di ritorno: `confidence`, `confidence_label`, `confidence_color`, `h2h_n`, `h2h_applied`, `delta_bk_1/x/2`, `book_prob_1/x/2`
- Retrocompatibile: senza `df` funziona come prima (senza H2H/bookmaker)

### Step 9 — `simulator.py` — Fattori H2H e forma
- In `simulate_match()`, dopo calcolo lambda base:
  - Se `"h2h"` in home_stats e non None: applicare `ALPHA_H2H * h2h_advantage`
  - Se `"forma_pesata"` in home_stats: applicare fattore forma
- Guard con `.get()` per retrocompatibilita'

### Step 10 — `main.py` — Aggiornamento chiamate
- `_esegui_simulazione()` e `_esegui_pronostico()`: passare `opponent=` a `get_team_stats()` e `df=` a `get_prediction()`
- NON modificare le chiamate in `league.py` per non rallentare la simulazione stagionale

### Step 11 — `main.py` — Nuove sezioni UI tab Pronostici
- Dopo i box 1X2 e suggerimento, aggiungere:

**Sezione Affidabilita'**: `CTkProgressBar` colorata (verde/giallo/rosso) + percentuale + label

**Sezione H2H**: box con `V Casa: N | Pareggi: N | V Ospite: N` + ultimi 5 risultati diretti; label grigia se < 3 scontri

**Sezione Confronto Mercato**: tabella 3 colonne (1, X, 2) con riga Modello, riga Mercato, riga Delta; nascosta se quote non disponibili

- Aumentare `minsize` a `(950, 750)`

---

## Verifica / DoD

| Step | File | Verifica |
|---|---|---|
| 0 | `data_loader.py` | Quote WHH parsate come float, Date ordinate |
| 1-3 | `stats_engine.py` | `get_team_stats(df, "Inter", opponent="Milan")` ritorna H2H + forma pesata |
| 4-8 | `predictor.py` | Prob 1X2 con Dixon-Coles sommano ~100%, confidence presente |
| 9 | `simulator.py` | `simulate_match()` funziona con e senza H2H |
| 10-11 | `main.py` | Tab Pronostici mostra affidabilita', H2H, confronto mercato |
| Tutti | Sintassi | `ast.parse()` su tutti i file |
| Tutti | App | `python main.py` si avvia senza errori |
