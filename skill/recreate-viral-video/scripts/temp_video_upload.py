#!/usr/bin/env python3
"""Upload one local video to tmpfile.link and return a verified temporary URL."""

from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import mimetypes
import secrets
import shutil
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


UPLOAD_HOST = "tmpfile.link"
UPLOAD_PATH = "/api/upload"
MAX_FILE_BYTES = 100_000_000
ANONYMOUS_RETENTION_DAYS = 7
CHUNK_BYTES = 1024 * 1024
MAX_RESPONSE_BYTES = 1024 * 1024
VIDEO_SUFFIXES = {
    ".avi",
    ".m4v",
    ".mkv",
    ".mov",
    ".mp4",
    ".mpeg",
    ".mpg",
    ".ts",
    ".webm",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Upload one local video to tmpfile.link and verify its public URL."
    )
    parser.add_argument("video", type=Path)
    parser.add_argument("--output", type=Path, help="Optional JSON metadata output")
    parser.add_argument("--timeout", type=float, default=300.0)
    parser.add_argument(
        "--confirm-external-upload",
        action="store_true",
        help="Confirm that this video may be transferred to the third-party host",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Validate the local video without uploading it",
    )
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(CHUNK_BYTES):
            digest.update(chunk)
    return digest.hexdigest()


def inspect_video(path: Path) -> dict[str, Any]:
    resolved = path.expanduser().resolve()
    if not resolved.is_file():
        raise RuntimeError(f"Video does not exist: {resolved}")
    size = resolved.stat().st_size
    if size <= 0:
        raise RuntimeError("Video is empty")
    if size > MAX_FILE_BYTES:
        raise RuntimeError(
            f"Video exceeds tmpfile.link's 100 MB limit: {size} bytes"
        )
    suffix = resolved.suffix.lower()
    if suffix not in VIDEO_SUFFIXES:
        raise RuntimeError(f"Unsupported video extension: {suffix or '(none)'}")

    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        raise RuntimeError("ffprobe is required to confirm that the file contains video")
    completed = subprocess.run(
        [
            ffprobe,
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "format=duration,format_name:stream=codec_name,width,height",
            "-of",
            "json",
            str(resolved),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or "unknown ffprobe error"
        raise RuntimeError(f"ffprobe could not read the video: {detail}")
    try:
        probe = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("ffprobe returned invalid JSON") from exc
    streams = probe.get("streams") if isinstance(probe, dict) else None
    if not isinstance(streams, list) or not streams or not isinstance(streams[0], dict):
        raise RuntimeError("File does not contain a readable video stream")
    stream = streams[0]
    format_info = probe.get("format") if isinstance(probe.get("format"), dict) else {}
    try:
        duration = float(format_info.get("duration"))
    except (TypeError, ValueError) as exc:
        raise RuntimeError("Video duration is unavailable") from exc
    if duration <= 0:
        raise RuntimeError("Video duration must be positive")
    mime_type = mimetypes.guess_type(resolved.name)[0] or "application/octet-stream"
    return {
        "path": resolved,
        "file_name": resolved.name,
        "size_bytes": size,
        "mime_type": mime_type,
        "sha256": sha256_file(resolved),
        "duration_s": duration,
        "codec": str(stream.get("codec_name") or "unknown"),
        "width": stream.get("width"),
        "height": stream.get("height"),
    }


def safe_ascii_filename(name: str, suffix: str) -> str:
    cleaned = name.replace("\r", "_").replace("\n", "_").replace('"', "_")
    ascii_name = cleaned.encode("ascii", errors="ignore").decode("ascii").strip()
    return ascii_name or f"video{suffix}"


def upload_video(info: dict[str, Any], *, timeout: float = 300.0) -> dict[str, Any]:
    if timeout <= 0:
        raise RuntimeError("Timeout must be positive")
    path = info["path"]
    if not isinstance(path, Path):
        raise RuntimeError("Validated upload info is missing the local path")
    boundary = f"----recreate-viral-video-{secrets.token_hex(16)}"
    fallback = safe_ascii_filename(path.name, path.suffix.lower())
    encoded_name = urllib.parse.quote(path.name, safe="")
    preamble = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{fallback}"; '
        f"filename*=UTF-8''{encoded_name}\r\n"
        f"Content-Type: {info['mime_type']}\r\n\r\n"
    ).encode("utf-8")
    closing = f"\r\n--{boundary}--\r\n".encode("ascii")
    content_length = len(preamble) + int(info["size_bytes"]) + len(closing)

    connection = http.client.HTTPSConnection(UPLOAD_HOST, timeout=timeout)
    try:
        connection.putrequest("POST", UPLOAD_PATH)
        connection.putheader("Accept", "application/json")
        connection.putheader("Content-Type", f"multipart/form-data; boundary={boundary}")
        connection.putheader("Content-Length", str(content_length))
        connection.putheader("User-Agent", "recreate-viral-video-skill/1")
        connection.endheaders()
        connection.send(preamble)
        with path.open("rb") as handle:
            while chunk := handle.read(CHUNK_BYTES):
                connection.send(chunk)
        connection.send(closing)
        response = connection.getresponse()
        payload = response.read(MAX_RESPONSE_BYTES + 1)
    except (OSError, http.client.HTTPException) as exc:
        raise RuntimeError(f"tmpfile.link upload failed: {exc}") from exc
    finally:
        connection.close()

    if len(payload) > MAX_RESPONSE_BYTES:
        raise RuntimeError("tmpfile.link returned an unexpectedly large response")
    text = payload.decode("utf-8", errors="replace")
    if not 200 <= response.status < 300:
        raise RuntimeError(f"tmpfile.link HTTP {response.status}: {text}")
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        raise RuntimeError("tmpfile.link returned invalid JSON") from exc
    if not isinstance(value, dict):
        raise RuntimeError("tmpfile.link returned a non-object JSON response")
    return value


def is_allowed_download_url(value: object) -> bool:
    if not isinstance(value, str) or not value:
        return False
    parsed = urllib.parse.urlparse(value)
    host = (parsed.hostname or "").lower()
    return parsed.scheme == "https" and (
        host == "d.tmpfile.link"
        or host == "tmpfile.link"
        or host.endswith(".tfdl.net")
    )


def extract_download_urls(response: dict[str, Any]) -> list[str]:
    candidates: list[str] = []
    for key in ("downloadLinkEncoded", "downloadLink"):
        value = response.get(key)
        if is_allowed_download_url(value) and value not in candidates:
            candidates.append(value)
    if not candidates:
        raise RuntimeError("tmpfile.link response did not include an allowed download URL")
    return candidates


def verify_download_url(url: str, *, timeout: float = 60.0) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "video/*,application/octet-stream;q=0.8",
            "Range": "bytes=0-0",
            "User-Agent": "recreate-viral-video-skill/1",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            response.read(1)
            status = response.status
            final_url = response.geturl()
            content_type = response.headers.get("Content-Type", "")
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"Temporary URL verification returned HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Temporary URL verification failed: {exc.reason}") from exc
    if status not in {200, 206}:
        raise RuntimeError(f"Temporary URL verification returned HTTP {status}")
    if not is_allowed_download_url(final_url):
        raise RuntimeError("Temporary URL redirected outside the allowed host")
    return {
        "verified": True,
        "http_status": status,
        "final_url": final_url,
        "content_type": content_type,
    }


