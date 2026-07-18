# Jewel AI Studio — UI/UX System Design

**Status:** Approved design + implementation reference  
**Product:** Professional AI Jewelry Production Studio (not a generic image generator)  
**Primary persona:** Jewelry operators who upload products, configure workflow/model, generate (often in batch), compare, download, and reuse assets  
**Primary surface:** Desktop Studio (`lg+` three-zone workspace). Mobile is secondary (sticky Generate + drawers).

---

## Phase 1 — Current UI/UX audit

### Current architecture

```
AppShell
└─ Sticky header (brand, nav, credits)
└─ Studio (lg+)
   ├─ Left: Workflow list + workspace stats
   ├─ Center: Input | Output + Generate bar + Recent
   └─ Right: Parameters / brand kit / model
```

### Critical issues

| ID | Problem | Impact | Solution |
|----|---------|--------|----------|
| P1 | Competing CTAs (dual Generate + Output strip) | Missed primary action | One ActionDock; Results tray for Download/Regenerate; Share/Save overflow |
| P2 | Parameters rail overloaded | Cognitive overload | Essentials vs Advanced progressive disclosure |
| P3 | Prompt below Generate | Instructions missed | Prompt in Inspector Essentials above Generate |
| P4 | Mobile Generate buried | Slow iterate loop | Sticky mobile ActionDock; Workflow/Inspector sheets |
| P5 | Workspace stat mini-cards | Visual noise | Fold into Session tray; Clear as quiet text |
| P6 | MultiSelect / modal a11y gaps | Keyboard/SR friction | Accessible listbox + Dialog focus trap |
| P7 | CSS vars unused; Admin indigo drift | Hard to brand | `--jewel-*` tokens driving UI |
| P8 | Toast-heavy during fal waits | Status missed | Output stage bar is source of truth |

### Preserve

- Input | Output production metaphor
- Session restore + brand kit persistence
- Failed Retry / Duplicate + History → Studio deep link
- DM Sans + light production baseline (no dark “AI default”)

---

## Phase 2 — Research patterns (adopt, don’t copy)

| Pattern | Why for Jewel |
|---------|---------------|
| Canvas-first workspace | Jewelry judgment is visual |
| Left tool / center stage / right properties | Workflow → Stage → Inspector |
| Generation queue + history strip | Elevate batch + recent |
| Labeled asset slots | Product / Person / Theme / Logo |
| Simple model + Advanced expand | Speed for operators, depth for experts |
| Sticky primary action | Generate always reachable |
| Compare / before-after | Approve loop |
| Progress as stage narrative | queued → generating → finalizing → ready |

**Avoid:** Dashboard metric grids in Studio, purple glow, chat-first UX, floating badge clutter.

---

## Phase 3 — Product framing

| Workflow | UX emphasis |
|----------|-------------|
| Catalog Image | Product + catalog mode + optional theme/logo |
| Virtual Try-On | Product + person slots |
| Background Replacement | Product fidelity + environment |
| Style From Reference | Product + style ref |
| Luxury Enhancement | Single product; conservative defaults |
| Gemstone Color Change | Product + color target |
| Custom Prompt | Prompt prominence + model freedom |

Loop: **Upload → Configure → Generate → Compare → Regenerate → Approve → Download → History → Reuse**.

---

## Phase 4 — Ideal UX strategy

**Happy path clicks ≤ 4:** Select workflow → drop product → Generate → Download.

**Batch:** Multi-upload → same configure → Generate → Batch tray (progress + ZIP).

---

## Phase 5 — Design system

### Visual direction

Light production studio — cool stone neutrals, ink text, deep studio blue CTAs, restrained champagne/metal for brand mark and focus rings.

### Color tokens

