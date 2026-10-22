@echo off
setlocal
cd /d %~dp0

if not exist .venv\Scripts\python.exe (
  echo Ambiente virtual ausente. Execute setup_windows.bat primeiro.
  pause
  exit /b 1
)

pushd backend
..\.venv\Scripts\python.exe -m app.scripts.backup_database
set "RESULT=%ERRORLEVEL%"
popd

if not "%RESULT%"=="0" (
  echo.
  echo O backup nao foi concluido.
  pause
  exit /b %RESULT%
)

echo.
echo Backup concluido.
pause
