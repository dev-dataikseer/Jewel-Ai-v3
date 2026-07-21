import { FacetMark } from "@/components/ui/FacetMark";

type JobStageBarProps = {
  stage: "idle" | "queued" | "generating" | "finalizing" | "ready" | "failed" | "cancelled";
  label: string;
  detail?: string;
};

const STAGES = ["queued", "generating", "finalizing", "ready"] as const;

export function JobStageBar({ stage, label, detail }: JobStageBarProps) {
  if (stage === "idle") return null;
  const activeIdx =
    stage === "failed" || stage === "cancelled"
      ? -1
      : Math.max(
          0,
          STAGES.indexOf(
            stage === "ready" ? "ready" : (stage as (typeof STAGES)[number]),
          ),
        );

  const showSpin = stage === "queued" || stage === "generating" || stage === "finalizing";

  return (
    <div className="mb-3 space-y-2" aria-live="polite">
      <div className="flex gap-1">
        {STAGES.map((s, i) => (
          <div
            key={s}
            className="h-1 flex-1 rounded-full"
            style={{
              backgroundColor:
                stage === "failed" || stage === "cancelled"
                  ? "var(--jewel-danger)"
                  : i <= activeIdx
                    ? "var(--jewel-accent)"
                    : "var(--jewel-border)",
            }}
          />
        ))}
      </div>
      <div className="flex items-start gap-2">
        {showSpin ? (
          <FacetMark variant="spin" size={18} className="mt-0.5 shrink-0 text-[var(--jewel-accent)]" />
        ) : stage === "ready" ? (
          <FacetMark variant="check" size={18} className="mt-0.5 shrink-0 text-[var(--jewel-accent)]" />
        ) : null}
        <div className="min-w-0">
          <p className="text-sm font-semibold text-jewel-ink">{label}</p>
          {detail && <p className="text-xs text-jewel-ink-muted">{detail}</p>}
        </div>
      </div>
    </div>
  );
}

export function resolveJobStage(job: {
  status: string;
  provider_metadata?: Record<string, unknown> | null;
}): JobStageBarProps["stage"] {
  if (job.status === "COMPLETED") return "ready";
  if (job.status === "FAILED") return "failed";
  if (job.status === "CANCELLED") return "cancelled";
  if (job.status === "PENDING") return "queued";
  const meta = job.provider_metadata || {};
  if (meta.webhook_pending || meta.progressStage === "waiting_on_fal") return "generating";
  if (meta.progressStage === "finalizing") return "finalizing";
  return "generating";
}
