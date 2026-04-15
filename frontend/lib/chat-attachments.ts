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
 * Merge legacy OCR parts when using POST /api/v1/ocr only (e.g. temp session).
 * Same paragraph spacing as backend build_combined_ocr_preview_draft for multi-part OCR text.
 */
export function buildCombinedMessage(userText: string, ocrParts: string[]): string {
  const ocr = ocrParts.map((t) => t.trim()).filter(Boolean).join("\n\n");
  const u = userText.trim();
  if (!ocr) return u;
  if (!u) return ocr;
  return `${u}\n\n${ocr}`;
}
