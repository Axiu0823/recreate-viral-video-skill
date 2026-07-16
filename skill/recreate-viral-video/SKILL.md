---
name: recreate-viral-video
description: Analyze and recreate viral short-form or long-form product videos (爆款视频拆解、爆款复刻、长视频分段复刻、同品替换、跨品类复刻、TikTok/Reels/Shorts 本地化). Use when a user supplies a reference video and wants to preserve its hook, beat timing, retention devices, emotion/conflict, action, persuasion, conversion logic, and optionally authorized original dialogue or signature performance while replacing the product, actor, setting, language, country, or market; optionally analyze with the current Codex model or Gemini API, generate character/scene references with Codex image generation (gpt-image-2), divide long sources into approved Seedance-sized clips, generate them sequentially through the Seedance 2.0 API, and assemble accepted clips locally. Do not use for generic video ideation without a reference, unauthorized likeness/voice cloning, or unauthorized reuse of footage/music.
---

# Recreate Viral Video

Turn a reference video into an original, localized product video that inherits transferable performance mechanics rather than protected surface expression. Produce an auditable analysis, a recreation contract, generated reference assets, a Seedance request, and a QC report.

## Operating principles

- Preserve functions, not pixels: keep the hook mechanism, beat order, relative timing, escalation, proof pattern, and CTA logic.
- Set a source-expression policy: preserve authorized original dialogue and signature performance when requested; otherwise rewrite them. Treat dialogue, performance/choreography, likeness, voice, music, footage, and brand assets as separate rights decisions.
- Ground product claims in user-provided evidence. Do not invent medical, financial, comparative, scarcity, testimonial, or performance claims.
- Treat the first 3–5 seconds as a guaranteed high-density sequence. Also trigger dense local analysis around every cut boundary, conflict turn, reveal, proof, payoff, and CTA.
- Verify both sides of every meaningful cut before assigning scene continuity. Shared product context does not prove that background, wardrobe, props, or lighting remain the same.
- Treat product demonstrations as causal state changes. A correct end frame cannot substitute for a missing loading, sealing, activation, transformation, or proof step.
- Keep analysis and generation separate. Never let a generated storyboard overwrite observations from the source.
- State uncertainty. If audio, a cut, or on-screen text cannot be verified, mark it unknown instead of guessing.

Read [references/methodology.md](references/methodology.md) before analyzing a new reference. Read [references/prompt-library.md](references/prompt-library.md) before generating images or compiling the Seedance prompt. Read [references/toolchain.md](references/toolchain.md) before using Gemini or Seedance APIs.

## 1. Run the intake gate

Ask one compact batch containing only missing high-impact fields:

1. Reference video file or accessible URL.
2. Recreation mode: `same_category` or `cross_category`.
3. Target product name, product images, verified selling points, and prohibited claims.
4. Usage context: keep the source context, replace it, or let the skill adapt it. For `cross_category`, require the intended use context.
5. Target country/market. Infer the natural language and actor profile, then let the user override them.
6. Aspect ratio. Probe the source and active model limit before discussing duration; never offer an unsupported source duration as one Seedance generation.
7. Analysis engine: `current_model` or `gemini_api`.
8. Source-expression policy: for dialogue choose `verbatim`, `translated_same_delivery`, or `rewrite`; for signature performance choose `preserve_authorized` or `adapt`. If preserving either, record the user's rights confirmation.
9. Optional: platform, CTA/offer, actor constraints, brand rules, number of variants, and retry budget.

Do not re-ask known fields. If the user asks for end-to-end execution and inputs are sufficient, continue without a second confirmation. Before a billable Seedance submission, request confirmation only when cost, model endpoint, or retry budget is still ambiguous.

## 2. Open a project package

Create `outputs/viral-remix/<date>-<slug>/` under the active workspace unless the user specifies another location. Copy `assets/project-template.json` into it as `project.json` and keep these artifacts:

```text
source/
analysis/
assets/
generation/
segments/
final/
qc/
project.json
```

