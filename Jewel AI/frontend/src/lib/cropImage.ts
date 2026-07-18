/** Helpers for cropping images with react-easy-crop pixel areas. */

export type CropAreaPixels = {
  x: number;
  y: number;
  width: number;
  height: number;
};

export async function getCroppedImageFile(
  imageSrc: string,
  crop: CropAreaPixels,
  fileName = "cropped.png",
  mimeType = "image/png",
): Promise<File> {
  const image = await loadImage(imageSrc);
  const canvas = document.createElement("canvas");
  const ctx = canvas.getContext("2d");
  if (!ctx) throw new Error("Canvas not supported");

  const w = Math.max(1, Math.round(crop.width));
  const h = Math.max(1, Math.round(crop.height));
  canvas.width = w;
  canvas.height = h;
  ctx.drawImage(image, crop.x, crop.y, crop.width, crop.height, 0, 0, w, h);

  const blob = await new Promise<Blob>((resolve, reject) => {
    canvas.toBlob(
      (b) => (b ? resolve(b) : reject(new Error("Failed to encode crop"))),
      mimeType,
      0.92,
    );
  });
  const base = fileName.replace(/\.[^.]+$/, "") || "cropped";
  const ext = mimeType === "image/jpeg" ? ".jpg" : mimeType === "image/webp" ? ".webp" : ".png";
  return new File([blob], `${base}${ext}`, { type: mimeType });
}

function loadImage(src: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = () => reject(new Error("Failed to load image for crop"));
    img.crossOrigin = "anonymous";
    img.src = src;
  });
}
