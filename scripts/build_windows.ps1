$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

python -c "import sys; assert sys.version_info[:2] == (3, 12); import tkinter"
python -m venv .build-venv
& .\.build-venv\Scripts\python.exe -m pip install --upgrade pip
& .\.build-venv\Scripts\python.exe -m pip install -r requirements-dev.txt
& .\.build-venv\Scripts\pyinstaller.exe `
  --noconfirm `
  --clean `
  --windowed `
  --name "Technocore Easy Setup" `
  app.py

Write-Host "Built: dist\Technocore Easy Setup\Technocore Easy Setup.exe"
Write-Host "This local build is unsigned. Authenticode-sign it before public distribution."
