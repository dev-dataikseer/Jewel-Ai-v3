# Jewel AI Studio — Prompt Engine Architecture & Tuning Guide

> **Implementation status (Jul 2026):** Catalog Layer 3 execution modes, branding
> clauses, IMAGE_N attachment maps, and Redis environment rotation live in
> `backend/app/prompt_engine/execution_mode.py` and
> `environment_rotation.py`, wired through `build_final_prompt`. Admin DB remains
> Layer 1 (master) + Layer 2 (subjects). See also `prompt_engine.txt` and
> `prompt_eval_checklist.md`.

## 0. Verdict on the doc you already have

The layered structure (Master → Subtype → Execution Mode → Attachment Map) is the right skeleton, and routing the Execution Mode purely in Python instead of writing an `if/else` inside the prompt text is the correct fix for prompt bleed. Keep that.

Three things in it will bite you in production if left as-is, and they're the actual hard part of "robust":

1. **"Randomly select ONE of the following environments" is not random.** You're asking the model to pick, and models under-sample options and cluster on 1–2 favorites across calls — especially with the same seed/temperature settings fal.ai wrappers often use. This is *exactly* why you're seeing repetitive backgrounds today even with variety text in the prompt. The randomness has to happen in your Python backend, not in the prompt.
2. **No dedup/rotation state.** Even true `random.choice()` will repeat by chance (birthday paradox — with 9 options you get a repeat within ~4 draws about half the time). For a bulk job of 20 items for one shop, "random" isn't enough; you need rotation so consecutive/recent outputs for the same job/client don't collide.
3. **Logo replacement and reference-background mirroring are coupled but shouldn't be.** A user can supply a reference image with *no* logo, a logo image with *no* reference, or both, or neither. Your Option A block assumes reference-present implies logo-swap. Split these into two independent flags.

Everything below fixes those three plus fills in the multi-type, bulk, and observability pieces from your feature table.

---

## 1. Core architectural change: image roles are independent flags, not a mode

Stop thinking "Reference Mode vs Creative Mode" as one binary. Model it as three independent booleans derived from `imageRoles`:

```python
has_reference = "reference" in image_roles      # background/style source supplied
has_logo      = "logo" in image_roles or provider_metadata.get("logoMode") == "active"
is_bulk       = job_data.get("workflow") in ("BULK_GENERATION", "CATALOG_IMAGE") and job_data.get("bulkIndex") is not None
```

This gives you **four real combinations**, not two:

| has_reference | has_logo | Behavior |
|---|---|---|
| False | False | Modern Dynamic Catalog, no branding pass |
| False | True | Modern Dynamic Catalog + apply logo as watermark |
| True | False | Mirror reference background; if reference already has a logo/watermark, erase it (clean removal, no replacement) |
| True | True | Mirror reference background; erase any existing branding in reference; apply the supplied logo |

Your current architecture silently drops the "reference with no logo" case into logo-swap language ("ERASE and IGNORE all branding... apply IMAGE_3 as SOLE branding") even when there's no `IMAGE_3`. That's a broken reference in the prompt when logo isn't supplied — the model will either hallucinate a logo instruction target or ignore it inconsistently. Split it.

---

## 2. Revised modular blocks

### Layer 1 — Master Base (unchanged from yours, it's solid)

Keep your preservation mandate, camera physics, and negative prompt block as-is. One addition: put the jewelry-box ban and repetitive-background ban here **and** repeat it in Layer 3B — negative prompts benefit from reinforcement at the point of highest relevance, but the master copy should stay as the baseline floor regardless of which Layer 3 branch fires.

### Layer 2 — Child Subtype (unchanged logic, one robustness fix)

For multi-type bulk jobs, don't just concatenate all matching subtype blocks blindly — sort them into a deterministic order (e.g. ring, necklace, earring, bracelet...) so the same combination always produces the same block ordering. Non-deterministic ordering makes prompt-diffing and regression testing useless later.

```python
SUBTYPE_ORDER = ["ring", "necklace", "earring", "bracelet", "pendant", "bangle", "brooch", "anklet", "set"]

def get_subtype_prompt(jewelry_types: list[str]) -> str:
    ordered = [t for t in SUBTYPE_ORDER if t in jewelry_types]
    blocks = [SUBTYPE_PROMPTS[t] for t in ordered if t in SUBTYPE_PROMPTS]
    return "\n".join(blocks)
```

### Layer 3A — Reference Mirroring (split logo out)

