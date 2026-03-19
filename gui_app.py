#!/usr/bin/env python3
"""GUI-обёртка для video_compressor — простое окно для сжатия видео."""
from __future__ import annotations

import os
import queue
import re
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path

from video_compressor import (
    PRESETS,
    VIDEO_EXTENSIONS,
    ensure_ffmpeg_available,
    build_output_path,
    ffmpeg_command,
    probe_duration_seconds,
)


def _setup_bundled_path() -> None:
    """Добавляет папку с ffmpeg из .app бандла в PATH."""
    if getattr(sys, "frozen", False):
        bundle_dir = Path(sys._MEIPASS)
    else:
        bundle_dir = Path(__file__).parent

    ffmpeg_path = bundle_dir / "ffmpeg"
    if ffmpeg_path.exists():
        os.environ["PATH"] = str(bundle_dir) + os.pathsep + os.environ.get("PATH", "")


_setup_bundled_path()

# Понятные названия режимов для пользователей
PRESET_UI = {
    "telegram": {
        "label": "Для Telegram",
        "desc": "Макс. качество при ограничениях Telegram (1280px, 30fps)",
    },
    "web": {
        "label": "Для интернета",
        "desc": "Баланс качества и размера — YouTube, соцсети, сайты",
    },
    "mobile": {
        "label": "Максимальное сжатие",
        "desc": "Минимальный размер файла, подходит для отправки по почте",
    },
    "archive": {
        "label": "Без потери качества",
        "desc": "Визуально неотличимо от оригинала, файл крупнее",
    },
}

PRESET_ORDER = ["archive", "telegram", "web", "mobile"]

SUPPORTED_FORMATS = sorted(ext.lstrip(".").upper() for ext in VIDEO_EXTENSIONS)


