@echo off
rem Publish every set to GitHub Releases from a double-click. Builds each set's
rem surah zips, uploads them, deletes the zips (scratch stays under a few GB).
rem Safe to re-run: existing releases and assets are skipped.
setlocal
cd /d "%~dp0..\.."
where py >nul 2>nul && (set "PY=py -3") || (set "PY=python")
%PY% --version || (echo Python 3.10 or newer is required. & pause & exit /b 1)
gh auth status || (echo GitHub CLI is not logged in. Run: gh auth login & pause & exit /b 1)
echo.
%PY% -m maqra publish-github --build --cleanup %*
echo.
echo Publish pass finished with exit code %ERRORLEVEL%.
pause
