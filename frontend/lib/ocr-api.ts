import { getApiBaseUrl } from "@/lib/api-config";

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
