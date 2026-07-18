import { useCallback, useState } from "react";
import Cropper, { type Area } from "react-easy-crop";
import { Check, X } from "lucide-react";
import { getCroppedImageFile, type CropAreaPixels } from "@/lib/cropImage";

type AspectOption = "free" | "1:1" | "4:3" | "3:4";

const ASPECTS: { id: AspectOption; label: string; value: number | undefined }[] = [
  { id: "free", label: "Free", value: undefined },
  { id: "1:1", label: "1:1", value: 1 },
  { id: "4:3", label: "4:3", value: 4 / 3 },
  { id: "3:4", label: "3:4", value: 3 / 4 },
];

type Props = {
  open: boolean;
  imageSrc: string;
  fileName?: string;
  title?: string;
  onCancel: () => void;
  onConfirm: (file: File) => void;
};

export function ImageCropModal({
  open,
  imageSrc,
  fileName = "cropped.png",
  title = "Crop image",
  onCancel,
  onConfirm,
}: Props) {
  const [crop, setCrop] = useState({ x: 0, y: 0 });
  const [zoom, setZoom] = useState(1);
  const [aspectId, setAspectId] = useState<AspectOption>("free");
  const [croppedAreaPixels, setCroppedAreaPixels] = useState<CropAreaPixels | null>(null);
  const [busy, setBusy] = useState(false);

  const onCropComplete = useCallback((_area: Area, pixels: Area) => {
    setCroppedAreaPixels(pixels);
  }, []);

  if (!open) return null;

  const aspect = ASPECTS.find((a) => a.id === aspectId)?.value;

  const confirm = async () => {
    if (!croppedAreaPixels) return;
    setBusy(true);
    try {
      const mime =
        fileName.toLowerCase().endsWith(".jpg") || fileName.toLowerCase().endsWith(".jpeg")
          ? "image/jpeg"
          : fileName.toLowerCase().endsWith(".webp")
            ? "image/webp"
            : "image/png";
      const file = await getCroppedImageFile(imageSrc, croppedAreaPixels, fileName, mime);
      onConfirm(file);
    } catch {
      onCancel();
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[80] flex items-center justify-center bg-slate-900/50 p-4">
      <div
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className="flex w-full max-w-2xl flex-col overflow-hidden rounded-2xl bg-white shadow-xl"
      >
        <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
          <h2 className="text-sm font-semibold text-slate-900">{title}</h2>
          <button
            type="button"
            onClick={onCancel}
            className="rounded-lg p-1.5 text-slate-500 hover:bg-slate-100"
            aria-label="Close crop"
          >
            <X className="size-4" />
          </button>
        </div>

        <div className="relative h-[360px] bg-slate-900">
          <Cropper
            image={imageSrc}
            crop={crop}
            zoom={zoom}
            aspect={aspect}
            onCropChange={setCrop}
            onZoomChange={setZoom}
            onCropComplete={onCropComplete}
          />
        </div>

        <div className="space-y-3 border-t border-slate-200 px-4 py-3">
          <div className="flex flex-wrap gap-1.5">
            {ASPECTS.map((a) => (
              <button
                key={a.id}
                type="button"
                onClick={() => setAspectId(a.id)}
                className={`rounded-lg px-2.5 py-1 text-[11px] font-semibold ${
                  aspectId === a.id
                    ? "bg-blue-600 text-white"
                    : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                }`}
              >
                {a.label}
              </button>
            ))}
          </div>
          <label className="flex items-center gap-3 text-xs text-slate-600">
            <span className="w-10 shrink-0">Zoom</span>
            <input
              type="range"
              min={1}
              max={3}
              step={0.05}
              value={zoom}
              onChange={(e) => setZoom(Number(e.target.value))}
              className="w-full"
            />
          </label>
          <div className="flex justify-end gap-2">
            <button type="button" onClick={onCancel} className="ui-btn-secondary" disabled={busy}>
              Cancel
            </button>
            <button
              type="button"
              onClick={() => void confirm()}
              disabled={busy || !croppedAreaPixels}
              className="ui-btn-primary"
            >
              <Check className="size-3.5" />
              {busy ? "Applying…" : "Apply crop"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
