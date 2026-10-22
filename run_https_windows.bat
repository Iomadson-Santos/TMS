@echo off
setlocal
cd /d %~dp0

if not exist .venv\Scripts\python.exe (
  echo Ambiente virtual ausente. Execute setup_windows.bat primeiro.
  pause
  exit /b 1
)
if not exist certs\server.crt (
  echo Certificado ausente: certs\server.crt
  echo Consulte RASTREAMENTO.md para criar um certificado confiavel.
  pause
  exit /b 1
)
if not exist certs\server.key (
  echo Chave ausente: certs\server.key
  echo Consulte RASTREAMENTO.md para criar um certificado confiavel.
  pause
  exit /b 1
)

set "PYTHON_EXE=%CD%\.venv\Scripts\python.exe"
echo.
echo TMS com HTTPS na porta 8443.
echo No celular, abra: https://IP_DO_COMPUTADOR:8443/motorista
echo.
ipconfig | findstr /i "IPv4"
echo.

pushd backend
"%PYTHON_EXE%" -m app.scripts.update_database
if errorlevel 1 (
  popd
  pause
  exit /b 1
)
"%PYTHON_EXE%" -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8443 --ssl-certfile ..\certs\server.crt --ssl-keyfile ..\certs\server.key
popd
