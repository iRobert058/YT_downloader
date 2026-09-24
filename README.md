<p align="center">
  <img src="assets/icon.png" width="128" alt="YT Downloader icon">
</p>

<h1 align="center">YT Downloader</h1>

<p align="center">A small macOS app for downloading YouTube videos and playlists as MP4 or MP3.</p>

> [!NOTE]
> **This project is vibecoded.** It was built by prompting an AI coding assistant, not written by hand.
> It works for me, but it hasn't been reviewed or tested thoroughly, so use it at your own risk.

## Features

- Paste a link, preview the video, and download it
- Video in best quality, 1080p, 720p or 480p (MP4, H.264 + AAC, plays in QuickTime)
- Audio-only MP3 (192 kbps) with cover art, title and artist tags
- Whole playlists at once
- Several downloads at the same time, with live progress
- Runs as a native macOS app window, and ffmpeg is bundled

## Requirements

- macOS (the `.app` build and the launcher are macOS-only; `python app.py --browser` should work elsewhere)
- Python 3.10 or newer

## Install

```bash
git clone https://github.com/<iRobert058>/YT_downloader.git
cd YT_downloader
./build_app.sh
```

This builds a standalone app (Python and ffmpeg included) and installs it as
`/Applications/YT Downloader.app`. Open it from Launchpad, Spotlight or the Dock.

YouTube changes often, and older yt-dlp versions eventually stop working.
When downloads start failing, run `./build_app.sh` again to rebuild with the latest yt-dlp.

### Run without building

- Double-click `Start YT Downloader.command`, or
- run `python app.py` after installing `requirements.txt` (add `--browser` to use your web browser instead of an app window).

## Usage

1. Paste a YouTube link and click **Look up**.
2. Pick a video quality and click **Download video**, or click **Download MP3** for audio only.
3. Files are saved to `~/Downloads/YT Downloader`.

## How it works

A small [Flask](https://flask.palletsprojects.com/) server runs the download API with
[yt-dlp](https://github.com/yt-dlp/yt-dlp). [pywebview](https://pywebview.flowrl.com/) shows the
interface in a native window, and [imageio-ffmpeg](https://github.com/imageio/imageio-ffmpeg) provides
ffmpeg for merging video and converting audio. [PyInstaller](https://pyinstaller.org/) packages it as a `.app`.

## Disclaimer

This tool is for personal use. Only download videos you have the right to download, and follow
YouTube's Terms of Service and your local copyright laws.

## License

[MIT](LICENSE)
