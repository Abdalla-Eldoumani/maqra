@echo off
rem Fetch the timings, ayah images, site files, and tool sources.
setlocal
cd /d "%~dp0..\.."
where py >nul 2>nul && (set "PY=py -3") || (set "PY=python")
%PY% -m maqra extras %*
echo.
echo Extras finished with exit code %ERRORLEVEL%.
pause
