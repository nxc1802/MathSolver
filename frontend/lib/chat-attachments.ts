/**
 * Draft images attached in the composer (before OCR / confirm).
 */
export type DraftImage = {
  id: string;
  file: File;
  previewUrl: string;
};

export function createDraftImage(file: File): DraftImage {
  return {
    id: `img-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`,
    file,
    previewUrl: URL.createObjectURL(file),
  };
}

export function revokeDraftImage(d: DraftImage): void {
  try {
    URL.revokeObjectURL(d.previewUrl);
  } catch {
    /* ignore */
  }
}

export function revokeDraftImages(list: DraftImage[]): void {
  list.forEach(revokeDraftImage);
}

/**
 * Final message combining user-typed text and OCR output(s).
 */
export function buildCombinedMessage(userText: string, ocrParts: string[]): string {
  const ocr = ocrParts.map((t) => t.trim()).filter(Boolean).join("\n\n");
  const u = userText.trim();
  if (!ocr) return u;
  if (!u) return `[Trích từ ảnh]\n${ocr}`;
  return `[User]\n${u}\n\n[Trích từ ảnh]\n${ocr}`;
}
