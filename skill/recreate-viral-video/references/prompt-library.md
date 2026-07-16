# Prompt library

## Contents

1. Analysis compiler
2. Character reference
3. Scene reference
4. Action keyframe
5. Motion-reference binding
6. Causal-proof compiler
7. Seedance compiler
8. Continuation compiler
9. Negative constraints

## Analysis compiler

Use the full JSON contract in `assets/gemini-analysis-prompt.txt` for Gemini and current-model analysis. Add the project facts after the contract:

```text
Target mode: {same_category|cross_category}
Target product: {product}
Target market: {country/market}
Target language: {language}
Target ratio/duration: {ratio}/{seconds}
Known product facts: {verified facts}
```

Do not let target facts contaminate source observations. Complete source analysis first, then write transfer recommendations.

## Character reference

Generate a new adult identity rather than an altered copy of the source actor.

```text
Create an identity-reference photograph of one original adult {gender/presentation, approximate age, target-market context}. Seamless pure white background, {full-body or three-quarter body}, relaxed neutral stance with hands clearly visible, direct but natural gaze, simple unbranded everyday clothing suited to {market and scenario}. Preserve human realism: visible pores and fine skin texture, subtle facial asymmetry, natural under-eye folds, tiny flyaway hairs, realistic teeth and eye moisture, slight fabric wrinkles, anatomically correct hands and joints, restrained grooming, no beauty filter, no glamour retouching. Even soft daylight-balanced studio illumination, accurate skin tone, moderate depth of field, no product, no prop, no logo, no text, no watermark, no collage, exactly one person.
```

If the final clip needs expressive acting, keep the identity sheet neutral and specify performance later in the video prompt. A dramatic expression in the identity sheet can destabilize facial consistency.

Reject waxy skin, airbrushed pores, perfect bilateral symmetry, oversized eyes, plastic teeth, duplicated fingers, fused garments, fashion-editorial posing, excessive bokeh, and cinematic teal-orange grading.

## Scene reference

```text
Create a photorealistic empty {room/store/outdoor setting} in {target market} for a vertical {ratio} user-generated product video. Camera position and eye level: {shot-plan anchor}. Use ordinary practical lighting from {motivated source}; include region-accurate architecture, outlets, fixtures, materials, everyday clutter, wear, and small imperfections. The space must feel inhabited but currently empty, with clean negative space where one actor will stand and use a product. Natural phone-camera dynamic range, plausible color temperature, straight geometry, no person, no product, no brand, no readable text, no poster, no watermark, no luxury styling unless required by the product.
```

The scene image defines environment only. Do not generate the actor into it unless an action keyframe is explicitly required.

## Action keyframe

Use only for difficult hand-object interactions:

```text
Using the supplied target product reference, create one photorealistic keyframe of the original adult character performing {single physically correct action} in the supplied scene. Keep the product silhouette, proportions, material, color, control placement, and attachments faithful to the reference. Show both hands clearly with plausible grip and contact points. Frame for {ratio}; leave room for motion before and after this instant. Natural micro-expression, realistic skin and clothing, ordinary phone-camera look. No invented feature, no altered logo or label, no duplicate product, no extra person, no text, no watermark.
```

If label fidelity matters, use the original product image as a separate Seedance reference; do not trust generated label text.

## Motion-reference binding

State which modality owns each attribute. Do not use “strictly reference everything” when the source video visually conflicts with the target images.

```text
图片1是所有可见产品实例的唯一外观标准：轮廓、比例、颜色、材质、按钮、接口、指示灯、底座和配件都以图片1为准，包括远景、盒内和重复出现的产品。视频1只控制镜头节奏、手部动作顺序、停顿、走位和相机运动；忽略视频1中的产品型号、包装、字幕、Logo、布景、服装、声音和音乐。图片2控制人物与服装，图片3控制场景。
```

If the model still copies conflicting source pixels, stop using the original video as a direct reference. Prefer, in order:

1. a crop that retains only the required hand/body motion;
2. a masked or low-detail motion donor with source text, logo, and product detail removed;
3. a short sequence of action keyframes;
4. text-only timing and blocking instructions.

Mute a motion donor unless its audio is separately authorized and required. Inspect the donor itself before upload. When multiple products are allowed, repeat that every instance must match the canonical target product; “multiple” controls count, not identity.

