@echo off
rem Start the full Maqra mirror from a double-click. Safe to re-run: it resumes.
setlocal
cd /d "%~dp0..\.."
where py >nul 2>nul && (set "PY=py -3") || (set "PY=python")
%PY% --version || (echo Python 3.10 or newer is required. & pause & exit /b 1)
echo.
echo Maqra mirror starting in %CD%
echo Data root: %CD%\data   (logs under data\state\logs)
echo Press Ctrl+C to stop; run this file again to resume.
echo.
%PY% -m maqra mirror %*
echo.
echo Mirror pass finished with exit code %ERRORLEVEL%.
%PY% -m maqra status
pause
