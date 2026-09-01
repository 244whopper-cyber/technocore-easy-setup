#!/bin/zsh
set -eu
cd -- "${0:A:h}/.."

if ! command -v python3.12 >/dev/null 2>&1; then
  print "Python 3.12 from python.org is required."
  exit 1
fi

python3.12 -c 'import tkinter'

python3.12 -m venv .build-venv
.build-venv/bin/python -m pip install --upgrade pip
.build-venv/bin/python -m pip install -r requirements-dev.txt
mkdir -p .pyinstaller-config
PYINSTALLER_CONFIG_DIR="$PWD/.pyinstaller-config" \
  .build-venv/bin/pyinstaller --noconfirm --clean macos_app.spec

app_target="$PWD/dist/TechnocoreEasySetup.app"
if [[ -e "$app_target" ]]; then
  previous_target="$PWD/dist/TechnocoreEasySetup.previous.$(date +%Y%m%d%H%M%S).app"
  mv -- "$app_target" "$previous_target"
fi
mkdir -p "$app_target/Contents/MacOS" "$app_target/Contents/Resources"
install -m 0755 packaging/macos/TechnocoreEasySetup \
  "$app_target/Contents/MacOS/TechnocoreEasySetup"
install -m 0644 packaging/macos/Info.plist "$app_target/Contents/Info.plist"
ditto "$PWD/dist/TechnocoreEasySetupRuntime" \
  "$app_target/Contents/Resources/runtime"
codesign --force --deep --sign - "$app_target"
codesign --verify --deep --strict "$app_target"

print "Built: dist/TechnocoreEasySetup.app"
print "This local build is unsigned. Sign and notarize before public distribution."
