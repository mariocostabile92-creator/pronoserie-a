"""
routes/pronostici.py - Endpoint per calcolo pronostici
Calcola predizioni 1X2, O/U, Goal/NoGoal per tutte le leghe
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional

router = APIRouter(prefix="/api", tags=["pronostici"])

# Import funzioni dal modulo principale (saranno definite in api_server.py)
# Queste funzioni verranno importate dinamicamente quando il modulo principale le definisce
import sys
import os
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
sys.path.insert(0, _ROOT)

from api_auth import get_optional_user
# from database import ...  # Importate in api_server

# Note: _compute_pronostico, check_limit, LEAGUES verranno importate dal modulo principale

@router.get("/pronostico/{home}/{away}")
async def pronostico(home: str, away: str, user: Optional[dict] = Depends(get_optional_user)):
    """Calcola pronostico Serie A per una partita."""
    # Import late binding (la funzione sarà definita in api_server)
    from api_server import check_limit, _compute_pronostico
    check_limit(user)
    return _compute_pronostico("serie-a", home, away)

@router.get("/{league}/pronostico/{home}/{away}")
async def pronostico_league(league: str, home: str, away: str, user: Optional[dict] = Depends(get_optional_user)):
    """Calcola pronostico per qualsiasi campionato."""
    from api_server import check_limit, _compute_pronostico, LEAGUES
    if league not in LEAGUES:
        raise HTTPException(404, "Campionato non trovato")
    check_limit(user)
    return _compute_pronostico(league, home, away)
