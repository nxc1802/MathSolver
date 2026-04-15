/** Max longer side after resize (px) before OCR upload */
const MAX_OCR_EDGE = 2048;
/** Max file size to send to OCR (bytes) */
const MAX_OCR_BYTES = 8 * 1024 * 1024;

/**
 * Resize image on canvas to reduce noise/payload for OCR. Returns PNG File when possible.
 */
export async function preprocessImageForOcr(file: File): Promise<File> {
  if (!file.type.startsWith("image/")) return file;
  if (file.size > MAX_OCR_BYTES) {
    throw new Error("Ảnh quá lớn (tối đa 8MB). Hãy chọn ảnh nhỏ hơn.");
  }

  const bitmap = await createImageBitmap(file).catch(() => null);
  if (!bitmap) return file;

  const w = bitmap.width;
  const h = bitmap.height;
  const scale = Math.min(1, MAX_OCR_EDGE / Math.max(w, h));
  if (scale >= 1) {
    bitmap.close();
    return file;
  }

  const tw = Math.round(w * scale);
  const th = Math.round(h * scale);
  const canvas = document.createElement("canvas");
  canvas.width = tw;
  canvas.height = th;
  const ctx = canvas.getContext("2d");
  if (!ctx) {
    bitmap.close();
    return file;
  }
  ctx.drawImage(bitmap, 0, 0, tw, th);
  bitmap.close();

  const blob: Blob | null = await new Promise((res) =>
    canvas.toBlob((b) => res(b), "image/png", 0.92)
  );
  if (!blob) return file;

  const base = file.name.replace(/\.[^.]+$/, "") || "image";
  return new File([blob], `${base}-ocr.png`, { type: "image/png" });
}
