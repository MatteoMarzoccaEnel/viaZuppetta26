@echo off
rem Rigenera tutti gli elaborati: tavole e piantine, modello 3D, computi, report pdf.
rem Serve dopo aver cambiato misure o pose in casa_pianta.py. Chiudere prima i pdf aperti.
cd /d "%~dp0"
set ERRORI=
for %%s in (casa_pianta casa_3d computo battiscopa bagno_rivestimento bagno_pianta muri_nuovi muro_disimpegno muro_ingresso report) do (
    echo === %%s
    python %%s.py > nul
    if errorlevel 1 (
        echo     ERRORE: rilanciare "python %%s.py" per vedere il dettaglio
        set ERRORI=1
    )
)
echo.
if defined ERRORI (echo Finito con errori) else (echo Fatto: tutto rigenerato)
pause