Keep API keys in environment variables only. Never write them into the project package, prompts, logs, or request JSON.

## 3. Check rights, likeness, and ad safety

Before analysis or generation:

- Confirm the reference is supplied for analysis and that the user is authorized to use the target product/brand assets.
- Default to an original adult actor. Keep source likeness and voice disabled unless the user separately confirms consent/rights and the active platform supports the authorized workflow.
- Allow verbatim dialogue, translated dialogue with the same delivery, signature gestures, choreography, and performance timing when the user selects them and confirms authorization. Do not infer that authorization from the uploaded video alone.
- Treat source footage, music, watermarks, logos, and brand assets separately. Do not reuse an item that is not user-owned, licensed, or otherwise authorized.
- Replace unsafe or policy-sensitive scenes while preserving their narrative function. Example: replace a weapon confrontation with a household urgency conflict rather than carrying the weapon into generated references.
- If the task depends on a real person or licensed character, stop and obtain the necessary permission/rights context before generation.

Record the decision in `project.json.rights_and_safety`.

## 4. Prepare and analyze the source

Run the deterministic preprocessor for local video files. It requires `ffmpeg` and `ffprobe` on `PATH`:

```bash
python3 scripts/prepare_video.py /path/reference.mp4 --output-dir /path/project/analysis/source-scan
```

It creates metadata, dense hook frames, a full-video contact sheet, extracted audio when present, and an audio waveform. Use the original video plus these artifacts; the contact sheets are a verification aid, not a substitute for audio/video inspection. If the dependency is unavailable, either install/provide it or use Gemini; do not claim dense hook verification from a single thumbnail.

### Current-model path

1. Inspect the video directly when the active surface supports video and audio understanding.
2. Always inspect `metadata.json`, `hook_contact.jpg`, and `timeline_contact.jpg` to verify duration and fast cuts.
3. If direct audio understanding is unavailable, inspect any transcript the user provides. Otherwise label auditory semantics unverified and offer the Gemini path; do not infer speech from lip movement.
4. Write `analysis/analysis.json` using the schema in `assets/gemini-analysis-prompt.txt`.

### Gemini API path

Treat an upload of a private/local video to Google as external data transfer. If the user explicitly selects Gemini, that choice authorizes the analysis upload unless the file appears confidential; for confidential material, confirm first.

```bash
GEMINI_API_KEY=... python3 scripts/gemini_video_analysis.py \
  /path/reference.mp4 \
  --output /path/project/analysis/analysis.json
```

Allow `--model` or `GEMINI_MODEL` to override the current default. The script uses Gemini Files plus the Interactions API and attempts to delete the uploaded file after analysis unless `--keep-upload` is set.

### Required eight dimensions

Analyze exactly these dimensions:

1. `hook`
2. `visual`
3. `audio`
4. `retention`
5. `emotion_conflict`
6. `action_performance`
7. `persuasion_proof`
8. `conversion`

Include a timestamped beat map and a dedicated 0–5 second hook diagnosis. Validate the result:

```bash
python3 scripts/validate_analysis.py /path/project/analysis/analysis.json
```

For every meaningful hard cut, record a `scene_boundaries` entry from dense frames immediately before and after the cut. Compare background, working surface, wardrobe, handled objects, prop geography, camera, and lighting. For every product proof, record a `causal_proof_chains` entry with the visible starting state, ordered actions, required continuous state changes, and terminal proof. Read the matching sections in [references/methodology.md](references/methodology.md).

## 5. Gate and segment long videos

Read [references/long-video-workflow.md](references/long-video-workflow.md) whenever the source exceeds the verified active Seedance duration or contains connected clips.

