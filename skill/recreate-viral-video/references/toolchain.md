# Toolchain and verified API notes

## Contents

1. Source analysis modes
2. Codex image generation
3. Gemini API
4. Seedance 2.0 API
5. Local video assembly
6. Official source routing

## Source analysis modes

### Current model

Use direct video/audio understanding when the active Codex surface exposes it. Run `scripts/prepare_video.py` for metadata and dense hook verification; it requires `ffmpeg` and `ffprobe` on `PATH`. If they are unavailable, provide/install them or switch to Gemini rather than pretending one thumbnail verifies a rapid hook. If the active surface cannot inspect the audio stream, do not call the audio dimension verified; use a supplied transcript or switch to Gemini.

### Gemini API

The implementation follows Google AI for Developers' current video-understanding flow: upload with the Files API, poll until active, then pass the file URI to the Interactions API. As checked on 2026-07-15, the official example used `gemini-3.5-flash`; the script allows `--model`/`GEMINI_MODEL` override because access and model names are volatile.

Requirements:

- `GEMINI_API_KEY` environment variable.
- User awareness that a local/private video is uploaded to Google.

The bundled script uses only the Python standard library and the official REST flow; no Gemini SDK installation is required.

The official guide notes that video understanding samples visual content by default; fast hooks may require local dense-frame verification. This is why the preprocessor samples the first five seconds at four frames per second.

## Codex image generation

Codex built-in image generation currently uses `gpt-image-2`. Invoke the image-generation capability directly (or `$imagegen` where appropriate) rather than building a second OpenAI API integration. Generate the character and scene separately, inspect each result, and keep the original product image as its own Seedance reference.

## Seedance 2.0 API

Official Ark documentation snapshots checked on 2026-07-15:

- Create: `POST https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks`
- Query: `GET https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks/{id}`
- Auth: `Authorization: Bearer $ARK_API_KEY`
- Success statuses: `queued`, `running`, `succeeded`; terminal failures include `failed` and `expired`.
- Successful `content.video_url` is temporary; local docs state 24 hours.

Seedance 2.0 series request facts from the local snapshot:

- `content` can include text, 1–9 reference images, 0–3 reference videos, and 0–3 reference audio items.
- Image reference role: `reference_image`; number images by upload order as `图片1`…`图片n` in the prompt.
- Video reference role: `reference_video`; single reference videos must be 2–15 seconds and use a public URL or Ark asset ID.
- Multimodal reference mode and strict `first_frame`/`last_frame` mode are mutually exclusive.
- `duration`: integer 4–15 or `-1` for the series.
- `frames`, `seed`, and `camera_fixed` are not supported by the series snapshot.
- `generate_audio: true` asks for synchronized voice, sound effects, and music; dialogue should be quoted.
- `return_last_frame: true` returns a temporary last-frame URL for continuity workflows.
- `ratio`: `16:9`, `4:3`, `1:1`, `3:4`, `9:16`, `21:9`, or `adaptive`.
- Default resolution is `720p`; model variants differ on `1080p` and `4k`, so verify the exact active Model ID/Endpoint ID.
- Avoid a guessed model string. Require the user's actual Model ID or Endpoint ID.
- Local images may be submitted as data URLs within documented request-size limits. Local reference video cannot be embedded as base64 under the current video-input contract; upload it first or omit it and rely on the beat map.
- Seedance 2.0 face-reference access can require platform-approved, generated, preset, or authorized real-person materials. If a face input is rejected, do not evade the control; use an original generated adult identity or the platform's authorized workflow.

## Local video assembly

Seedance generates clips but does not perform this workflow's final assembly. Codex runs `scripts/merge_videos.py` locally after all clips are accepted. The script requires `ffmpeg` and `ffprobe` on `PATH`; it normalizes accepted media and concatenates it with deterministic hard or match-action cuts. Do not call assembly complete when those dependencies are unavailable or when only a schema validation ran.

## Official source routing

Before changing Seedance fields or model IDs, read [seedance-official-docs.md](seedance-official-docs.md), then re-open the linked official material:

1. `创建视频生成任务 API`
2. `Doubao Seedance 2.0 系列提示词指南`
3. The current Ark model/endpoint page when account-specific capability differs from the public guide.

Do not treat pricing, account balance requirements, availability, rate limits, or old model names as durable facts. Recheck them when they matter.
