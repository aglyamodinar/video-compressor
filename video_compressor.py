#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from shutil import which
from typing import Iterable

VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v"}


@dataclass(frozen=True)
class Preset:
    crf: int
    speed: str
    audio_bitrate: str
    default_scale: int | None = None
    default_fps: int | None = None


PRESETS = {
    "web": Preset(crf=27, speed="medium", audio_bitrate="128k"),
    "archive": Preset(crf=22, speed="slow", audio_bitrate="192k"),
    "mobile": Preset(crf=29, speed="faster", audio_bitrate="96k"),
    "telegram": Preset(
        crf=28, speed="slow", audio_bitrate="96k", default_scale=1280, default_fps=30
    ),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Сжатие видео через ffmpeg (один файл или папка)."
    )
    parser.add_argument(
        "input_path",
        type=Path,
        help="Путь к видеофайлу или папке с видеофайлами.",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Путь выходного файла/папки. По умолчанию создается рядом с input.",
    )
    parser.add_argument(
        "--preset",
        choices=sorted(PRESETS),
        default="web",
        help="Готовый профиль сжатия.",
    )
    parser.add_argument(
        "--crf",
        type=int,
        help="Качество H.264: меньше = лучше качество и больше размер (обычно 18-32).",
    )
    parser.add_argument(
        "--speed",
        default=None,
        choices=[
            "ultrafast",
            "superfast",
            "veryfast",
            "faster",
            "fast",
            "medium",
            "slow",
            "slower",
            "veryslow",
        ],
        help="Скорость кодирования x264 (медленнее обычно дает меньший размер).",
    )
    parser.add_argument(
        "--audio-bitrate",
        default=None,
        help="Аудио-битрейт, например 96k, 128k, 192k.",
    )
    parser.add_argument(
        "--scale",
        type=int,
        help="Максимальная ширина (в пикселях) с сохранением пропорций, например 1280.",
    )
    parser.add_argument(
        "--fps",
        type=int,
        help="Ограничение FPS (например 30).",
    )
    parser.add_argument(
        "--target-size-mb",
        type=float,
        help=(
            "Целевой размер файла в МБ. Включает 2-pass кодирование и приоритизирует "
            "минимальный размер (полезно для Telegram)."
        ),
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Рекурсивно искать видео в подпапках (если input_path — папка).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Показать команды ffmpeg без запуска.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Перезаписывать существующие файлы без вопроса.",
    )
    return parser.parse_args()


def ensure_ffmpeg_available(require_ffprobe: bool = False) -> None:
    if which("ffmpeg") is None:
        raise RuntimeError(
            "ffmpeg не найден. Установите его и повторите запуск.\n"
            "macOS (Homebrew): brew install ffmpeg"
        )
    if require_ffprobe and which("ffprobe") is None:
        raise RuntimeError("ffprobe не найден. Установите ffmpeg с ffprobe и повторите запуск.")


def collect_input_files(path: Path, recursive: bool) -> list[Path]:
    if path.is_file():
        return [path]
    if not path.is_dir():
        raise FileNotFoundError(f"Путь не найден: {path}")

    pattern = "**/*" if recursive else "*"
    files = [
        p for p in path.glob(pattern) if p.is_file() and p.suffix.lower() in VIDEO_EXTENSIONS
    ]
    if not files:
        raise FileNotFoundError(f"Видео не найдены в: {path}")
    return sorted(files)


def build_output_path(input_file: Path, input_root: Path, output_target: Path | None) -> Path:
    suffix = "_compressed.mp4"
    if output_target is None:
        return input_file.with_name(f"{input_file.stem}{suffix}")

    if input_root.is_file():
        if output_target.suffix:
            return output_target
        return output_target / f"{input_file.stem}{suffix}"

    relative = input_file.relative_to(input_root)
    base = relative.with_suffix("")
    return output_target / f"{base}{suffix}"


def ffmpeg_command(
    source: Path,
    destination: Path,
    crf: int,
    speed: str,
    audio_bitrate: str,
    scale: int | None,
    fps: int | None,
    overwrite: bool,
) -> list[str]:
    command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-stats",
        "-y" if overwrite else "-n",
        "-i",
        str(source),
        "-c:v",
        "libx264",
        "-preset",
        speed,
        "-crf",
        str(crf),
    ]

    filters: list[str] = []
    if scale:
        filters.append(f"scale='min({scale},iw)':-2")
    if fps:
        filters.append(f"fps={fps}")
    if filters:
        command.extend(["-vf", ",".join(filters)])

    command.extend(
        [
            "-c:a",
            "aac",
            "-b:a",
            audio_bitrate,
            "-pix_fmt",
            "yuv420p",
            "-profile:v",
            "high",
            "-movflags",
            "+faststart",
            str(destination),
        ]
    )
    return command


