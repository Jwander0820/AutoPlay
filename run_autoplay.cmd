@echo off
setlocal

set "PROJECT_DIR=%~dp0"
set "PYTHON_EXE=%AUTOPLAY_PYTHON%"

if "%PYTHON_EXE%"=="" set "PYTHON_EXE=D:\venv\AutoPlay\Scripts\python.exe"
if not exist "%PYTHON_EXE%" set "PYTHON_EXE=python"

cd /d "%PROJECT_DIR%"
"%PYTHON_EXE%" "%PROJECT_DIR%run_autoplay.py"

if errorlevel 1 (
    echo.
    echo AutoPlay launcher exited with an error.
    echo Check that PyCharm/CMD is using the intended venv Python.
    echo Expected example: D:\venv\AutoPlay\Scripts\python.exe
    pause
)
