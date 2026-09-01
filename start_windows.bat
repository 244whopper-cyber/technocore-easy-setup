@echo off
setlocal
cd /d "%~dp0"

py -3.12 --version >nul 2>&1
if errorlevel 1 (
  echo Python 3.12 was not found. Install it from https://www.python.org/downloads/windows/
  echo Python 3.12 ga mitsukarimasen. python.org kara install shite kudasai.
  pause
  exit /b 1
)

py -3.12 -c "import tkinter" >nul 2>&1
if errorlevel 1 (
  echo This Python 3.12 does not include Tk. Install Python 3.12 from python.org.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\pythonw.exe" py -3.12 -m venv .venv
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r requirements.txt
if errorlevel 1 (
  pause
  exit /b 1
)
start "Technocore Easy Setup" ".venv\Scripts\pythonw.exe" app.py
