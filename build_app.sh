#!/bin/bash
# Builds "YT Downloader.app" into ./dist. Re-run it to pick up the latest yt-dlp.
set -e
cd "$(dirname "$0")"

[ -d .venv ] || python3 -m venv .venv
source .venv/bin/activate
[ -x .venv/bin/pip ] || python -m ensurepip >/dev/null
python -m pip install -q --upgrade -r requirements.txt pyinstaller

pyinstaller --noconfirm --clean --windowed \
  --name "YT Downloader" \
  --icon assets/icon.icns \
  --osx-bundle-identifier com.robertkarzijn.ytdownloader \
  --add-data "templates:templates" \
  --collect-all imageio_ffmpeg \
  --collect-submodules webview \
  app.py

# Install into /Applications, replacing any older copy (quit it first if running).
osascript -e 'quit app "YT Downloader"' 2>/dev/null || true
rm -rf "/Applications/YT Downloader.app"
cp -R "dist/YT Downloader.app" /Applications/

echo
echo "Installed: /Applications/YT Downloader.app"