def parse_audio_bitrate_kbps(value: str) -> int:
    value = value.strip().lower()
    if value.endswith("k") and value[:-1].isdigit():
        return int(value[:-1])
    if value.isdigit():
        return int(value)
    raise ValueError(f"Не удалось распознать аудио-битрейт: {value}")


def probe_duration_seconds(path: Path) -> float:
    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(path),
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe завершился с ошибкой для {path}")
    try:
        return float(result.stdout.strip())
    except ValueError as error:
        raise RuntimeError(f"Не удалось определить длительность файла: {path}") from error


def two_pass_commands(
    source: Path,
    destination: Path,
    speed: str,
    audio_bitrate: str,
    scale: int | None,
    fps: int | None,
    target_size_mb: float,
    overwrite: bool,
) -> tuple[list[list[str]], Path]:
    duration = probe_duration_seconds(source)
    if duration <= 0:
        raise RuntimeError(f"Некорректная длительность видео: {source}")

    audio_kbps = parse_audio_bitrate_kbps(audio_bitrate)
    total_kilobits = target_size_mb * 8192
    total_kbps = total_kilobits / duration
    video_kbps = max(120, int(total_kbps - audio_kbps - 16))

    if video_kbps <= 120:
        print(
            f"Предупреждение: очень маленький target-size для {source.name}. "
            "Качество может заметно упасть.",
            file=sys.stderr,
        )

    filters: list[str] = []
    if scale:
        filters.append(f"scale='min({scale},iw)':-2")
    if fps:
        filters.append(f"fps={fps}")

    passlog = destination.parent / f".{destination.stem}_passlog"
    vf_args = ["-vf", ",".join(filters)] if filters else []

    base_video_args = [
        "-c:v",
        "libx264",
        "-preset",
        speed,
        "-b:v",
        f"{video_kbps}k",
        "-pix_fmt",
        "yuv420p",
        "-profile:v",
        "high",
    ]

    first_pass = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-stats",
        "-y",
        "-i",
        str(source),
        *vf_args,
        *base_video_args,
        "-an",
        "-pass",
        "1",
        "-passlogfile",
        str(passlog),
        "-f",
        "mp4",
        os.devnull,
    ]
    second_pass = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-stats",
        "-y" if overwrite else "-n",
        "-i",
        str(source),
        *vf_args,
        *base_video_args,
        "-pass",
        "2",
        "-passlogfile",
        str(passlog),
        "-c:a",
        "aac",
        "-b:a",
        audio_bitrate,
        "-movflags",
        "+faststart",
        str(destination),
    ]
    return [first_pass, second_pass], passlog


def run_commands(commands: Iterable[list[str]], dry_run: bool) -> int:
    errors = 0
    for command in commands:
        print("$", shlex.join(command))
        if dry_run:
            continue
        result = subprocess.run(command)
        if result.returncode != 0:
            errors += 1
    return errors


def main() -> int:
    args = parse_args()
    if args.target_size_mb is not None and args.target_size_mb <= 0:
        raise ValueError("--target-size-mb должен быть больше 0.")
    ensure_ffmpeg_available(require_ffprobe=args.target_size_mb is not None)

    preset = PRESETS[args.preset]
    crf = args.crf if args.crf is not None else preset.crf
    speed = args.speed if args.speed is not None else preset.speed
    audio_bitrate = args.audio_bitrate if args.audio_bitrate is not None else preset.audio_bitrate
    scale = args.scale if args.scale is not None else preset.default_scale
    fps = args.fps if args.fps is not None else preset.default_fps

    input_files = collect_input_files(args.input_path, recursive=args.recursive)

    output_target = args.output
    commands: list[list[str]] = []
    passlog_files: list[Path] = []

    for source in input_files:
        destination = build_output_path(source, args.input_path, output_target)
        destination.parent.mkdir(parents=True, exist_ok=True)

        if args.target_size_mb is not None:
            two_pass, passlog = two_pass_commands(
                source=source,
                destination=destination,
                speed=speed,
                audio_bitrate=audio_bitrate,
                scale=scale,
                fps=fps,
                target_size_mb=args.target_size_mb,
                overwrite=args.overwrite,
            )
            commands.extend(two_pass)
            passlog_files.append(passlog)
        else:
            command = ffmpeg_command(
                source=source,
                destination=destination,
                crf=crf,
                speed=speed,
                audio_bitrate=audio_bitrate,
                scale=scale,
                fps=fps,
                overwrite=args.overwrite,
            )
            commands.append(command)

    errors = run_commands(commands, dry_run=args.dry_run)
    if not args.dry_run:
        for passlog in passlog_files:
            for candidate in passlog.parent.glob(f"{passlog.name}*"):
                candidate.unlink(missing_ok=True)

    if errors:
        print(f"\nЗавершено с ошибками: {errors} файл(ов).", file=sys.stderr)
        return 1

    print(f"\nГотово. Обработано файлов: {len(input_files)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
