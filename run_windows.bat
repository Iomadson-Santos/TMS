@echo off
setlocal
cd /d %~dp0

if not exist .venv\Scripts\python.exe (
  echo Ambiente virtual ausente. Execute setup_windows.bat primeiro.
  pause
  exit /b 1
)

set "PYTHON_EXE=%CD%\.venv\Scripts\python.exe"
pushd backend
"%PYTHON_EXE%" -m app.scripts.update_database
if errorlevel 1 (
  popd
  pause
  exit /b 1
)
start "" cmd /c "timeout /t 3 /nobreak >nul & start http://127.0.0.1:8000"
"%PYTHON_EXE%" -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
popd
