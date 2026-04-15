import { getApiBaseUrl } from "@/lib/api-config";

/** Response from POST /api/v1/sessions/{session_id}/ocr_preview (API.md v5.1) */
export type OcrPreviewResponse = {
  ocr_text: string;
  user_message: string;
  combined_draft: string;
};

/**
 * Session-scoped OCR preview (recommended). Does not write messages or start solve.
 * @see docs/API.md — POST /api/v1/sessions/{session_id}/ocr_preview
 */
export async function postOcrPreview(
  sessionId: string,
  file: File,
  userMessage: string | null,
  accessToken: string | undefined
): Promise<OcrPreviewResponse> {
  const formData = new FormData();
  formData.append("file", file);
  if (userMessage != null && userMessage.trim()) {
    formData.append("user_message", userMessage.trim());
  }
  const headers: Record<string, string> = {};
  if (accessToken) headers.Authorization = `Bearer ${accessToken}`;
  const res = await fetch(
    `${getApiBaseUrl()}/api/v1/sessions/${encodeURIComponent(sessionId)}/ocr_preview`,
    {
      method: "POST",
      body: formData,
      headers,
    }
  );
  if (!res.ok) {
    let detail = `OCR preview HTTP ${res.status}`;
    try {
      const j = (await res.json()) as { detail?: unknown };
      if (j?.detail != null) {
        detail =
          typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail);
      }
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  return (await res.json()) as OcrPreviewResponse;
}

/**
 * Legacy stateless OCR (e.g. temp session or tools without a session id).
 * @see docs/API.md — POST /api/v1/ocr
 */
export async function postOcr(
  file: File,
  accessToken: string | undefined
): Promise<string> {
  const formData = new FormData();
  formData.append("file", file);
  const headers: Record<string, string> = {};
  if (accessToken) headers.Authorization = `Bearer ${accessToken}`;
  const res = await fetch(`${getApiBaseUrl()}/api/v1/ocr`, {
    method: "POST",
    body: formData,
    headers,
  });
  if (!res.ok) throw new Error(`OCR HTTP ${res.status}`);
  const data = (await res.json()) as { text?: string };
  return (data.text ?? "").trim();
}
