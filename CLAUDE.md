# YT Downloader

macOS desktop app: a Flask server (`app.py`) wrapping yt-dlp, shown in a pywebview window.
The whole UI is one file, `templates/index.html` (vanilla HTML/CSS/JS, no build step).

## Commands
- Set up: `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt -r requirements-dev.txt`
- Run in an app window: `.venv/bin/python app.py`. Add `--browser` to use the web browser instead.
- Tests: `.venv/bin/python -m pytest -q tests`
- Build and install the `.app`: `./build_app.sh`. It replaces `/Applications/YT Downloader.app`, so ask before running it.

## Structure
- `app.py`: yt-dlp format presets, download jobs (background threads, in-memory `jobs` dict), JSON API under `/api/*`.
- `state` in `app.py` holds the current save folder and the pywebview window. It's `None` in `--browser` mode.
- The chosen save folder is saved to `~/Library/Application Support/YT Downloader/settings.json`. The default is `~/Downloads/YT Downloader`.

## Pitfalls
- The client never sends file system paths for the save folder. The server opens the native picker itself (`pick_folder`). Keep it that way: the server listens on localhost.
- Each job captures its folder when it starts. Changing the folder doesn't affect downloads already running.
- In tests, monkeypatch `pick_folder` and `SETTINGS_FILE`. Never open real dialogs or write to the real settings file.
- `build/`, `dist/` and `*.spec` are build output (gitignored). Don't edit them.
- Keep MP4 presets on H.264 + AAC (`COMPAT`) so files play in QuickTime.
