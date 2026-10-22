@echo off
setlocal
cd /d %~dp0

if not exist .venv\Scripts\python.exe (
  echo Ambiente virtual ausente. Execute setup_windows.bat primeiro.
  pause
  exit /b 1
)

set "PYTHON_EXE=%CD%\.venv\Scripts\python.exe"
"%PYTHON_EXE%" -m pip install -r backend\requirements-dev.txt
if errorlevel 1 (
  echo.
  echo Nao foi possivel instalar as ferramentas de revisao.
  pause
  exit /b 1
)

echo.
echo Ferramentas de revisao instaladas.
pause
