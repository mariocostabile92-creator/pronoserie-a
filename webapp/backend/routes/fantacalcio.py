"""
routes/fantacalcio.py - Consigli fantacalcio per tutti i campionati supportati
Endpoint: /api/fantacalcio/consigli/{giornata},
          /api/{league}/fantacalcio/consigli/{giornata}
"""
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

router = APIRouter(prefix="/api", tags=["fantacalcio"])
limiter = Limiter(key_func=get_remote_address)


@router.get("/fantacalcio/consigli/{giornata}")
@limiter.limit("20/minute")
async def fantacalcio_consigli(giornata: int, request: Request):
    """Consigli fantacalcio Serie A per la giornata specificata."""
    from api_server import _fantacalcio_impl
    return _fantacalcio_impl("serie-a", giornata)


@router.get("/{league}/fantacalcio/consigli/{giornata}")
@limiter.limit("20/minute")
async def fantacalcio_consigli_league(league: str, giornata: int, request: Request):
    """Consigli fantacalcio per qualsiasi campionato supportato."""
    from api_server import FANTACALCIO_LEAGUES, _fantacalcio_impl
    if league not in FANTACALCIO_LEAGUES:
        raise HTTPException(404, "Campionato non supportato per il fantacalcio")
    return _fantacalcio_impl(league, giornata)
