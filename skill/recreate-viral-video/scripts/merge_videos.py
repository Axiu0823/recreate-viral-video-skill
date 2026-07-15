#!/usr/bin/env python3
"""Normalize and concatenate accepted generated clips with deterministic cuts."""

from __future__ import annotations

import argparse
import json
import math
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Merge accepted clips from merge-plan.json")
    parser.add_argument("merge_plan", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--validate-only", action="store_true")
    return parser.parse_args()


def finite_number(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    parsed = float(value)
    return parsed if math.isfinite(parsed) else None


def load_plan(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    try:
        plan = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RuntimeError(f"Merge plan does not exist: {path}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid merge-plan JSON: {exc}") from exc
    if not isinstance(plan, dict):
        raise RuntimeError("Merge plan root must be an object")
    if plan.get("assembly_mode", "hard_cut") not in {"hard_cut", "match_action_cut"}:
        raise RuntimeError("assembly_mode must be hard_cut or match_action_cut")
    raw_clips = plan.get("clips")
    if not isinstance(raw_clips, list) or not raw_clips:
        raise RuntimeError("clips must be a non-empty array")
    clips: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, item in enumerate(raw_clips):
        if not isinstance(item, dict):
            raise RuntimeError(f"clips[{index}] must be an object")
        clip_id = item.get("clip_id")
        if not isinstance(clip_id, str) or not clip_id or clip_id in seen:
            raise RuntimeError(f"clips[{index}].clip_id must be unique and non-empty")
        seen.add(clip_id)
        value = item.get("path")
        if not isinstance(value, str) or not value:
            raise RuntimeError(f"clips[{index}].path is required")
        clip_path = Path(value).expanduser()
        if not clip_path.is_absolute():
            clip_path = (path.parent / clip_path).resolve()
        if not clip_path.is_file():
            raise RuntimeError(f"Clip does not exist: {clip_path}")
        trim_start = finite_number(item.get("trim_start_s", 0))
        trim_end = finite_number(item.get("trim_end_s", 0))
        if trim_start is None or trim_end is None or trim_start < 0 or trim_end < 0:
            raise RuntimeError(f"clips[{index}] trims must be non-negative numbers")
        transition_in = item.get("transition_in", "hard_cut")
        if transition_in not in {"opening", "hard_cut", "match_action_cut"}:
            raise RuntimeError(
                f"clips[{index}].transition_in must be opening, hard_cut, or match_action_cut"
            )
        clips.append(
            {
                "clip_id": clip_id,
                "path": clip_path,
                "trim_start_s": trim_start,
                "trim_end_s": trim_end,
                "transition_in": transition_in,
            }
        )
    return plan, clips


def run(command: list[str], *, capture: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        check=True,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
    )


def probe(ffprobe: str, path: Path) -> dict[str, Any]:
    result = run(
        [
            ffprobe,
            "-v",
            "error",
            "-show_format",
            "-show_streams",
            "-of",
            "json",
            str(path),
        ],
        capture=True,
    )
    return json.loads(result.stdout)


def media_info(value: dict[str, Any]) -> dict[str, Any]:
    video = next(
        (stream for stream in value.get("streams", []) if stream.get("codec_type") == "video"),
        None,
    )
    if not isinstance(video, dict):
        raise RuntimeError("Clip has no video stream")
    duration = finite_number(value.get("format", {}).get("duration"))
    if duration is None or duration <= 0:
        duration = finite_number(video.get("duration"))
    if duration is None or duration <= 0:
        raise RuntimeError("Could not determine clip duration")
    rate = str(video.get("avg_frame_rate", "24/1"))
    try:
        numerator, denominator = rate.split("/", 1)
        fps = float(numerator) / float(denominator)
    except (ValueError, ZeroDivisionError):
        fps = 24.0
    return {
        "duration_s": duration,
        "width": int(video["width"]),
        "height": int(video["height"]),
        "fps": fps,
        "has_audio": any(
            stream.get("codec_type") == "audio" for stream in value.get("streams", [])
        ),
    }


def concat_escape(path: Path) -> str:
    return str(path).replace("'", "'\\''")


def main() -> int:
    args = parse_args()
    plan_path = args.merge_plan.expanduser().resolve()
    output = args.output.expanduser().resolve()
    plan, clips = load_plan(plan_path)
    if args.validate_only:
        print(f"valid: {plan_path}")
        return 0

    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:
        missing = "ffmpeg" if not ffmpeg else "ffprobe"
        raise RuntimeError(f"Required executable not found: {missing}")

    infos = [media_info(probe(ffprobe, clip["path"])) for clip in clips]
    target_width = plan.get("target_width") or infos[0]["width"]
    target_height = plan.get("target_height") or infos[0]["height"]
    target_fps = plan.get("target_fps") or round(infos[0]["fps"])
    audio_lufs = finite_number(plan.get("audio_lufs", -16.0))
    if not all(isinstance(value, int) and value > 0 for value in (target_width, target_height, target_fps)):
        raise RuntimeError("target_width, target_height, and target_fps must be positive integers")
    if audio_lufs is None:
        raise RuntimeError("audio_lufs must be numeric")

    output.parent.mkdir(parents=True, exist_ok=True)
    report_clips = []
    with tempfile.TemporaryDirectory(prefix="viral-merge-", dir=output.parent) as temp_name:
        temp_dir = Path(temp_name)
        normalized: list[Path] = []
        for index, (clip, info) in enumerate(zip(clips, infos, strict=True)):
            remaining = info["duration_s"] - clip["trim_start_s"] - clip["trim_end_s"]
            if remaining <= 0.1:
                raise RuntimeError(f"Trims remove the entire clip: {clip['clip_id']}")
            destination = temp_dir / f"{index:03d}.mp4"
            filter_video = (
                f"scale={target_width}:{target_height}:force_original_aspect_ratio=decrease,"
                f"pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2:black,"
                f"fps={target_fps},format=yuv420p"
            )
            command = [
                ffmpeg,
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-i",
                str(clip["path"]),
            ]
            if not info["has_audio"]:
                command.extend(
                    [
                        "-f",
                        "lavfi",
                        "-t",
                        f"{remaining:.6f}",
                        "-i",
                        "anullsrc=channel_layout=stereo:sample_rate=48000",
                    ]
                )
            command.extend(
                [
                    "-ss",
                    f"{clip['trim_start_s']:.6f}",
                    "-t",
                    f"{remaining:.6f}",
                    "-map",
                    "0:v:0",
                    "-map",
                    "0:a:0" if info["has_audio"] else "1:a:0",
                    "-vf",
                    filter_video,
                    "-af",
                    f"loudnorm=I={audio_lufs:g}:TP=-1.5:LRA=11,aresample=48000",
                    "-c:v",
                    "libx264",
                    "-preset",
                    "medium",
                    "-crf",
                    "18",
                    "-c:a",
                    "aac",
                    "-b:a",
                    "192k",
                    "-ar",
                    "48000",
                    "-ac",
                    "2",
                    "-shortest",
                    "-movflags",
                    "+faststart",
                    str(destination),
                ]
            )
            run(command)
            normalized.append(destination)
            report_clips.append(
                {
                    "clip_id": clip["clip_id"],
                    "source": str(clip["path"]),
                    "source_duration_s": info["duration_s"],
                    "trim_start_s": clip["trim_start_s"],
                    "trim_end_s": clip["trim_end_s"],
                    "normalized_duration_s": remaining,
                    "transition_in": clip["transition_in"],
                }
            )
        concat_file = temp_dir / "concat.txt"
        concat_file.write_text(
            "".join(f"file '{concat_escape(path)}'\n" for path in normalized),
            encoding="utf-8",
        )
        run(
            [
                ffmpeg,
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(concat_file),
                "-c",
                "copy",
                "-movflags",
                "+faststart",
                str(output),
            ]
        )
    final_info = media_info(probe(ffprobe, output))
    report_path = output.parent / "merge-report.json"
    report_path.write_text(
        json.dumps(
            {
                "output": str(output),
                "assembly_mode": plan.get("assembly_mode", "hard_cut"),
                "target_width": target_width,
                "target_height": target_height,
                "target_fps": target_fps,
                "audio_lufs": audio_lufs,
                "clips": report_clips,
                "final_duration_s": final_info["duration_s"],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(output)
    print(report_path)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
