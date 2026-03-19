# Video Compressor — Compress Video Without Quality Loss

Free offline video compression tool. Works locally on your computer — no files are uploaded anywhere.

**Supported formats:** MP4, MOV, MKV, AVI, WEBM, M4V

---

## Quick Start (2 steps)

### 1. Install

```bash
git clone https://github.com/aglyamodinar/video-compressor.git
cd video-compressor
bash setup.sh
```

The script automatically installs all dependencies (ffmpeg, Python, tkinter).

### 2. Run

**GUI (for everyone):**

```bash
python3 gui_app.py
```

**Command line (advanced):**

```bash
python3 video_compressor.py video.mp4
```

---

## Compression Modes

| Mode | Use case | File size |
|------|----------|-----------|
| **No quality loss** | Archiving, quality matters most | Large |
| **For Telegram** | Telegram-ready (1280px, 30fps) | Medium |
| **For web** | YouTube, social media, websites | Medium |
| **Maximum compression** | Email, saving disk space | Small |

## GUI Features

- Add one or multiple video files
- Choose compression mode
- Click "Compress" and track progress for each file
- Open the output folder with one click

## CLI Examples

```bash
# Single file
python3 video_compressor.py input.mp4

# For Telegram
python3 video_compressor.py input.mp4 --preset telegram

# Compress all videos in a folder
python3 video_compressor.py ./videos -o ./compressed

# Target file size (e.g. 40 MB)
python3 video_compressor.py input.mp4 --preset telegram --target-size-mb 40

# Custom settings
python3 video_compressor.py input.mp4 --crf 28 --speed fast --audio-bitrate 96k --scale 1280 --fps 30
```

## Build standalone .app (macOS)

```bash
pip3 install pyinstaller
bash build_app.sh
```

The `VideoCompressor.app` will appear in `dist/`.

## Requirements

- macOS / Linux / Windows
- Python 3.10+
- ffmpeg

On macOS everything is installed automatically via `setup.sh`.

---

# Русская версия

## Быстрый старт (2 шага)

### 1. Установка

```bash
git clone https://github.com/aglyamodinar/video-compressor.git
cd video-compressor
bash setup.sh
```

Скрипт автоматически установит все зависимости (ffmpeg, Python, tkinter).

### 2. Запуск

**С графическим интерфейсом (для всех):**

```bash
python3 gui_app.py
```

**Из командной строки (для продвинутых):**

```bash
python3 video_compressor.py video.mp4
```

## Режимы сжатия

| Режим | Для чего | Размер файла |
|-------|----------|-------------|
| **Без потери качества** | Архивация, когда важно качество | Крупный |
| **Для Telegram** | Отправка в Telegram (1280px, 30fps) | Средний |
| **Для интернета** | YouTube, соцсети, сайты | Средний |
| **Максимальное сжатие** | Отправка по почте, экономия места | Маленький |

## GUI — графический интерфейс

- Добавьте один или несколько видеофайлов
- Выберите режим сжатия
- Нажмите «Сжать видео»
- Следите за прогрессом каждого файла в таблице
- Откройте папку с результатом одним кликом

## Примеры командной строки

```bash
# Сжать один файл
python3 video_compressor.py input.mp4

# Сжать для Telegram
python3 video_compressor.py input.mp4 --preset telegram

# Сжать все видео в папке
python3 video_compressor.py ./videos -o ./compressed

# Сжать под конкретный размер (40 МБ)
python3 video_compressor.py input.mp4 --preset telegram --target-size-mb 40
```

## Сборка .app (macOS)

```bash
pip3 install pyinstaller
bash build_app.sh
```

Готовый `VideoCompressor.app` появится в папке `dist/`.

## Требования

- macOS / Linux / Windows
- Python 3.10+
- ffmpeg

На macOS всё ставится автоматически через `setup.sh`.
