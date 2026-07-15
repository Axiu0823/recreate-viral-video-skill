#!/usr/bin/env python3
"""Split a source video from an approved segment plan using ffmpeg."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

from validate_segments import load_and_validate


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Split a long source video into approved ranges")
    parser.add_argument("video", type=Path)
    parser.add_argument("segment_plan", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--validate-only", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    video = args.video.expanduser().resolve()
    plan_path = args.segment_plan.expanduser().resolve()
    output_dir = args.output_dir.expanduser().resolve()
    if not video.is_file():
        raise RuntimeError(f"Source video does not exist: {video}")
    plan, errors = load_and_validate(plan_path, require_approved=True)
    if errors:
        raise RuntimeError("; ".join(errors))
    if args.validate_only:
        print(f"valid: {plan_path}")
        return 0

    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("Required executable not found: ffmpeg")
    output_dir.mkdir(parents=True, exist_ok=True)
    results = []
    for index, segment in enumerate(plan["segments"], start=1):
        segment_id = segment["segment_id"]
        start = float(segment["source_start_s"])
        end = float(segment["source_end_s"])
        duration = end - start
        destination = output_dir / f"{index:02d}-{segment_id}.mp4"
        command = [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(video),
            "-ss",
            f"{start:.6f}",
            "-t",
            f"{duration:.6f}",
            "-map",
            "0:v:0",
            "-map",
            "0:a:0?",
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
            "-movflags",
            "+faststart",
            "-avoid_negative_ts",
            "make_zero",
            str(destination),
        ]
        subprocess.run(command, check=True)
        results.append(
            {
                "segment_id": segment_id,
                "source_start_s": start,
                "source_end_s": end,
                "path": str(destination),
            }
        )
    manifest = output_dir / "split-manifest.json"
    manifest.write_text(
        json.dumps({"source": str(video), "segments": results}, ensure_ascii=False, indent=2)
        + "\n",
        encoding="utf-8",
    )
    print(manifest)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
