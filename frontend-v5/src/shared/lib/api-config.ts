/**
 * Defaults align with backend/API.md (local Docker / HF Spaces often use port 7860).
 * Override with NEXT_PUBLIC_API_URL and optionally NEXT_PUBLIC_WS_URL.
 */

export const DEFAULT_API_BASE = "http://localhost:7860";

export function getApiBaseUrl(): string {
  const fromEnv = process.env.NEXT_PUBLIC_API_URL?.trim();
  return fromEnv || DEFAULT_API_BASE;
}

/**
 * WebSocket base: explicit NEXT_PUBLIC_WS_URL, or derived from API URL (same host/port).
 */
export function getWsBaseUrl(): string {
  const explicit = process.env.NEXT_PUBLIC_WS_URL?.trim();
  if (explicit) return explicit.replace(/\/$/, "");

  try {
    const u = new URL(getApiBaseUrl());
    const wsProto = u.protocol === "https:" ? "wss:" : "ws:";
    return `${wsProto}//${u.host}`;
  } catch {
    return "ws://localhost:7860";
  }
}