def upload_and_verify(
    video: Path | dict[str, Any], *, timeout: float = 300.0
) -> dict[str, Any]:
    info = inspect_video(video) if isinstance(video, Path) else video
    response = upload_video(info, timeout=timeout)
    last_error: RuntimeError | None = None
    verification: dict[str, Any] | None = None
    download_url = ""
    for candidate in extract_download_urls(response):
        try:
            verification = verify_download_url(candidate, timeout=min(timeout, 60.0))
            download_url = candidate
            break
        except RuntimeError as exc:
            last_error = exc
    if verification is None:
        raise last_error or RuntimeError("Could not verify the temporary URL")

    uploaded_at = datetime.now(timezone.utc).replace(microsecond=0)
    expected_expires_at = uploaded_at + timedelta(days=ANONYMOUS_RETENTION_DAYS)
    return {
        "provider": "tmpfile.link",
        "upload_mode": "anonymous",
        "file_name": info["file_name"],
        "size_bytes": info["size_bytes"],
        "mime_type": info["mime_type"],
        "sha256": info["sha256"],
        "duration_s": info["duration_s"],
        "codec": info["codec"],
        "width": info["width"],
        "height": info["height"],
        "download_url": download_url,
        "uploaded_at": uploaded_at.isoformat(),
        "expected_expires_at": expected_expires_at.isoformat(),
        "retention_note": "Anonymous uploads are expected to expire after 7 days.",
        "verification": verification,
    }


def write_json(path: Path, value: dict[str, Any]) -> None:
    destination = path.expanduser().resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def main() -> int:
    args = parse_args()
    info = inspect_video(args.video)
    if args.validate_only:
        print(
            f"valid: {info['file_name']} {info['size_bytes']} bytes "
            f"{info['duration_s']:.3f}s"
        )
        return 0
    if not args.confirm_external_upload:
        raise RuntimeError(
            "Uploading sends the video to tmpfile.link. "
            "Re-run with --confirm-external-upload after authorization."
        )
    record = upload_and_verify(info, timeout=args.timeout)
    if args.output:
        write_json(args.output, record)
        print(f"metadata={args.output.expanduser().resolve()}")
    print(f"download_url={record['download_url']}")
    print(f"expected_expires_at={record['expected_expires_at']}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
