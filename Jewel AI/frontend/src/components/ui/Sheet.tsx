import { useEffect, useRef } from "react";
import { X } from "lucide-react";

type SheetProps = {
  open: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
  side?: "left" | "right" | "bottom";
};

/** Mobile/tablet drawer for Workflows or Inspector. Focus trap + Escape + restore focus.
 *  Tablet (md–lg): slightly wider panels; desktop (lg+) uses the 3-zone grid instead of sheets.
 */
export function Sheet({ open, onClose, title, children, side = "bottom" }: SheetProps) {
  const panelRef = useRef<HTMLDivElement>(null);
  const previousFocus = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (!open) return;
    previousFocus.current = document.activeElement as HTMLElement | null;
    const panel = panelRef.current;
    const focusable = panel?.querySelectorAll<HTMLElement>(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])',
    );
    focusable?.[0]?.focus();

    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        onClose();
        return;
      }
      if (e.key !== "Tab" || !panel || !focusable?.length) return;
      const list = Array.from(focusable);
      const first = list[0];
      const last = list[list.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    };
    document.addEventListener("keydown", onKey);
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = prev;
      previousFocus.current?.focus?.();
    };
  }, [open, onClose]);

  if (!open) return null;

  const sideClass =
    side === "left"
      ? "inset-y-0 left-0 w-[min(100%,280px)] md:w-[min(100%,320px)]"
      : side === "right"
        ? "inset-y-0 right-0 w-[min(100%,320px)] md:w-[min(100%,360px)]"
        : "inset-x-0 bottom-0 max-h-[85vh] rounded-t-jewel-lg md:max-h-[80vh]";

  return (
    <div className="fixed inset-0 z-50 lg:hidden">
      <button
        type="button"
        className="absolute inset-0 bg-jewel-ink/40"
        aria-label="Close panel"
        onClick={onClose}
      />
      <div
        ref={panelRef}
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
