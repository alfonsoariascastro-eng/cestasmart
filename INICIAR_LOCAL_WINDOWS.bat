@echo off
setlocal
cd /d "%~dp0"
set "PY="
where py >nul 2>nul && set "PY=py"
if not defined PY where python >nul 2>nul && set "PY=python"
if not defined PY (echo ERROR: Python no disponible.&pause&exit /b 1)
%PY% -m pip install -r requirements.txt
if exist "%USERPROFILE%\go\bin\grocery.exe" set "PATH=%PATH%;%USERPROFILE%\go\bin"
set PORT=5061
%PY% app.py
pause
