"""
main.py
Simulatore Pronostici Calcio - Serie A
Interfaccia grafica con CustomTkinter
"""

import customtkinter as ctk
from tkinter import messagebox
import tkinter as tk
import threading
import pandas as pd

from data_loader import load_all_data, get_teams
from stats_engine import get_team_stats
from simulator import simulate_match
from predictor import get_prediction
from league import simulate_season, simulate_remaining_season
from history_db import save_simulation, get_history, clear_history
from season_2526 import (get_classifica_reale, SQUADRE_2526, GIORNATA_ATTUALE,
                         GIORNATE_TOTALI, get_calendario_rimanente, get_risultati_stagione)
from squads_2526 import get_marcatori, get_rosa, get_allenatore, get_giocatori_per_ruolo
from auto_update import esegui_aggiornamento, get_ultimo_aggiornamento
from live_data import (get_infortunati, get_formazione, get_n_indisponibili,
                       avvia_aggiornamento_background)
from pitch_view import create_pitch_widget
from player_photos import get_player_photo_tk

# Tema scuro moderno
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ─────────────────────────────────────────────
# Colori
# ─────────────────────────────────────────────
COL_BG = "#1a1a2e"
COL_CARD = "#16213e"
COL_ACCENT = "#0f3460"
COL_VERDE = "#2ecc71"
COL_GIALLO = "#f39c12"
COL_ROSSO = "#e74c3c"
COL_BLU = "#3498db"
COL_TESTO = "#ecf0f1"
COL_GRIGIO = "#7f8c8d"

