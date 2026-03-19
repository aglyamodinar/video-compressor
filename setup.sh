#!/bin/bash
# Быстрая установка Video Compressor на macOS
set -e

echo "=== Video Compressor — установка ==="
echo ""

# Проверяем Homebrew
if ! command -v brew &> /dev/null; then
    echo "Устанавливаю Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi

# Проверяем ffmpeg
if ! command -v ffmpeg &> /dev/null; then
    echo "Устанавливаю ffmpeg..."
    brew install ffmpeg
else
    echo "ffmpeg уже установлен ✓"
fi

# Проверяем Python
if ! command -v python3 &> /dev/null; then
    echo "Устанавливаю Python..."
    brew install python
else
    echo "Python уже установлен ✓"
fi

# Проверяем tkinter
if ! python3 -c "import tkinter" 2>/dev/null; then
    echo "Устанавливаю tkinter..."
    PY_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    brew install "python-tk@${PY_VERSION}"
else
    echo "tkinter уже установлен ✓"
fi

echo ""
echo "=== Установка завершена! ==="
echo ""
echo "Запуск GUI:"
echo "  python3 gui_app.py"
echo ""
echo "Запуск из командной строки:"
echo "  python3 video_compressor.py video.mp4 --preset telegram"
echo ""