| Token | Role | Value |
|-------|------|-------|
| `--jewel-bg` | App canvas | `#F4F5F7` |
| `--jewel-surface` | Panels | `#FFFFFF` |
| `--jewel-surface-muted` | Nested wells | `#EEF0F3` |
| `--jewel-ink` | Primary text | `#0F1419` |
| `--jewel-ink-muted` | Secondary | `#5C6570` |
| `--jewel-border` | Hairlines | `#D8DDE3` |
| `--jewel-accent` | Primary CTA | `#1F4B8F` |
| `--jewel-accent-hover` | CTA hover | `#183A70` |
| `--jewel-accent-soft` | Selected chips | `#E8EEF7` |
| `--jewel-metal` | Brand accent | `#A67C52` |
| `--jewel-success` | Success | `#059669` |
| `--jewel-warning` | Warning | `#D97706` |
| `--jewel-danger` | Danger | `#E11D48` |

### Typography

- Family: DM Sans
- Scale: 11 / 12 / 13 / 14 / 16 / 20 / 24 px
- Zone title 16 semibold; labels 12 medium; helper 11 muted

### Spacing / radius / elevation

- Space: 4, 8, 12, 16, 24, 32, 48
- Radius: sm 6, md 10, lg 16
- Shadow: one soft level for sticky bars only

### Buttons

Primary / Secondary / Ghost / Icon / Danger + loading & disabled. In Studio, Primary = Generate only.

### Feedback

- Job stage bar on Output
- Inline slot errors
- Toasts: share copied, workspace cleared, batch ZIP — not every job tick

---

## Phase 6 — System layout

```
Application
├── Header (brand metal mark + nav + credits + account)
├── Workspace
│   ├── WorkflowRail (workflows only)
│   ├── Stage (InputBoard | OutputBoard + Compare)
│   └── Inspector (Essentials → Advanced → Model)
├── ActionDock (Generate sticky)
└── SessionTray (Recent + Batch)
```

### Component hierarchy

```
AppShell → AppHeader
StudioPage
  WorkflowRail
  Stage → InputBoard (UploadSlot[]) / OutputBoard / CompareToggle
  Inspector → Essentials / Advanced / Model
  ActionDock
  SessionTray
HistoryPage → AssetLibraryGrid → GenerationDetailModal
```

### Responsive

- Desktop/ultrawide: 3-zone + tray
- Mobile: Stage first; Workflow & Inspector sheets; ActionDock sticky bottom

### Accessibility

WCAG AA; focus rings; Dialog focus trap; MultiSelect listbox pattern; `aria-live` on Output stage.

### Motion

150–200ms panel transitions; History skeletons; Output crossfade; no decorative ambient motion.

---

## Phase 7 — Frontend architecture

| Area | Target |
|------|--------|
| Studio | Thin page + `features/studio/*` |
| Tokens | `theme/tokens.css` + Tailwind extend |
| UI | `components/ui/` Dialog, sheets helpers |
| State | `useStudioWorkspace` extraction over time; no forced global store |

```
src/
  theme/tokens.css
  components/ui/
  features/studio/
  features/history/
  pages/
```

---

## Phase 8 — Implementation waves

| Wave | Scope |
|------|-------|
| A | Token foundation (`--jewel-*` → Tailwind / `ui-*`) |
| B | Studio IA: ActionDock, Inspector disclosure, remove stat cards, prompt placement |
| C | UploadSlot roles, Results tray, compare |
| D | Mobile sheets, Dialog / MultiSelect a11y |
| E | History reuse polish, Admin token sync |

### Migration

Strangler pattern: new components wrap existing generate/upload hooks. Same route `/`. Regression: single generate, batch ZIP, brand kit, session restore, History deep link, Share, Admin prompts.

### Out of scope (first waves)

httpOnly auth overhaul, credits billing product, full Admin Prompt Editor redesign, dark mode, mobile-as-primary.

### Success metrics

- Happy-path clicks ≤ 4
- Generate always visible
- Zero duplicate primary CTAs in viewport
- Keyboard completes jewelry multi-select + generate
- Clearer generation stage narrative
