# Long-video segmentation and assembly

## Contents

1. Long-video gate
2. Segmentation proposal
3. Segment and scene state
4. Sequential generation
5. Continuity handoff
6. Deterministic assembly

## Long-video gate

Probe the source duration before asking for a target duration. Verify the exact active Seedance model or endpoint limits from current local documentation. For the current Seedance 2.0 snapshot:

- generated clip duration: integer 4–15 seconds or `-1`;
- one reference video: 2–15 seconds;
- all reference videos in one request: no more than 15 seconds total.

When the source exceeds the active generation limit, stop before image generation or a billable video request and report:

- measured source duration;
- verified minimum and maximum generated-clip duration;
- minimum mathematical segment count `ceil(source_duration / max_duration)`;
- recommended semantic segment count;
- any remainder that cannot form a valid final segment.

Do not promise one generation matching a duration beyond the active limit.

## Segmentation proposal

Support two modes:

- `user_ranges`: validate the exact start/end ranges supplied by the user.
- `model_proposed`: analyze the whole source first, propose ranges, explain every boundary, and wait for user approval.

Prefer semantic boundaries over equal-length slices:

- end of a spoken clause or deliberate pause;
- completion of a hand/product action;
- camera cut or motivated transition;
- scene, location, or time change;
- conflict, reveal, proof, payoff, or CTA boundary.

Do not cut mid-word, mid-gesture, during product contact, during an open camera move, or between a claim and its visible proof. Merge a remainder shorter than the supported minimum into the preceding segment and move the earlier boundary if necessary.

Use dense inspection around every proposed boundary. The first 3–5 seconds remain a guaranteed hook pass, but every conflict turn, reveal, proof, CTA, and cut boundary may also trigger dense local analysis.

Store the approved plan in `analysis/segment-plan.json` and validate it with `scripts/validate_segments.py`.

## Segment and scene state

Plan globally and generate locally. Every segment must include:

- `segment_id`, source start/end, and integer target duration;
- `scene_id`, `sequence_index`, and `parent_segment_id`;
- one narrative job and one felt intent;
- planned start/end state;
- already completed beats and beats reserved for later;
- dialogue/performance policy;
- continuity locks and allowed changes;
- boundary reason and transition type;
- status: `proposed`, `approved`, `generating`, `accepted`, `rejected`, or `replaced`.

Treat a scene as the re-anchor unit. Open a new scene from canonical product, character, and environment references. Chain accepted output only inside a scene. Default maximum output-sourced chain depth to 2 and never exceed 3; re-anchor earlier when identity, product, geography, motion, or audio drifts.

## Sequential generation

Compile only the next unresolved segment. Later prompts remain provisional until the preceding generated clip is accepted.

For every segment:

1. Extract or timestamp the matching source range.
2. Compile one Seedance prompt and one request using the segment's reference video plus canonical images.
3. Set `return_last_frame: true`.
4. Generate and download the clip.
5. Inspect the actual start/end state, dialogue, action, product geometry, and audio.
6. Mark the clip accepted or rejected.
7. Update canon only from accepted footage.
8. Compile the next prompt from the observed end state.

Rejected footage never becomes a parent source. If the previous accepted clip ends differently from the plan, observed footage overrides planned state.

## Continuity handoff

For a continuation inside one scene, use the previous accepted video and/or returned last frame as an additional multimodal reference. In multimodal reference mode, pass the last frame as `reference_image` and describe it as the required opening state; do not mix strict `first_frame`/`last_frame` roles with other multimodal reference roles.

Carry forward:

- identity and wardrobe;
- product state, orientation, and which hand holds it;
- body position, gaze, open gesture, and motion direction;
- camera height, lens feel, position, and movement phase;
- environment, light direction, time, and prop geography;
- dialogue/audio phase and room tone;
- completed beats that must not replay.

Use editorial cuts at scene boundaries. Do not promise seamless continuity across a scene change.

## Deterministic assembly

Codex, not Seedance, performs final assembly. Use `scripts/merge_videos.py` after every segment is accepted.

Default to hard cuts or match-action cuts. Record trims in `generation/merge-plan.json` to remove duplicate opening/ending frames. Normalize resolution, frame rate, pixel format, audio sample rate, channel layout, and clip loudness before concatenation.

Generate clips with dialogue, sync effects, and room tone, but avoid a separately regenerated music bed in every segment. Add or unify campaign music in post when available; independent generated music will not remain continuous across clips.

The merge step must not invent frames or regenerate content. It may trim, normalize, concatenate, and mux accepted media. Preserve the individual accepted clips, merge plan, final file, and merge report.
