"""YouTube Downloader - a small desktop app built on yt-dlp.

Run `python app.py` to open the app window (or `python app.py --browser`
to use your web browser instead). Build a macOS .app with ./build_app.sh.
"""

import os
import socket
import subprocess
import sys
import threading
import uuid
import webbrowser
from pathlib import Path

import imageio_ffmpeg
import yt_dlp
from flask import Flask, jsonify, render_template, request

# In a windowed .app there is no console; yt-dlp still expects streams to exist.
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

HOST = "127.0.0.1"
# Bundled by PyInstaller, resources live in sys._MEIPASS instead of next to this file.
BASE_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
DOWNLOAD_DIR = Path.home() / "Downloads" / "YT Downloader"
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

# Prefer H.264 + AAC so MP4s play in QuickTime/Photos/iMovie (AV1/VP9 + Opus often don't).
COMPAT = ["vcodec:h264", "res", "acodec:m4a"]

# Format presets shown in the UI: key -> (label, yt-dlp options)
PRESETS = {
    "best": ("Best quality (MP4)", {
        "format": "bv*+ba/b",
        "merge_output_format": "mp4",
        "format_sort": COMPAT,
    }),
    "1080": ("1080p (MP4)", {
        "format": "bv*[height<=1080]+ba/b[height<=1080]",
        "merge_output_format": "mp4",
        "format_sort": COMPAT,
    }),
    "720": ("720p (MP4)", {
        "format": "bv*[height<=720]+ba/b[height<=720]",
        "merge_output_format": "mp4",
        "format_sort": COMPAT,
    }),
    "480": ("480p (MP4)", {
        "format": "bv*[height<=480]+ba/b[height<=480]",
        "merge_output_format": "mp4",
        "format_sort": COMPAT,
    }),
    "mp3": ("Audio only (MP3)", {
        "format": "ba/b",
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }, {
            "key": "FFmpegMetadata",  # title / artist tags
        }, {
            "key": "FFmpegThumbnailsConvertor",  # YouTube serves webp; MP3 covers need jpg
            "format": "jpg",
            "when": "before_dl",
        }, {
            "key": "EmbedThumbnail",  # cover art shown in Music / Finder
        }],
        "writethumbnail": True,
    }),
}

app = Flask(__name__, template_folder=str(BASE_DIR / "templates"))
jobs = {}  # job_id -> status dict
jobs_lock = threading.Lock()


def update_job(job_id, **fields):
    with jobs_lock:
        jobs[job_id].update(fields)


def run_download(job_id, url, preset, playlist):
    def on_progress(d):
        if d["status"] == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            done = d.get("downloaded_bytes") or 0
            info = d.get("info_dict") or {}
            update_job(
                job_id,
                state="downloading",
                percent=round(done / total * 100, 1) if total else None,
                speed=d.get("_speed_str", "").strip(),
                eta=d.get("_eta_str", "").strip(),
                title=info.get("title", jobs[job_id]["title"]),
                item=info.get("playlist_index"),
                items=info.get("n_entries"),
            )
        elif d["status"] == "finished":
            update_job(job_id, state="processing", percent=100)

    def on_postprocess(d):
        if d["status"] == "finished":
            path = d.get("info_dict", {}).get("filepath")
            if path:
                update_job(job_id, file=path)

    opts = {
        **PRESETS[preset][1],
        "outtmpl": str(DOWNLOAD_DIR / "%(title)s [%(id)s].%(ext)s"),
        "ffmpeg_location": FFMPEG,
        "noplaylist": not playlist,
        "progress_hooks": [on_progress],
        "postprocessor_hooks": [on_postprocess],
        "quiet": True,
        "no_warnings": True,
    }
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])
        update_job(job_id, state="done", percent=100)
    except Exception as e:  # yt-dlp raises many error types; surface them all
        msg = str(e).replace("ERROR: ", "")
        update_job(job_id, state="error", error=msg)


@app.route("/")
def index():
    presets = [(k, v[0]) for k, v in PRESETS.items() if k != "mp3"]  # MP3 has its own button
    return render_template("index.html", presets=presets, folder=str(DOWNLOAD_DIR))


@app.post("/api/info")
def info():
    url = (request.json or {}).get("url", "").strip()
    if not url:
        return jsonify(error="Please paste a link."), 400
    try:
        opts = {"quiet": True, "no_warnings": True, "extract_flat": "in_playlist"}
        with yt_dlp.YoutubeDL(opts) as ydl:
            data = ydl.extract_info(url, download=False)
    except Exception as e:
        return jsonify(error=str(e).replace("ERROR: ", "")), 400
    is_playlist = data.get("_type") == "playlist"
    return jsonify(
        title=data.get("title"),
        uploader=data.get("uploader") or data.get("channel"),
        duration=data.get("duration_string"),
        thumbnail=data.get("thumbnail") or (data.get("thumbnails") or [{}])[-1].get("url"),
        playlist=is_playlist,
        count=len(data.get("entries") or []) if is_playlist else None,
    )


@app.post("/api/download")
def download():
    body = request.json or {}
    url = body.get("url", "").strip()
    preset = body.get("preset", "best")
    if not url or preset not in PRESETS:
        return jsonify(error="Invalid request."), 400
    job_id = uuid.uuid4().hex[:8]
    with jobs_lock:
        jobs[job_id] = {"state": "starting", "percent": 0, "title": body.get("title") or url}
    threading.Thread(
        target=run_download,
        args=(job_id, url, preset, bool(body.get("playlist"))),
        daemon=True,
    ).start()
    return jsonify(id=job_id)


@app.get("/api/jobs")
def list_jobs():
    with jobs_lock:
        return jsonify({k: dict(v) for k, v in jobs.items()})


@app.post("/api/reveal")
def reveal():
    """Open the downloads folder (or highlight a file) in Finder/Explorer."""
    path = (request.json or {}).get("file")
    target = Path(path) if path and Path(path).exists() else DOWNLOAD_DIR
    if sys.platform == "darwin":
        cmd = ["open", "-R", str(target)] if target.is_file() else ["open", str(target)]
    elif sys.platform == "win32":
        cmd = ["explorer", f"/select,{target}"] if target.is_file() else ["explorer", str(target)]
    else:
        cmd = ["xdg-open", str(target.parent if target.is_file() else target)]
    subprocess.Popen(cmd)
    return jsonify(ok=True)


def free_port():
    with socket.socket() as s:
        s.bind((HOST, 0))
        return s.getsockname()[1]


def main():
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    port = free_port()
    url = f"http://{HOST}:{port}"

    if "--browser" in sys.argv:
        print(f"YouTube Downloader running at {url}  (Ctrl+C to quit)")
        threading.Timer(1.0, webbrowser.open, args=(url,)).start()
        app.run(host=HOST, port=port, debug=False)
        return

    import webview

    threading.Thread(
        target=app.run, kwargs={"host": HOST, "port": port, "debug": False}, daemon=True
    ).start()
    webview.create_window("YT Downloader", url, width=760, height=820, min_size=(420, 500))
    webview.start()  # blocks until the window is closed; the server thread dies with us


if __name__ == "__main__":
    main()
