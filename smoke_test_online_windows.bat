@echo off
setlocal EnableExtensions
cd /d %~dp0

set "PYTHON_EXE=.venv\Scripts\python.exe"
if not exist "%PYTHON_EXE%" set "PYTHON_EXE=py"

set /p "TMS_URL=Informe a URL HTTPS do TMS: "
if "%TMS_URL%"=="" (
  echo URL obrigatoria.
  pause
  exit /b 1
)

"%PYTHON_EXE%" smoke_test_online.py --url "%TMS_URL%" --login
set "EXIT_CODE=%ERRORLEVEL%"

echo.
if "%EXIT_CODE%"=="0" (
  echo Teste online concluido com sucesso.
) else (
  echo O teste encontrou uma falha. Revise a mensagem acima.
)
pause
exit /b %EXIT_CODE%
