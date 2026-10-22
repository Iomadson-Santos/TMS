@echo off
setlocal
cd /d %~dp0

if not exist .venv\Scripts\python.exe (
  echo Ambiente virtual ausente. Execute setup_windows.bat primeiro.
  pause
  exit /b 1
)

set "PYTHON_EXE=%CD%\.venv\Scripts\python.exe"
if "%TMS_FORWARDED_ALLOW_IPS%"=="" set "TMS_FORWARDED_ALLOW_IPS=127.0.0.1"

pushd backend
"%PYTHON_EXE%" -m app.scripts.security_check --config-only
if errorlevel 1 goto :error

"%PYTHON_EXE%" -m app.scripts.update_database
if errorlevel 1 goto :error

"%PYTHON_EXE%" -m app.scripts.security_check
if errorlevel 1 goto :error

echo.
echo TMS aprovado. Iniciando somente em 127.0.0.1:8000 para uso atras do proxy HTTPS.
"%PYTHON_EXE%" -m uvicorn app.main:app ^
  --host 127.0.0.1 ^
  --port 8000 ^
  --workers 1 ^
  --proxy-headers ^
  --forwarded-allow-ips="%TMS_FORWARDED_ALLOW_IPS%" ^
  --no-server-header ^
  --timeout-keep-alive 5 ^
  --limit-concurrency 500
popd
exit /b 0

:error
popd
echo.
echo Inicializacao de producao bloqueada. Corrija os erros exibidos acima.
pause
exit /b 1
