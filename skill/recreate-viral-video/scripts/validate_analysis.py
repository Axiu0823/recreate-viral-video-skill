#!/usr/bin/env python3
"""Validate the structural invariants of an eight-dimension video analysis."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path


DIMENSIONS = {
    "hook",
    "visual",
    "audio",
    "retention",
    "emotion_conflict",
    "action_performance",
    "persuasion_proof",
    "conversion",
}

SCENE_BOUNDARY_CLASSIFICATIONS = {"same_scene", "new_scene"}
PROOF_CONTINUITIES = {"continuous", "editorial_cut_allowed"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate analysis.json")
    parser.add_argument("analysis", type=Path)
    return parser.parse_args()


def number(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    result = float(value)
    return result if math.isfinite(result) else None


def validate_confidence(value: object, label: str, errors: list[str]) -> None:
    parsed = number(value)
    if parsed is None or not 0 <= parsed <= 1:
        errors.append(f"{label}.confidence must be between 0 and 1")


def main() -> int:
    args = parse_args()
    path = args.analysis.expanduser().resolve()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"error: file does not exist: {path}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as exc:
        print(f"error: invalid JSON: {exc}", file=sys.stderr)
        return 1

    errors: list[str] = []
    if not isinstance(data, dict):
        errors.append("root must be an object")
        data = {}

    summary = data.get("source_summary")
    if not isinstance(summary, dict):
        errors.append("source_summary must be an object")
    else:
        duration = number(summary.get("duration_s"))
        if duration is None or duration <= 0:
            errors.append("source_summary.duration_s must be positive")
        validate_confidence(summary.get("confidence"), "source_summary", errors)

    hook = data.get("hook_0_5s")
    if not isinstance(hook, dict):
        errors.append("hook_0_5s must be an object")
    else:
        micro_beats = hook.get("micro_beats")
        if not isinstance(micro_beats, list) or not micro_beats:
            errors.append("hook_0_5s.micro_beats must be a non-empty array")
        else:
            for index, beat in enumerate(micro_beats):
                if not isinstance(beat, dict):
                    errors.append(f"hook micro beat {index} must be an object")
                    continue
                start = number(beat.get("start_s"))
                end = number(beat.get("end_s"))
                if start is None or end is None or start < 0 or end <= start or end > 5.25:
                    errors.append(
                        f"hook micro beat {index} must have 0 <= start < end <= 5.25"
                    )
                validate_confidence(beat.get("confidence"), f"hook micro beat {index}", errors)

    timeline = data.get("timeline")
    if not isinstance(timeline, list) or not timeline:
        errors.append("timeline must be a non-empty array")
    else:
        previous_start = -1.0
        for index, beat in enumerate(timeline):
            if not isinstance(beat, dict):
                errors.append(f"timeline beat {index} must be an object")
                continue
            start = number(beat.get("start_s"))
            end = number(beat.get("end_s"))
            if start is None or end is None or start < 0 or end <= start:
                errors.append(f"timeline beat {index} must have 0 <= start < end")
            elif start < previous_start:
                errors.append("timeline beats must be sorted by start_s")
            else:
                previous_start = start
            validate_confidence(beat.get("confidence"), f"timeline beat {index}", errors)

    scene_boundaries = data.get("scene_boundaries")
    if not isinstance(scene_boundaries, list):
        errors.append("scene_boundaries must be an array")
    else:
        for index, boundary in enumerate(scene_boundaries):
            label = f"scene_boundaries[{index}]"
            if not isinstance(boundary, dict):
                errors.append(f"{label} must be an object")
                continue
            at_s = number(boundary.get("at_s"))
            if at_s is None or at_s <= 0:
                errors.append(f"{label}.at_s must be positive")
            for side in ("before_observation", "after_observation"):
                if not isinstance(boundary.get(side), dict):
                    errors.append(f"{label}.{side} must be an object")
            if not isinstance(boundary.get("changed_dimensions"), list):
                errors.append(f"{label}.changed_dimensions must be an array")
            if boundary.get("classification") not in SCENE_BOUNDARY_CLASSIFICATIONS:
                errors.append(f"{label}.classification is invalid")
            evidence = boundary.get("evidence_frame_times_s")
            if not isinstance(evidence, list) or len(evidence) < 2:
                errors.append(f"{label}.evidence_frame_times_s must contain both sides")
            elif any(number(value) is None or float(value) < 0 for value in evidence):
                errors.append(f"{label}.evidence_frame_times_s must contain non-negative numbers")
            validate_confidence(boundary.get("confidence"), label, errors)

    proof_chains = data.get("causal_proof_chains")
    if not isinstance(proof_chains, list):
        errors.append("causal_proof_chains must be an array")
    else:
        for index, chain in enumerate(proof_chains):
            label = f"causal_proof_chains[{index}]"
            if not isinstance(chain, dict):
                errors.append(f"{label} must be an object")
                continue
            start = number(chain.get("start_s"))
            end = number(chain.get("end_s"))
            if start is None or end is None or start < 0 or end <= start:
                errors.append(f"{label} must have 0 <= start_s < end_s")
            for required in ("claim_or_belief_shift", "visible_start_state", "terminal_proof"):
                if not isinstance(chain.get(required), str) or not chain[required].strip():
                    errors.append(f"{label}.{required} is required")
            if not isinstance(chain.get("must_show_progression"), bool):
                errors.append(f"{label}.must_show_progression must be boolean")
            steps = chain.get("steps")
            if not isinstance(steps, list) or not steps:
                errors.append(f"{label}.steps must be a non-empty array")
            else:
                for step_index, step in enumerate(steps):
                    step_label = f"{label}.steps[{step_index}]"
                    if not isinstance(step, dict):
                        errors.append(f"{step_label} must be an object")
                        continue
                    if step.get("order") != step_index + 1:
                        errors.append(f"{step_label}.order must equal {step_index + 1}")
                    for required in ("action", "required_visible_end_state"):
                        if not isinstance(step.get(required), str) or not step[required].strip():
                            errors.append(f"{step_label}.{required} is required")
                    if step.get("continuity") not in PROOF_CONTINUITIES:
                        errors.append(f"{step_label}.continuity is invalid")
            validate_confidence(chain.get("confidence"), label, errors)

    dimensions = data.get("dimensions")
    if not isinstance(dimensions, dict):
        errors.append("dimensions must be an object")
    else:
        keys = set(dimensions)
        missing = sorted(DIMENSIONS - keys)
        extra = sorted(keys - DIMENSIONS)
        if missing:
            errors.append(f"missing dimensions: {', '.join(missing)}")
        if extra:
            errors.append(f"unexpected dimensions: {', '.join(extra)}")
        for key in DIMENSIONS & keys:
            value = dimensions[key]
            if not isinstance(value, dict):
                errors.append(f"dimensions.{key} must be an object")
                continue
            for required in ("observation", "function", "transfer_rule", "evidence_timestamps"):
                if required not in value:
                    errors.append(f"dimensions.{key}.{required} is required")
            validate_confidence(value.get("confidence"), f"dimensions.{key}", errors)

    for key in (
        "transferable_genes",
        "safety_rights_claim_risks",
        "unknowns",
    ):
        if not isinstance(data.get(key), list):
            errors.append(f"{key} must be an array")

    rights_sensitive = data.get("rights_sensitive_elements")
    legacy_rights_sensitive = data.get("surface_elements_do_not_copy")
    if not isinstance(rights_sensitive, list) and not isinstance(legacy_rights_sensitive, list):
        errors.append("rights_sensitive_elements must be an array")

    source_expression = data.get("source_expression")
    if not isinstance(source_expression, dict):
        errors.append("source_expression must be an object")
    else:
        for key in ("dialogue_segments", "signature_performance_segments"):
            segments = source_expression.get(key)
            if not isinstance(segments, list):
                errors.append(f"source_expression.{key} must be an array")
                continue
            for index, segment in enumerate(segments):
                if not isinstance(segment, dict):
                    errors.append(f"source_expression.{key}[{index}] must be an object")
                    continue
                start = number(segment.get("start_s"))
                end = number(segment.get("end_s"))
                if start is None or end is None or start < 0 or end <= start:
                    errors.append(
                        f"source_expression.{key}[{index}] must have 0 <= start < end"
                    )
                validate_confidence(
                    segment.get("confidence"),
                    f"source_expression.{key}[{index}]",
                    errors,
                )

    recommendations = data.get("transfer_recommendations")
    if not isinstance(recommendations, dict):
        errors.append("transfer_recommendations must be an object")
    else:
        for key in ("same_category", "cross_category"):
            if not isinstance(recommendations.get(key), list):
                errors.append(f"transfer_recommendations.{key} must be an array")

    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        return 1

    print(f"valid: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
