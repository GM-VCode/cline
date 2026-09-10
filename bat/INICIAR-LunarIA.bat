@echo off
chcp 65001 >nul
title LunarIA Stack Completa (modelo + proxy)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0INICIAR-STACK-COMPLETA.ps1"
