/** Map raw job/provider error strings to short operator-facing reasons. */
export function humanizeJobError(raw: string | null | undefined): string {
  const text = (raw || "").trim();
  if (!text) return "Generation failed for an unknown reason";
  const lower = text.toLowerCase();

  if (lower.includes("401") || lower.includes("403") || lower.includes("unauthorized") || lower.includes("forbidden")) {
    return "Storage or API authentication expired — check provider keys";
  }
  if (lower.includes("timeout") || lower.includes("timed out") || lower.includes("deadline")) {
    return "Timed out waiting for the provider";
  }
  if (lower.includes("rate limit") || lower.includes("429") || lower.includes("quota")) {
    return "Provider rate limit or quota hit";
  }
  if (lower.includes("rejected") || lower.includes("safety") || lower.includes("content policy")) {
    return "Provider rejected this prompt or image";
  }
  if (lower.includes("no images") || lower.includes("empty response")) {
    return "Provider returned no images";
  }
  if (lower.includes("insufficient credits") || lower.includes("402")) {
    return "Insufficient credits";
  }
  if (lower.includes("network") || lower.includes("econnrefused") || lower.includes("dns")) {
    return "Network error reaching the provider";
  }

  // First readable sentence, capped
  const sentence = text.split(/[\n.!?]/)[0]?.trim() || text;
  const cleaned = sentence.replace(/\s+/g, " ");
  return cleaned.length > 120 ? `${cleaned.slice(0, 117)}…` : cleaned;
}
