import { useCallback, useRef, useState } from "react";
import { Crop, Plus, UploadCloud, X } from "lucide-react";
import { toast } from "sonner";

const MAX_FILES = 30;

type Props = {
  id: string;
  /** Shown only on empty state inside the stage */
  emptyTitle?: string;
  files: File[];
  previews: string[];
  error?: string;
  onAppend: (files: File[]) => void;
  onReplace: (files: File[]) => void;
  onRemoveAt: (index: number) => void;
  onClearAll: () => void;
  imageZoom?: number;
  /** When true, hide per-image remove overlays (parent header owns Replace) */
  cleanPreview?: boolean;
  /** Crop a specific uploaded file (local File only) */
  onCropAt?: (index: number) => void;
};

export function ProductUploadGallery({
  id,
  emptyTitle = "Product",
  files,
  previews,
  error,
  onAppend,
  onReplace,
  onRemoveAt,
  onClearAll,
  imageZoom = 1,
  cleanPreview = false,
  onCropAt,
}: Props) {
  const emptyInputId = `${id}-empty-input`;
  const addInputId = `${id}-add-input`;
  const emptyInputRef = useRef<HTMLInputElement>(null);
  const addInputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);

  const hasFiles = files.length > 0;
  const hasPreviewOnly = !hasFiles && previews.length > 0;
  const room = Math.max(0, MAX_FILES - files.length);
  const isSingle = files.length === 1 || (hasPreviewOnly && previews.length === 1);

  const takeFiles = useCallback(
    (list: FileList | null, mode: "append" | "replace") => {
      if (!list?.length) return;
      const incoming = Array.from(list).filter((f) =>
        /^image\/(jpeg|png|webp)$/i.test(f.type),
      );
      if (!incoming.length) return;

      if (mode === "replace") {
        onReplace(incoming.slice(0, MAX_FILES));
        return;
      }

      if (room <= 0) {
        toast.message(`Limit is ${MAX_FILES} images`);
        return;
      }
      const next = incoming.slice(0, room);
      if (incoming.length > room) {
        toast.message(`Added ${next.length} — limit is ${MAX_FILES}`);
      }
      onAppend(next);
    },
    [onAppend, onReplace, room],
  );

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    takeFiles(e.dataTransfer.files, hasFiles ? "append" : "replace");
  };

  const stageClass = `relative min-h-0 h-full w-full flex-1 overflow-hidden rounded-lg transition-colors ${
    dragging
      ? "border-2 border-[var(--jewel-accent)] bg-[var(--jewel-accent-soft)]/40"
      : error
        ? "border-2 border-[var(--jewel-danger)] bg-white"
        : !hasFiles && !hasPreviewOnly
          ? "border-2 border-dashed border-[var(--jewel-border)] bg-white hover:border-[var(--jewel-accent)]"
          : "border border-[var(--jewel-border)] bg-white"
  }`;

  return (
    <div className="flex w-full h-full min-h-0 flex-col">
      <input
        ref={addInputRef}
        id={addInputId}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        className="hidden"
        multiple
        onChange={(e) => {
          takeFiles(e.target.files, "append");
          e.target.value = "";
        }}
      />
      <input
        ref={emptyInputRef}
        id={emptyInputId}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        className="hidden"
        multiple
        onChange={(e) => {
          takeFiles(e.target.files, "replace");
          e.target.value = "";
        }}
      />

      <div
        className={stageClass}
        onDragEnter={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragOver={(e) => e.preventDefault()}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
      >
        {!hasFiles && !hasPreviewOnly ? (
          <label
            htmlFor={emptyInputId}
            className="absolute inset-0 flex cursor-pointer flex-col items-center justify-center gap-2 p-4"
          >
            <UploadCloud className="size-8 text-[var(--jewel-accent)]" aria-hidden="true" />
            <span className="text-sm font-semibold text-[var(--jewel-ink)]">
              {dragging ? "Drop images" : emptyTitle}
            </span>
            <span className="text-[11px] text-[var(--jewel-ink-muted)]">
              Click or drop to upload
            </span>
          </label>
        ) : isSingle ? (
          <div className="absolute inset-0 flex flex-col">
            <div className="flex h-8 shrink-0 items-center justify-between gap-2 border-b border-[var(--jewel-hairline)] px-2 bg-white/95">
              <span className="text-[10px] font-semibold uppercase tracking-wide text-jewel-ink-muted">
                {emptyTitle}
              </span>
              <div className="flex items-center gap-0.5">
                {onCropAt && hasFiles ? (
                  <button
                    type="button"
                    onClick={() => onCropAt(0)}
                    className="inline-flex h-7 items-center gap-1 rounded-md px-2 text-[11px] font-semibold text-slate-700 hover:bg-[var(--jewel-accent-soft)] hover:text-[var(--jewel-accent)]"
                    aria-label="Crop image"
                    title="Crop"
                  >
                    <Crop className="size-3.5" />
                    Crop
                  </button>
                ) : null}
                <button
                  type="button"
                  onClick={onClearAll}
                  className="inline-flex h-7 items-center gap-1 rounded-md px-2 text-[11px] font-semibold text-slate-600 hover:bg-rose-50 hover:text-rose-600"
                  aria-label="Clear image"
                  title="Clear"
                >
                  <X className="size-3.5" strokeWidth={2.5} />
                  Clear
                </button>
              </div>
            </div>
            <div className="relative min-h-0 flex-1 flex items-center justify-center p-3">
              <img
                src={previews[0]}
                alt={files[0]?.name || "Product"}
                className="max-h-full max-w-full object-contain transition-transform"
                style={{ transform: `scale(${imageZoom})` }}
              />
              {dragging ? (
                <div className="pointer-events-none absolute inset-0 flex items-center justify-center bg-[var(--jewel-accent)]/15">
                  <span className="rounded-lg bg-white px-3 py-1.5 text-xs font-semibold text-[var(--jewel-accent)] shadow-sm">
                    Drop to add
                  </span>
                </div>
              ) : null}
            </div>
          </div>
        ) : (
          <div className="absolute inset-0 flex flex-col">
            <div className="min-h-0 flex-1 overflow-y-auto p-2 pb-10">
              <div className="grid grid-cols-3 gap-1.5 sm:grid-cols-4">
                {previews.map((url, i) => (
                  <div
                    key={`${files[i]?.name ?? "img"}-${i}-${url.slice(-12)}`}
                    className="group relative aspect-square overflow-hidden rounded-lg border border-[var(--jewel-border)] bg-white"
                  >
                    <img
                      src={url}
                      alt={files[i]?.name || `Product ${i + 1}`}
                      className="size-full object-cover"
                    />
                    <span className="absolute left-1 top-1 rounded bg-white/90 border border-[var(--jewel-border)] px-1 py-px text-[9px] font-semibold tabular-nums text-slate-700">
                      {i + 1}
                    </span>
                    <div
                      className={`absolute right-1 top-1 flex flex-col gap-0.5 ${
                        onCropAt ? "opacity-100" : "opacity-0 group-hover:opacity-100"
                      } transition-opacity focus-within:opacity-100`}
                    >
                      {onCropAt && files[i] ? (
                        <button
                          type="button"
                          onClick={() => onCropAt(i)}
                          className="flex size-6 items-center justify-center rounded-md bg-white/95 text-slate-700 hover:bg-[var(--jewel-accent-soft)] hover:text-[var(--jewel-accent)]"
                          aria-label={`Crop image ${i + 1}`}
                          title="Crop"
                        >
                          <Crop className="size-3" />
                        </button>
                      ) : null}
                      {!cleanPreview ? (
                        <button
                          type="button"
                          onClick={() => onRemoveAt(i)}
                          className="flex size-6 items-center justify-center rounded-md bg-white/90 text-slate-700 hover:bg-rose-100 hover:text-rose-600"
                          aria-label={`Remove image ${i + 1}`}
                        >
                          <X className="size-3.5" strokeWidth={2.5} />
                        </button>
                      ) : null}
                    </div>
                  </div>
                ))}
              </div>
            </div>
            <div className="absolute inset-x-0 bottom-0 flex items-center justify-between gap-2 border-t border-[var(--jewel-hairline)] bg-white px-2 py-1.5">
              <span className="text-[10px] font-semibold tabular-nums text-slate-600">
                {files.length} selected
              </span>
              <div className="flex items-center gap-1.5">
                {room > 0 ? (
                  <button
                    type="button"
                    onClick={() => addInputRef.current?.click()}
                    className="inline-flex items-center gap-1 rounded-md bg-[var(--jewel-surface-muted)] px-2 py-1 text-[10px] font-semibold text-slate-700 hover:bg-[var(--jewel-accent-soft)]"
                  >
                    <Plus className="size-3" />
                    Add
                  </button>
                ) : null}
                <button
                  type="button"
                  onClick={onClearAll}
                  className="rounded-md px-2 py-1 text-[10px] font-semibold text-slate-500 hover:bg-[var(--jewel-surface-muted)]"
                >
                  Clear
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

      {error ? <p className="mt-1 text-xs text-red-600 shrink-0">{error}</p> : null}
    </div>
  );
}
