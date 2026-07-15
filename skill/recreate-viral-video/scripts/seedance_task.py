#!/usr/bin/env python3
"""Submit, poll, and optionally download a Seedance 2.0 Ark task."""

from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


TASKS_URL = "https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks"
TERMINAL = {"succeeded", "failed", "expired", "cancelled"}
ALLOWED_RATIOS = {"16:9", "4:3", "1:1", "3:4", "9:16", "21:9", "adaptive"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Submit a Seedance 2.0 request JSON, poll its task, and download output."
    )
    parser.add_argument("request_json", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--poll-interval", type=float, default=10.0)
    parser.add_argument("--timeout", type=float, default=1800.0)
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--no-poll", action="store_true")
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Validate request structure without reading credentials or calling Ark",
    )
    return parser.parse_args()


def load_request(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("Request JSON root must be an object")
    return value


def validate_request(body: dict[str, Any]) -> None:
    model = body.get("model")
    if (
        not isinstance(model, str)
        or not model.strip()
        or "<" in model
        or model.upper().startswith("REPLACE_")
    ):
        raise RuntimeError("Set model to a real Seedance 2.0 Model ID or Endpoint ID")
    content = body.get("content")
    if not isinstance(content, list) or not content:
        raise RuntimeError("content must be a non-empty array")

    duration = body.get("duration", 5)
    if not isinstance(duration, int) or (duration != -1 and not 4 <= duration <= 15):
        raise RuntimeError("Seedance 2.0 duration must be an integer from 4 to 15, or -1")
    if "frames" in body or "seed" in body or "camera_fixed" in body:
        raise RuntimeError("Seedance 2.0 request must omit frames, seed, and camera_fixed")
    ratio = body.get("ratio", "adaptive")
    if ratio not in ALLOWED_RATIOS:
        raise RuntimeError(f"Unsupported ratio: {ratio}")
    if body.get("resolution") == "1080p" and any(
        token in model.lower() for token in ("mini", "fast")
    ):
        raise RuntimeError("The current local docs say Seedance 2.0 Mini/Fast do not support 1080p")

    image_roles = {
        item.get("role")
        for item in content
        if isinstance(item, dict) and item.get("type") == "image_url"
    }
    if "reference_image" in image_roles and image_roles & {"first_frame", "last_frame"}:
        raise RuntimeError("Do not mix multimodal reference images with first/last-frame mode")
    for item in content:
        if not isinstance(item, dict):
            raise RuntimeError("Every content item must be an object")
        if item.get("type") == "image_url" and item.get("role") != "reference_image":
            raise RuntimeError("This workflow expects image role reference_image")
        if item.get("type") == "video_url" and item.get("role") != "reference_video":
            raise RuntimeError("Reference videos must use role reference_video")


def data_url(path: Path) -> str:
    size = path.stat().st_size
    if size >= 30 * 1024 * 1024:
        raise RuntimeError(f"Local image exceeds the documented 30 MB limit: {path}")
    mime_type = mimetypes.guess_type(path.name)[0] or "image/png"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def expand_local_images(body: dict[str, Any], request_dir: Path) -> None:
    for item in body.get("content", []):
        if item.get("type") == "image_url":
            image = item.get("image_url")
            if not isinstance(image, dict) or not isinstance(image.get("url"), str):
                raise RuntimeError("image_url items require image_url.url")
            value = image["url"]
            if value.startswith(("http://", "https://", "data:", "asset://")):
                continue
            path = Path(value).expanduser()
            if not path.is_absolute():
                path = (request_dir / path).resolve()
            if not path.is_file():
                raise RuntimeError(f"Local image does not exist: {path}")
            image["url"] = data_url(path)
        elif item.get("type") == "video_url":
            video = item.get("video_url")
            if not isinstance(video, dict) or not isinstance(video.get("url"), str):
                raise RuntimeError("video_url items require video_url.url")
            value = video["url"]
            if not value.startswith(("http://", "https://", "asset://")):
                raise RuntimeError(
                    "Seedance reference_video requires a public URL or Ark asset ID; "
                    "local/base64 video is not supported by this workflow"
                )


def api_json(method: str, url: str, api_key: str, body: dict | None = None) -> dict:
    data = None
    headers = {"Authorization": f"Bearer {api_key}"}
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            payload = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Ark API HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Ark API network error: {exc.reason}") from exc
    value = json.loads(payload)
    if not isinstance(value, dict):
        raise RuntimeError("Ark API returned a non-object JSON response")
    return value


def write_json(path: Path, value: dict) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def download(url: str, destination: Path) -> None:
    try:
        with urllib.request.urlopen(url, timeout=120) as response:
            destination.write_bytes(response.read())
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Could not download generated video: {exc.reason}") from exc


def main() -> int:
    args = parse_args()
    request_path = args.request_json.expanduser().resolve()
    output_dir = args.output_dir.expanduser().resolve()
    if not request_path.is_file():
        raise RuntimeError(f"Request JSON does not exist: {request_path}")
    if args.poll_interval <= 0 or args.timeout <= 0:
        raise RuntimeError("Polling interval and timeout must be positive")

    body = load_request(request_path)
    validate_request(body)
    if args.validate_only:
        print(f"valid: {request_path}")
        return 0

    api_key = os.environ.get("ARK_API_KEY")
    if not api_key:
        raise RuntimeError("ARK_API_KEY is not set")
    expand_local_images(body, request_path.parent)
    payload_size = len(json.dumps(body, ensure_ascii=False).encode("utf-8"))
    if payload_size >= 64 * 1024 * 1024:
        raise RuntimeError("Expanded request body reaches the documented 64 MB limit")
    output_dir.mkdir(parents=True, exist_ok=True)

    submitted = api_json("POST", TASKS_URL, api_key, body)
    write_json(output_dir / "submit-response.json", submitted)
    task_id = submitted.get("id")
    if not isinstance(task_id, str) or not task_id:
        raise RuntimeError("Ark create-task response did not include id")
    print(f"task_id={task_id}")
    if args.no_poll:
        return 0

    deadline = time.monotonic() + args.timeout
    task = submitted
    while True:
        task = api_json("GET", f"{TASKS_URL}/{task_id}", api_key)
        write_json(output_dir / "task-response.json", task)
        status = str(task.get("status", "")).lower()
        print(f"status={status or 'unknown'}")
        if status in TERMINAL:
            break
        if time.monotonic() >= deadline:
            raise RuntimeError(f"Polling timed out for task {task_id}")
        time.sleep(args.poll_interval)

    if str(task.get("status", "")).lower() != "succeeded":
        error = task.get("error")
        raise RuntimeError(f"Seedance task ended without success: {error or task.get('status')}")

    video_url = (task.get("content") or {}).get("video_url")
    if not isinstance(video_url, str) or not video_url:
        raise RuntimeError("Successful Seedance response did not include content.video_url")
    print(f"video_url={video_url}")
    if args.download:
        destination = output_dir / "video.mp4"
        download(video_url, destination)
        print(destination)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
