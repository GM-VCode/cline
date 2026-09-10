@echo off
chcp 65001 >nul
title Parar Stack LunarIA
echo Derrubando modelo, proxy e main.py...
taskkill /f /im llama-server.exe >nul 2>&1
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | Where-Object { $_.CommandLine -match 'main\.py|tools\\proxy\.py|tools/proxy\.py' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"
echo STACK PARADA.
pause
