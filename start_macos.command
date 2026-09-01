#!/bin/zsh
set -eu
cd -- "${0:A:h}"

if ! command -v python3.12 >/dev/null 2>&1; then
  print "Python 3.12 was not found. Install it from https://www.python.org/downloads/macos/ and try again."
  print "Python 3.12 が見つかりません。python.org からインストールして、もう一度実行してください。"
  read -k 1 "?Press any key to close / キーを押して閉じる"
  exit 1
fi

if ! python3.12 -c 'import tkinter' >/dev/null 2>&1; then
  print "This Python 3.12 does not include Tk. Install Python 3.12 from python.org."
  print "このPythonにはGUI用のTkがありません。python.org版Python 3.12をインストールしてください。"
  read -k 1 "?Press any key to close / キーを押して閉じる"
  exit 1
fi

if [[ ! -x .venv/bin/python ]]; then
  python3.12 -m venv .venv
fi

.venv/bin/python -m pip install --disable-pip-version-check -r requirements.txt
.venv/bin/python app.py
