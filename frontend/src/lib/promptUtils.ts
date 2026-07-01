import type { PromptLayer, PromptTemplate, SubjectPrompt } from "@/types";

export function masterToSingleText(template: {
  prompt_text?: string | null;
  layers?: PromptLayer[];
}): string {
  if (template.prompt_text?.trim()) {
    return template.prompt_text.trim();
  }
  if (template.layers?.length) {
    return template.layers
      .filter(
        (l) =>
          !l.is_system &&
          l.type !== "insert_point" &&
          l.type !== "variant_insert" &&
          l.type !== "user_insert" &&
          l.enabled !== false &&
          l.content
      )
      .sort((a, b) => a.order - b.order)
      .map((l) => `${l.label}: ${l.content}`)
      .join("\n\n");
  }
  return "";
}

export function subjectToSingleText(subject: {
  prompt_text?: string | null;
  layers?: PromptLayer[];
}): string {
  return masterToSingleText(subject);
}

export const VARIANT_WORKFLOWS = [
  "GEMSTONE_COLOR_CHANGE",
  "BACKGROUND_REPLACEMENT",
  "LUXURY_ENHANCEMENT",
  "REFERENCE_STYLE_MATCH",
] as const;

const VARIANT_FIELD_MAP: Record<string, string> = {
  GEMSTONE_COLOR_CHANGE: "gemstone_target_color",
  BACKGROUND_REPLACEMENT: "background_style",
  LUXURY_ENHANCEMENT: "metal_type",
  REFERENCE_STYLE_MATCH: "background_style",
};

export function variantPayloadField(workflow: string, label: string): Record<string, string> {
  const field = VARIANT_FIELD_MAP[workflow];
  if (!field || !label.trim()) return {};
  return { [field]: label.trim() };
}

export const MASTER_CHILD_KEY = "__master__";

export function childKeyForSubject(jewelryType: string) {
  return `subject:${jewelryType}`;
}

export function childKeyForVariant(variantKey: string) {
  return `variant:${variantKey}`;
}

export function parseChildKey(
  key: string
): { type: "master" } | { type: "subject"; jewelryType: string } | { type: "variant"; variantKey: string } {
  if (key === MASTER_CHILD_KEY) return { type: "master" };
  if (key.startsWith("subject:")) return { type: "subject", jewelryType: key.slice(8) };
  if (key.startsWith("variant:")) return { type: "variant", variantKey: key.slice(8) };
  return { type: "master" };
}

export function findSubject(subjects: SubjectPrompt[], workflow: string, jewelryType: string) {
  return subjects.find((s) => s.workflow === workflow && s.jewelry_type === jewelryType);
}

export function findMaster(templates: PromptTemplate[], workflow: string) {
  return templates.find((p) => p.workflow === workflow);
}
