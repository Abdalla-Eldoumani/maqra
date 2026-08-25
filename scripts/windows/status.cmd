@echo off
rem Show how far the mirror has got.
setlocal
cd /d "%~dp0..\.."
where py >nul 2>nul && (set "PY=py -3") || (set "PY=python")
%PY% -m maqra status
%PY% -m maqra list
pause