## Causal-proof compiler

Give a critical demonstration its own focused generation. Bind each time range to a visible state transition:

```text
本镜头只完成一个因果证明，不省略步骤，不用跳切伪造过程。
0.0–1.0秒：清楚展示{visible start state}。
1.0–2.0秒：{action 1}，完成后必须看见{state 1}。
2.0–3.5秒：{activation/action 2}；从{state 1}连续变化到{state 2}，画面中始终是同一个对象，内容物不得突然出现、消失或更换。
3.5–4.0秒：从{proof angle}稳定展示{terminal proof}。
```

Use `continuous` only when the transformation itself is evidence. Use `editorial_cut_allowed` only where the source and product truth permit a before/after cut. A last-frame anchor controls the desired terminal geometry but does not authorize skipping the required progression.

## Seedance compiler

Keep the final prompt compact and concrete. Use this order:

```text
[Reference binding]
产品外观严格参考图片1；人物身份、脸部和服装参考图片2；场景空间与光线参考图片3。{optional action keyframe/video binding}

[Intent]
制作一条面向{market}的{duration}秒{platform}实拍UGC商品视频，目标情绪是{felt intent}。

[Timed beats]
0.0–{t1}s：{visible hook action + camera + spoken/SFX cue}。
{t1}–{t2}s：{conflict/pain + transition + performance}。
{t2}–{t3}s：{product reveal/demo + proof}。
{t3}–{end}s：{payoff + native-language CTA}。

[Realism and constraints]
普通手机实拍质感，皮肤有真实纹理和细微不对称，表情与口型自然，手部与产品接触符合物理逻辑，环境光有明确来源。全程只有一个对应人物，不出现分身；不生成字幕、额外Logo、水印或未提供的产品功能。{rights exclusions}
```

For `verbatim` dialogue, place the transcribed source line in quotation marks without rewriting it and preserve its timestamp, pause pattern, emphasis, and interruption. For `translated_same_delivery`, translate meaning naturally while preserving line duration and delivery beats. For `rewrite`, write a new localized line with the same rhetorical job. Treat the source voice as a separate authorization setting. Specify sound intent: room tone, handling sound, one transition SFX, restrained background music, or deliberate silence.

If using `视频1` with authorized dialogue/performance preservation, say:

```text
严格参考视频1中的原对白文本、动作顺序、手势、停顿、表情节奏、走位、镜头配合和标志性表演，由图片2中的人物重新演绎。保留对白和表演不代表复制原人物外貌、原声线、音乐、品牌或原始画面；这些按独立授权设置执行。
```

If expression should be adapted, say:

```text
仅抽象参考视频1的镜头节拍、动作强度、停留装置和转化顺序；不复制视频1中的人物外貌、声音、对白、品牌、字幕、音乐、布景或标志性构图。
```

## Continuation compiler

Compile only the next accepted-sequence segment. Start from observed footage rather than the old plan:

```text
这是{project_id}的{segment_id}，承接已验收的{parent_segment_id}。上一段实际结束状态：{observed_end_state}。

产品、人物和场景继续参考图片1、图片2、图片3；图片4是上一段实际尾帧，视频2是上一段已验收成片。下一段开场必须继承图片4/视频2中的人物站位、产品所在手、身体朝向、视线、未完成动作、相机高度与运动方向、光线和环境声。不得重演已完成事件：{already_happened}。

本段唯一任务：{narrative_job}。观众应感到：{felt_intent}。
{timed_beats}

本段结束状态：{planned_end_state}。为下一段保留：{reserved_for_later}。
```

At a scene boundary, omit the previous output as a continuity source, reopen from canonical images, and specify an intentional cut.

## Negative constraints

Use only constraints relevant to a likely failure:

- one actor only; no duplicate, twin, reflection clone, or extra limb;
- preserve product geometry; no invented buttons, ports, accessories, or duplicate product;
- no beauty filter, waxy skin, floating hand, frozen smile, or unmotivated eye movement;
- no unauthorized source likeness, voice, music, footage, logo, watermark, captions, or signature background; apply the approved dialogue/performance policy separately;
- no unsupported before/after, fake testimonial, false scarcity, or medical/performance guarantee;
- no weapons, explicit sexuality, minors in adult product advertising, or dangerous product use.

Avoid long generic negative lists. Every added constraint competes with the shot instructions.
