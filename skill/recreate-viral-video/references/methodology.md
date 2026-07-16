# Viral-video inheritance methodology

## Contents

1. Eight dimensions
2. Hook diagnosis
3. Beat-map rules
4. Scene-boundary verification
5. Causal proof chains
6. Same-category transfer
7. Cross-category transfer
8. Localization
9. QC scoring

## Eight dimensions

Analyze observation, inferred function, transfer rule, target adaptation, confidence, and evidence timestamps for every dimension.

| Key | Observe | Infer and transfer |
|---|---|---|
| `hook` | First frame, first spoken clause, first action, reveal timing, withheld information | Curiosity, contrast, pain, conflict, proof-first, taboo/question, unexpected result, or open loop |
| `visual` | Framing, focal length feel, product scale, lighting, color, edit grammar, overlays, scene density | Visual hierarchy and the order in which the viewer discovers information |
| `audio` | Dialogue text, voice, pace, pauses, sound effects, music, silence, sync, exact role of each sound | Preserve authorized dialogue verbatim or translate it with the same delivery when selected; treat voice and music as separate rights decisions |
| `retention` | Shot duration, information density, pattern interrupts, resets, open loops, captions, reveal spacing | Why a viewer has a reason to stay through each beat |
| `emotion_conflict` | Pain, embarrassment, fear, surprise, desire, relief, tension, escalation, payoff | Emotional curve and conflict function; replace unsafe or culturally inappropriate expression |
| `action_performance` | Body language, gaze, micro-expression, gesture, product handling, blocking, camera movement | Performance intensity and action sequence; remap actions to physically correct product use |
| `persuasion_proof` | Demonstration, before/after, authority, specificity, objection handling, social proof, risk reversal | Evidence order and belief shift; every target claim must be independently supported |
| `conversion` | Offer, CTA wording, product reveal, urgency, link/shop cue, end frame, verbal/visual handoff | Conversion path and CTA timing; rewrite for platform, market, and actual offer |

## Hook diagnosis

Treat 0–5 seconds as a sequence, not a label.

Split at every visible, audible, or semantic change. Record:

- `first_frame_contract`: what the viewer thinks the video is about at first glance.
- `trigger_time`: the first curiosity, contrast, pain, conflict, or proof signal.
- `withheld_information`: what is intentionally unanswered.
- `stakes`: what the viewer may gain, lose, avoid, or discover.
- `pattern_interrupt`: visual/audio event that breaks expectation.
- `promise`: explicit or implied payoff.
- `product_visibility`: hidden, peripheral, partial, or explicit.
- `hook_resolution_time`: when the open loop advances or resolves.

Use one or more mechanism labels: `curiosity_gap`, `visual_contradiction`, `pain_recognition`, `social_conflict`, `result_first`, `proof_first`, `unexpected_action`, `taboo_question`, `time_pressure`, `identity_challenge`, `open_loop`.

Do not call fast cutting a hook unless it creates a meaningful unanswered question or stake.

## Beat-map rules

Create beats on semantic changes, not fixed one-second intervals. Each beat needs:

```json
{
  "start_s": 0.0,
  "end_s": 1.2,
  "shot_function": "show painful consequence before explanation",
  "visual": "observable action and framing",
  "audio": "speech/SFX/music/silence",
  "emotion": "viewer emotion and performer emotion",
  "retention_device": "unanswered question or pattern interrupt",
  "transition": "hard cut, whip, match action, reveal, pause",
  "confidence": 0.0
}
```

Compute relative timing as `beat duration / total duration`. Preserve relative timing rather than absolute frames unless a platform constraint requires otherwise.

Separate observation from inference:

- Observation: “At 00:01.1, the actor stops speaking and looks off camera.”
- Inference: “The pause delays the reveal and raises social tension.”
- Transfer: “Insert a short silent reaction immediately before the target product reveal.”

## Scene-boundary verification

Do not infer visual continuity from a shared product, use context, actor, or voice-over. At every meaningful hard cut and every proposed segment boundary, inspect dense frames on both sides and record:

