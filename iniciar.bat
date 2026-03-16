@echo off
title TMS - Servidor
color 0A
echo.
echo  ========================================
echo   TMS - Sistema de Gestao de Frota
echo  ========================================
echo.
echo  Iniciando servidor...
echo.

cd /d "%~dp0"
call venv\Scripts\activate.bat
cd backend
uvicorn main:app --reload

pause