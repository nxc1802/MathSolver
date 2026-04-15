import { getApiBaseUrl } from "@/lib/api-config";

/** Response from POST /api/v1/sessions/{session_id}/ocr_preview (see docs/API.md) */
export type OcrPreviewResponse = {
  ocr_text: string;
  user_message: string;
  combined_draft: string;
};

/**
 * Session-scoped OCR preview (recommended before solve when user attaches images).
 * POST multipart: file + optional user_message.
 */
export async function postOcrPreview(
  sessionId: string,
  file: File,
  userMessage: string | undefined,
  accessToken: string | undefined
): Promise<OcrPreviewResponse> {
  const formData = new FormData();
  formData.append("file", file);
  const um = userMessage?.trim() ?? "";
  if (um) formData.append("user_message", um);
  const headers: Record<string, string> = {};
  if (accessToken) headers.Authorization = `Bearer ${accessToken}`;
  const res = await fetch(
    `${getApiBaseUrl()}/api/v1/sessions/${encodeURIComponent(sessionId)}/ocr_preview`,
    { method: "POST", body: formData, headers }
  );
  if (!res.ok) throw new Error(`OCR preview HTTP ${res.status}`);
  return (await res.json()) as OcrPreviewResponse;
}

/**
 * Legacy stateless OCR — POST /api/v1/ocr (no session).
 * Used when session id is temporary (e.g. temp-*) and ocr_preview is unavailable.
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
