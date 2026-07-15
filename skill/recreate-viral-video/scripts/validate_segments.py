#!/usr/bin/env python3
"""Validate a complete, generation-safe long-video segment plan."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any


def finite_number(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    parsed = float(value)
    return parsed if math.isfinite(parsed) else None


def load_and_validate(
    path: Path, *, require_approved: bool = False, tolerance: float = 0.05
) -> tuple[dict[str, Any], list[str]]:
    try:
        plan = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}, [f"file does not exist: {path}"]
    except json.JSONDecodeError as exc:
        return {}, [f"invalid JSON: {exc}"]
    if not isinstance(plan, dict):
        return {}, ["root must be an object"]

    errors: list[str] = []
    source_duration = finite_number(plan.get("source_duration_s"))
    model_min = finite_number(plan.get("model_min_duration_s"))
    model_max = finite_number(plan.get("model_max_duration_s"))
    reference_min = finite_number(plan.get("reference_video_min_duration_s", 2))
    reference_max = finite_number(plan.get("reference_video_max_duration_s"))
    if source_duration is None or source_duration <= 0:
        errors.append("source_duration_s must be positive")
    if model_min is None or model_min <= 0:
        errors.append("model_min_duration_s must be positive")
    if model_max is None or model_min is not None and model_max < model_min:
        errors.append("model_max_duration_s must be >= model_min_duration_s")
    if reference_min is None or reference_min <= 0:
        errors.append("reference_video_min_duration_s must be positive")
    if reference_max is None or reference_min is not None and reference_max < reference_min:
        errors.append("reference_video_max_duration_s must be >= reference_video_min_duration_s")
    if require_approved and plan.get("approved") is not True:
        errors.append("segment plan must be approved before splitting or generation")
    if plan.get("segmentation_mode") not in {"user_ranges", "model_proposed"}:
        errors.append("segmentation_mode must be user_ranges or model_proposed")

    segments = plan.get("segments")
    if not isinstance(segments, list) or not segments:
        errors.append("segments must be a non-empty array")
        return plan, errors

    seen_ids: set[str] = set()
    previous_end: float | None = None
    previous_id: str | None = None
    for index, segment in enumerate(segments):
        label = f"segments[{index}]"
        if not isinstance(segment, dict):
            errors.append(f"{label} must be an object")
            continue
        segment_id = segment.get("segment_id")
        if not isinstance(segment_id, str) or not segment_id:
            errors.append(f"{label}.segment_id is required")
        elif segment_id in seen_ids:
            errors.append(f"duplicate segment_id: {segment_id}")
        else:
            seen_ids.add(segment_id)
        sequence_index = segment.get("sequence_index")
        if isinstance(sequence_index, bool) or not isinstance(sequence_index, int):
            errors.append(f"{label}.sequence_index must be an integer")
        elif sequence_index != index + 1:
            errors.append(f"{label}.sequence_index must equal {index + 1}")
        parent_id = segment.get("parent_segment_id")
        if index == 0 and parent_id is not None:
            errors.append("first segment parent_segment_id must be null")
        if index > 0 and parent_id != previous_id:
            errors.append(f"{label}.parent_segment_id must reference the previous segment")
        start = finite_number(segment.get("source_start_s"))
        end = finite_number(segment.get("source_end_s"))
        target = segment.get("target_duration_s")
        if start is None or end is None or start < 0 or end <= start:
            errors.append(f"{label} must have 0 <= source_start_s < source_end_s")
        else:
            span = end - start
            if reference_min is not None and span + tolerance < reference_min:
                errors.append(f"{label} source span is below reference-video minimum")
            if reference_max is not None and span - tolerance > reference_max:
                errors.append(f"{label} source span exceeds reference-video maximum")
            if previous_end is None:
                if abs(start) > tolerance:
                    errors.append("first segment must start at 0")
            elif abs(start - previous_end) > tolerance:
                relation = "gap" if start > previous_end else "overlap"
                errors.append(f"{label} has a {relation} against the previous segment")
            previous_end = end
        if isinstance(target, bool) or not isinstance(target, int):
            errors.append(f"{label}.target_duration_s must be an integer")
        elif model_min is not None and model_max is not None and not model_min <= target <= model_max:
            errors.append(f"{label}.target_duration_s is outside model limits")
        for required in (
            "scene_id",
            "narrative_job",
            "felt_intent",
            "boundary_reason",
            "planned_start_state",
            "planned_end_state",
            "status",
        ):
            if not isinstance(segment.get(required), str) or not segment[required].strip():
                errors.append(f"{label}.{required} is required")
        if segment.get("status") not in {
            "proposed",
            "approved",
            "generating",
            "accepted",
            "rejected",
            "replaced",
        }:
            errors.append(f"{label}.status is invalid")
        elif require_approved and segment.get("status") not in {"approved", "accepted", "replaced"}:
            errors.append(f"{label}.status must be approved before splitting")
        if isinstance(segment_id, str) and segment_id:
            previous_id = segment_id

    if (
        source_duration is not None
        and previous_end is not None
        and abs(previous_end - source_duration) > tolerance
    ):
        errors.append("last segment must end at source_duration_s")
    return plan, errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate a long-video segment plan")
    parser.add_argument("plan", type=Path)
    parser.add_argument("--require-approved", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    path = args.plan.expanduser().resolve()
    _, errors = load_and_validate(path, require_approved=args.require_approved)
    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        return 1
    print(f"valid: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
