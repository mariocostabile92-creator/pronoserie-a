#!/bin/bash
# =============================================================================
# Script per pubblicare aggiornamenti OTA su EAS Update (canale production)
# Uso: ./scripts/publish-update.sh "Descrizione dell'aggiornamento"
# =============================================================================

# Descrizione dell'aggiornamento (passata come argomento o default)
MESSAGGIO="${1:-Aggiornamento automatico}"

echo "======================================"
echo "  Pubblicazione aggiornamento OTA"
echo "  Canale: production"
echo "  Messaggio: $MESSAGGIO"
echo "======================================"

# Pubblica l'aggiornamento sul canale production
eas update --branch production --message "$MESSAGGIO"

echo ""
echo "Aggiornamento pubblicato con successo!"
echo "Gli utenti riceveranno l'update al prossimo avvio dell'app."
