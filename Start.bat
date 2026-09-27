@echo off
setlocal
cd /d "%~dp0"

if exist "%~dp0HelldiversStratagemWheel.exe" (
  start "" "%~dp0HelldiversStratagemWheel.exe"
  exit /b 0
)

set "PYLAUNCH="
where py >nul 2>&1
if not errorlevel 1 (
  py -3 -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>&1
  if not errorlevel 1 set "PYLAUNCH=py -3"
)
if not defined PYLAUNCH (
  where python >nul 2>&1
  if not errorlevel 1 (
    python -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>&1
    if not errorlevel 1 set "PYLAUNCH=python"
  )
)
if not defined PYLAUNCH goto missing_python

if not exist ".venv\Scripts\python.exe" (
  echo Creating .venv
  %PYLAUNCH% -m venv .venv
  if errorlevel 1 goto venv_failed
)

echo Installing packages
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto pip_failed

".venv\Scripts\python.exe" -m stratagems
exit /b %ERRORLEVEL%

:missing_python
echo.
echo Python 3.11 or newer was not found.
echo Install it from https://www.python.org/downloads/ and check "Add python.exe to PATH".
echo.
exit /b 1

:venv_failed
echo Could not create .venv.
exit /b 1

:pip_failed
echo Could not install requirements.txt.
exit /b 1