1. Probe the source duration and verify the active Model ID/Endpoint ID limits from the current local Ark docs.
2. If the source fits one generation, classify it as `standalone_clip` and continue.
3. If it exceeds the limit, classify it as `sequence_project`. Stop before image generation or any billable Seedance call.
4. Report the measured duration, verified maximum, mathematical minimum segment count, and a semantic recommendation.
5. Let the user provide exact ranges (`user_ranges`) or let the model propose ranges (`model_proposed`).
6. For model proposals, analyze the full source first and cut only at completed dialogue, action, camera, scene, or persuasion beats. Do not cut mid-line, mid-gesture, or during product contact.
7. Show every `start–end` range, narrative job, boundary reason, scene-boundary classification, evidence frame times, and target integer duration. Never carry continuity locks across a verified scene reset. Wait for explicit approval.
8. Save the approved plan as `analysis/segment-plan.json` and validate it:

```bash
python3 scripts/validate_segments.py /path/project/analysis/segment-plan.json --require-approved
```

9. Split the source only after approval:

```bash
python3 scripts/split_video.py /path/reference.mp4 \
  /path/project/analysis/segment-plan.json \
  --output-dir /path/project/segments/source
```

For the current local Seedance 2.0 snapshot, generated clips accept integer duration 4–15 seconds and one reference video accepts 2–15 seconds. Recheck the exact active endpoint on every job. Merge a too-short remainder into the preceding segment by moving the semantic boundary.

## 6. Build the recreation contract

Convert observations into three explicit lists:

- `preserve`: abstract mechanisms and measured timing plus any authorized exact expression, such as verbatim dialogue, signature gestures, choreography, pauses, facial beats, or blocking.
- `adapt`: product, actor, language, market, setting, props, cultural cues, legally supportable claims, and CTA.
- `forbid`: only items that are unauthorized, unsupported, unsafe, or incompatible with the target product/market. Keep likeness, voice, music, footage, logos, and dialogue as separate decisions rather than one blanket rule.

Set `source_expression_policy` before compiling the shot plan:

- `dialogue`: `verbatim`, `translated_same_delivery`, or `rewrite`.
- `signature_performance`: `preserve_authorized` or `adapt`.
- `likeness`: `original_actor` or `authorized_source_likeness`.
- `voice`: `new_voice` or `authorized_source_voice`.

For `same_category`:

- Preserve shot functions, beat order, relative shot duration, product reveal timing, demonstration logic, emotional curve, and CTA placement.
- Preserve exact dialogue and signature performance when selected and authorized; retain their timestamps, pauses, gesture order, facial beats, and camera relationship.
- Replace the product and default to a new actor and new background.
- Keep the use context only when the user selected `keep`, and localize physical details to the target market.
- Do not promise frame-for-frame identity.

For `cross_category`:

- Preserve only abstract functions: curiosity gap, pain trigger, escalation, reveal, proof, objection handling, payoff, and CTA.
- Preserve authorized dialogue or signature performance only when it still makes semantic and physical sense for the new product; otherwise translate or remap it while keeping the delivery function.
- Remap every literal action to the target product’s real use. Reject actions that do not make physical or commercial sense.
- Rebuild claims, proof, props, and setting from the target product and market.

Write the contract and shot plan to `project.json.recreation_contract`. Each shot must include start/end time, narrative job, visible action, camera, audio/dialogue, emotion, retention device, transition, and product truth source. For a product demonstration, also add a non-skippable action chain with observable start/end states and a proof requirement. Mark whether the proof needs continuous progression; do not reduce a continuous transformation to disconnected before/after frames.

Create a canonical product-identity lock from the user's original images. Apply it to every visible instance, including background units, bundles, reflections, and repeated products; allowing multiple products never allows mixed product models.

For a `sequence_project`, add a global story spine, final outcome, scene map, continuity bible, and one provisional segment card per approved range. Generate only the next unresolved segment prompt; later cards remain provisional.

## 7. Generate original reference images with Codex image generation

Use Codex’s built-in image generation tool, which currently uses `gpt-image-2`, for each asset. Generate assets in separate calls so each has one clear reference role.

