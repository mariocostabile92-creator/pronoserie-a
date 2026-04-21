@echo off
REM =============================================================================
REM Script per pubblicare aggiornamenti OTA su EAS Update (canale production)
REM Uso: scripts\publish-update.bat "Descrizione dell'aggiornamento"
REM =============================================================================

REM Descrizione dell'aggiornamento (passata come argomento o default)
SET MESSAGGIO=%~1
IF "%MESSAGGIO%"=="" SET MESSAGGIO=Aggiornamento automatico

echo ======================================
echo   Pubblicazione aggiornamento OTA
echo   Canale: production
echo   Messaggio: %MESSAGGIO%
echo ======================================

REM Pubblica l'aggiornamento sul canale production
eas update --branch production --message "%MESSAGGIO%"

echo.
echo Aggiornamento pubblicato con successo!
echo Gli utenti riceveranno l'update al prossimo avvio dell'app.
