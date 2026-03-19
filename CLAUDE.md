# Video Compressor

Offline video compression tool using ffmpeg. Two interfaces: GUI (gui_app.py) and CLI (video_compressor.py).

## Quick Actions for Agents

**User wants to compress a video:**
```bash
python3 video_compressor.py INPUT_FILE --preset telegram
```

**User wants to launch the GUI:**
```bash
python3 gui_app.py
```

**User wants to build a standalone .app:**
```bash
bash install.sh
```

**User wants to install dependencies only:**
```bash
bash setup.sh
```

## Architecture

```
video_compressor.py   — core logic (presets, ffmpeg commands, 1-pass/2-pass encoding)
gui_app.py            — tkinter GUI, imports from video_compressor.py
setup.sh              — installs dependencies (ffmpeg, python, tkinter) on macOS
build_app.sh          — builds .app via PyInstaller
install.sh            — setup + build + launch in one command
```

## Key Concepts

### Presets (defined in video_compressor.py → PRESETS dict)
- `archive` — CRF 22, slow, 192k audio. Best quality, largest files.
- `telegram` — CRF 28, slow, 96k audio, 1280px max width, 30fps. Optimized for Telegram.
- `web` — CRF 27, medium, 128k audio. Balanced.
- `mobile` — CRF 29, faster, 96k audio. Smallest files.

### Supported input formats
MP4, MOV, MKV, AVI, WEBM, M4V (defined in VIDEO_EXTENSIONS set)

### How compression works
- Default: single-pass CRF encoding (H.264 via libx264)
- With `--target-size-mb`: two-pass encoding to hit exact file size
- Output: always MP4 with H.264 video + AAC audio + faststart flag

### GUI (gui_app.py)
- Multi-file selection with status table (name, size, status per file)
- Sequential processing with per-file progress bar
- Preset selector with user-friendly Russian labels
- "Open folder" button after completion
- Bundled ffmpeg path support for PyInstaller .app builds

## Dependencies

- Python 3.10+
- ffmpeg and ffprobe in PATH
- tkinter (for GUI only)
- PyInstaller (for .app build only)

## Common Modifications

**Add a new preset:** Add entry to `PRESETS` dict in video_compressor.py, then add label/description to `PRESET_UI` and `PRESET_ORDER` in gui_app.py.

**Change supported formats:** Edit `VIDEO_EXTENSIONS` set in video_compressor.py.

**Add a new GUI feature:** gui_app.py uses threading for ffmpeg — communicate via `self.progress_queue` (queue.Queue). Never call tkinter from worker thread.
