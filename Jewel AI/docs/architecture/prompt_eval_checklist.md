# Prompt eval checklist (catalog execution architecture + fragments)

Use this after changing Layer 3 execution fragments, branding clauses, attachment maps,
or the fidelity lock. Re-run the same product photos every time — score pass/fail, not aesthetics.

## Role combinations (must all pass)

| Case | has_reference | has_logo | Checks |
|------|---------------|----------|--------|
| A | No | No | Modern catalog env present; no logo; no jewelry box; gem/metal preserved |
| B | No | Yes | Logo appears once as watermark; no invented mark; product preserved |
| C | Yes | No | Mirrors theme env; old watermarks in theme removed; no dangling logo instruction |
| D | Yes | Yes | Theme mirrored; old branding erased; supplied logo once; product preserved |

## Catalog modes

| Mode | Needs theme | Checks |
|------|-------------|--------|
| modern | No | Assigned environment from rotation pool |
| reference_mirror | Yes | Full environment mirror (not mood-only) |
| style_mood | Yes | Lighting/mood only; composition of Image 1 kept |

## Try-on

| tryOnMode | Checks |
|-----------|--------|
| studio | Jewelry placed on model; piece identity preserved |
| customer | Customer face/skin not beautified; jewelry only added |

Default model must be image-edit compositing (e.g. Nano Banana Pro), not FASHN garment VTON.

## Jewelry types (sample set)

Run cases A–D on at least: Ring, Necklace, Earrings (Studs), multi Ring+Necklace.

## Pass criteria (boolean)

- [ ] Gemstone count / facet structure preserved
- [ ] Fidelity lock appears at start and end of assembled prompt
- [ ] No velvet jewelry box / ring box / retail packaging prop
- [ ] Logo present only when requested, and only once
- [ ] When reference+no logo: no invented branding
- [ ] When reference+logo: reference watermarks gone
- [ ] Bulk (no theme): consecutive items use different `environmentChosen` in promptDebug when pool allows
- [ ] Image labels use `Image N` (not bracket `[IMAGE_N]`)

## Where to inspect

Job `provider_metadata.promptDebug`:
- `executionMode`, `catalogMode`, `tryOnMode`, `environmentChosen`, `hasReference`, `hasLogo`, `subtypesIncluded`
- `fragmentVersions` (active fragment version ids)
- `imageRoles` / `logoMode` from the image packet

## Change discipline

Edit fragments in Admin UI (not Python). Tag `EXECUTION_MODE_VERSION` only when assembler routing changes.
