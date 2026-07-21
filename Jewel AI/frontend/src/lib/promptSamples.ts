/**
 * Fill-in paste templates for Admin → Prompts → Download sample.
 * Keep {{PLACEHOLDERS}} exactly — the engine fills them at generate time.
 */

export const SAMPLE_MASTER_PROMPT = `================================================================================
CATALOG / IMAGE WORKFLOW — MASTER PROMPT TEMPLATE
Admin → Prompts → Workflow = Catalog (or similar) → Prompt = Master prompt
================================================================================
HOW TO USE
1) Copy the PASTE BLOCK below (between >>> and <<<)
2) Replace text inside [BRACKETS] with your words — OR use the ready example
3) Do NOT delete lines that look like {{THIS}}
4) Paste into Admin and click Save

PLACEHOLDERS IN THIS TEMPLATE (leave exactly as written)
  {{SUBTYPE_BLOCK}}     = jewelry-type text (Ring, Necklace, …) inserted automatically
  {{EXECUTION_BLOCK}}   = Catalog mode (modern / match reference / match mood)
  {{BRANDING_CLAUSE}}    = logo + theme rules inserted automatically

>>>
ROLE: [YOUR ROLE — e.g. master commercial jewelry photographer and luxury retoucher]

CAMERA: [YOUR CAMERA — e.g. 100mm macro, f/11, sharp jewelry from Image 1, soft background]

LIGHTING: [YOUR LIGHTING — e.g. soft softboxes + accurate contact shadow under Image 1]

{{SUBTYPE_BLOCK}}

{{EXECUTION_BLOCK}}

{{BRANDING_CLAUSE}}

INSTRUCTION: [YOUR RULES — e.g. keep Image 1 jewelry identity locked]

NEGATIVE PROMPT: [AVOID — e.g. 3d render, CGI, plastic, warped band, floating object, missing shadow]
<<<

READY EXAMPLE (paste as-is, then tweak wording):
>>>
ROLE: You are a master commercial jewelry photographer and luxury retoucher.

CAMERA: 100mm macro lens, f/11 aperture, edge-to-edge sharpness on the jewelry piece from Image 1, shallow depth of field on the background. Editorial print quality.

LIGHTING: Soft diffused studio lighting from large softboxes. Dense, physically accurate contact shadow beneath the jewelry from Image 1. Realistic metal reflections without overexposure.

{{SUBTYPE_BLOCK}}

{{EXECUTION_BLOCK}}

{{BRANDING_CLAUSE}}

NEGATIVE PROMPT: 3d render, CGI, plastic texture, warped band, distorted facets, floating object, missing contact shadow, cluttered background, neon colors, watermark collision, redesigned jewelry.
<<<
`;

export const SAMPLE_JEWELRY_PROMPT = `================================================================================
JEWELRY-TYPE PROMPT TEMPLATE (Ring / Necklace / Bracelet / …)
Admin → Prompts → same Workflow → Prompt = Ring (or Necklace, …)
================================================================================
HOW TO USE
1) This is SHORT — only 1–4 sentences about how THIS piece sits in the frame
2) No ROLE / CAMERA / LIGHTING here (those live in Master)
3) Usually NO {{PLACEHOLDERS}} — the Master uses {{SUBTYPE_BLOCK}} to pull this text in
4) Paste into Admin and Save — then do the next jewelry type

FILL-IN:
>>>
The [PIECE]'s [PART] rests / hangs / sits [CONTACT WITH SURFACE OR BODY]. Generate a tight, dark contact shadow [WHERE]. Preserve exact scale and detail from Image 1.
<<<

RING EXAMPLE:
>>>
The ring's shank rests flat against the supporting surface at its true point of contact. Generate a tight, dark contact shadow directly beneath the band, not a diffuse ambient shadow.
<<<

NECKLACE EXAMPLE:
>>>
The necklace hangs with natural gravity from Image 1. Links and pendant keep true proportions. Soft contact shadow only where the chain or pendant truly meets a surface.
<<<

EARRING EXAMPLE:
>>>
The earring hangs with correct gravity and orientation from Image 1. Preserve post/hook geometry. Contact shadow only where metal meets skin or display surface.
<<<
`;

export const SAMPLE_TRYON_PROMPT = `================================================================================
VIRTUAL TRY-ON — MASTER PROMPT TEMPLATE
Admin → Prompts → Workflow = Try-On → Prompt = Master prompt
================================================================================
HOW TO USE
1) Copy PASTE BLOCK — keep {{PLACEMENT_ANATOMY}} and {{TRYON_MODE_CLAUSE}}
2) Paste → Save

PLACEHOLDERS (leave exactly as written)
  {{PLACEMENT_ANATOMY}}  = where the piece sits on the body for the jewelry type
  {{TRYON_MODE_CLAUSE}}   = extra rules when Studio Try-on mode = Customer

>>>
ROLE: You are a jewelry compositing specialist placing a real piece onto a person photo.

INSTRUCTION: Place the jewelry piece from Image 1 onto the person in Image 2, {{PLACEMENT_ANATOMY}}. Match the jewelry's scale, perspective, and lighting to the person's pose and the scene's light direction. Do not alter the person's face, body, pose, skin tone, or existing clothing. Do not alter the jewelry piece itself beyond the perspective and lighting match required to seat it naturally on the body.

{{TRYON_MODE_CLAUSE}}

NEGATIVE PROMPT: warped jewelry to fit body contour, resized jewelry disproportionate to body scale, changed person identity, changed pose, floating jewelry not touching skin, missing contact shadow where jewelry meets skin.
<<<
`;

export function sampleFilename(kind: "master" | "jewelry" | "tryon"): string {
  if (kind === "jewelry") return "jewel-ai-TEMPLATE-jewelry-type.txt";
  if (kind === "tryon") return "jewel-ai-TEMPLATE-tryon-master.txt";
  return "jewel-ai-TEMPLATE-catalog-master.txt";
}

export function sampleBodyFor(
  workflowId: string,
  childType: "master" | "subject" | "variant",
): { kind: "master" | "jewelry" | "tryon"; text: string } {
  if (childType === "subject") {
    return { kind: "jewelry", text: SAMPLE_JEWELRY_PROMPT };
  }
  if (workflowId === "VIRTUAL_TRY_ON") {
    return { kind: "tryon", text: SAMPLE_TRYON_PROMPT };
  }
  return { kind: "master", text: SAMPLE_MASTER_PROMPT };
}

export function downloadTextFile(filename: string, text: string) {
  const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.rel = "noopener";
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
