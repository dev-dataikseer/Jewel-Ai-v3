import { useCallback, useRef, useState } from "react";
import { Crop, Replace, UploadCloud, X } from "lucide-react";

type Props = {
  id: string;
  label: string;
  previews: string[];
  onFiles: (files: FileList | null) => void;
  single?: boolean;
  multiple?: boolean;
  error?: string;
  /** Compact chip when assets already selected (inspector / brand kit) */
  compact?: boolean;
  /** Fill parent cell equally with Product stage (Studio dual Input) */
  stage?: boolean;
  fileCount?: number;
  fileName?: string | null;
  onCrop?: () => void;
  cropLabel?: string;
  onClear?: () => void;
  hint?: string;
};

export function UploadZone({
  id,
  label,
  previews,
  onFiles,
  single,
  multiple,
  error,
  compact,
  stage,
  fileCount,
  fileName,
  onCrop,
  cropLabel = "Crop",
  onClear,
  hint,
}: Props) {
  const inputId = `${id}-input`;
  const helpId = `${id}-help`;
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);

  const applyFiles = useCallback(
    (list: FileList | null) => {
      onFiles(list);
      if (inputRef.current) inputRef.current.value = "";
    },
    [onFiles],
  );

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    applyFiles(e.dataTransfer.files);
  };

  const hasPreview = previews.length > 0;

  const fileInput = (
    <input
      ref={inputRef}
      id={inputId}
      type="file"
      accept="image/jpeg,image/png,image/webp"
      className="hidden"
      aria-describedby={helpId}
      multiple={multiple && !single}
      onChange={(e) => applyFiles(e.target.files)}
    />
  );

  if (stage) {
    return (
      <div className="flex h-full min-h-0 w-full flex-col">
        <div
          className={`relative min-h-0 flex-1 overflow-hidden rounded-lg transition-colors ${
            dragging
              ? "border-2 border-[var(--jewel-accent)] bg-[var(--jewel-accent-soft)]/40"
              : error
                ? "border-2 border-[var(--jewel-danger)] bg-white"
                : hasPreview
                  ? "border border-[var(--jewel-border)] bg-white"
                  : "border-2 border-dashed border-[var(--jewel-border)] bg-white hover:border-[var(--jewel-accent)]"
          }`}
          onDragEnter={(e) => {
            e.preventDefault();
            setDragging(true);
          }}
          onDragOver={(e) => e.preventDefault()}
          onDragLeave={() => setDragging(false)}
          onDrop={onDrop}
        >
          {hasPreview ? (
            <div className="absolute inset-0 flex flex-col">
              <div className="flex h-8 shrink-0 items-center justify-between gap-2 border-b border-[var(--jewel-hairline)] px-2">
                <span className="text-[10px] font-semibold uppercase tracking-wide text-jewel-ink-muted">
                  {label}
                </span>
                <div className="flex items-center gap-0.5">
                  {onCrop ? (
                    <button
                      type="button"
                      onClick={onCrop}
                      className="flex size-7 items-center justify-center rounded-md text-slate-600 hover:bg-[var(--jewel-accent-soft)] hover:text-[var(--jewel-accent)]"
                      aria-label={cropLabel}
                      title={cropLabel}
                    >
                      <Crop className="size-3.5" />
                    </button>
                  ) : null}
                  <button
                    type="button"
                    onClick={() => inputRef.current?.click()}
                    className="flex size-7 items-center justify-center rounded-md text-slate-600 hover:bg-[var(--jewel-surface-muted)]"
                    aria-label="Replace image"
                    title="Replace"
                  >
                    <Replace className="size-3.5" />
                  </button>
                  {onClear ? (
                    <button
                      type="button"
                      onClick={onClear}
                      className="flex size-7 items-center justify-center rounded-md text-slate-600 hover:bg-rose-50 hover:text-rose-600"
                      aria-label="Clear image"
                      title="Clear"
                    >
                      <X className="size-3.5" />
                    </button>
                  ) : null}
                </div>
              </div>
              <div className="relative min-h-0 flex-1 flex items-center justify-center p-2">
                <img
                  src={previews[0]}
                  alt={`${label} preview`}
                  className="max-h-full max-w-full object-contain"
                />
              </div>
            </div>
          ) : (
            <label
              htmlFor={inputId}
              className="absolute inset-0 flex cursor-pointer flex-col items-center justify-center gap-1.5 p-3 text-center"
            >
              <UploadCloud className="size-7 text-[var(--jewel-accent)]" aria-hidden="true" />
              <span className="text-sm font-semibold text-jewel-ink">
                {dragging ? "Drop image" : label}
              </span>
              <span className="text-[11px] text-jewel-ink-muted">Click or drop to upload</span>
            </label>
          )}
          {fileInput}
        </div>
        <p id={helpId} className="sr-only">
          Upload {label.toLowerCase()} image as JPEG, PNG, or WebP
        </p>
        {error ? <p className="mt-1 text-xs text-red-600 shrink-0">{error}</p> : null}
      </div>
    );
  }

  if (compact && hasPreview) {
    return (
      <div className="space-y-1">
        <div className="flex items-center justify-between gap-2">
          <label className="ui-label mb-0">{label}</label>
          {hint && <span className="text-[10px] text-slate-400">{hint}</span>}
        </div>
        <div
          className={`flex items-center gap-2 rounded-xl border bg-white px-2 py-1.5 ${
            error ? "border-red-300" : "border-slate-200"
          }`}
        >
          <img
            src={previews[0]}
            alt={`${label} preview`}
            className="size-12 shrink-0 rounded-lg object-cover border border-slate-100"
          />
          <div className="min-w-0 flex-1">
            <p className="truncate text-[11px] font-medium text-slate-700">
              {fileName || (fileCount && fileCount > 1 ? `${fileCount} files` : "Selected")}
            </p>
            {fileCount && fileCount > 1 && (
              <p className="text-[10px] text-slate-400">{fileCount} images ready</p>
            )}
          </div>
          <div className="flex shrink-0 items-center gap-0.5">
            {onCrop ? (
              <button
                type="button"
                onClick={onCrop}
                className="rounded-lg p-1.5 text-slate-500 hover:bg-slate-100 hover:text-slate-800"
                title={cropLabel}
                aria-label={cropLabel}
              >
                <Crop className="size-3.5" />
              </button>
            ) : null}
            <button
              type="button"
              onClick={() => inputRef.current?.click()}
              className="rounded-lg p-1.5 text-slate-500 hover:bg-slate-100 hover:text-slate-800"
              title="Replace"
              aria-label="Replace image"
            >
              <Replace className="size-3.5" />
            </button>
            {onClear && (
              <button
                type="button"
                onClick={onClear}
                className="rounded-lg p-1.5 text-slate-500 hover:bg-slate-100 hover:text-slate-800"
                title="Clear"
                aria-label="Clear image"
              >
                <X className="size-3.5" />
              </button>
            )}
          </div>
          {fileInput}
        </div>
        {error && <p className="text-xs text-red-600">{error}</p>}
      </div>
    );
  }

  return (
    <div className="flex flex-col">
      <div className="flex items-center justify-between gap-2">
        <label htmlFor={inputId} className="ui-label">
          {label}
        </label>
        {hint && <span className="text-[10px] text-slate-400">{hint}</span>}
      </div>
      <label
        htmlFor={inputId}
        onDragEnter={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragOver={(e) => e.preventDefault()}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        className={`flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed transition-colors ${
          hasPreview ? "min-h-[72px] p-2" : "min-h-[88px] p-3"
        } ${
          dragging
            ? "border-blue-400 bg-blue-50/50"
            : error
              ? "border-red-400 bg-slate-50/50"
              : "border-slate-200 bg-slate-50/50 hover:border-blue-400 hover:bg-blue-50/30"
        }`}
      >
        <UploadCloud className="mb-1 size-5 text-blue-600" aria-hidden="true" />
        <span className="text-[11px] font-semibold text-slate-700">
          {dragging ? "Drop" : "Upload"}
        </span>
        {fileInput}
      </label>
      <p id={helpId} className="sr-only">
        Upload {label.toLowerCase()} image as JPEG, PNG, or WebP
      </p>
      {error && <p className="mt-1 text-xs text-red-600">{error}</p>}
      {hasPreview && (
        <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
          {previews.slice(0, 6).map((url, i) => (
            <img
              key={`${url}-${i}`}
              src={url}
              alt={`${label} preview ${i + 1}`}
              loading="lazy"
              className="size-11 rounded-lg border border-slate-200 object-cover"
            />
          ))}
          {fileCount != null && fileCount > 6 && (
            <span className="text-[10px] font-medium text-slate-500">+{fileCount - 6} more</span>
          )}
          {onCrop && single && (
            <button
              type="button"
              onClick={onCrop}
              className="text-[10px] font-medium text-slate-400 hover:text-slate-600"
            >
              {cropLabel} (optional)
            </button>
          )}
          {onClear && (
            <button
              type="button"
              onClick={onClear}
              className="inline-flex items-center gap-1 rounded-lg border border-slate-200 px-2 py-1 text-[10px] font-semibold text-slate-600 hover:bg-slate-50"
            >
              <X className="size-3" /> Clear
            </button>
          )}
        </div>
      )}
    </div>
  );
}
