/**
 * Sample prompt templates for Admin download.
 * Placeholders must match the prompt assembler (see docs/Modals/Prompts).
 */

export const SAMPLE_MASTER_PROMPT = `ROLE: You are a master commercial jewelry photographer and luxury retoucher.

CAMERA: 100mm macro lens, f/11 aperture, edge-to-edge sharpness on the jewelry piece from Image 1. Editorial print quality, high resolution.

LIGHTING: Soft, diffused studio lighting from large overhead softboxes with subtle fill. Generate a dense, physically accurate contact shadow directly beneath the jewelry piece from Image 1.

{{SUBTYPE_BLOCK}}

{{EXECUTION_BLOCK}}

{{BRANDING_CLAUSE}}

INSTRUCTION: Keep Image 1 jewelry identity locked. Do not redesign metalwork, gemstones, proportions, or camera angle unless the workflow explicitly requires a controlled change.

NEGATIVE PROMPT: 3d render, CGI, plastic texture, warped band, distorted facets, floating object, missing contact shadow, cluttered background, watermark collision.

────────────────────────────────────────────────────────
PLACEHOLDER GUIDE (do not delete these if your workflow uses them)
────────────────────────────────────────────────────────
{{SUBTYPE_BLOCK}}          → Replaced with the selected jewelry-type text (Ring, Necklace, …)
{{EXECUTION_BLOCK}}        → Catalog mode: modern / match reference / match mood
{{BRANDING_CLAUSE}}         → Logo × theme/reference branding rules
{{CHOSEN_ENVIRONMENT}}     → One line from the environment pool (when used in a fragment)
{{PLACEMENT_ANATOMY}}      → Try-on body placement for the jewelry type
{{TRYON_MODE_CLAUSE}}       → Extra rules when Try-on mode = Customer
{{USER_CUSTOM_INSTRUCTION}} → Studio free-text the user typed
{{USER_ADDITION_TEXT}}      → Same family as custom instruction (alias)
{{LOGO_IMAGE_INDEX}}        → Image slot number for the logo
{{THEME_LINE}} / {{LOGO_LINE}} → Optional attachment lines

SECTION TIP
Use clear section labels (ROLE:, CAMERA:, LIGHTING:, INSTRUCTION:, NEGATIVE PROMPT:).
The engine can derive layers from these headings when you save.
Leave {{PLACEHOLDERS}} exactly as written — the system fills them at generate time.
`;

export const SAMPLE_JEWELRY_PROMPT = `The ring's shank rests flat against the supporting surface at its true point of contact. Generate a tight, dark contact shadow directly beneath the band, not a diffuse ambient shadow.

────────────────────────────────────────────────────────
JEWELRY-TYPE PROMPT TIPS
────────────────────────────────────────────────────────
• Write 1–4 sentences about how THIS jewelry type sits in the frame.
• Focus on contact points, shadows, scale, and physics — not a full studio brief.
• Master workflow prompts already cover ROLE / CAMERA / LIGHTING.
• Do not invent new {{PLACEHOLDERS}} here unless you know the assembler injects them.
• Example topics: band contact, pendant hang, earring gravity, clasp orientation.
`;

export const SAMPLE_TRYON_PROMPT = `ROLE: You are a jewelry compositing specialist placing a real piece onto a person photo.

INSTRUCTION: Place the jewelry piece from Image 1 onto the person in Image 2, {{PLACEMENT_ANATOMY}}. Match the jewelry's scale, perspective, and lighting to the person's pose and the scene's light direction. Do not alter the person's face, body, pose, skin tone, or existing clothing. Do not alter the jewelry piece itself beyond the perspective and lighting match required to seat it naturally on the body.

{{TRYON_MODE_CLAUSE}}

NEGATIVE PROMPT: warped jewelry to fit body contour, resized jewelry disproportionate to body scale, changed person identity, changed pose, floating jewelry not touching skin, missing contact shadow where jewelry meets skin.

────────────────────────────────────────────────────────
TRY-ON PLACEHOLDERS
────────────────────────────────────────────────────────
{{PLACEMENT_ANATOMY}}  → Where the piece sits on the body for the jewelry type
{{TRYON_MODE_CLAUSE}}   → Extra preserve rules when mode = Customer photo
`;

export function sampleFilename(kind: "master" | "jewelry" | "tryon"): string {
  if (kind === "jewelry") return "jewel-ai-sample-jewelry-prompt.txt";
  if (kind === "tryon") return "jewel-ai-sample-tryon-prompt.txt";
  return "jewel-ai-sample-master-prompt.txt";
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
