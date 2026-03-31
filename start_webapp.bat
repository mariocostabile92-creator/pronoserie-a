@echo off
echo ========================================
echo  AVVIO WEB APP PRONOSTICI SERIE A
echo ========================================
echo.
echo Avvio backend API su http://127.0.0.1:8000 ...
echo Apri il browser su: http://127.0.0.1:8000/app
echo.
echo Per fermare: premi Ctrl+C
echo ========================================

cd /d "%~dp0webapp\backend"
python -m uvicorn api_server:app --host 127.0.0.1 --port 8000
