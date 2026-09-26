@echo off
rem Rigenera solo il modello 3D: serve dopo aver aggiunto o tolto texture in texture\<formato>\
cd /d "%~dp0"
python casa_3d.py
if errorlevel 1 (echo. & echo ERRORE in casa_3d.py) else (echo. & echo Fatto: ricarica casa_3d.html nel browser)
pause
