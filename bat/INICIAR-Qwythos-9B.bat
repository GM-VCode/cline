@echo off
chcp 65001 >nul
title LunarIA (Qwythos-9B) - Servidor para o Cline
echo ============================================================
echo   LunarIA / Qwythos-9B  (llama.cpp Vulkan - RX 6800)
echo   Config: edite o arquivo .env nesta pasta
echo ============================================================
rem Usa o Python do venv se existir; senao usa o py -3 do sistema
rem (%~dp0 e a pasta bat\; o projeto esta na pasta pai: ..\)
if exist "%~dp0..\.venv\Scripts\python.exe" (
  "%~dp0..\.venv\Scripts\python.exe" "%~dp0..\main.py"
) else (
  py -3 "%~dp0..\main.py"
)
pause