```text
EXECUTION MODE: REFERENCE MIRRORING
1. ENVIRONMENT MIRRORING: Analyze [IMAGE_2: REFERENCE]. Extract and replicate its background architecture, surface material, lighting direction, shadow density, and color grading. Place the primary jewelry subject from [IMAGE_1] into this exact style of environment.
2. SUBJECT ISOLATION: Ignore any jewelry, hands, or models shown in [IMAGE_2]. It is a style/environment reference only — never copy its subject matter.
{{BRANDING_CLAUSE}}
```

Where `{{BRANDING_CLAUSE}}` is injected by Python based on `has_logo`:

```python
if has_logo:
    branding_clause = (
        "3. BRAND REPLACEMENT: Inspect the Reference Image for any existing watermark, "
        "logo, or text overlay. Erase it completely — it must not appear in the output. "
        "Apply [IMAGE_3: LOGO] as the sole branding, positioned as a discreet high-end "
        "commercial watermark (bottom-right or top-center), matching the scene's lighting "
        "and never overlapping the jewelry subject."
    )
else:
    branding_clause = (
        "3. BRAND CLEANUP: If the Reference Image contains any existing watermark, logo, "
        "or text overlay, erase it completely. The output must contain no branding of any kind."
    )
```

This removes the dangling `IMAGE_3` reference when no logo was supplied — the single largest source of the "modal should replace our logo but sometimes doesn't / sometimes invents one" failure mode.

### Layer 3B — Modern Dynamic Catalog (randomness moved to backend)

```text
EXECUTION MODE: MODERN DYNAMIC CATALOG
1. MODERN LUXURY STANDARDS: Generate a fresh, ultra-modern editorial catalog setting. Strictly forbidden: velvet jewelry boxes, ring boxes, leather display stands, generic gradient studio backdrops, and any prop that resembles traditional retail packaging.
2. ASSIGNED ENVIRONMENT: {{CHOSEN_ENVIRONMENT}}
3. GROUNDING & PERSPECTIVE: The supporting surface plane must align with the jewelry's current resting orientation. Generate a deep, dense ambient-occlusion contact shadow anchoring the piece to the surface.
{{BRANDING_CLAUSE}}
```

`{{CHOSEN_ENVIRONMENT}}` is a **concrete, specific sentence** chosen by Python, not a menu handed to the model:

```python
import random

ENVIRONMENT_POOL = [
    "A matte travertine stone slab with soft architectural shadow lines crossing the surface at a low angle.",
    "Dark brushed concrete with a single directional light source casting a long, soft-edged shadow.",
    "Fluted cream marble with vertical channel grooves catching diffuse studio light.",
    "Caustic water reflections on a dark glass surface, with rippling light patterns playing across the background.",
    "Smooth river stones in graduated grey tones, arranged with negative space around the subject.",
    "Dark volcanic basalt with a fine mist of water droplets catching specular highlights.",
    "Raw unbleached silk drapery pooling softly beneath the subject, natural fiber texture visible.",
    "A frosted acrylic plinth lit from below with a cool rim light separating subject from background.",
    "Brushed champagne-gold metal surface with a soft gradient reflection of the jewelry piece.",
]

def choose_environment(job_id: str, client_id: str) -> str:
    """Deterministic-but-varied pick with rotation to avoid repeats."""
    recent = get_recent_environments(client_id, lookback=5)   # from your job history / cache
    available = [e for e in ENVIRONMENT_POOL if e not in recent] or ENVIRONMENT_POOL
    choice = random.choice(available)
    record_environment_used(client_id, job_id, choice)
    return choice
```

`get_recent_environments` / `record_environment_used` can be as simple as a small table or Redis list keyed by `client_id` (or `shop_id`) storing the last N environment strings used, checked before each new job. This is the actual fix for "not repetitive backgrounds" — the prompt-side "randomly select" instruction was never going to reliably deliver it.

For **bulk jobs**, call `choose_environment` once per item in the batch, feeding the same rolling history, so item 1 and item 7 of a 20-piece batch don't land on the same backdrop.

### Layer 4 — Attachment Role Mapping (unchanged, keep as-is)

Your version is fine. One addition: make the image count/order match what's actually attached — don't emit `[IMAGE_3: COMPANY LOGO]` in the role-mapping text if no logo was attached this job, for the same "dangling reference" reason as above.

```python
def build_attachment_mapping(has_reference: bool, has_logo: bool) -> str:
    lines = ["ATTACHMENT ROLES & INSTRUCTIONS:",
             "- [IMAGE_1]: PRIMARY SUBJECT. Extract ONLY the jewelry piece. Preserve 100% of its physical structure and pixels."]
    if has_reference:
        lines.append("- [IMAGE_2]: REFERENCE ENVIRONMENT. Use ONLY for background, lighting, and style replication. Ignore any jewelry shown in this image.")
    if has_logo:
        idx = 3 if has_reference else 2
        lines.append(f"- [IMAGE_{idx}]: COMPANY LOGO. Use solely as a clean, secondary watermark or brand overlay.")
    return "\n".join(lines)
```

