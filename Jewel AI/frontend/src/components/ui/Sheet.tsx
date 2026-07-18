import { useEffect } from "react";
import { X } from "lucide-react";

type SheetProps = {
  open: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
  side?: "left" | "right" | "bottom";
};

/** Mobile/tablet drawer for Workflows or Inspector. */
export function Sheet({ open, onClose, title, children, side = "bottom" }: SheetProps) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = prev;
    };
  }, [open, onClose]);

  if (!open) return null;

  const sideClass =
    side === "left"
      ? "inset-y-0 left-0 w-[min(100%,280px)]"
      : side === "right"
        ? "inset-y-0 right-0 w-[min(100%,320px)]"
        : "inset-x-0 bottom-0 max-h-[85vh] rounded-t-jewel-lg";

  return (
    <div className="fixed inset-0 z-50 lg:hidden">
      <button
        type="button"
        className="absolute inset-0 bg-jewel-ink/40"
        aria-label="Close panel"
        onClick={onClose}
      />
      <div
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className={`absolute flex flex-col border border-jewel-border bg-jewel-surface shadow-sticky ${sideClass}`}
      >
        <div className="flex items-center justify-between gap-2 border-b border-jewel-border px-4 py-3">
          <p className="text-sm font-semibold text-jewel-ink">{title}</p>
          <button type="button" onClick={onClose} className="ui-btn-ghost h-8 w-8 p-0" aria-label="Close">
            <X className="size-4" />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-4">{children}</div>
      </div>
    </div>
  );
}
