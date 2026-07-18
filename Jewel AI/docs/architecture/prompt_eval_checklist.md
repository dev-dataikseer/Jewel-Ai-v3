# Prompt eval checklist (catalog execution architecture)

Use this after changing Layer 3 execution mode, branding clauses, or attachment maps.
Re-run the same product photos every time — score pass/fail, not aesthetics.

## Role combinations (must all pass)

| Case | has_reference | has_logo | Checks |
|------|---------------|----------|--------|
| A | No | No | Modern catalog env present; no logo; no jewelry box; gem/metal preserved |
| B | No | Yes | Logo appears once as watermark; no invented mark; product preserved |
| C | Yes | No | Mirrors theme env; old watermarks in theme removed; no dangling logo instruction |
| D | Yes | Yes | Theme mirrored; old branding erased; supplied logo once; product preserved |

## Jewelry types (sample set)

Run cases A–D on at least: Ring, Necklace, Earrings (Studs), multi Ring+Necklace.

## Pass criteria (boolean)

- [ ] Gemstone count / facet structure preserved
- [ ] No velvet jewelry box / ring box / retail packaging prop
- [ ] Logo present only when requested, and only once
- [ ] When reference+no logo: no invented branding
- [ ] When reference+logo: reference watermarks gone
- [ ] Bulk (no theme): consecutive items use different `environmentChosen` in promptDebug when pool allows

## Where to inspect

Job `provider_metadata.promptDebug`:
- `executionMode`, `environmentChosen`, `hasReference`, `hasLogo`, `subtypesIncluded`
- `imageRoles` / `logoMode` from the image packet

## Change discipline

Change one layer at a time (Master DB / Subject DB / `execution_mode.py` / attachments). Tag `EXECUTION_MODE_VERSION` when editing Layer 3.
