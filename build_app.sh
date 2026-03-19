#!/bin/bash
# Сборка VideoCompressor.app для macOS
set -e

echo "=== Сборка VideoCompressor.app ==="

FFMPEG_PATH=$(which ffmpeg)
FFPROBE_PATH=$(which ffprobe)

if [ -z "$FFMPEG_PATH" ] || [ -z "$FFPROBE_PATH" ]; then
    echo "Ошибка: ffmpeg/ffprobe не найдены. Установите: brew install ffmpeg"
    exit 1
fi

rm -rf build dist *.spec

pyinstaller \
  --name "VideoCompressor" \
  --windowed \
  --add-binary "${FFMPEG_PATH}:." \
  --add-binary "${FFPROBE_PATH}:." \
  --noconfirm \
  gui_app.py

echo ""
echo "=== Готово! ==="
echo "Приложение: dist/VideoCompressor.app"
echo ""
open dist/
