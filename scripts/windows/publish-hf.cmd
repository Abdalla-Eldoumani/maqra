@echo off
rem Upload every set to Hugging Face (one dataset per set) from a double-click.
rem Safe to re-run: upload_large_folder resumes per file.
setlocal
cd /d "%~dp0..\.."
where py >nul 2>nul && (set "PY=py -3") || (set "PY=python")
%PY% --version || (echo Python 3.10 or newer is required. & pause & exit /b 1)
%PY% -c "import huggingface_hub" 2>nul || %PY% -m pip install huggingface_hub
%PY% -c "from huggingface_hub import whoami; print('Hugging Face account:', whoami()['name'])" || (echo Not logged in to Hugging Face. Run: hf auth login & pause & exit /b 1)
echo.
%PY% -m maqra publish-hf %*
echo.
echo Publish pass finished with exit code %ERRORLEVEL%.
pause
