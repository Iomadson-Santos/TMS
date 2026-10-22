@echo off
setlocal
cd /d %~dp0

if not exist .venv\Scripts\python.exe (
  echo Ambiente virtual ausente. Execute setup_windows.bat primeiro.
  pause
  exit /b 1
)

cd backend
..\.venv\Scripts\python.exe -m app.scripts.upgrade_env_security
if errorlevel 1 (
  echo.
  echo Falha ao atualizar as configuracoes de seguranca.
  pause
  exit /b 1
)

..\.venv\Scripts\python.exe -m app.scripts.update_database
if errorlevel 1 (
  echo.
  echo Falha ao atualizar o banco. Leia a mensagem acima.
  pause
  exit /b 1
)

echo.
echo Atualizacao concluida com sucesso.
pause
