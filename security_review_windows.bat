@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d %~dp0

if not exist .venv\Scripts\python.exe (
  echo Ambiente virtual ausente. Execute setup_windows.bat primeiro.
  pause
  exit /b 1
)

set "PYTHON_EXE=%CD%\.venv\Scripts\python.exe"
pushd backend

"%PYTHON_EXE%" -c "import pytest, ruff, bandit, pip_audit" >nul 2>nul
if errorlevel 1 (
  popd
  echo Ferramentas ausentes. Execute setup_security_tools_windows.bat primeiro.
  pause
  exit /b 1
)

echo [1/5] Compilando Python...
"%PYTHON_EXE%" -m compileall -q app tests alembic
if errorlevel 1 goto :error

echo [2/5] Executando testes...
set "PYTHONPATH=."
"%PYTHON_EXE%" -m pytest -q
if errorlevel 1 goto :error

echo [3/5] Executando Ruff...
"%PYTHON_EXE%" -m ruff check app tests alembic --select E9,F63,F7,F82
if errorlevel 1 goto :error

echo [4/5] Executando Bandit...
"%PYTHON_EXE%" -m bandit -q -ll -r app -x tests -s B105,B106,B107
if errorlevel 1 goto :error

echo [5/5] Auditando dependencias...
"%PYTHON_EXE%" -m pip_audit -r requirements.txt
if errorlevel 1 goto :error

popd
where node >nul 2>nul
if errorlevel 1 (
  echo [AVISO] Node.js ausente; a sintaxe JavaScript nao foi verificada.
) else (
  echo Verificando JavaScript...
  for %%F in (frontend\assets\js\*.js) do (
    node --check "%%F"
    if errorlevel 1 goto :js_error
  )
)

echo.
echo Revisao automatizada concluida sem falhas.
pause
exit /b 0

:error
popd
echo.
echo Revisao interrompida por uma falha. Leia a mensagem acima.
pause
exit /b 1

:js_error
echo.
echo Revisao interrompida por erro de JavaScript.
pause
exit /b 1