FONT_TITOLO = ("Segoe UI", 22, "bold")
FONT_GRANDE = ("Segoe UI", 18, "bold")
FONT_MEDIO = ("Segoe UI", 14)
FONT_PICCOLO = ("Segoe UI", 12)
FONT_BOLD = ("Segoe UI", 13, "bold")


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Simulatore Calcio - Serie A")
        self.geometry("950x750")
        self.minsize(950, 750)
        self.configure(fg_color=COL_BG)

        # Dati globali
        self.df = None
        self.squadre = []
        self.ultimo_sim = None
        self.ultimo_pred = None
        self.home_sel = None
        self.away_sel = None

        # Costruisce UI
        self._build_header()
        self._build_tabs()
        self._build_status_bar()

        # Carica dati in background
        self.after(300, self._carica_dati)

        # Avvia aggiornamento automatico dati live
        avvia_aggiornamento_background()

    # ─────────────────────────────────────────
    # Header
    # ─────────────────────────────────────────
    def _build_header(self):
        header = ctk.CTkFrame(self, fg_color=COL_ACCENT, height=60, corner_radius=0)
        header.pack(fill="x", side="top")

        ctk.CTkLabel(
            header,
            text="⚽  Simulatore Pronostici Calcio  ⚽",
            font=FONT_TITOLO,
            text_color=COL_TESTO
        ).pack(pady=12)

    # ─────────────────────────────────────────
    # Tab principale
    # ─────────────────────────────────────────
    def _build_tabs(self):
        self.tabs = ctk.CTkTabview(
            self,
            fg_color=COL_CARD,
            segmented_button_fg_color=COL_ACCENT,
            segmented_button_selected_color=COL_BLU,
            segmented_button_unselected_color=COL_ACCENT,
            text_color=COL_TESTO,
            corner_radius=10
        )
        self.tabs.pack(fill="both", expand=True, padx=12, pady=(8, 4))

        for nome in ["Pronostici", "Calendario", "Classifica", "Squadre"]:
            self.tabs.add(nome)

        self._build_tab_pronostici()
        self._build_tab_calendario()
        self._build_tab_classifica()
        self._build_tab_squadre()

    # ─────────────────────────────────────────
    # TAB 1 — Pronostici
    # ─────────────────────────────────────────
    def _build_tab_pronostici(self):
        tab = self.tabs.tab("Pronostici")
        tab.configure(fg_color="#0a0f1a")

        # Sfondo stadio con gradiente
        bg_frame = ctk.CTkFrame(tab, fg_color="#0d1b2a", corner_radius=0)
        bg_frame.pack(fill="both", expand=True)

        # Decorazione palloni laterali
        deco_top = ctk.CTkFrame(bg_frame, fg_color="#1b2838", height=4, corner_radius=0)
        deco_top.pack(fill="x")

        # Contenitore centrato
        center = ctk.CTkFrame(bg_frame, fg_color="transparent")
        center.pack(expand=True)

        # Titolo con emoji stadio
        ctk.CTkLabel(center, text="CALCOLA PRONOSTICO",
                     font=("Segoe UI", 24, "bold"), text_color=COL_TESTO).pack(pady=(20, 4))
        ctk.CTkLabel(center, text="Scegli le squadre e scopri il pronostico dell'IA",
                     font=("Segoe UI", 11), text_color=COL_GRIGIO).pack(pady=(0, 16))

        # Box selezione centrato
        sel_frame = ctk.CTkFrame(center, fg_color="#162447", corner_radius=16,
                                  border_color=COL_BLU, border_width=1)
        sel_frame.pack(padx=40, pady=4)

        # Riga squadre
        sq_row = ctk.CTkFrame(sel_frame, fg_color="transparent")
        sq_row.pack(pady=(16, 8))

        ctk.CTkLabel(sq_row, text="CASA", font=FONT_BOLD, text_color=COL_VERDE).pack(side="left", padx=(24, 8))
        self.combo_home_pred = ctk.CTkComboBox(sq_row, values=["Caricamento..."], width=200, font=FONT_MEDIO,
                                               fg_color=COL_BG, text_color=COL_TESTO, button_color=COL_BLU)
        self.combo_home_pred.pack(side="left", padx=4)

        ctk.CTkLabel(sq_row, text="  VS  ", font=("Segoe UI", 20, "bold"),
                     text_color=COL_GIALLO).pack(side="left", padx=8)

        self.combo_away_pred = ctk.CTkComboBox(sq_row, values=["Caricamento..."], width=200, font=FONT_MEDIO,
                                               fg_color=COL_BG, text_color=COL_TESTO, button_color=COL_BLU)
        self.combo_away_pred.pack(side="left", padx=4)
        ctk.CTkLabel(sq_row, text="OSPITE", font=FONT_BOLD, text_color=COL_ROSSO).pack(side="left", padx=(8, 24))

        # Pulsante grande centrato
        ctk.CTkButton(
            sel_frame, text="CALCOLA PRONOSTICO", font=("Segoe UI", 16, "bold"),
            fg_color=COL_VERDE, hover_color="#27ae60", text_color="#000",
            height=50, width=300, corner_radius=25,
            command=self._esegui_pronostico
        ).pack(pady=(8, 16))

        # Area risultato
        self.pred_frame = ctk.CTkFrame(center, fg_color="#162447", corner_radius=16)
        self.pred_frame.pack(fill="both", expand=True, padx=40, pady=(8, 20))

        self.lbl_attesa_pred = ctk.CTkLabel(
            self.pred_frame,
            text="Seleziona le squadre e clicca CALCOLA PRONOSTICO",
            font=FONT_MEDIO, text_color=COL_GRIGIO
        )
        self.lbl_attesa_pred.pack(expand=True)

    def _esegui_pronostico(self):
        if self.df is None:
            messagebox.showwarning("Attenzione", "I dati non sono ancora stati caricati.")
            return
        home = self.combo_home_pred.get()
        away = self.combo_away_pred.get()
        if home == away:
            messagebox.showwarning("Attenzione", "Seleziona due squadre diverse!")
            return
        try:
            hs = get_team_stats(self.df, home, opponent=away)
            as_ = get_team_stats(self.df, away, opponent=home)
            pred = get_prediction(hs, as_, df=self.df)
            self._mostra_pronostico(home, away, pred, hs, as_)
        except Exception as e:
            messagebox.showerror("Errore", f"Errore nel calcolo:\n{e}")

    def _mostra_pronostico(self, home, away, pred, hs, as_):
        for w in self.pred_frame.winfo_children():
            w.destroy()

        # Scrollable per tutto il contenuto
        scroll = ctk.CTkScrollableFrame(self.pred_frame, fg_color="transparent")
        scroll.pack(fill="both", expand=True)

        # Titolo partita
        ctk.CTkLabel(
            scroll,
            text=f"{home}  vs  {away}",
            font=FONT_GRANDE, text_color=COL_TESTO
        ).pack(pady=(10, 6))

        # Tre box 1 X 2
        box_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        box_frame.pack(pady=4)

        colori = {"1": COL_VERDE, "X": COL_GIALLO, "2": COL_ROSSO}
        labels_ris = {"1": "1\nCasa vince", "X": "X\nPareggio", "2": "2\nOspite vince"}
        probs = {"1": pred["prob_1"], "X": pred["prob_x"], "2": pred["prob_2"]}
        quote = {"1": pred["quota_1"], "X": pred["quota_x"], "2": pred["quota_2"]}

        for i, chiave in enumerate(["1", "X", "2"]):
            is_sugg = (chiave == pred["suggerimento"])
            border = 3 if is_sugg else 1
            box = ctk.CTkFrame(box_frame, fg_color=COL_BG, corner_radius=14,
                               border_color=colori[chiave], border_width=border,
                               width=160, height=120)
            box.grid(row=0, column=i, padx=14, pady=4)
            box.grid_propagate(False)

            ctk.CTkLabel(box, text=labels_ris[chiave], font=FONT_BOLD,
                         text_color=colori[chiave]).pack(pady=(12, 2))
            ctk.CTkLabel(box, text=f"{probs[chiave]:.1f}%", font=("Segoe UI", 20, "bold"),
                         text_color=COL_TESTO).pack()
            ctk.CTkLabel(box, text=f"Quota: {quote[chiave]}", font=FONT_PICCOLO,
                         text_color=COL_GRIGIO).pack(pady=(2, 6))

            if is_sugg:
                ctk.CTkLabel(box, text="CONSIGLIATO", font=("Segoe UI", 9, "bold"),
                             text_color=colori[chiave]).pack()

        # Suggerimento testuale
        ctk.CTkLabel(
            scroll,
            text=f"Pronostico: {pred['suggerimento']}  —  {pred['sugg_label']}",
            font=FONT_BOLD,
            text_color=colori[pred["suggerimento"]]
        ).pack(pady=6)

        # ── SEZIONE AFFIDABILITA' ──
        conf_frame = ctk.CTkFrame(scroll, fg_color=COL_BG, corner_radius=10)
        conf_frame.pack(fill="x", padx=30, pady=4)

        conf_val = pred.get("confidence", 0.5)
        conf_label = pred.get("confidence_label", "Media")
        conf_color = pred.get("confidence_color", COL_GIALLO)

        ctk.CTkLabel(conf_frame, text=f"Affidabilita': {conf_label} ({round(conf_val * 100)}%)",
                     font=FONT_BOLD, text_color=conf_color).pack(pady=(8, 4))
        bar = ctk.CTkProgressBar(conf_frame, width=350, height=14,
                                  fg_color=COL_ACCENT, progress_color=conf_color)
        bar.set(conf_val)
        bar.pack(pady=(0, 8))

        # ── SEZIONE xG ──
        if pred.get("xg_applied"):
            xg_frame = ctk.CTkFrame(scroll, fg_color=COL_BG, corner_radius=10)
            xg_frame.pack(fill="x", padx=30, pady=4)

            ctk.CTkLabel(xg_frame, text="Expected Goals (xG) - Stagione 2025-2026",
                         font=FONT_BOLD, text_color=COL_TESTO).pack(pady=(8, 4))

            xg_row = ctk.CTkFrame(xg_frame, fg_color="transparent")
            xg_row.pack(pady=2)

            xg_h = pred.get("xg_home", 0)
            xg_a = pred.get("xg_away", 0)
            ctk.CTkLabel(xg_row, text=f"{home}: {xg_h} xG/p", font=FONT_BOLD,
                         text_color=COL_VERDE).pack(side="left", padx=20)
            ctk.CTkLabel(xg_row, text="vs", font=FONT_PICCOLO,
                         text_color=COL_GRIGIO).pack(side="left", padx=8)
            ctk.CTkLabel(xg_row, text=f"{away}: {xg_a} xG/p", font=FONT_BOLD,
                         text_color=COL_ROSSO).pack(side="left", padx=20)

            # Barra visuale confronto xG
            tot_xg = (xg_h or 0.01) + (xg_a or 0.01)
            pct_h = (xg_h or 0) / tot_xg
            xg_bar_frame = ctk.CTkFrame(xg_frame, fg_color="transparent")
            xg_bar_frame.pack(fill="x", padx=20, pady=(4, 8))
            xg_bar_h = ctk.CTkProgressBar(xg_bar_frame, width=300, height=10,
                                           fg_color=COL_ROSSO, progress_color=COL_VERDE)
            xg_bar_h.set(pct_h)
            xg_bar_h.pack(fill="x")

        # ── SEZIONE H2H ──
        h2h_frame = ctk.CTkFrame(scroll, fg_color=COL_BG, corner_radius=10)
        h2h_frame.pack(fill="x", padx=30, pady=4)

        h2h_data = hs.get("h2h")
        if h2h_data is not None:
            ctk.CTkLabel(h2h_frame, text=f"Testa a testa ({h2h_data['n_partite']} partite)",
                         font=FONT_BOLD, text_color=COL_TESTO).pack(pady=(8, 4))

            stats_row = ctk.CTkFrame(h2h_frame, fg_color="transparent")
            stats_row.pack(pady=2)
            for label, val, col in [
                (f"V {home}", h2h_data["vittorie_home"], COL_VERDE),
                ("Pareggi", h2h_data["pareggi"], COL_GIALLO),
                (f"V {away}", h2h_data["vittorie_away"], COL_ROSSO),
            ]:
                ctk.CTkLabel(stats_row, text=f"{label}: {val}", font=FONT_PICCOLO,
                             text_color=col).pack(side="left", padx=16)

            # Ultimi 5 scontri diretti
            if h2h_data.get("ultimi_5_h2h"):
                ctk.CTkLabel(h2h_frame, text="Ultimi scontri:",
                             font=FONT_PICCOLO, text_color=COL_GRIGIO).pack(pady=(4, 2))
                for match_str in h2h_data["ultimi_5_h2h"][:3]:
                    ctk.CTkLabel(h2h_frame, text=match_str,
                                 font=FONT_PICCOLO, text_color=COL_TESTO).pack()
            ctk.CTkLabel(h2h_frame, text="", height=6).pack()
        else:
            ctk.CTkLabel(h2h_frame, text="H2H: dati insufficienti (< 3 scontri diretti)",
                         font=FONT_PICCOLO, text_color=COL_GRIGIO).pack(pady=8)

        # ── SEZIONE CONFRONTO MERCATO ──
        if pred.get("book_prob_1") is not None:
            bk_frame = ctk.CTkFrame(scroll, fg_color=COL_BG, corner_radius=10)
            bk_frame.pack(fill="x", padx=30, pady=4)

            n_bk = pred.get("n_bookmakers", 0)
            ctk.CTkLabel(bk_frame, text=f"Confronto Mercato ({n_bk} bookmaker)",
                         font=FONT_BOLD, text_color=COL_TESTO).pack(pady=(8, 4))

            # Header
            tbl = ctk.CTkFrame(bk_frame, fg_color="transparent")
            tbl.pack(pady=2)

            for c, txt in enumerate(["", "1", "X", "2"]):
                ctk.CTkLabel(tbl, text=txt, font=FONT_BOLD, text_color=COL_TESTO,
                             width=80).grid(row=0, column=c, padx=4)

            # Riga modello
            ctk.CTkLabel(tbl, text="Modello", font=FONT_PICCOLO, text_color=COL_GRIGIO,
                         width=80).grid(row=1, column=0, padx=4)
            for c, key in enumerate(["prob_1", "prob_x", "prob_2"], start=1):
                ctk.CTkLabel(tbl, text=f"{pred[key]:.1f}%", font=FONT_PICCOLO,
                             text_color=COL_TESTO, width=80).grid(row=1, column=c, padx=4)

            # Riga mercato
            ctk.CTkLabel(tbl, text="Mercato", font=FONT_PICCOLO, text_color=COL_GRIGIO,
                         width=80).grid(row=2, column=0, padx=4)
            for c, key in enumerate(["book_prob_1", "book_prob_x", "book_prob_2"], start=1):
                ctk.CTkLabel(tbl, text=f"{pred[key]:.1f}%", font=FONT_PICCOLO,
                             text_color=COL_TESTO, width=80).grid(row=2, column=c, padx=4)

            # Riga delta
            ctk.CTkLabel(tbl, text="Delta", font=FONT_PICCOLO, text_color=COL_GRIGIO,
                         width=80).grid(row=3, column=0, padx=4)
            for c, key in enumerate(["delta_bk_1", "delta_bk_x", "delta_bk_2"], start=1):
                d = pred[key]
                d_col = COL_VERDE if d > 2 else (COL_ROSSO if d < -2 else COL_GRIGIO)
                sign = "+" if d > 0 else ""
                ctk.CTkLabel(tbl, text=f"{sign}{d:.1f}%", font=FONT_PICCOLO,
                             text_color=d_col, width=80).grid(row=3, column=c, padx=4)

            ctk.CTkLabel(bk_frame, text="", height=6).pack()

        # ── SEZIONE OVER/UNDER + GOAL/NOGOAL ──
        ou_frame = ctk.CTkFrame(scroll, fg_color=COL_BG, corner_radius=10)
        ou_frame.pack(fill="x", padx=30, pady=4)

        gol_att = pred.get("gol_attesi", 0)
        ctk.CTkLabel(ou_frame, text=f"Mercati Gol  |  Gol attesi: {gol_att}",
                     font=FONT_BOLD, text_color=COL_TESTO).pack(pady=(8, 4))

        # Over/Under boxes
        ou_row = ctk.CTkFrame(ou_frame, fg_color="transparent")
        ou_row.pack(pady=2)

        for i, soglia in enumerate(["1.5", "2.5", "3.5"]):
            over_val = pred.get(f"over_{soglia.replace('.','')}", 50)
            under_val = pred.get(f"under_{soglia.replace('.','')}", 50)
            is_over = over_val > under_val
            val_max = max(over_val, under_val)
            lbl = f"Over {soglia}" if is_over else f"Under {soglia}"
            col = COL_VERDE if is_over else COL_BLU

            box = ctk.CTkFrame(ou_row, fg_color=COL_CARD, corner_radius=10,
                               border_color=col, border_width=2 if val_max > 60 else 1,
                               width=130, height=60)
            box.grid(row=0, column=i, padx=8, pady=4)
            box.grid_propagate(False)

            ctk.CTkLabel(box, text=lbl, font=FONT_PICCOLO, text_color=col).pack(pady=(8, 0))
            ctk.CTkLabel(box, text=f"{val_max:.0f}%", font=FONT_BOLD, text_color=COL_TESTO).pack()

        # Goal/NoGoal box
        goal_si = pred.get("goal_si", 50)
        goal_no = pred.get("goal_no", 50)
        is_goal = goal_si > goal_no
        goal_val = max(goal_si, goal_no)
        goal_lbl = "GOAL Si" if is_goal else "GOAL No"
        goal_col = COL_VERDE if is_goal else COL_BLU

        goal_box = ctk.CTkFrame(ou_row, fg_color=COL_CARD, corner_radius=10,
                                border_color=goal_col, border_width=2 if goal_val > 60 else 1,
                                width=130, height=60)
        goal_box.grid(row=0, column=3, padx=8, pady=4)
        goal_box.grid_propagate(False)

        ctk.CTkLabel(goal_box, text=goal_lbl, font=FONT_PICCOLO, text_color=goal_col).pack(pady=(8, 0))
        ctk.CTkLabel(goal_box, text=f"{goal_val:.0f}%", font=FONT_BOLD, text_color=COL_TESTO).pack()

        # Tips extra consigliati dall'IA
        tips_extra = pred.get("tips_extra", [])
        if tips_extra:
            tip_row = ctk.CTkFrame(ou_frame, fg_color="transparent")
            tip_row.pack(pady=(4, 2))
            ctk.CTkLabel(tip_row, text="Giocate consigliate:", font=FONT_PICCOLO,
                         text_color=COL_GRIGIO).pack(side="left", padx=8)
            for tip_name, tip_pct, tip_col in tips_extra:
                ctk.CTkLabel(tip_row, text=f" {tip_name} ({tip_pct}%) ", font=FONT_BOLD,
                             fg_color=tip_col, text_color="#000",
                             corner_radius=8, height=24).pack(side="left", padx=4)

        # Risultato esatto piu' probabile
        esatti = pred.get("risultati_esatti", [])
        if esatti:
            ctk.CTkLabel(ou_frame, text="Risultato esatto piu' probabile:",
                         font=FONT_PICCOLO, text_color=COL_GRIGIO).pack(pady=(6, 2))
            re_row = ctk.CTkFrame(ou_frame, fg_color="transparent")
            re_row.pack(pady=(0, 8))
            for r in esatti[:5]:
                ctk.CTkLabel(re_row, text=f" {r['score']} ({r['prob']}%) ", font=FONT_BOLD,
                             fg_color=COL_ACCENT, text_color=COL_TESTO,
                             corner_radius=8, height=26).pack(side="left", padx=3)

        # ── FORMA RECENTE ──
        forma_frame = ctk.CTkFrame(scroll, fg_color=COL_BG, corner_radius=10)
        forma_frame.pack(fill="x", padx=30, pady=(4, 10))

        ctk.CTkLabel(forma_frame, text="Forma recente (ultime 5 partite)",
                     font=FONT_PICCOLO, text_color=COL_GRIGIO).pack(pady=(8, 4))

        for squadra, forma in [(home, hs["forma_recente"]), (away, as_["forma_recente"])]:
            riga = ctk.CTkFrame(forma_frame, fg_color="transparent")
            riga.pack(pady=2)
            ctk.CTkLabel(riga, text=f"{squadra}:", font=FONT_PICCOLO,
                         text_color=COL_TESTO, width=140).pack(side="left")
            for r in forma:
                col = COL_VERDE if r == "V" else (COL_GIALLO if r == "P" else (COL_ROSSO if r == "S" else COL_GRIGIO))
                ctk.CTkLabel(riga, text=f" {r} ", font=FONT_BOLD,
                             fg_color=col, text_color="#000",
                             corner_radius=6, width=28, height=24).pack(side="left", padx=2)
        ctk.CTkLabel(forma_frame, text="", height=6).pack()

    # ─────────────────────────────────────────
    # TAB 3 — Classifica
    # ─────────────────────────────────────────
    def _build_tab_classifica(self):
        tab = self.tabs.tab("Classifica")
        tab.configure(fg_color=COL_CARD)

        # Barra superiore
        ctrl = ctk.CTkFrame(tab, fg_color=COL_ACCENT, corner_radius=10)
        ctrl.pack(fill="x", padx=16, pady=(12, 8))

        ctk.CTkLabel(ctrl, text=f"Serie A 2025-2026  |  Giornata {GIORNATA_ATTUALE}/{GIORNATE_TOTALI}",
                     font=FONT_BOLD, text_color=COL_TESTO).pack(side="left", padx=20, pady=10)

        btn_row = ctk.CTkFrame(ctrl, fg_color="transparent")
        btn_row.pack(side="right", padx=10, pady=8)

        ctk.CTkButton(
            btn_row, text=f"Classifica Reale ({GIORNATA_ATTUALE}ª G)",
            font=FONT_PICCOLO, fg_color=COL_BLU, hover_color="#2980b9",
            height=32, width=200, corner_radius=16,
            command=self._mostra_classifica_reale
        ).pack(side="left", padx=4)

        ctk.CTkButton(
            btn_row, text="Simula Finale (G.31-38)",
            font=FONT_PICCOLO, fg_color="#8e44ad", hover_color="#6c3483",
            height=32, width=200, corner_radius=16,
            command=self._simula_rimanenti
        ).pack(side="left", padx=4)

        self.progress_class = ctk.CTkProgressBar(ctrl, width=150, height=8,
                                                  fg_color=COL_BG, progress_color=COL_BLU)
        self.progress_class.set(0)
        self.progress_class.pack(side="right", padx=8, pady=10)

        self.lbl_progress_class = ctk.CTkLabel(ctrl, text="", font=("Segoe UI", 10),
                                                text_color=COL_GRIGIO)
        self.lbl_progress_class.pack(side="right", padx=4, pady=10)

        # Container a due colonne: marcatori | classifica
        container = ctk.CTkFrame(tab, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=16, pady=4)
        container.grid_columnconfigure(0, weight=2)
        container.grid_columnconfigure(1, weight=3)
        container.grid_rowconfigure(0, weight=1)

        # COLONNA SINISTRA: Classifica Marcatori
        left = ctk.CTkFrame(container, fg_color=COL_BG, corner_radius=10)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 4))

        ctk.CTkLabel(left, text="Classifica Marcatori", font=FONT_BOLD,
                     text_color=COL_GIALLO).pack(pady=(10, 6))

        marc_scroll = ctk.CTkScrollableFrame(left, fg_color="transparent")
        marc_scroll.pack(fill="both", expand=True, padx=4, pady=(0, 8))

        mh = ctk.CTkFrame(marc_scroll, fg_color=COL_ACCENT, corner_radius=4)
        mh.pack(fill="x", pady=(0, 2))
        for c, (txt, w) in enumerate([("#", 25), ("Giocatore", 120), ("Squadra", 80), ("Gol", 35)]):
            ctk.CTkLabel(mh, text=txt, font=FONT_BOLD, text_color=COL_TESTO,
                         width=w).grid(row=0, column=c, padx=1, pady=4)

        marcatori = get_marcatori()
        for m in marcatori:
            r = ctk.CTkFrame(marc_scroll, fg_color=COL_CARD, corner_radius=3)
            r.pack(fill="x", pady=1)
            col_gol = COL_VERDE if m["pos"] <= 3 else (COL_GIALLO if m["pos"] <= 10 else COL_TESTO)
            vals = [(str(m["pos"]), 25), (m["giocatore"], 120), (m["squadra"], 80), (str(m["gol"]), 35)]
            for c, (val, w) in enumerate(vals):
                tc = col_gol if c == 3 else COL_TESTO
                ctk.CTkLabel(r, text=val, font=("Segoe UI", 11), text_color=tc,
                             width=w).grid(row=0, column=c, padx=1, pady=2)

        # COLONNA DESTRA: Classifica Serie A
        right = ctk.CTkFrame(container, fg_color=COL_BG, corner_radius=10)
        right.grid(row=0, column=1, sticky="nsew", padx=(4, 0))

        self.class_frame = ctk.CTkScrollableFrame(right, fg_color="transparent")
        self.class_frame.pack(fill="both", expand=True, padx=4, pady=4)

        # Mostra subito la classifica reale
        self.after(500, self._mostra_classifica_reale)

    def _mostra_classifica_reale(self):
        """Mostra la classifica reale aggiornata alla 30ª giornata."""
        import pandas as pd
        dati = get_classifica_reale()
        df_class = pd.DataFrame(dati)
        df_class.index = range(1, len(df_class) + 1)
        df_class.index.name = "Pos"
        self._mostra_classifica(df_class, titolo=f"Classifica Reale — {GIORNATA_ATTUALE}ª Giornata")
        self.lbl_progress_class.configure(text=f"Dati reali aggiornati alla {GIORNATA_ATTUALE}ª giornata")
        self.progress_class.set(1.0)

    def _simula_rimanenti(self):
        """Simula le 8 giornate rimanenti partendo dalla classifica reale."""
        if self.df is None:
            messagebox.showwarning("Attenzione", "I dati non sono ancora stati caricati.")
            return

        self.lbl_progress_class.configure(text="Simulazione giornate 31-38 in corso...")
        self.progress_class.set(0.2)

        def _worker():
            try:
                self.after(0, lambda: self.progress_class.set(0.5))
                df_class = simulate_remaining_season(get_team_stats, self.df)
                self.after(0, lambda: self.progress_class.set(0.9))
                self.after(0, lambda: self._mostra_classifica(
                    df_class, titolo="Proiezione Finale 2025-2026 (giornate 31-38 simulate)"
                ))
                self.after(0, lambda: self.progress_class.set(1.0))
                self.after(0, lambda: self.lbl_progress_class.configure(
                    text="Proiezione completata: classifica finale simulata"
                ))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Errore", f"Errore simulazione:\n{e}"))

        threading.Thread(target=_worker, daemon=True).start()

    def _simula_stagione(self):
        if self.df is None:
            messagebox.showwarning("Attenzione", "I dati non sono ancora stati caricati.")
            return

        squadre_da_usare = SQUADRE_2526 if SQUADRE_2526 else (self.squadre[:20] if len(self.squadre) >= 20 else self.squadre)

        self.lbl_progress_class.configure(text="Simulazione stagione completa in corso...")
        self.progress_class.set(0.1)

        def _worker():
            try:
                self.after(0, lambda: self.progress_class.set(0.3))
                df_class, _ = simulate_season(squadre_da_usare, get_team_stats, self.df)
                self.after(0, lambda: self.progress_class.set(0.9))
                self.after(0, lambda: self._mostra_classifica(
                    df_class, titolo="Simulazione Stagione Completa (basata su dati storici)"
                ))
                self.after(0, lambda: self.progress_class.set(1.0))
                self.after(0, lambda: self.lbl_progress_class.configure(text="Simulazione completata!"))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Errore", f"Errore simulazione:\n{e}"))

        threading.Thread(target=_worker, daemon=True).start()

    def _mostra_classifica(self, df_class, titolo="Classifica"):
        for w in self.class_frame.winfo_children():
            w.destroy()

        # Titolo
        ctk.CTkLabel(self.class_frame, text=titolo, font=FONT_BOLD,
                     text_color=COL_TESTO).pack(pady=(6, 4))

        # Intestazione tabella
        colonne = ["Pos", "Squadra", "G", "V", "P", "S", "GF", "GS", "DR", "Punti"]
        larghezze = [40, 180, 35, 35, 35, 35, 40, 40, 45, 55]
        header_frame = ctk.CTkFrame(self.class_frame, fg_color=COL_ACCENT, corner_radius=6)
        header_frame.pack(fill="x", pady=(4, 2))

        for i, (col, larg) in enumerate(zip(colonne, larghezze)):
            ctk.CTkLabel(header_frame, text=col, font=FONT_BOLD,
                         text_color=COL_TESTO, width=larg).grid(row=0, column=i, padx=2, pady=6)

        # Righe classifica
        n_tot = len(df_class)
        for pos, (_, row) in enumerate(df_class.iterrows(), start=1):
            if pos <= 4:
                col_bg = "#0d3b1e"
            elif pos <= 6:
                col_bg = "#3d2200"
            elif pos > n_tot - 3:
                col_bg = "#3d0000"
            else:
                col_bg = COL_BG

            riga_frame = ctk.CTkFrame(self.class_frame, fg_color=col_bg, corner_radius=4)
            riga_frame.pack(fill="x", pady=1)

            gf = row.get("GF", row.get("GF", 0))
            gs = row.get("GS", row.get("GS", 0))
            dr = row.get("DR", row.get("DR", 0))
            s_col = "S" if "S" in row else "P"

            valori = [str(pos), str(row["Squadra"]), str(row["G"]), str(row["V"]),
                      str(row.get("N", row.get("P", 0))), str(row.get(s_col, 0)),
                      str(gf), str(gs), str(dr), str(row["Punti"])]

            for i, (val, larg) in enumerate(zip(valori, larghezze)):
                ctk.CTkLabel(riga_frame, text=val, font=FONT_PICCOLO,
                             text_color=COL_TESTO, width=larg).grid(row=0, column=i, padx=2, pady=4)

        # Legenda colori
        leg = ctk.CTkFrame(self.class_frame, fg_color="transparent")
        leg.pack(pady=8)
        for testo, col in [("Champions League", "#2ecc71"), ("Europa League", "#e67e22"), ("Retrocessione", "#e74c3c")]:
            ctk.CTkLabel(leg, text=f"■ {testo}", font=FONT_PICCOLO, text_color=col).pack(side="left", padx=12)

    # ─────────────────────────────────────────
    # TAB 2 — Calendario
    # ─────────────────────────────────────────
    def _build_tab_calendario(self):
        tab = self.tabs.tab("Calendario")
        tab.configure(fg_color=COL_CARD)

        # Barra superiore
        ctrl = ctk.CTkFrame(tab, fg_color=COL_ACCENT, corner_radius=10)
        ctrl.pack(fill="x", padx=12, pady=(10, 6))

        ctk.CTkLabel(ctrl, text="Calendario Serie A 2025-2026",
                     font=FONT_BOLD, text_color=COL_TESTO).pack(side="left", padx=16, pady=8)

        # Dropdown giornata
        self.combo_giornata = ctk.CTkComboBox(
            ctrl, values=[f"Giornata {g}" for g in range(31, 39)],
            width=140, font=FONT_PICCOLO,
            fg_color=COL_BG, text_color=COL_TESTO, button_color=COL_BLU,
            command=self._on_giornata_change
        )
        self.combo_giornata.pack(side="right", padx=8, pady=8)
        self.combo_giornata.set("Giornata 31")

        ctk.CTkButton(
            ctrl, text="Simula Pronostici", font=FONT_PICCOLO,
            fg_color="#8e44ad", hover_color="#6c3483",
            width=160, height=30, corner_radius=14,
            command=self._simula_giornata_calendario
        ).pack(side="right", padx=4, pady=8)

        # Tabs interni: Prossime | Storico
        self.cal_inner_tabs = ctk.CTkTabview(
            tab, fg_color=COL_BG, height=30,
            segmented_button_fg_color=COL_ACCENT,
            segmented_button_selected_color=COL_BLU,
            segmented_button_unselected_color=COL_ACCENT,
        )
        self.cal_inner_tabs.pack(fill="both", expand=True, padx=12, pady=4)
        self.cal_inner_tabs.add("Prossime Giornate")
        self.cal_inner_tabs.add("Risultati (G.1-30)")

        # Container prossime giornate: sinistra (principale) + destra (altre)
        prossime_tab = self.cal_inner_tabs.tab("Prossime Giornate")
        prossime_container = ctk.CTkFrame(prossime_tab, fg_color="transparent")
        prossime_container.pack(fill="both", expand=True)
        prossime_container.grid_columnconfigure(0, weight=3)
        prossime_container.grid_columnconfigure(1, weight=2)
        prossime_container.grid_rowconfigure(0, weight=1)

        # Sinistra: giornata principale
        self.cal_main = ctk.CTkScrollableFrame(prossime_container, fg_color=COL_BG, corner_radius=8)
        self.cal_main.grid(row=0, column=0, sticky="nsew", padx=(0, 4))

        # Destra: giornate a venire
        self.cal_side = ctk.CTkScrollableFrame(prossime_container, fg_color=COL_BG, corner_radius=8)
        self.cal_side.grid(row=0, column=1, sticky="nsew", padx=(4, 0))

        # Storico
        storico_tab = self.cal_inner_tabs.tab("Risultati (G.1-30)")
        self.cal_storico = ctk.CTkScrollableFrame(storico_tab, fg_color=COL_BG, corner_radius=8)
        self.cal_storico.pack(fill="both", expand=True)

        # Carica vista iniziale
        self._mostra_calendario_split(31)

    def _on_giornata_change(self, value):
        g_num = int(value.replace("Giornata ", ""))
        self._mostra_calendario_split(g_num)

    def _mostra_calendario_split(self, g_principale: int):
        """Mostra giornata principale a sinistra, le altre a destra."""
        calendario = get_calendario_rimanente()

        # SINISTRA: giornata principale con partite cliccabili
        for w in self.cal_main.winfo_children():
            w.destroy()

        g = calendario.get(g_principale)
        if g:
            ctk.CTkLabel(self.cal_main, text=f"Giornata {g_principale}",
                         font=FONT_GRANDE, text_color=COL_TESTO).pack(pady=(8, 2))
            ctk.CTkLabel(self.cal_main, text=g["data"],
                         font=FONT_PICCOLO, text_color=COL_GRIGIO).pack(pady=(0, 8))

            for home, away in g["partite"]:
                btn = ctk.CTkButton(
                    self.cal_main,
                    text=f"  {home}   vs   {away}  ",
                    font=FONT_MEDIO, text_color=COL_TESTO,
                    fg_color=COL_CARD, hover_color=COL_ACCENT,
                    height=38, corner_radius=6, anchor="center",
                    command=lambda h=home, a=away: self._mostra_dettaglio_partita(h, a)
                )
                btn.pack(fill="x", pady=2, padx=8)

        # DESTRA: altre giornate compatte
        for w in self.cal_side.winfo_children():
            w.destroy()

        ctk.CTkLabel(self.cal_side, text="Prossime giornate",
                     font=FONT_BOLD, text_color=COL_GRIGIO).pack(pady=(8, 4))

        for g_num in range(31, 39):
            if g_num == g_principale:
                continue
            g = calendario.get(g_num)
            if not g:
                continue

            g_frame = ctk.CTkFrame(self.cal_side, fg_color=COL_CARD, corner_radius=6)
            g_frame.pack(fill="x", pady=3, padx=4)

            header = ctk.CTkFrame(g_frame, fg_color="transparent")
            header.pack(fill="x")
            ctk.CTkLabel(header, text=f"G.{g_num}", font=FONT_BOLD,
                         text_color=COL_BLU).pack(side="left", padx=8, pady=4)
            ctk.CTkLabel(header, text=g["data"], font=("Segoe UI", 9),
                         text_color=COL_GRIGIO).pack(side="right", padx=8, pady=4)

            for home, away in g["partite"]:
                ctk.CTkLabel(g_frame, text=f"{home} - {away}",
                             font=("Segoe UI", 10), text_color=COL_TESTO).pack(anchor="w", padx=12, pady=0)
            ctk.CTkLabel(g_frame, text="", height=4).pack()

        # STORICO: carica dopo che i dati sono pronti (non ora)
        # Verra' chiamato da _on_dati_caricati

    def _carica_storico_risultati(self):
        """Carica i risultati delle giornate 1-30 dai CSV."""
        for w in self.cal_storico.winfo_children():
            w.destroy()

        if self.df is None:
            ctk.CTkLabel(self.cal_storico, text="Carica i dati per vedere lo storico",
                         font=FONT_MEDIO, text_color=COL_GRIGIO).pack(pady=20)
            return

        giornate = get_risultati_stagione(self.df)
        if not giornate:
            ctk.CTkLabel(self.cal_storico, text="Nessun risultato disponibile per la stagione 2025-2026",
                         font=FONT_MEDIO, text_color=COL_GRIGIO).pack(pady=20)
            return

        ctk.CTkLabel(self.cal_storico, text=f"Risultati Stagione 2025-2026 ({len(giornate)} giornate)",
                     font=FONT_BOLD, text_color=COL_TESTO).pack(pady=(8, 4))

        # Mostra dalla piu' recente
        for g in reversed(giornate):
            g_frame = ctk.CTkFrame(self.cal_storico, fg_color=COL_ACCENT, corner_radius=6)
            g_frame.pack(fill="x", pady=3, padx=4)

            ctk.CTkLabel(g_frame, text=f"Giornata {g['giornata']}  —  {g['data']}",
                         font=FONT_BOLD, text_color=COL_TESTO).pack(anchor="w", padx=8, pady=(4, 2))

            for r in g["risultati"]:
                ris_col = COL_VERDE if r["risultato"] == "H" else (COL_GIALLO if r["risultato"] == "D" else COL_ROSSO)
                ctk.CTkLabel(g_frame, text=f"  {r['home']} {r['gol_home']}-{r['gol_away']} {r['away']}",
                             font=("Segoe UI", 10), text_color=ris_col).pack(anchor="w", padx=12, pady=0)
            ctk.CTkLabel(g_frame, text="", height=3).pack()

    def _simula_giornata_calendario(self):
        """Simula i pronostici per la giornata selezionata."""
        if self.df is None:
            messagebox.showwarning("Attenzione", "I dati non sono ancora stati caricati.")
            return

        sel = self.combo_giornata.get()
        g_num = int(sel.replace("Giornata ", ""))
        calendario = get_calendario_rimanente()
        giornata = calendario.get(g_num)
        if not giornata:
            return

        # Mostra nel pannello principale
        for w in self.cal_main.winfo_children():
            w.destroy()

        ctk.CTkLabel(self.cal_main, text=f"Pronostici Giornata {g_num}",
                     font=FONT_GRANDE, text_color=COL_TESTO).pack(pady=(8, 2))
        ctk.CTkLabel(self.cal_main, text=giornata["data"],
                     font=FONT_PICCOLO, text_color=COL_GRIGIO).pack(pady=(0, 6))

        # Header
        hdr = ctk.CTkFrame(self.cal_main, fg_color=COL_ACCENT, corner_radius=6)
        hdr.pack(fill="x", padx=4, pady=(0, 2))
        cols = [("Casa", 90), ("Ospite", 90), ("1", 38), ("X", 38), ("2", 38), ("Tip", 28), ("O/U", 65), ("Goal", 55), ("Aff.", 40)]
        for c, (txt, w) in enumerate(cols):
            ctk.CTkLabel(hdr, text=txt, font=FONT_BOLD, text_color=COL_TESTO,
                         width=w).grid(row=0, column=c, padx=1, pady=4)

        for home, away in giornata["partite"]:
            try:
                hs = get_team_stats(self.df, home, opponent=away)
                as_ = get_team_stats(self.df, away, opponent=home)
                pred = get_prediction(hs, as_, df=self.df)

                r = ctk.CTkFrame(self.cal_main, fg_color=COL_CARD, corner_radius=4, cursor="hand2")
                r.pack(fill="x", padx=4, pady=1)
                r.bind("<Button-1>", lambda e, h=home, a=away: self._mostra_dettaglio_partita(h, a))

                colori_tip = {"1": COL_VERDE, "X": COL_GIALLO, "2": COL_ROSSO}
                ou_val = pred.get("over_25", 50)
                ou_tip = f"O2.5 {ou_val:.0f}%" if ou_val > 50 else f"U2.5 {100-ou_val:.0f}%"
                ou_col = COL_VERDE if ou_val > 50 else COL_BLU
                goal_val = pred.get("goal_si", 50)
                goal_tip = f"Si {goal_val:.0f}%" if goal_val > 50 else f"No {100-goal_val:.0f}%"
                gc = COL_VERDE if goal_val > 50 else COL_BLU

                vals = [
                    (home, 90, COL_TESTO), (away, 90, COL_TESTO),
                    (f"{pred['prob_1']:.0f}%", 38, COL_VERDE),
                    (f"{pred['prob_x']:.0f}%", 38, COL_GIALLO),
                    (f"{pred['prob_2']:.0f}%", 38, COL_ROSSO),
                    (pred["suggerimento"], 28, colori_tip.get(pred["suggerimento"], COL_TESTO)),
                    (ou_tip, 65, ou_col), (goal_tip, 55, gc),
                    (f"{round(pred['confidence']*100)}%", 40, pred.get("confidence_color", COL_GRIGIO)),
                ]
                for c, (val, w, col) in enumerate(vals):
                    ctk.CTkLabel(r, text=val, font=("Segoe UI", 10),
                                 text_color=col, width=w).grid(row=0, column=c, padx=1, pady=3)
            except Exception:
                ctk.CTkLabel(self.cal_main, text=f"{home} vs {away}: errore",
                             font=FONT_PICCOLO, text_color=COL_ROSSO).pack(padx=8, pady=1)

        # Pulsante torna
        ctk.CTkButton(
            self.cal_main, text="Torna al Calendario", font=FONT_PICCOLO,
            fg_color=COL_BLU, hover_color="#2980b9",
            width=160, height=28, corner_radius=12,
            command=lambda: self._mostra_calendario_split(g_num)
        ).pack(pady=8)

    def _mostra_dettaglio_partita(self, home: str, away: str):
        """Mostra pronostico completo con formazioni nel pannello principale."""
        if self.df is None:
            messagebox.showwarning("Attenzione", "Dati non caricati.")
            return

        for w in self.cal_main.winfo_children():
            w.destroy()

        try:
            hs = get_team_stats(self.df, home, opponent=away)
            as_ = get_team_stats(self.df, away, opponent=home)
            pred = get_prediction(hs, as_, df=self.df)
        except Exception as e:
            ctk.CTkLabel(self.cal_main, text=f"Errore: {e}",
                         font=FONT_MEDIO, text_color=COL_ROSSO).pack(pady=20)
            return

        # Titolo centrato
        ctk.CTkLabel(self.cal_main, text=f"{home}  vs  {away}",
                     font=FONT_GRANDE, text_color=COL_TESTO).pack(pady=(8, 4))

        # 1X2 centrato
        colori = {"1": COL_VERDE, "X": COL_GIALLO, "2": COL_ROSSO}
        box_frame = ctk.CTkFrame(self.cal_main, fg_color="transparent")
        box_frame.pack(pady=4)
        for i, (chiave, prob, quota) in enumerate([
            ("1", pred["prob_1"], pred["quota_1"]),
            ("X", pred["prob_x"], pred["quota_x"]),
            ("2", pred["prob_2"], pred["quota_2"]),
        ]):
            is_sugg = (chiave == pred["suggerimento"])
            box = ctk.CTkFrame(box_frame, fg_color=COL_BG, corner_radius=10,
                               border_color=colori[chiave], border_width=3 if is_sugg else 1,
                               width=120, height=75)
            box.grid(row=0, column=i, padx=8, pady=2)
            box.grid_propagate(False)
            lbl = {"1": "1 Casa", "X": "X Pareggio", "2": "2 Ospite"}[chiave]
            ctk.CTkLabel(box, text=lbl, font=("Segoe UI", 10), text_color=colori[chiave]).pack(pady=(8, 0))
            ctk.CTkLabel(box, text=f"{prob:.1f}%", font=("Segoe UI", 16, "bold"), text_color=COL_TESTO).pack()
            ctk.CTkLabel(box, text=f"Q. {quota}", font=("Segoe UI", 9), text_color=COL_GRIGIO).pack()

        # Consiglio + affidabilita'
        sugg_col = colori.get(pred["suggerimento"], COL_TESTO)
        ctk.CTkLabel(self.cal_main, text=f"Consiglio: {pred['suggerimento']} — {pred['sugg_label']}",
                     font=FONT_BOLD, text_color=sugg_col).pack(pady=2)
        conf_col = pred.get("confidence_color", COL_GIALLO)
        ctk.CTkLabel(self.cal_main, text=f"Affidabilita': {pred['confidence_label']} ({round(pred['confidence']*100)}%)",
                     font=FONT_PICCOLO, text_color=conf_col).pack(pady=1)

        # Over/Under + Goal compatto
        ou_row = ctk.CTkFrame(self.cal_main, fg_color="transparent")
        ou_row.pack(pady=4)
        for soglia in ["1.5", "2.5", "3.5"]:
            ov = pred.get(f"over_{soglia.replace('.','')}", 50)
            un = pred.get(f"under_{soglia.replace('.','')}", 50)
            is_o = ov > un
            lbl = f"O{soglia}" if is_o else f"U{soglia}"
            val = max(ov, un)
            col = COL_VERDE if is_o else COL_BLU
            ctk.CTkLabel(ou_row, text=f" {lbl}:{val:.0f}% ", font=FONT_BOLD,
                         fg_color=col, text_color="#000", corner_radius=6,
                         height=22).pack(side="left", padx=3)
        gs = pred.get("goal_si", 50)
        gn = pred.get("goal_no", 50)
        g_lbl = f"Goal:{gs:.0f}%" if gs > gn else f"NoGoal:{gn:.0f}%"
        g_col = COL_VERDE if gs > gn else COL_BLU
        ctk.CTkLabel(ou_row, text=f" {g_lbl} ", font=FONT_BOLD,
                     fg_color=g_col, text_color="#000", corner_radius=6,
                     height=22).pack(side="left", padx=3)

        # Risultati esatti
        esatti = pred.get("risultati_esatti", [])
        if esatti:
            re_row = ctk.CTkFrame(self.cal_main, fg_color="transparent")
            re_row.pack(pady=2)
            ctk.CTkLabel(re_row, text="Esatto:", font=("Segoe UI", 9), text_color=COL_GRIGIO).pack(side="left", padx=4)
            for r in esatti[:4]:
                ctk.CTkLabel(re_row, text=f" {r['score']}({r['prob']}%) ", font=("Segoe UI", 10, "bold"),
                             fg_color=COL_ACCENT, text_color=COL_TESTO,
                             corner_radius=4, height=20).pack(side="left", padx=2)

        # FORMAZIONI
        ctk.CTkLabel(self.cal_main, text="Probabili Formazioni",
                     font=FONT_BOLD, text_color=COL_TESTO).pack(pady=(8, 2))

        for squadra, col_s in [(home, COL_VERDE), (away, COL_ROSSO)]:
            sf = ctk.CTkFrame(self.cal_main, fg_color=COL_CARD, corner_radius=6)
            sf.pack(fill="x", padx=8, pady=2)

            form = get_formazione(squadra)
            allenatore = get_allenatore(squadra)

            if form:
                ctk.CTkLabel(sf, text=f"{squadra} ({form['modulo']}) — All. {allenatore}",
                             font=FONT_BOLD, text_color=col_s).pack(anchor="w", padx=8, pady=(4, 0))
                ctk.CTkLabel(sf, text=", ".join(form["titolari"]),
                             font=("Segoe UI", 10), text_color=COL_TESTO,
                             wraplength=450).pack(anchor="w", padx=8, pady=1)
            else:
                ctk.CTkLabel(sf, text=f"{squadra} — All. {allenatore}",
                             font=FONT_BOLD, text_color=col_s).pack(anchor="w", padx=8, pady=4)

            inj = get_infortunati(squadra)
            if inj:
                inj_row = ctk.CTkFrame(sf, fg_color="transparent")
                inj_row.pack(anchor="w", padx=8, pady=(0, 4))
                for inf in inj[:4]:
                    tc = COL_ROSSO if inf["tipo"] == "infortunio" else COL_GIALLO
                    ic = "X" if inf["tipo"] == "infortunio" else "?"
                    ctk.CTkLabel(inj_row, text=f" {ic} {inf['nome']} ",
                                 font=("Segoe UI", 9), fg_color=tc, text_color="#000",
                                 corner_radius=4, height=16).pack(side="left", padx=1)

        # Pulsante torna
        ctk.CTkButton(
            self.cal_main, text="Torna al Calendario", font=FONT_PICCOLO,
            fg_color=COL_BLU, hover_color="#2980b9",
            width=160, height=28, corner_radius=12,
            command=lambda: self._mostra_calendario_split(31)
        ).pack(pady=8)

    # ─────────────────────────────────────────
    # TAB 4 — Squadre (Campo + Rose con foto)
    # ─────────────────────────────────────────
    def _build_tab_squadre(self):
        tab = self.tabs.tab("Squadre")
        tab.configure(fg_color=COL_CARD)

        top_frame = ctk.CTkFrame(tab, fg_color=COL_ACCENT, corner_radius=10)
        top_frame.pack(fill="x", padx=16, pady=(12, 8))

        ctk.CTkLabel(top_frame, text="Rose Serie A 2025-2026", font=FONT_BOLD,
                     text_color=COL_TESTO).pack(side="left", padx=20, pady=10)

        ctk.CTkLabel(top_frame, text="Squadra:", font=FONT_PICCOLO,
                     text_color=COL_GRIGIO).pack(side="left", padx=(20, 4))
        self.combo_rosa = ctk.CTkComboBox(
            top_frame, values=SQUADRE_2526, width=180, font=FONT_PICCOLO,
            fg_color=COL_BG, text_color=COL_TESTO, button_color=COL_BLU,
            command=self._mostra_squadra
        )
        self.combo_rosa.pack(side="left", padx=4, pady=10)
        self.combo_rosa.set(SQUADRE_2526[0] if SQUADRE_2526 else "")

        # Container 2 colonne: campo | rosa
        self.sq_container = ctk.CTkFrame(tab, fg_color="transparent")
        self.sq_container.pack(fill="both", expand=True, padx=16, pady=4)
        self.sq_container.grid_columnconfigure(0, weight=2)
        self.sq_container.grid_columnconfigure(1, weight=3)
        self.sq_container.grid_rowconfigure(0, weight=1)

        # Pannello sinistro: campo di calcio
        self.pitch_frame = ctk.CTkFrame(self.sq_container, fg_color=COL_BG, corner_radius=10)
        self.pitch_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 4))

        # Pannello destro: rosa con foto
        self.rosa_scroll = ctk.CTkScrollableFrame(self.sq_container, fg_color=COL_BG, corner_radius=10)
        self.rosa_scroll.grid(row=0, column=1, sticky="nsew", padx=(4, 0))

        # Cache foto per evitare garbage collection
        self._photo_refs = []

        self._mostra_squadra(SQUADRE_2526[0] if SQUADRE_2526 else "Inter")

    def _mostra_squadra(self, squadra: str):
        """Aggiorna sia il campo che la rosa."""
        self._mostra_campo(squadra)
        self._mostra_rosa(squadra)

    def _mostra_campo(self, squadra: str):
        """Disegna il campo di calcio con la formazione."""
        for w in self.pitch_frame.winfo_children():
            w.destroy()

        ctk.CTkLabel(self.pitch_frame, text="Probabile Formazione",
                     font=FONT_BOLD, text_color=COL_TESTO).pack(pady=(8, 0))

        form = get_formazione(squadra)
        if form:
            allenatore = get_allenatore(squadra)
            ctk.CTkLabel(self.pitch_frame, text=f"All. {allenatore}",
                         font=("Segoe UI", 10), text_color=COL_GRIGIO).pack(pady=(0, 4))

            pitch = create_pitch_widget(
                self.pitch_frame,
                width=340, height=420,
                home_titolari=form["titolari"],
                home_modulo=form["modulo"],
                home_name=f"{squadra}",
                away_titolari=None,
                away_modulo="4-4-2",
                away_name=""
            )
            pitch.pack(padx=8, pady=(0, 8))
        else:
            ctk.CTkLabel(self.pitch_frame,
                         text=f"Formazione non disponibile\nper {squadra}",
                         font=FONT_MEDIO, text_color=COL_GRIGIO).pack(expand=True)

    def _mostra_rosa(self, squadra: str):
        """Mostra la rosa con foto e stato infortunati."""
        for w in self.rosa_scroll.winfo_children():
            w.destroy()
        self._photo_refs = []

        allenatore = get_allenatore(squadra)
        gruppi = get_giocatori_per_ruolo(squadra)
        infortunati = get_infortunati(squadra)
        nomi_inf = {i["nome"].lower(): i for i in infortunati}

        ctk.CTkLabel(self.rosa_scroll, text=squadra, font=FONT_GRANDE,
                     text_color=COL_TESTO).pack(pady=(6, 2))
        ctk.CTkLabel(self.rosa_scroll, text=f"Allenatore: {allenatore}",
                     font=FONT_PICCOLO, text_color=COL_GRIGIO).pack(pady=(0, 4))

        # Box infortunati
        if infortunati:
            inj_box = ctk.CTkFrame(self.rosa_scroll, fg_color="#3d0000", corner_radius=8)
            inj_box.pack(fill="x", padx=4, pady=(0, 6))
            ctk.CTkLabel(inj_box, text=f"Indisponibili ({len(infortunati)})",
                         font=FONT_BOLD, text_color=COL_ROSSO).pack(anchor="w", padx=8, pady=(6, 2))
            for inf in infortunati:
                tipo_col = COL_ROSSO if inf["tipo"] == "infortunio" else COL_GIALLO
                tipo_icon = "X" if inf["tipo"] == "infortunio" else "?"
                ctk.CTkLabel(inj_box, text=f"  {tipo_icon} {inf['nome']} — {inf['dettaglio']}",
                             font=("Segoe UI", 10), text_color=tipo_col).pack(anchor="w", padx=8, pady=1)
            ctk.CTkLabel(inj_box, text="", height=4).pack()

        nomi_ruoli = {"P": "Portieri", "D": "Difensori", "C": "Centrocampisti", "A": "Attaccanti"}
        colori_ruoli = {"P": COL_GIALLO, "D": COL_BLU, "C": COL_VERDE, "A": COL_ROSSO}

        for ruolo in ["P", "D", "C", "A"]:
            giocatori = gruppi.get(ruolo, [])
            if not giocatori:
                continue

            ctk.CTkLabel(self.rosa_scroll, text=nomi_ruoli[ruolo], font=FONT_BOLD,
                         text_color=colori_ruoli[ruolo]).pack(anchor="w", padx=8, pady=(6, 2))

            for nome, num in giocatori:
                is_inj = False
                inj_info = None
                for inj_name, inj_data in nomi_inf.items():
                    if inj_name in nome.lower() or nome.lower() in inj_name:
                        is_inj = True
                        inj_info = inj_data
                        break

                riga = ctk.CTkFrame(self.rosa_scroll,
                                    fg_color="#3d0000" if is_inj else COL_CARD,
                                    corner_radius=4)
                riga.pack(fill="x", pady=1, padx=4)

                # Foto giocatore
                try:
                    photo = get_player_photo_tk(nome, master=self.rosa_scroll)
                    if photo:
                        self._photo_refs.append(photo)
                        lbl_foto = tk.Label(riga, image=photo, bg="#3d0000" if is_inj else "#16213e",
                                            borderwidth=0)
                        lbl_foto.pack(side="left", padx=(4, 2), pady=2)
                except Exception:
                    pass

                ctk.CTkLabel(riga, text=str(num), font=FONT_BOLD,
                             text_color=colori_ruoli[ruolo], width=30).pack(side="left", padx=(4, 2), pady=3)

                nome_col = COL_ROSSO if is_inj else COL_TESTO
                ctk.CTkLabel(riga, text=nome, font=FONT_PICCOLO,
                             text_color=nome_col).pack(side="left", padx=4, pady=3)

                if is_inj and inj_info:
                    tipo_icon = "X" if inj_info["tipo"] == "infortunio" else "?"
                    ctk.CTkLabel(riga, text=f" {tipo_icon} {inj_info['dettaglio']} ",
                                 font=("Segoe UI", 9), text_color=COL_ROSSO).pack(side="right", padx=8, pady=3)

    # ─────────────────────────────────────────
    # TAB 5 — Storico
    # ─────────────────────────────────────────
    def _build_tab_storico(self):
        tab = self.tabs.tab("Storico")
        tab.configure(fg_color=COL_CARD)

        ctrl = ctk.CTkFrame(tab, fg_color=COL_ACCENT, corner_radius=10)
        ctrl.pack(fill="x", padx=16, pady=(12, 8))

        ctk.CTkLabel(ctrl, text="Storico Simulazioni", font=FONT_BOLD,
                     text_color=COL_TESTO).pack(side="left", padx=20, pady=10)

        ctk.CTkButton(ctrl, text="Aggiorna", font=FONT_PICCOLO,
                      fg_color=COL_BLU, hover_color="#2980b9",
                      width=100, height=32, corner_radius=14,
                      command=self._aggiorna_storico).pack(side="right", padx=8, pady=10)

        ctk.CTkButton(ctrl, text="Cancella tutto", font=FONT_PICCOLO,
                      fg_color=COL_ROSSO, hover_color="#c0392b",
                      width=130, height=32, corner_radius=14,
                      command=self._cancella_storico).pack(side="right", padx=4, pady=10)

        self.storico_frame = ctk.CTkScrollableFrame(tab, fg_color=COL_BG, corner_radius=10)
        self.storico_frame.pack(fill="both", expand=True, padx=16, pady=4)

        self._aggiorna_storico()

    def _aggiorna_storico(self):
        for w in self.storico_frame.winfo_children():
            w.destroy()

        try:
            storia = get_history()
        except Exception:
            storia = []

        if not storia:
            ctk.CTkLabel(self.storico_frame, text="Nessuna simulazione salvata.",
                         font=FONT_MEDIO, text_color=COL_GRIGIO).pack(pady=30)
            return

        # Intestazione
        colonne = ["Data", "Casa", "Ospite", "Risultato", "Pronostico", "Quota"]
        larghezze = [130, 160, 160, 90, 100, 70]
        header = ctk.CTkFrame(self.storico_frame, fg_color=COL_ACCENT, corner_radius=6)
        header.pack(fill="x", pady=(4, 2))
        for i, (col, larg) in enumerate(zip(colonne, larghezze)):
            ctk.CTkLabel(header, text=col, font=FONT_BOLD,
                         text_color=COL_TESTO, width=larg).grid(row=0, column=i, padx=2, pady=6)

        for record in storia:
            riga = ctk.CTkFrame(self.storico_frame, fg_color=COL_CARD, corner_radius=4)
            riga.pack(fill="x", pady=1)
            valori = [
                record.get("data_sim", "-"),
                record.get("home", "-"),
                record.get("away", "-"),
                record.get("risultato", "-"),
                record.get("pronostico", "-"),
                str(record.get("quota_pronostico", "-"))
            ]
            for i, (val, larg) in enumerate(zip(valori, larghezze)):
                ctk.CTkLabel(riga, text=val, font=FONT_PICCOLO,
                             text_color=COL_TESTO, width=larg).grid(row=0, column=i, padx=2, pady=4)

    def _cancella_storico(self):
        if messagebox.askyesno("Conferma", "Vuoi davvero cancellare tutto lo storico?"):
            try:
                clear_history()
                self._aggiorna_storico()
            except Exception as e:
                messagebox.showerror("Errore", f"Impossibile cancellare:\n{e}")

    # ─────────────────────────────────────────
    # Barra di stato
    # ─────────────────────────────────────────
    def _build_status_bar(self):
        status = ctk.CTkFrame(self, fg_color=COL_ACCENT, height=32, corner_radius=0)
        status.pack(fill="x", side="bottom")

        self.lbl_status = ctk.CTkLabel(status, text="Caricamento dati in corso...",
                                        font=FONT_PICCOLO, text_color=COL_GRIGIO)
        self.lbl_status.pack(side="left", padx=16, pady=4)

        # Pulsante aggiorna dati
        ctk.CTkButton(
            status, text="Aggiorna Dati", font=("Segoe UI", 10),
            fg_color="#8e44ad", hover_color="#6c3483",
            width=110, height=22, corner_radius=10,
            command=self._aggiorna_dati_web
        ).pack(side="right", padx=8, pady=5)

        # Ultimo aggiornamento
        ultimo = get_ultimo_aggiornamento()
        self.lbl_update = ctk.CTkLabel(status, text=f"Agg: {ultimo}",
                                        font=("Segoe UI", 10), text_color=COL_GRIGIO)
        self.lbl_update.pack(side="right", padx=4, pady=4)

        self.progress_bar = ctk.CTkProgressBar(status, width=150, height=10,
                                                fg_color=COL_BG, progress_color=COL_VERDE)
        self.progress_bar.set(0)
        self.progress_bar.pack(side="right", padx=8, pady=6)

    def _aggiorna_dati_web(self):
        """Scarica dati aggiornati dal web e ricarica."""
        self._set_status("Aggiornamento dati in corso...", 0.3)

        def _worker():
            try:
                ok = esegui_aggiornamento()
                self.after(0, lambda: self.progress_bar.set(0.7))
                if ok:
                    # Ricarica i CSV
                    self.after(0, self._carica_dati)
                    self.after(0, lambda: self.lbl_update.configure(
                        text=f"Agg: {get_ultimo_aggiornamento()}"
                    ))
                else:
                    self.after(0, lambda: self._set_status("Aggiornamento parziale", 1.0))
            except Exception as e:
                self.after(0, lambda: self._set_status(f"Errore aggiornamento: {e}", 0))

        threading.Thread(target=_worker, daemon=True).start()

    def _set_status(self, testo, progresso=None):
        self.lbl_status.configure(text=testo)
        if progresso is not None:
            self.progress_bar.set(progresso)

    # ─────────────────────────────────────────
    # Caricamento dati CSV
    # ─────────────────────────────────────────
    def _carica_dati(self):
        def _worker():
            try:
                self.after(0, lambda: self._set_status("Scansione file CSV...", 0.2))
                df = load_all_data()
                self.after(0, lambda: self._set_status("Calcolo statistiche...", 0.6))
                squadre = get_teams(df)
                self.after(0, lambda: self._on_dati_caricati(df, squadre))
            except FileNotFoundError as e:
                self.after(0, lambda: self._on_errore_caricamento(str(e)))
            except Exception as e:
                self.after(0, lambda: self._on_errore_caricamento(f"Errore imprevisto:\n{e}"))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_dati_caricati(self, df, squadre):
        self.df = df
        self.squadre = squadre
        n = len(df)
        n_sq = len(squadre)

        # Usa le squadre 2025-26 se disponibili nei dati, altrimenti usa quelle dai CSV
        squadre_dropdown = [s for s in SQUADRE_2526 if s in squadre]
        if len(squadre_dropdown) < 5:
            squadre_dropdown = squadre  # fallback ai CSV

        # Aggiorna tutti i dropdown
        for combo in [self.combo_home_pred, self.combo_away_pred]:
            combo.configure(values=squadre_dropdown)
            combo.set(squadre_dropdown[0] if squadre_dropdown else "")

        if len(squadre_dropdown) >= 2:
            self.combo_away_pred.set(squadre_dropdown[1])

        self._set_status(
            f"Dati caricati: {n:,} partite  |  {n_sq} squadre  |  Serie A 1993-2026",
            1.0
        )

        # Carica storico risultati nel tab Calendario
        try:
            self._carica_storico_risultati()
        except Exception:
            pass

    def _on_errore_caricamento(self, msg):
        self._set_status("ERRORE caricamento dati", 0)
        messagebox.showerror(
            "Errore Caricamento Dati",
            f"{msg}\n\nVerifica che la cartella 'Mariocalcio' sia sul Desktop\n"
            f"e che contenga file .csv con le partite di Serie A."
        )


if __name__ == "__main__":
    app = App()
    app.mainloop()