def format_size(size_bytes: int) -> str:
    mb = size_bytes / (1024 * 1024)
    if mb >= 1000:
        return f"{mb / 1024:.1f} ГБ"
    return f"{mb:.1f} МБ"


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Сжатие видео без потери качества")
        self.minsize(600, 520)
        self.resizable(True, True)

        self.files: list[Path] = []
        self.process: subprocess.Popen | None = None
        self.progress_queue: queue.Queue = queue.Queue()
        self._compressing = False
        self._current_index = 0

        self._check_ffmpeg()
        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _check_ffmpeg(self) -> None:
        try:
            ensure_ffmpeg_available(require_ffprobe=True)
        except RuntimeError as e:
            messagebox.showerror("ffmpeg не найден", str(e))
            self.destroy()
            raise SystemExit(1)

    def _build_ui(self) -> None:
        px = 20

        # --- Заголовок ---
        title_label = ttk.Label(
            self,
            text="Сжатие видео без потери качества",
            font=("Helvetica", 18, "bold"),
        )
        title_label.pack(padx=px, pady=(18, 2))

        formats_text = "Форматы: " + ", ".join(SUPPORTED_FORMATS)
        formats_label = ttk.Label(self, text=formats_text, foreground="gray")
        formats_label.pack(padx=px, pady=(0, 10))

        # --- Выбор файлов ---
        file_frame = ttk.LabelFrame(self, text="Видеофайлы", padding=10)
        file_frame.pack(fill="both", expand=True, padx=px, pady=(0, 5))

        # Таблица файлов
        columns = ("name", "size", "status")
        self.tree = ttk.Treeview(
            file_frame, columns=columns, show="headings", height=6
        )
        self.tree.heading("name", text="Файл")
        self.tree.heading("size", text="Размер")
        self.tree.heading("status", text="Статус")
        self.tree.column("name", width=260, minwidth=150)
        self.tree.column("size", width=90, minwidth=70, anchor="center")
        self.tree.column("status", width=160, minwidth=100, anchor="center")

        scrollbar = ttk.Scrollbar(file_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Кнопки под таблицей
        btn_row = ttk.Frame(self)
        btn_row.pack(fill="x", padx=px, pady=(5, 5))

        self.add_btn = ttk.Button(
            btn_row, text="Добавить файлы…", command=self._browse_files
        )
        self.add_btn.pack(side="left")

        self.clear_btn = ttk.Button(
            btn_row, text="Очистить список", command=self._clear_files
        )
        self.clear_btn.pack(side="left", padx=(10, 0))

        # --- Режим сжатия ---
        preset_frame = ttk.LabelFrame(self, text="Режим сжатия", padding=10)
        preset_frame.pack(fill="x", padx=px, pady=5)

        self.preset_var = tk.StringVar(value="archive")
        combo_labels = [PRESET_UI[k]["label"] for k in PRESET_ORDER]
        self.preset_combo = ttk.Combobox(
            preset_frame,
            textvariable=tk.StringVar(),
            values=combo_labels,
            state="readonly",
            width=30,
        )
        self.preset_combo.current(0)  # "Без потери качества"
        self.preset_combo.pack(anchor="w")
        self.preset_combo.bind("<<ComboboxSelected>>", self._on_preset_change)

        self.preset_desc = ttk.Label(
            preset_frame,
            text=PRESET_UI["archive"]["desc"],
            foreground="gray",
        )
        self.preset_desc.pack(anchor="w", pady=(4, 0))

        # --- Прогресс ---
        progress_frame = ttk.LabelFrame(self, text="Прогресс", padding=10)
        progress_frame.pack(fill="x", padx=px, pady=5)

        self.progressbar = ttk.Progressbar(
            progress_frame, mode="determinate", maximum=100
        )
        self.progressbar.pack(fill="x")

        self.status_label = ttk.Label(progress_frame, text="Ожидание…")
        self.status_label.pack(anchor="w", pady=(4, 0))

        # --- Кнопки действий ---
        action_row = ttk.Frame(self)
        action_row.pack(padx=px, pady=(10, 5))

        self.compress_btn = ttk.Button(
            action_row, text="Сжать видео", command=self._start_compress
        )
        self.compress_btn.pack(side="left")

        self.open_folder_btn = ttk.Button(
            action_row, text="Открыть папку", command=self._open_output_folder
        )
        self.open_folder_btn.pack(side="left", padx=(10, 0))
        self.open_folder_btn.pack_forget()

        # Отступ снизу
        ttk.Label(self, text="").pack(pady=(0, 5))

    def _get_selected_preset_key(self) -> str:
        idx = self.preset_combo.current()
        if 0 <= idx < len(PRESET_ORDER):
            return PRESET_ORDER[idx]
        return "archive"

    def _browse_files(self) -> None:
        exts = " ".join(f"*{ext}" for ext in sorted(VIDEO_EXTENSIONS))
        paths = filedialog.askopenfilenames(
            title="Выберите видеофайлы",
            filetypes=[("Видео", exts), ("Все файлы", "*.*")],
        )
        if not paths:
            return
        for p in paths:
            path = Path(p)
            if path not in self.files:
                self.files.append(path)
                size = format_size(path.stat().st_size)
                self.tree.insert("", "end", iid=str(path), values=(path.name, size, "Ожидает"))

    def _clear_files(self) -> None:
        if self._compressing:
            return
        self.files.clear()
        for item in self.tree.get_children():
            self.tree.delete(item)

    def _on_preset_change(self, _event: object = None) -> None:
        key = self._get_selected_preset_key()
        self.preset_desc.config(text=PRESET_UI[key]["desc"])

    def _start_compress(self) -> None:
        if self._compressing:
            return
        if not self.files:
            messagebox.showwarning("Нет файлов", "Сначала добавьте видеофайлы.")
            return

        self._compressing = True
        self._current_index = 0
        self.compress_btn.config(state="disabled")
        self.add_btn.config(state="disabled")
        self.clear_btn.config(state="disabled")
        self.open_folder_btn.pack_forget()

        # Сбросить статусы
        for item in self.tree.get_children():
            self.tree.set(item, "status", "Ожидает")

        self._compress_next()

    def _compress_next(self) -> None:
        if self._current_index >= len(self.files):
            self._all_done()
            return

        source = self.files[self._current_index]
        iid = str(source)
        total = len(self.files)
        num = self._current_index + 1

        self.tree.set(iid, "status", "Сжимается…")
        self.tree.selection_set(iid)
        self.tree.see(iid)

        self.status_label.config(text=f"Файл {num} из {total}: {source.name}")
        self.progressbar["value"] = 0

        preset_key = self._get_selected_preset_key()
        preset = PRESETS[preset_key]

        output = build_output_path(source, source, None)

        cmd = ffmpeg_command(
            source=source,
            destination=output,
            crf=preset.crf,
            speed=preset.speed,
            audio_bitrate=preset.audio_bitrate,
            scale=preset.default_scale,
            fps=preset.default_fps,
            overwrite=True,
        )
        try:
            idx = cmd.index("error")
            cmd[idx] = "info"
        except ValueError:
            pass

        try:
            duration = probe_duration_seconds(source)
        except RuntimeError:
            duration = 0.0

        # Очистка очереди
        while not self.progress_queue.empty():
            try:
                self.progress_queue.get_nowait()
            except queue.Empty:
                break

        thread = threading.Thread(
            target=self._worker, args=(cmd, duration, source, output), daemon=True
        )
        thread.start()
        self.after(100, self._poll_progress)

    def _worker(self, cmd: list[str], duration: float, source: Path, output: Path) -> None:
        try:
            proc = subprocess.Popen(
                cmd, stderr=subprocess.PIPE, stdout=subprocess.DEVNULL, text=True
            )
            self.process = proc
            time_re = re.compile(r"time=(\d+):(\d+):(\d+\.\d+)")

            for line in proc.stderr:
                m = time_re.search(line)
                if m and duration > 0:
                    elapsed = (
                        int(m.group(1)) * 3600
                        + int(m.group(2)) * 60
                        + float(m.group(3))
                    )
                    pct = min(100, elapsed / duration * 100)
                    self.progress_queue.put(("progress", pct))

            proc.wait()
            self.progress_queue.put(("done", proc.returncode, source, output))
        except Exception as e:
            self.progress_queue.put(("error", str(e), source))

    def _poll_progress(self) -> None:
        try:
            while True:
                msg = self.progress_queue.get_nowait()
                kind = msg[0]

                if kind == "progress":
                    self.progressbar["value"] = msg[1]
                    num = self._current_index + 1
                    total = len(self.files)
                    source = self.files[self._current_index]
                    self.status_label.config(
                        text=f"Файл {num} из {total}: {source.name} — {msg[1]:.0f}%"
                    )

                elif kind == "done":
                    self._on_file_done(msg[1], msg[2], msg[3])
                    return

                elif kind == "error":
                    self._on_file_error(msg[1], msg[2])
                    return

        except queue.Empty:
            pass

        if self._compressing:
            self.after(100, self._poll_progress)

    def _on_file_done(self, returncode: int, source: Path, output: Path) -> None:
        self.process = None
        iid = str(source)

        if returncode != 0:
            self.tree.set(iid, "status", "Ошибка")
        else:
            orig = source.stat().st_size
            if output.exists():
                comp = output.stat().st_size
                savings = (1 - comp / orig) * 100 if orig > 0 else 0
                self.tree.set(
                    iid, "status", f"{format_size(comp)} (−{savings:.0f}%)"
                )
            else:
                self.tree.set(iid, "status", "Готово")

        self._current_index += 1
        self._compress_next()

    def _on_file_error(self, message: str, source: Path) -> None:
        self.process = None
        iid = str(source)
        self.tree.set(iid, "status", "Ошибка")

        self._current_index += 1
        self._compress_next()

    def _all_done(self) -> None:
        self._compressing = False
        self.compress_btn.config(state="normal")
        self.add_btn.config(state="normal")
        self.clear_btn.config(state="normal")
        self.progressbar["value"] = 100

        errors = sum(
            1 for item in self.tree.get_children()
            if "Ошибка" in str(self.tree.set(item, "status"))
        )
        total = len(self.files)
        ok = total - errors

        if errors:
            self.status_label.config(text=f"Готово: {ok} из {total} (ошибок: {errors})")
        else:
            self.status_label.config(text=f"Готово! Обработано файлов: {total}")

        if self.files:
            last_output = build_output_path(self.files[-1], self.files[-1], None)
            if last_output.exists():
                self._last_output = last_output
                self.open_folder_btn.pack(side="left", padx=(10, 0))

    def _open_output_folder(self) -> None:
        if not hasattr(self, "_last_output") or not self._last_output.parent.exists():
            return
        if sys.platform == "win32":
            subprocess.Popen(["explorer", "/select,", str(self._last_output)])
        elif sys.platform == "darwin":
            subprocess.Popen(["open", "-R", str(self._last_output)])
        else:
            subprocess.Popen(["xdg-open", str(self._last_output.parent)])

    def _on_close(self) -> None:
        if self.process is not None:
            self.process.terminate()
        self.destroy()


if __name__ == "__main__":
    app = App()
    app.mainloop()