| Dimension | Before cut | After cut | Changed? |
|---|---|---|---|
| Background/location | Observable room, wall, floor, bed, counter, exterior | Same fields | yes/no/unknown |
| Working surface | Material, color, texture, orientation | Same fields | yes/no/unknown |
| Wardrobe/body | Sleeves, jewelry, watch, nails, visible skin, actor count | Same fields | yes/no/unknown |
| Handled objects | Product instance, garments, props, containers | Same fields | yes/no/unknown |
| Prop geography | Suitcase, furniture, tools, object placement | Same fields | yes/no/unknown |
| Camera/light | Height, angle, direction, color temperature, shadows | Same fields | yes/no/unknown |

Classify the boundary as `same_scene` only when the evidence supports continuity. Use `new_scene` when a changed background, surface, wardrobe, object set, prop layout, camera setup, or lighting reset materially changes the generation prompt. A hard cut can remain inside one scene, and the same use context can contain several scenes.

Store evidence frame times and confidence. If either side is occluded or blurred, mark the dimension unknown and inspect additional nearby frames instead of copying continuity locks forward.

## Causal proof chains

For every product demonstration, model what the viewer must see to believe the claim:

```json
{
  "claim_or_belief_shift": "the product causes the visible result",
  "visible_start_state": "observable condition before use",
  "steps": [
    {
      "order": 1,
      "action": "physically correct user action",
      "required_visible_end_state": "observable state after the action",
      "continuity": "continuous"
    }
  ],
  "terminal_proof": "observable result and proof angle",
  "must_show_progression": true
}
```

Distinguish an endpoint proof from a causal proof. A before/after cut can prove comparison when the source uses one, but it cannot replace a required continuous transformation. Reject a take when an object appears after a cut without being placed, a sealed item changes contents, activation is missing, the process jumps directly to the result, or the terminal proof contradicts the preceding state.

An inserted terminal still may extend a valid result hold. It cannot repair a missing action or state transition.

## Same-category transfer

Preserve:

- hook mechanism and first reveal timing;
- shot-function order and relative beat duration;
- problem demonstration, product interaction, proof sequence, payoff, and CTA position;
- energy curve, gesture intensity, and camera-motion function.

Adapt:

- exact product handling to the target product instructions;
- claim wording to verified facts;
- actor, wardrobe, background, props, language, currency, units, outlet type, home layout, and CTA convention;
- source use context only when the user selected `keep`.

Preserve exact dialogue, gestures, choreography, mannerisms, pauses, and performance timing when the user selects them and confirms authorization. Do not automatically carry over likeness, voice, music, footage, graphics, packaging, or background arrangement; authorize each separately.

## Cross-category transfer

Map source beats by job:

| Source job | Target mapping question |
|---|---|
| Pain recognition | What real, frequent problem does the target product solve? |
| Contradiction | What unexpected result can be shown truthfully? |
| Product reveal | At what point will seeing the product answer the open loop? |
| Demonstration | What visible action proves the benefit without unsupported claims? |
| Objection handling | What believable doubt blocks purchase, and what evidence addresses it? |
| Payoff | What immediate, filmable change follows correct use? |
| CTA | What next action is available in this market/platform? |

Reject literal inheritance when the source action would be unsafe, physically implausible, irrelevant, or deceptive for the target product.

## Localization

Localize behavior, not just words:

- spoken register, sentence length, interruption style, humor, politeness, and CTA directness;
- adult actor profile without stereotyping or exoticizing the market;
- home/store layout, electrical outlets, appliance style, currency, measurements, seasonal cues, packaging language, driving side, and platform shopping behavior;
- claim restrictions, disclosure needs, and category-specific ad rules.

Use native phrasing. Do not translate the source script literally. Preserve the rhetorical job of each line.

## QC scoring

Score 0–5 for each dimension:

- `0`: missing or contradictory.
- `1`: present but nonfunctional.
- `2`: weak or late.
- `3`: functionally adequate.
- `4`: strong and coherent.
- `5`: exceptionally clear without sacrificing originality or product truth.

Pass only when hook, product fidelity, safety/rights, and conversion have no critical failure. The average score alone cannot override a critical failure.
