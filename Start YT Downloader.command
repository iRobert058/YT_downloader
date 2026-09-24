#!/bin/bash
# Double-click this file in Finder to launch the downloader.
cd "$(dirname "$0")"

if [ ! -d .venv ]; then
  echo "First run: setting up (this takes a minute)..."
  python3 -m venv .venv || exit 1
fi
source .venv/bin/activate
[ -x .venv/bin/pip ] || python -m ensurepip >/dev/null
# Keep yt-dlp current - YouTube changes often and old versions break.
python -m pip install -q --upgrade -r requirements.txt
python app.py