---

## 3. Full assembly function

```python
def build_final_prompt(job_data: dict, provider_metadata: dict) -> str:
    image_roles = provider_metadata.get("imageRoles", {})
    has_reference = "reference" in image_roles
    has_logo = "logo" in image_roles or provider_metadata.get("logoMode") == "active"

    jewelry_types = job_data.get("jewelryTypes", [])

    parts = [MASTER_BASE_PROMPT, get_subtype_prompt(jewelry_types)]

    branding_clause = build_branding_clause(has_logo, mode="reference" if has_reference else "catalog")

    if has_reference:
        parts.append(REFERENCE_MIRRORING_TEMPLATE.format(BRANDING_CLAUSE=branding_clause))
    else:
        environment = choose_environment(job_data["job_id"], job_data.get("client_id", "default"))
        parts.append(MODERN_DYNAMIC_TEMPLATE.format(
            CHOSEN_ENVIRONMENT=environment,
            BRANDING_CLAUSE=branding_clause,
        ))

    parts.append(build_attachment_mapping(has_reference, has_logo))

    final_prompt = "\n\n".join(p for p in parts if p)

    # Persist for debugging/History (your feature table item)
    provider_metadata["imageRoles"] = image_roles
    provider_metadata["logoMode"] = "active" if has_logo else "inactive"
    provider_metadata["promptDebug"] = {
        "hasReference": has_reference,
        "hasLogo": has_logo,
        "environmentChosen": environment if not has_reference else None,
        "subtypesIncluded": jewelry_types,
    }

    return final_prompt
```

This satisfies your feature table row directly: `final_prompt + promptDebug + imageRoles` persisted in `provider_metadata`, queryable later from History without re-deriving what happened.

---

## 4. Prompt tuning methodology (phase 2, once the above is wired up)

Prompt tuning for an image model is empirical, not something you get right by staring at the text. Set this up before you start hand-tweaking wording:

**4.1 Build a fixed regression set.** 8–12 real product photos spanning your jewelry types (ring, necklace, earring, bundled multi-type) × the 4 role combinations from the table in §1 = ~40 canonical test cases. Re-run this exact set every time you touch a prompt block. Without this you're tuning by vibes and can't tell if a wording change helped or just moved the failure elsewhere.

**4.2 Score against your own negative prompt, not aesthetics.** For each output, check pass/fail on concrete things you can verify: did it preserve gemstone count/facet structure, did it avoid jewelry boxes, did the logo (if requested) actually appear and appear once, did an old logo get removed. Save these as booleans per test case run — this becomes your eval harness.

**4.3 Change one layer at a time.** Because your architecture is now modular (Master / Subtype / Execution / Attachment), when a regression appears you can bisect: swap in the previous version of just the Execution Mode block and re-run the 40 cases to confirm that's the source before touching anything else.

**4.4 Version your prompt blocks.** Tag `MASTER_BASE_PROMPT`, `REFERENCE_MIRRORING_TEMPLATE`, etc. with a version string and store it in `promptDebug` alongside the job (`"masterVersion": "v3.4.0"`). When a shop owner reports a bad batch weeks later, you can see exactly which prompt version generated it instead of guessing.

**4.5 Treat the negative prompt as a living blocklist.** Every time a bad output pattern shows up (a new box style, a new watermark artifact, a background that's technically "modern" but you don't want), add the specific phrase to the negative prompt and re-run the regression set. This list should only grow.

**4.6 For the vision-model-specific behavior (Gemini/GPT-4o/whatever fal.ai routes to), test provider-by-provider.** "ERASE and IGNORE branding" language that works cleanly on GPT-4o may need slightly more explicit phrasing on another model in your failover chain. Keep a small provider-specific override map for wording, not full duplicate prompt sets — same modular layers, targeted phrase swaps only where a provider demonstrably needs it.

---

## 5. What this leaves you with

- Reference/no-reference and logo/no-logo are now four independently-composed, testable states instead of one conditional block with a hardcoded assumption.
- Background variety is guaranteed by backend state (rotation against recent history), not requested from the model and hoped for.
- No dangling `[IMAGE_3]` references when a logo wasn't actually attached.
- `provider_metadata` carries enough (`imageRoles`, `logoMode`, `promptDebug`) to debug any specific job from History without re-deriving the routing decision.
- Multi-type and bulk jobs get deterministic subtype ordering and per-item environment rotation, so batch outputs read as a coherent catalog rather than a grab-bag.
