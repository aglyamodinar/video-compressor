#!/bin/bash
# Одна команда: установка зависимостей + сборка .app + запуск
set -e

echo "=== Video Compressor — установка и сборка ==="
echo ""

# --- Зависимости ---

if ! command -v brew &> /dev/null; then
    echo "Устанавливаю Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi

if ! command -v ffmpeg &> /dev/null; then
    echo "Устанавливаю ffmpeg..."
    brew install ffmpeg
else
    echo "ffmpeg ✓"
fi

if ! command -v python3 &> /dev/null; then
    echo "Устанавливаю Python..."
    brew install python
else
    echo "Python ✓"
fi

if ! python3 -c "import tkinter" 2>/dev/null; then
    PY_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    echo "Устанавливаю tkinter..."
    brew install "python-tk@${PY_VERSION}"
else
    echo "tkinter ✓"
fi

# PyInstaller
if ! command -v pyinstaller &> /dev/null; then
    echo "Устанавливаю PyInstaller..."
    pip3 install --break-system-packages pyinstaller
else
    echo "PyInstaller ✓"
fi

# --- Сборка .app ---

echo ""
echo "Собираю VideoCompressor.app..."

FFMPEG_PATH=$(which ffmpeg)
FFPROBE_PATH=$(which ffprobe)

rm -rf build dist *.spec

pyinstaller \
  --name "VideoCompressor" \
  --windowed \
  --add-binary "${FFMPEG_PATH}:." \
  --add-binary "${FFPROBE_PATH}:." \
  --noconfirm \
  gui_app.py > /dev/null 2>&1

# --- Копируем в /Applications ---

APP_PATH="dist/VideoCompressor.app"

if [ -d "$APP_PATH" ]; then
    echo ""
    echo "=== Готово! ==="
    echo ""
    read -p "Установить в /Applications? (y/n) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        cp -R "$APP_PATH" /Applications/
        echo "Установлено в /Applications/VideoCompressor.app"
        echo "Запускаю..."
        open /Applications/VideoCompressor.app
    else
        echo "Приложение: $(pwd)/$APP_PATH"
        echo "Запускаю..."
        open "$APP_PATH"
    fi
else
    echo "Ошибка сборки. Попробуйте: python3 gui_app.py"
    exit 1
fi
