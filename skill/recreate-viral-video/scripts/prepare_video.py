#!/usr/bin/env python3
"""Create deterministic inspection artifacts for a short reference video."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Probe a reference video, sample the first seconds densely, create a "
            "timeline contact sheet, and extract audio diagnostics."
        )
    )
    parser.add_argument("video", type=Path, help="Local reference video")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--hook-seconds", type=float, default=5.0)
    parser.add_argument("--hook-fps", type=float, default=4.0)
    parser.add_argument("--timeline-fps", type=float, default=1.0)
    return parser.parse_args()


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def require_binary(name: str) -> str:
    path = shutil.which(name)
    if not path:
        raise RuntimeError(f"Required executable not found: {name}")
    return path


def video_duration(probe: dict) -> float:
    candidates = [probe.get("format", {}).get("duration")]
    candidates.extend(
        stream.get("duration")
        for stream in probe.get("streams", [])
        if stream.get("codec_type") == "video"
    )
    for value in candidates:
        try:
            duration = float(value)
        except (TypeError, ValueError):
            continue
        if duration > 0:
            return duration
    raise RuntimeError("ffprobe did not report a positive video duration")


def make_video_artifact(
    ffmpeg: str,
    source: Path,
    destination: Path,
    filter_graph: str,
    *,
    duration: float | None = None,
    frames: int | None = None,
) -> None:
    command = [ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", str(source)]
    if duration is not None:
        command.extend(["-t", f"{duration:.3f}"])
    command.extend(["-vf", filter_graph])
    if frames is not None:
        command.extend(["-frames:v", str(frames)])
    command.append(str(destination))
    run(command)


def main() -> int:
    args = parse_args()
    source = args.video.expanduser().resolve()
    output_dir = args.output_dir.expanduser().resolve()

    if not source.is_file():
        raise RuntimeError(f"Video does not exist: {source}")
    if args.hook_seconds <= 0 or args.hook_fps <= 0 or args.timeline_fps <= 0:
        raise RuntimeError("Sampling durations and rates must be positive")

    ffmpeg = require_binary("ffmpeg")
    ffprobe = require_binary("ffprobe")
    output_dir.mkdir(parents=True, exist_ok=True)

    probe_result = run(
        [
            ffprobe,
            "-v",
            "error",
            "-show_format",
            "-show_streams",
            "-of",
            "json",
            str(source),
        ]
    )
    probe = json.loads(probe_result.stdout)
    duration = video_duration(probe)
    hook_duration = min(duration, args.hook_seconds)
    has_audio = any(
        stream.get("codec_type") == "audio" for stream in probe.get("streams", [])
    )

    metadata_path = output_dir / "metadata.json"
    metadata_path.write_text(
        json.dumps(probe, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    hook_dir = output_dir / "hook_frames"
    timeline_dir = output_dir / "timeline_frames"
    hook_dir.mkdir(exist_ok=True)
    timeline_dir.mkdir(exist_ok=True)
    for stale in hook_dir.glob("hook_*.jpg"):
        stale.unlink()
    for stale in timeline_dir.glob("frame_*.jpg"):
        stale.unlink()

    scale = "scale=960:-2:force_original_aspect_ratio=decrease"
    make_video_artifact(
        ffmpeg,
        source,
        hook_dir / "hook_%03d.jpg",
        f"fps={args.hook_fps:g},{scale}",
        duration=hook_duration,
    )
    make_video_artifact(
        ffmpeg,
        source,
        timeline_dir / "frame_%03d.jpg",
        f"fps={args.timeline_fps:g},{scale}",
    )

    hook_contact = output_dir / "hook_contact.jpg"
    hook_tiles = max(1, min(20, round(hook_duration * args.hook_fps)))
    hook_columns = 4
    hook_rows = (hook_tiles + hook_columns - 1) // hook_columns
    make_video_artifact(
        ffmpeg,
        source,
        hook_contact,
        (
            f"fps={args.hook_fps:g},scale=320:-2:force_original_aspect_ratio=decrease,"
            f"tile={hook_columns}x{hook_rows}:padding=5:margin=5:color=white"
        ),
        duration=hook_duration,
        frames=1,
    )

    timeline_contact = output_dir / "timeline_contact.jpg"
    contact_rate = min(2.0, max(0.1, 20.0 / duration))
    make_video_artifact(
        ffmpeg,
        source,
        timeline_contact,
        (
            f"fps={contact_rate:.6f},scale=320:-2:force_original_aspect_ratio=decrease,"
            "tile=5x4:padding=5:margin=5:color=white"
        ),
        frames=1,
    )

    audio_path: Path | None = None
    waveform_path: Path | None = None
    if has_audio:
        audio_path = output_dir / "audio.wav"
        run(
            [
                ffmpeg,
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-i",
                str(source),
                "-vn",
                "-ac",
                "1",
                "-ar",
                "16000",
                str(audio_path),
            ]
        )
        waveform_path = output_dir / "audio_waveform.png"
        run(
            [
                ffmpeg,
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-i",
                str(source),
                "-filter_complex",
                "aformat=channel_layouts=mono,showwavespic=s=1600x300:colors=0x2E6CE6",
                "-frames:v",
                "1",
                str(waveform_path),
            ]
        )

    video_stream = next(
        (
            stream
            for stream in probe.get("streams", [])
            if stream.get("codec_type") == "video"
        ),
        {},
    )
    manifest = {
        "source": str(source),
        "duration_s": duration,
        "width": video_stream.get("width"),
        "height": video_stream.get("height"),
        "avg_frame_rate": video_stream.get("avg_frame_rate"),
        "has_audio": has_audio,
        "sampling": {
            "hook_seconds": hook_duration,
            "hook_fps": args.hook_fps,
            "timeline_fps": args.timeline_fps,
            "timeline_contact_fps": contact_rate,
        },
        "artifacts": {
            "metadata": str(metadata_path),
            "hook_frames": str(hook_dir),
            "hook_contact": str(hook_contact),
            "timeline_frames": str(timeline_dir),
            "timeline_contact": str(timeline_contact),
            "audio": str(audio_path) if audio_path else None,
            "audio_waveform": str(waveform_path) if waveform_path else None,
        },
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(manifest_path)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
