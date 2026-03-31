"""Ottimizzazione rapida pesi."""
import sys, os, warnings
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
warnings.filterwarnings("ignore")

from data_loader import load_all_data
from stats_engine import get_team_stats
from season_2526 import SQUADRE_2526, get_risultati_stagione, get_xg, get_xg_media_campionato
from predictor import calcola_probabilita, calcola_mercati_extra
from live_data import get_impatto_infortunati

df = load_all_data()
gs = get_risultati_stagione(df)
print(f"Partite: {sum(len(g['risultati']) for g in gs)}")

best_s = 0
best_p = {}

for ah in [0.04, 0.08, 0.12, 0.18, 0.25]:
    for af in [0.03, 0.06, 0.10, 0.15, 0.20]:
        for ax in [0.15, 0.25, 0.35, 0.45, 0.55]:
            for rh in [-0.08, -0.13, -0.18]:
                ok1 = oku = okg = tot = 0
                for g in gs:
                    for r in g["risultati"]:
                        h, a = r["home"], r["away"]
                        if h not in SQUADRE_2526 or a not in SQUADRE_2526:
                            continue
                        try:
                            hs = get_team_stats(df, h, opponent=a)
                            aa = get_team_stats(df, a, opponent=h)
                            lh = hs["forza_att_casa"] * aa["forza_dif_trasf"] * hs["media_gol_casa_campionato"]
                            la = aa["forza_att_trasf"] * hs["forza_dif_casa"] * hs["media_gol_trasf_campionato"]
                            xh, xa = get_xg(h), get_xg(a)
                            if xh and xa:
                                mm = get_xg_media_campionato()
                                lh = (1 - ax) * lh + ax * (xh["xG_pg"] * (xa["xGA_pg"] / mm["xGA_pg_medio"]))
                                la = (1 - ax) * la + ax * (xa["xG_pg"] * (xh["xGA_pg"] / mm["xGA_pg_medio"]))
                            hh = hs.get("h2h")
                            if hh:
                                lh *= (1 + ah * hh["h2h_advantage"])
                                la *= (1 - ah * hh["h2h_advantage"])
                            fd = hs.get("forma_casa_pesata", 1.5) - aa.get("forma_trasf_pesata", 1.5)
                            ff = 1 + af * fd
                            lh *= ff
                            la *= (2 - ff)
                            lh *= get_impatto_infortunati(h)
                            la *= get_impatto_infortunati(a)
                            lh = max(0.3, min(lh, 5))
                            la = max(0.3, min(la, 5))
                            p = calcola_probabilita(lh, la, rh)
                            e = calcola_mercati_extra(lh, la, rh)
                            mp = max(p["prob_1"], p["prob_x"], p["prob_2"])
                            s = "1" if mp == p["prob_1"] else ("X" if mp == p["prob_x"] else "2")
                            tot += 1
                            m = {"H": "1", "D": "X", "A": "2"}
                            if s == m.get(r["risultato"], "?"):
                                ok1 += 1
                            gt = r["gol_home"] + r["gol_away"]
                            if (gt > 2.5) == (e["over_25"] > 50):
                                oku += 1
                            ig = r["gol_home"] >= 1 and r["gol_away"] >= 1
                            if ig == (e["goal_si"] > 50):
                                okg += 1
                        except Exception:
                            pass
                if tot > 0:
                    sc = ok1 / tot * 100 * 0.4 + oku / tot * 100 * 0.3 + okg / tot * 100 * 0.3
                    if sc > best_s:
                        best_s = sc
                        best_p = {"h2h": ah, "forma": af, "xg": ax, "rho": rh,
                                  "1x2": ok1 / tot * 100, "ou": oku / tot * 100, "goal": okg / tot * 100}
                        print(f"NEW BEST {sc:.1f}%: H2H={ah} F={af} xG={ax} rho={rh} | 1X2={ok1/tot*100:.1f}% OU={oku/tot*100:.1f}% G={okg/tot*100:.1f}%")

print(f"\nFINAL: Score={best_s:.1f}%")
print(f"  ALPHA_H2H={best_p['h2h']}, ALPHA_FORMA={best_p['forma']}, ALPHA_XG={best_p['xg']}, RHO={best_p['rho']}")
print(f"  1X2={best_p['1x2']:.1f}%, O/U={best_p['ou']:.1f}%, Goal={best_p['goal']:.1f}%")
