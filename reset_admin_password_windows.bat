@echo off
setlocal
cd /d "%~dp0"

echo ============================================================
echo TMS Ciranda - Reset seguro da senha do administrador
echo ============================================================
echo.
echo Antes de continuar, pare o servidor TMS com CTRL+C.
echo A nova senha nao sera exibida nem salva no historico.
echo.

if not exist ".venv\Scripts\python.exe" (
  echo Ambiente virtual ausente.
  echo Abra este arquivo dentro da pasta principal do TMS.
  pause
  exit /b 1
)

if not exist "backend\app\scripts\reset_admin_password.py" (
  echo Script de reset ausente. Reextraia a atualizacao na pasta do TMS.
  pause
  exit /b 1
)

pushd backend
"..\.venv\Scripts\python.exe" -m app.scripts.reset_admin_password
set "RESULT=%ERRORLEVEL%"
popd

echo.
if not "%RESULT%"=="0" (
  echo O reset nao foi concluido. Nenhuma alteracao parcial deve ser utilizada.
  pause
  exit /b %RESULT%
)

echo Reset concluido.
echo Agora execute run_windows.bat e entre com a nova senha.
pause
exit /b 0
