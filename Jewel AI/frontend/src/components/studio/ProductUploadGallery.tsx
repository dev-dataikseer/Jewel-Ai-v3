import { useCallback, useRef, useState } from "react";
import { ImagePlus, Plus, UploadCloud, X } from "lucide-react";
import { toast } from "sonner";

const MAX_FILES = 30;

type Props = {
  id: string;
  label?: string;
  files: File[];
  previews: string[];
  error?: string;
  onAppend: (files: File[]) => void;
  onReplace: (files: File[]) => void;
  onRemoveAt: (index: number) => void;
  onClearAll: () => void;
  onCrop?: () => void;
};

export function ProductUploadGallery({
  id,
  label = "Product (multi for bulk)",
  files,
  previews,
  error,
  onAppend,
  onReplace,
  onRemoveAt,
  onClearAll,
  onCrop,
}: Props) {
  const emptyInputId = `${id}-empty-input`;
  const addInputId = `${id}-add-input`;
  const emptyInputRef = useRef<HTMLInputElement>(null);
  const addInputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);

  const hasFiles = files.length > 0;
  const room = Math.max(0, MAX_FILES - files.length);
  const isSingle = files.length === 1;

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

  // Match Studio Output frame: fixed 240px stage, image fits inside (object-contain)
  const stageClass = `relative h-[240px] w-full shrink-0 overflow-hidden rounded-xl border-2 transition-colors ${
    dragging
      ? "border-blue-400 bg-blue-50/40"
      : error
        ? "border-red-400 bg-slate-50/50"
        : hasFiles
          ? "border-slate-200 bg-slate-950"
          : "border-dashed border-slate-200 bg-slate-50/50 hover:border-blue-400 hover:bg-blue-50/30"
  }`;

  return (
    <div className="flex w-full flex-col gap-2">
      {/* Header — upload actions move here once images exist */}
      <div className="flex items-center justify-between gap-2">
        <div className="min-w-0">
          <label className="ui-label mb-0">{label}</label>
          {hasFiles && (
            <p className="truncate text-[10px] text-slate-400">
              {isSingle
                ? files[0]?.name || "1 image"
                : `${files.length} images selected`}
            </p>
          )}
        </div>
        <div className="flex shrink-0 items-center gap-1.5">
          {hasFiles && (
            <span className="hidden text-[10px] tabular-nums text-slate-400 sm:inline">
              {files.length}/{MAX_FILES}
            </span>
          )}
          {hasFiles && room > 0 && (
            <button
              type="button"
              onClick={() => addInputRef.current?.click()}
              className="inline-flex h-7 items-center gap-1 rounded-lg border border-slate-200 bg-white px-2 text-[10px] font-semibold text-slate-700 shadow-sm transition hover:border-blue-300 hover:bg-blue-50 hover:text-blue-700"
            >
              <ImagePlus className="size-3.5" />
              Add more
            </button>
          )}
          {hasFiles && (
            <button
              type="button"
              onClick={onClearAll}
              className="inline-flex h-7 items-center rounded-lg px-2 text-[10px] font-semibold text-slate-500 transition hover:bg-slate-100 hover:text-slate-800"
            >
              Clear
            </button>
          )}
        </div>
      </div>

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

      {/* Stage — same footprint empty ↔ filled */}
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
        {!hasFiles ? (
          <label
            htmlFor={emptyInputId}
            className="absolute inset-0 flex cursor-pointer flex-col items-center justify-center p-4"
          >
            <UploadCloud className="mb-2 size-6 text-blue-600" aria-hidden="true" />
            <span className="text-xs font-semibold text-slate-700">
              {dragging ? "Drop to upload" : "Click or drop product images"}
            </span>
            <span className="mt-1 text-[10px] text-slate-400">
              Up to {MAX_FILES} · JPEG, PNG, WebP
            </span>
          </label>
        ) : isSingle ? (
          <div className="group absolute inset-0 flex items-center justify-center p-3">
            <img
              src={previews[0]}
              alt={files[0]?.name || "Product"}
              className="max-h-full max-w-full rounded object-contain"
            />
            <button
              type="button"
              onClick={() => onRemoveAt(0)}
              className="absolute right-2 top-2 flex size-7 items-center justify-center rounded-lg bg-slate-900/75 text-white opacity-90 transition hover:bg-rose-600 group-hover:opacity-100"
              title="Remove image"
              aria-label="Remove image"
            >
              <X className="size-3.5" strokeWidth={2.5} />
            </button>
            {dragging && (
              <div className="pointer-events-none absolute inset-0 flex items-center justify-center bg-blue-600/20 backdrop-blur-[1px]">
                <span className="rounded-lg bg-white px-3 py-1.5 text-xs font-semibold text-blue-700 shadow-sm">
                  Drop to add more
                </span>
              </div>
            )}
          </div>
        ) : (
          <div className="absolute inset-0 flex flex-col">
            <div className="min-h-0 flex-1 overflow-y-auto p-2 pb-10">
              <div className="grid grid-cols-3 gap-1.5 sm:grid-cols-4">
                {previews.map((url, i) => (
                  <div
                    key={`${files[i]?.name ?? "img"}-${i}-${url.slice(-12)}`}
                    className="group relative aspect-square overflow-hidden rounded-lg border border-white/10 bg-slate-900"
                  >
                    <img
                      src={url}
                      alt={files[i]?.name || `Product ${i + 1}`}
                      className="size-full object-cover"
                    />
                    <span className="absolute left-1 top-1 rounded bg-black/55 px-1 py-px text-[9px] font-semibold tabular-nums text-white">
                      {i + 1}
                    </span>
                    <button
                      type="button"
                      onClick={() => onRemoveAt(i)}
                      className="absolute right-1 top-1 flex size-6 items-center justify-center rounded-md bg-black/70 text-white"
                      title={`Remove image ${i + 1}`}
                      aria-label={`Remove image ${i + 1}`}
                    >
                      <X className="size-3.5" strokeWidth={2.5} />
                    </button>
                  </div>
                ))}
              </div>
            </div>
            <div className="absolute inset-x-0 bottom-0 flex items-center justify-between gap-2 border-t border-white/10 bg-slate-950/90 px-2 py-1.5 backdrop-blur-sm">
              <span className="text-[10px] font-semibold tabular-nums text-slate-200">
                {files.length} selected
              </span>
              <div className="flex items-center gap-1.5">
                {room > 0 && (
                  <button
                    type="button"
                    onClick={() => addInputRef.current?.click()}
                    className="inline-flex items-center gap-1 rounded-md bg-white/10 px-2 py-1 text-[10px] font-semibold text-white hover:bg-white/20"
                  >
                    <Plus className="size-3" />
                    Add more
                  </button>
                )}
                <button
                  type="button"
                  onClick={onClearAll}
                  className="rounded-md px-2 py-1 text-[10px] font-semibold text-slate-300 hover:bg-white/10 hover:text-white"
                >
                  Clear
                </button>
              </div>
            </div>
            {dragging && (
              <div className="pointer-events-none absolute inset-0 flex items-center justify-center bg-blue-600/20 backdrop-blur-[1px]">
                <span className="rounded-lg bg-white px-3 py-1.5 text-xs font-semibold text-blue-700 shadow-sm">
                  Drop to add more
                </span>
              </div>
            )}
          </div>
        )}
      </div>

      {isSingle && onCrop && (
        <button
          type="button"
          onClick={onCrop}
          className="self-start text-[10px] font-medium text-slate-400 hover:text-slate-600"
        >
          Crop (optional)
        </button>
      )}
      {error && <p className="text-xs text-red-600">{error}</p>}
    </div>
  );
}
