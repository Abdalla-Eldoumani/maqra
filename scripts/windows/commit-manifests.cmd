@echo off
rem Commit every new or changed manifest and timing file, one file per commit. Does not push.
setlocal
cd /d "%~dp0..\.."
where py >nul 2>nul && (set "PY=py -3") || (set "PY=python")
%PY% tools\commit_manifests.py
echo.
git log --oneline -5
pause
