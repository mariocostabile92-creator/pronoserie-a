"""
player_photos.py
Scarica e cache le foto dei calciatori da fonti pubbliche.
Usa la API di ui-avatars.com come fallback per generare avatar con iniziali.
"""

import os
import hashlib
import urllib.request
from PIL import Image, ImageTk, ImageDraw
import io

CACHE_DIR = os.path.join(os.path.dirname(__file__), "photo_cache")
PHOTO_SIZE = 40

# Cache in memoria per evitare ricaricamenti
_photo_cache = {}


def _ensure_cache_dir():
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR, exist_ok=True)


def _get_cache_path(nome: str) -> str:
    _ensure_cache_dir()
    h = hashlib.md5(nome.lower().encode()).hexdigest()[:12]
    return os.path.join(CACHE_DIR, f"{h}.png")


def _download_photo(nome: str) -> str | None:
    """Prova a scaricare la foto del calciatore. Ritorna il path locale o None."""
    cache_path = _get_cache_path(nome)
    if os.path.exists(cache_path):
        return cache_path

    # Usa ui-avatars.com per generare avatar con iniziali
    # Gratuito, nessuna API key necessaria, sempre funzionante
    parts = nome.split()
    if len(parts) >= 2:
        initials = parts[0][0] + parts[-1][0]
    else:
        initials = nome[:2]

    url = (
        f"https://ui-avatars.com/api/?name={initials}"
        f"&size={PHOTO_SIZE * 2}&background=0f3460&color=ecf0f1"
        f"&bold=true&format=png&rounded=true"
    )

    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0"
        })
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = resp.read()
            with open(cache_path, "wb") as f:
                f.write(data)
            return cache_path
    except Exception:
        return None


def _create_initials_image(nome: str) -> Image.Image:
    """Crea un avatar con iniziali localmente (senza rete)."""
    img = Image.new("RGBA", (PHOTO_SIZE, PHOTO_SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Cerchio sfondo
    draw.ellipse([0, 0, PHOTO_SIZE - 1, PHOTO_SIZE - 1], fill="#0f3460")

    # Iniziali
    parts = nome.split()
    if len(parts) >= 2:
        initials = (parts[0][0] + parts[-1][0]).upper()
    else:
        initials = nome[:2].upper()

    # Testo centrato
    try:
        bbox = draw.textbbox((0, 0), initials)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
    except Exception:
        tw, th = 16, 16

    x = (PHOTO_SIZE - tw) / 2
    y = (PHOTO_SIZE - th) / 2 - 2
    draw.text((x, y), initials, fill="#ecf0f1")

    return img


def get_player_photo_tk(nome: str, master=None) -> ImageTk.PhotoImage | None:
    """
    Ritorna un ImageTk.PhotoImage per il giocatore.
    Usa cache in memoria per performance.
    """
    key = nome.lower()
    if key in _photo_cache:
        return _photo_cache[key]

    try:
        # Prova a scaricare
        path = _download_photo(nome)
        if path and os.path.exists(path):
            img = Image.open(path)
            img = img.resize((PHOTO_SIZE, PHOTO_SIZE), Image.LANCZOS)
        else:
            img = _create_initials_image(nome)

        photo = ImageTk.PhotoImage(img, master=master)
        _photo_cache[key] = photo
        return photo
    except Exception:
        # Fallback: crea avatar locale
        try:
            img = _create_initials_image(nome)
            photo = ImageTk.PhotoImage(img, master=master)
            _photo_cache[key] = photo
            return photo
        except Exception:
            return None


def preload_photos(nomi: list, callback=None):
    """Pre-scarica le foto in background."""
    import threading

    def _worker():
        for nome in nomi:
            _download_photo(nome)
        if callback:
            callback()

    threading.Thread(target=_worker, daemon=True).start()
