@echo off
setlocal
cd /d %~dp0

if not exist .venv\Scripts\python.exe (
  echo Ambiente virtual ausente. Execute setup_windows.bat primeiro.
  pause
  exit /b 1
)

set "PYTHON_EXE=%CD%\.venv\Scripts\python.exe"

echo.
echo ============================================================
echo TMS MOTORISTA - ACESSO PELA REDE LOCAL
echo ============================================================
echo 1. Mantenha o computador e o celular na mesma rede Wi-Fi.
echo 2. No celular, abra: http://IP_DO_COMPUTADOR:8000/motorista
echo 3. Use um dos enderecos IPv4 exibidos abaixo.
echo.
ipconfig | findstr /i "IPv4"
echo.
echo ATENCAO: navegadores de celular normalmente bloqueiam o GPS
echo em conexoes HTTP. A tela funciona, mas o rastreamento exige HTTPS.
echo Consulte o arquivo RASTREAMENTO.md para publicar com HTTPS.
echo ============================================================
echo.

pushd backend
"%PYTHON_EXE%" -m app.scripts.update_database
if errorlevel 1 (
  popd
  pause
  exit /b 1
)
start "" cmd /c "timeout /t 3 /nobreak >nul & start http://127.0.0.1:8000/motorista"
"%PYTHON_EXE%" -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
popd
