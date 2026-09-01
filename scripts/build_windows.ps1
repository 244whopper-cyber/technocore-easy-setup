$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

py -3.12 -c "import tkinter"
py -3.12 -m venv .build-venv
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
