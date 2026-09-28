@echo off
rem Doble clic para arrancar el piloto. Equivale a: py -3.12 iniciar.py
where py >nul 2>nul
if %errorlevel%==0 (
  py -3.12 "%~dp0iniciar.py" %*
) else (
  python "%~dp0iniciar.py" %*
)
if errorlevel 1 pause
