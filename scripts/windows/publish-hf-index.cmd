@echo off
rem Publish the registry/manifests/timings dataset and the ayah images dataset.
setlocal
cd /d "%~dp0..\.."
where py >nul 2>nul && (set "PY=py -3") || (set "PY=python")
%PY% -c "from huggingface_hub import whoami; print('Hugging Face account:', whoami()['name'])" || (echo Not logged in to Hugging Face. Run: hf auth login & pause & exit /b 1)
echo.
%PY% -m maqra publish-hf --index --images %*
echo.
echo Publish pass finished with exit code %ERRORLEVEL%.
pause
