@echo off
setlocal
cd /d %~dp0

if not exist .venv\Scripts\python.exe (
  where py >nul 2>nul
  if not errorlevel 1 (
    py -3 -m venv .venv
  ) else (
    where python >nul 2>nul
    if errorlevel 1 (
      echo Python nao encontrado. Instale o Python 3.11 ou superior.
      pause
      exit /b 1
    )
    python -m venv .venv
  )
)

if not exist .venv\Scripts\python.exe (
  echo Nao foi possivel criar o ambiente virtual.
  pause
  exit /b 1
)

set "PYTHON_EXE=%CD%\.venv\Scripts\python.exe"
"%PYTHON_EXE%" -m pip install --upgrade pip
if errorlevel 1 goto :error
"%PYTHON_EXE%" -m pip install -r backend\requirements.txt
if errorlevel 1 goto :error

pushd backend
if not exist .env copy .env.example .env >nul
"%PYTHON_EXE%" -m app.scripts.update_database
if errorlevel 1 (
  popd
  goto :error
)
"%PYTHON_EXE%" -m app.scripts.seed
if errorlevel 1 (
  popd
  goto :error
)
popd

echo.
echo Instalacao concluida.
echo Execute run_windows.bat para iniciar o TMS.
pause
exit /b 0

:error
echo.
echo A instalacao nao foi concluida. Corrija o erro exibido acima e tente novamente.
pause
exit /b 1
