@echo off
rem Re-hash every mirrored file against the committed manifests.
setlocal
cd /d "%~dp0..\.."
where py >nul 2>nul && (set "PY=py -3") || (set "PY=python")
%PY% -m maqra verify %*
echo.
echo Verify finished with exit code %ERRORLEVEL%.
pause