1. `assets/character-white.png`: original adult actor on a seamless white background; full body or three-quarter body plus enough facial detail for identity anchoring; no product, logo, text, or copied likeness.
2. `assets/scene.png`: target-market environment only; no person and no product; match the final aspect ratio and ordinary real-world details.
3. Optional `assets/action-keyframe.png`: generate only when a difficult product interaction needs a composition anchor. Use the original product image as a reference and state which geometry must remain exact.

Use the realism prompts in [references/prompt-library.md](references/prompt-library.md). Inspect every output for hands, teeth, eyes, product geometry, readable labels, cultural errors, and accidental logos. Regenerate one defect at a time. Never accept a synthetic model sheet merely because it looks polished.

Keep the user’s original product image separate; do not rely on a regenerated packshot for product fidelity.

## 8. Compile the Seedance 2.0 request

Build one compact natural-language prompt from the approved shot plan. Keep it under the current platform guidance and put essential subject/reference bindings first.

Use this default reference order:

- `图片1`: original target product image.
- `图片2`: generated character white-background reference.
- `图片3`: generated target-market scene.
- `图片4`: optional action keyframe.
- `视频1`: optional authorized reference video, used for motion/camera/timing and, when selected, exact authorized dialogue/performance; exclude it when no public URL or Ark asset ID is available.

Pass each image with `role: reference_image` in upload order and refer to it as `图片1`…`图片n`. Pass an eligible reference video with `role: reference_video` and call it `视频1`. Do not mix `first_frame`/`last_frame` mode with multimodal reference mode.

Set reference precedence explicitly: canonical images control product, actor, wardrobe, and scene identity; reference video controls only the authorized motion, camera, timing, and performance assigned to it. If a source video contains a visually conflicting product, caption, logo, bag, wardrobe, or background that the model keeps copying, do not rely on negative wording alone. Omit that video, crop or mask the conflicting region, or create a silent low-detail motion donor and inspect it before upload. Read [references/prompt-library.md](references/prompt-library.md) for the binding pattern.

Allocate one generation to one critical physical proof. When the narrative requires several causal steps or a continuous transformation, use the minimum supported clip duration for focused micro-shots and trim them in post. A terminal anchor may constrain the desired result, but it never proves that the required process occurred.

The prompt must state the chosen expression policy. For authorized dialogue and signature performance, use:

```text
产品外观严格参考图片1；人物身份、脸部与服装参考图片2；空间、材质与光线参考图片3。严格参考视频1中的原对白文本、动作顺序、手势、停顿、表情节奏、走位、镜头配合和标志性表演，由图片2中的人物重新演绎。人物外貌、声线、音乐、原始画面和品牌素材按照各自的独立授权设置执行，不因保留对白或表演而自动复制。
```

For rewritten expression, use the abstract-reference binding in [references/prompt-library.md](references/prompt-library.md).

Use a user-configured Seedance 2.0 Model ID or Endpoint ID; do not guess one. Confirm the active model supports the chosen resolution. For the current local Ark documentation, Seedance 2.0 accepts integer duration 4–15 seconds, does not support `frames`, `seed`, or `camera_fixed`, and supports synchronized audio through `generate_audio`.

For a standalone clip, save the request as `generation/seedance-request.json`. For a sequence, save one request per segment under `generation/<segment-id>/seedance-request.json`. Each request uses only that segment's source range and narrative job.

Submit and poll the current request:

```bash
ARK_API_KEY=... python3 scripts/seedance_task.py \
  /path/project/generation/seedance-request.json \
  --output-dir /path/project/generation --download
```

Download successful output promptly because returned video URLs are temporary. Preserve the raw response and the exact prompt used.

## 9. Generate sequences one accepted segment at a time

For long video, plan globally but generate sequentially:

