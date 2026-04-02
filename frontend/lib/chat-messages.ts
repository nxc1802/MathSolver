import type { ChatMessage, MessageRole, MessageType } from "@/types/chat";

/** Raw row from GET /api/v1/sessions/{id}/messages */
export function messageFromApi(m: {
  id: string;
  role: string;
  type: string;
  content: string;
  created_at: string;
  metadata?: Record<string, unknown> | null;
}): ChatMessage {
  return {
    id: m.id,
    role: m.role as MessageRole,
    type: m.type as MessageType,
    content: m.content,
    timestamp: new Date(m.created_at).getTime(),
    metadata: normalizeMessageMetadata(m.metadata),
  };
}

export function normalizeMessageMetadata(
  raw: Record<string, unknown> | null | undefined
): ChatMessage["metadata"] {
  if (!raw || typeof raw !== "object") return undefined;

  const video_url =
    (typeof raw.video_url === "string" && raw.video_url) ||
    (typeof raw.videoUrl === "string" && raw.videoUrl) ||
    undefined;

  const job_id =
    (typeof raw.job_id === "string" && raw.job_id) ||
    (typeof raw.jobId === "string" && raw.jobId) ||
    undefined;

  const geometry_dsl =
    typeof raw.geometry_dsl === "string" ? raw.geometry_dsl : undefined;
  const image_url =
    typeof raw.image_url === "string" ? raw.image_url : undefined;

  let coordinates: Record<string, [number, number]> | undefined;
  if (raw.coordinates && typeof raw.coordinates === "object") {
    coordinates = raw.coordinates as Record<string, [number, number]>;
  }

  const out: NonNullable<ChatMessage["metadata"]> = {};
  if (coordinates) out.coordinates = coordinates;
  if (video_url) out.video_url = video_url;
  if (job_id) out.job_id = job_id;
  if (geometry_dsl) out.geometry_dsl = geometry_dsl;
  if (image_url) out.image_url = image_url;

  return Object.keys(out).length ? out : undefined;
}
