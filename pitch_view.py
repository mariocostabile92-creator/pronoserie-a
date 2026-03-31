"""
pitch_view.py
Disegna un campo di calcio con le posizioni dei giocatori secondo il modulo tattico.
Usa tkinter Canvas integrato in CustomTkinter.
"""

import tkinter as tk

# Colori campo
PITCH_GREEN = "#2d8a4e"
PITCH_LIGHT = "#34a058"
PITCH_LINE = "#ffffff"
DOT_HOME = "#3498db"
DOT_AWAY = "#e74c3c"
TEXT_COLOR = "#ffffff"

# Posizioni giocatori per modulo (x%, y% dal basso)
# y: 0% = porta, 100% = meta' campo
MODULI = {
    "4-4-2": [
        (50, 3),  # Portiere
        (15, 20), (38, 22), (62, 22), (85, 20),  # Difesa
        (15, 45), (38, 48), (62, 48), (85, 45),  # Centrocampo
        (35, 72), (65, 72),  # Attacco
    ],
    "4-3-3": [
        (50, 3),
        (15, 20), (38, 22), (62, 22), (85, 20),
        (30, 45), (50, 48), (70, 45),
        (20, 72), (50, 75), (80, 72),
    ],
    "3-5-2": [
        (50, 3),
        (25, 20), (50, 22), (75, 20),
        (10, 42), (35, 45), (50, 48), (65, 45), (90, 42),
        (35, 72), (65, 72),
    ],
    "3-4-2-1": [
        (50, 3),
        (25, 20), (50, 22), (75, 20),
        (15, 42), (40, 45), (60, 45), (85, 42),
        (35, 62), (65, 62),
        (50, 78),
    ],
    "4-2-3-1": [
        (50, 3),
        (15, 20), (38, 22), (62, 22), (85, 20),
        (35, 40), (65, 40),
        (20, 58), (50, 62), (80, 58),
        (50, 78),
    ],
    "4-3-1-2": [
        (50, 3),
        (15, 20), (38, 22), (62, 22), (85, 20),
        (30, 40), (50, 42), (70, 40),
        (50, 58),
        (35, 75), (65, 75),
    ],
    "4-1-4-1": [
        (50, 3),
        (15, 20), (38, 22), (62, 22), (85, 20),
        (50, 38),
        (15, 55), (38, 58), (62, 58), (85, 55),
        (50, 78),
    ],
    "5-3-2": [
        (50, 3),
        (10, 20), (30, 22), (50, 22), (70, 22), (90, 20),
        (30, 45), (50, 48), (70, 45),
        (35, 72), (65, 72),
    ],
}

# Fallback generico per moduli sconosciuti
DEFAULT_POSITIONS = MODULI["4-4-2"]


def get_positions(modulo: str) -> list:
    """Ritorna le posizioni (x%, y%) per un modulo."""
    modulo_clean = modulo.strip().replace(" ", "")
    if modulo_clean in MODULI:
        return MODULI[modulo_clean]
    # Prova varianti
    for key in MODULI:
        if key.replace("-", "") == modulo_clean.replace("-", ""):
            return MODULI[key]
    return DEFAULT_POSITIONS


def draw_pitch(canvas, width, height):
    """Disegna il campo di calcio sul canvas."""
    # Sfondo verde con strisce
    stripe_h = height / 10
    for i in range(10):
        col = PITCH_GREEN if i % 2 == 0 else PITCH_LIGHT
        canvas.create_rectangle(0, i * stripe_h, width, (i + 1) * stripe_h,
                                fill=col, outline="")

    # Bordo campo
    m = 8  # margine
    canvas.create_rectangle(m, m, width - m, height - m, outline=PITCH_LINE, width=2)

    # Linea di meta' campo
    mid_y = height / 2
    canvas.create_line(m, mid_y, width - m, mid_y, fill=PITCH_LINE, width=1)

    # Cerchio di centrocampo
    r = min(width, height) * 0.08
    canvas.create_oval(width / 2 - r, mid_y - r, width / 2 + r, mid_y + r,
                       outline=PITCH_LINE, width=1)

    # Area di rigore (basso - casa)
    aw = width * 0.44
    ah = height * 0.14
    ax = (width - aw) / 2
    canvas.create_rectangle(ax, height - m - ah, ax + aw, height - m,
                            outline=PITCH_LINE, width=1)

    # Area di rigore (alto - ospite)
    canvas.create_rectangle(ax, m, ax + aw, m + ah,
                            outline=PITCH_LINE, width=1)

    # Porta (basso)
    pw = width * 0.16
    px = (width - pw) / 2
    canvas.create_rectangle(px, height - m, px + pw, height - m + 4,
                            outline=PITCH_LINE, width=1)

    # Porta (alto)
    canvas.create_rectangle(px, m - 4, px + pw, m,
                            outline=PITCH_LINE, width=1)


def draw_team(canvas, width, height, titolari: list, modulo: str,
              side: str = "home", dot_color: str = None):
    """
    Disegna una squadra sul campo.
    side: "home" (meta' bassa) o "away" (meta' alta)
    """
    positions = get_positions(modulo)
    if dot_color is None:
        dot_color = DOT_HOME if side == "home" else DOT_AWAY

    half_h = height / 2
    m = 12

    for i, (px, py) in enumerate(positions):
        if i >= len(titolari):
            break

        # Converti percentuali in coordinate
        x = m + (width - 2 * m) * (px / 100)

        if side == "home":
            # Meta' bassa: y dal basso
            y = height - m - (half_h - 2 * m) * (py / 100)
        else:
            # Meta' alta: y dall'alto (invertito)
            y = m + (half_h - 2 * m) * (py / 100)

        # Pallino giocatore
        r = 10
        canvas.create_oval(x - r, y - r, x + r, y + r,
                           fill=dot_color, outline="#fff", width=1)

        # Nome abbreviato
        nome = titolari[i]
        # Abbrevia: prendi cognome o prime 8 lettere
        parts = nome.split()
        short = parts[-1][:8] if parts else nome[:8]

        canvas.create_text(x, y + r + 8, text=short, fill=TEXT_COLOR,
                           font=("Segoe UI", 7, "bold"), anchor="n")


def create_pitch_widget(parent, width=380, height=500,
                         home_titolari=None, home_modulo="4-4-2",
                         away_titolari=None, away_modulo="4-4-2",
                         home_name="Casa", away_name="Ospite"):
    """
    Crea un widget Canvas con il campo e le due squadre.
    Ritorna il frame contenitore.
    """
    import customtkinter as ctk

    frame = ctk.CTkFrame(parent, fg_color="#1a1a2e", corner_radius=10)

    # Label squadra casa (sotto)
    ctk.CTkLabel(frame, text=f"{home_name} ({home_modulo})",
                 font=("Segoe UI", 11, "bold"), text_color=DOT_HOME).pack(pady=(6, 0))

    # Canvas
    canvas = tk.Canvas(frame, width=width, height=height,
                       bg=PITCH_GREEN, highlightthickness=0)
    canvas.pack(padx=8, pady=4)

    # Disegna campo
    draw_pitch(canvas, width, height)

    # Disegna squadre
    if home_titolari:
        draw_team(canvas, width, height, home_titolari, home_modulo, "home", DOT_HOME)
    if away_titolari:
        draw_team(canvas, width, height, away_titolari, away_modulo, "away", DOT_AWAY)

    # Label squadra ospite (sopra)
    ctk.CTkLabel(frame, text=f"{away_name} ({away_modulo})",
                 font=("Segoe UI", 11, "bold"), text_color=DOT_AWAY).pack(pady=(0, 6))

    return frame