1. Compile and generate only the first unresolved segment.
2. Set `return_last_frame: true`.
3. Inspect the actual clip and record its observed end state.
4. Mark it `accepted` or `rejected` and record `approval_scope` as `continuation_only` or `final_segment`. Rejected footage never updates canon or becomes a parent reference. `continuation_only` is not final acceptance.
5. Let accepted footage override the planned state when they differ.
6. Inside one scene, pass the previous accepted clip and/or returned last frame as an additional multimodal reference for the next segment. Describe the required opening state; do not mix strict first/last-frame mode with multimodal reference roles.
7. At a scene boundary, use an intentional editorial cut and reopen from canonical product, character, and scene references.
8. Limit consecutive output-sourced generations to 2 by default and never exceed 3; re-anchor earlier if identity, product, geography, motion, or audio drifts.
9. Keep dialogue, sync effects, and room tone in each clip, but avoid independently regenerated music beds; unify music in post.

Do not finalize segment N+1 until segment N is accepted or deliberately replaced.

## 10. Run functional QC and iterate

Compare the generated take with the recreation contract, not pixel similarity. Record in `qc/report.json`:

- The hook mechanism is visibly established by 3 seconds and resolved or advanced by 5 seconds.
- All eight dimensions reproduce their intended function.
- Same-category beat timing stays approximately within ±15%; cross-category timing may vary up to ±25% when required by product truth.
- The product is recognizable and used physically correctly.
- Every non-skippable action is visible in order, with no object or product state appearing discontinuously between cuts.
- Every required continuous proof shows the state progression, not only a terminal result or inserted still frame.
- Scene resets match the source boundary audit; same use context is not treated as same background or wardrobe.
- Every visible product instance follows the canonical product-identity lock.
- Actor identity, anatomy, gaze, expression, skin texture, hands, and lip-sync remain plausible.
- Language sounds native to the target market; captions, if added in post, are correct and safe-area compliant.
- Claims are supported, unauthorized source assets are absent, authorized dialogue/performance follows the approved policy, and CTA is complete.
- The video contains no accidental duplicate actor, broken product geometry, invented logo, watermark, or unsafe carryover.

For a failed take, choose one action: keep, fix in post, edit, re-roll, or rewrite. Change one variable per retry and respect the user’s retry budget. Do not hide failures behind more adjectives.

Post-production may repair captions, audio balance, trims, and an already-valid hold duration. It may not convert a failed causal demonstration into a pass by inserting a desired end-state frame, hiding a skipped action, or covering a product-identity mismatch.

For sequences, run QC on every segment before continuing, then run a second QC pass on the assembled video for duplicated frames, cut timing, dialogue continuity, audio jumps, product/actor drift, scene-boundary fidelity, causal proof continuity, and total narrative flow. Recheck the full recreation contract before final acceptance; earlier continuation approvals cannot override a later global mismatch.

## 11. Assemble accepted clips locally

Codex performs final assembly; Seedance does not. Create `generation/merge-plan.json` listing accepted clips in order and any start/end trims needed to remove repeated transition frames. Validate first:

```bash
python3 scripts/merge_videos.py /path/project/generation/merge-plan.json \
  --output /path/project/final/final-video.mp4 --validate-only
```

Then merge with `ffmpeg` and `ffprobe` available on `PATH`:

```bash
python3 scripts/merge_videos.py /path/project/generation/merge-plan.json \
  --output /path/project/final/final-video.mp4
```

The script normalizes resolution, frame rate, pixel format, audio sample rate/channel layout, and loudness, then concatenates with deterministic hard or match-action cuts. It does not invent frames or regenerate accepted footage. Preserve individual clips, the merge plan, `final-video.mp4`, and `merge-report.json`.

## Deliverables

Return a concise summary and links to the project package artifacts:

- `analysis/analysis.json`
- `analysis/segment-plan.json` for long sources
- `project.json` with the recreation contract and shot plan
- generated character and scene references
- standalone request/video or per-segment requests, task responses, and accepted videos
- `generation/merge-plan.json`, `final/final-video.mp4`, and `final/merge-report.json` for sequences
- `qc/report.json`

State which analysis engine ran, which current/local documentation was checked, what was not verified, and whether a billable API call was actually made.
