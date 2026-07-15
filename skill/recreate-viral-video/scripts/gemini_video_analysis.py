#!/usr/bin/env python3
"""Analyze a local video with Gemini Files + Interactions REST APIs."""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


SKILL_DIR = Path(__file__).resolve().parent.parent
DEFAULT_PROMPT = SKILL_DIR / "assets" / "gemini-analysis-prompt.txt"
FILES_UPLOAD_URL = "https://generativelanguage.googleapis.com/upload/v1beta/files"
API_ROOT = "https://generativelanguage.googleapis.com/v1beta"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Upload a video to Gemini, request the eight-dimension analysis, and save JSON."
    )
    parser.add_argument("video", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--prompt-file", type=Path, default=DEFAULT_PROMPT)
    parser.add_argument(
        "--model",
        default=os.environ.get("GEMINI_MODEL", "gemini-3.5-flash"),
        help="Gemini video-capable model; overrides GEMINI_MODEL",
    )
    parser.add_argument("--poll-interval", type=float, default=5.0)
    parser.add_argument("--processing-timeout", type=float, default=900.0)
    parser.add_argument(
        "--keep-upload",
        action="store_true",
        help="Do not attempt to delete the uploaded Gemini file after analysis",
    )
    return parser.parse_args()


def http_json(
    method: str,
    url: str,
    headers: dict[str, str],
    data: bytes | None = None,
    *,
    timeout: float = 120.0,
) -> tuple[dict[str, Any], Any]:
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
            response_headers = response.headers
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Gemini API HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Gemini API network error: {exc.reason}") from exc
    if not raw.strip():
        return {}, response_headers
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise RuntimeError("Gemini API returned non-object JSON")
    return value, response_headers


def start_resumable_upload(video: Path, mime_type: str, api_key: str) -> str:
    metadata = json.dumps(
        {"file": {"display_name": video.name}}, ensure_ascii=False
    ).encode("utf-8")
    _, headers = http_json(
        "POST",
        FILES_UPLOAD_URL,
        {
            "x-goog-api-key": api_key,
            "X-Goog-Upload-Protocol": "resumable",
            "X-Goog-Upload-Command": "start",
            "X-Goog-Upload-Header-Content-Length": str(video.stat().st_size),
            "X-Goog-Upload-Header-Content-Type": mime_type,
            "Content-Type": "application/json",
        },
        metadata,
    )
    upload_url = headers.get("X-Goog-Upload-URL")
    if not upload_url:
        raise RuntimeError("Gemini upload start response did not include X-Goog-Upload-URL")
    return upload_url


def upload_video(upload_url: str, video: Path, mime_type: str) -> dict[str, Any]:
    payload = video.read_bytes()
    value, _ = http_json(
        "POST",
        upload_url,
        {
            "Content-Length": str(len(payload)),
            "Content-Type": mime_type,
            "X-Goog-Upload-Offset": "0",
            "X-Goog-Upload-Command": "upload, finalize",
        },
        payload,
        timeout=600.0,
    )
    file_object = value.get("file")
    if not isinstance(file_object, dict):
        raise RuntimeError("Gemini upload response did not include file")
    return file_object


def file_state(file_object: dict[str, Any]) -> str:
    state = file_object.get("state", "")
    if isinstance(state, dict):
        state = state.get("name", "")
    return str(state).upper()


def get_file(name: str, api_key: str) -> dict[str, Any]:
    value, _ = http_json(
        "GET", f"{API_ROOT}/{name}", {"x-goog-api-key": api_key}
    )
    file_object = value.get("file") if isinstance(value.get("file"), dict) else value
    return file_object


def delete_file(name: str, api_key: str) -> None:
    http_json("DELETE", f"{API_ROOT}/{name}", {"x-goog-api-key": api_key})


def interaction_text(response: dict[str, Any]) -> str:
    direct = response.get("output_text")
    if isinstance(direct, str) and direct.strip():
        return direct
    chunks: list[str] = []
    for step in response.get("steps", []):
        if not isinstance(step, dict):
            continue
        content = step.get("content", [])
        if isinstance(content, dict):
            content = [content]
        if not isinstance(content, list):
            continue
        for part in content:
            if isinstance(part, dict) and isinstance(part.get("text"), str):
                chunks.append(part["text"])
    if not chunks:
        raise RuntimeError("Gemini interaction response did not contain text")
    return "\n".join(chunks)


def parse_json_output(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()
    value = json.loads(stripped)
    if not isinstance(value, dict):
        raise ValueError("Gemini output must be one JSON object")
    return value


def main() -> int:
    args = parse_args()
    video = args.video.expanduser().resolve()
    prompt_file = args.prompt_file.expanduser().resolve()
    output = args.output.expanduser().resolve()
    api_key = os.environ.get("GEMINI_API_KEY")

    if not video.is_file():
        raise RuntimeError(f"Video does not exist: {video}")
    if not prompt_file.is_file():
        raise RuntimeError(f"Prompt file does not exist: {prompt_file}")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set")
    if args.poll_interval <= 0 or args.processing_timeout <= 0:
        raise RuntimeError("Polling interval and timeout must be positive")

    prompt = prompt_file.read_text(encoding="utf-8")
    mime_type = mimetypes.guess_type(video.name)[0] or "video/mp4"
    file_name: str | None = None

    try:
        upload_url = start_resumable_upload(video, mime_type, api_key)
        current = upload_video(upload_url, video, mime_type)
        file_name = current.get("name")
        if not isinstance(file_name, str) or not file_name:
            raise RuntimeError("Gemini file object did not include name")

        deadline = time.monotonic() + args.processing_timeout
        while file_state(current) not in {"ACTIVE", "FAILED"}:
            if time.monotonic() >= deadline:
                raise RuntimeError("Gemini file processing timed out")
            time.sleep(args.poll_interval)
            current = get_file(file_name, api_key)
        if file_state(current) == "FAILED":
            raise RuntimeError("Gemini file processing failed")

        uri = current.get("uri")
        if not isinstance(uri, str) or not uri:
            raise RuntimeError("Gemini active file did not include uri")
        file_mime = current.get("mimeType") or current.get("mime_type") or mime_type
        request_body = {
            "model": args.model,
            "input": [
                {"type": "video", "uri": uri, "mime_type": file_mime},
                {"type": "text", "text": prompt},
            ],
        }
        interaction, _ = http_json(
            "POST",
            f"{API_ROOT}/interactions",
            {"x-goog-api-key": api_key, "Content-Type": "application/json"},
            json.dumps(request_body, ensure_ascii=False).encode("utf-8"),
            timeout=600.0,
        )
        result = parse_json_output(interaction_text(interaction))
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(output)
        return 0
    finally:
        if file_name is not None and not args.keep_upload:
            try:
                delete_file(file_name, api_key)
            except Exception as exc:  # best effort; do not hide a valid analysis
                print(f"warning: could not delete Gemini upload: {exc}", file=sys.stderr)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
