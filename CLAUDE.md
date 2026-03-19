# Video Compressor

Утилита для сжатия видео через ffmpeg. Два интерфейса: GUI (gui_app.py) и CLI (video_compressor.py).

## Структура

- `video_compressor.py` — основная логика: пресеты, построение команд ffmpeg, 1-pass и 2-pass кодирование
- `gui_app.py` — GUI на tkinter, импортирует логику из video_compressor.py
- `setup.sh` — автоустановка зависимостей на macOS
- `build_app.sh` — сборка .app через PyInstaller

## Запуск

```bash
bash setup.sh        # установка зависимостей
python3 gui_app.py   # GUI
python3 video_compressor.py input.mp4 --preset telegram  # CLI
```

## Зависимости

- Python 3.10+, ffmpeg, ffprobe, tkinter (для GUI)
- PyInstaller (только для сборки .app)
