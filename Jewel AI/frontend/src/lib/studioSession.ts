import type { Job } from "@/types";

const SESSION_KEY = "jewel:studio-session:v1";

export type StudioSessionDraft = {
  workflow: string;
  tryOnPreset?: string;
  jewelryTypes: string[];
  aspectRatio: string;
  personGeneration: string;
  numberOfImages: number;
  modelEndpointId: string;
  modelParams: Record<string, unknown>;
  workflowVariantKey: string;
  stylePresetId: string;
  promptText: string;
  sessionJobIds: string[];
  activeJobId: string | null;
  /** Locked asset URLs from a loaded history job (no File objects). */
  lockedInputUrl?: string | null;
  lockedReferenceUrl?: string | null;
  lockedModelUrl?: string | null;
};

export function loadStudioSession(): StudioSessionDraft | null {
  try {
    const raw = sessionStorage.getItem(SESSION_KEY);
    if (!raw) return null;
    return JSON.parse(raw) as StudioSessionDraft;
  } catch {
    return null;
  }
}

export function saveStudioSession(draft: StudioSessionDraft) {
  try {
    sessionStorage.setItem(SESSION_KEY, JSON.stringify(draft));
  } catch {
    /* quota / private mode */
  }
}

export function clearStudioSession() {
  try {
    sessionStorage.removeItem(SESSION_KEY);
  } catch {
    /* ignore */
  }
}

export function mergeSessionJobs(prev: Job[], incoming: Job[]): Job[] {
  const map = new Map<string, Job>();
  for (const j of [...incoming, ...prev]) {
    map.set(j.id, { ...(map.get(j.id) || {}), ...j });
  }
  return Array.from(map.values()).sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
  );
}
