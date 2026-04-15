import { supabase } from "@/lib/supabase";

/**
 * Upload a chat attachment to Supabase Storage for solve(image_url).
 * Returns public URL or null if upload is disabled / fails (caller falls back to text-only).
 */
export async function uploadChatImageForSolve(
  sessionId: string,
  file: File
): Promise<string | null> {
  const bucket =
    process.env.NEXT_PUBLIC_SUPABASE_CHAT_BUCKET?.trim() ||
    process.env.NEXT_PUBLIC_SUPABASE_BUCKET?.trim() ||
    "";
  if (!bucket) return null;

  const ext = file.type.includes("png")
    ? "png"
    : file.type.includes("webp")
      ? "webp"
      : "jpg";
  const path = `chat-input/${sessionId}/${crypto.randomUUID()}.${ext}`;

  const { error } = await supabase.storage.from(bucket).upload(path, file, {
    cacheControl: "3600",
    upsert: false,
    contentType: file.type || `image/${ext}`,
  });

  if (error) {
    console.warn("[uploadChatImageForSolve]", error.message);
    return null;
  }

  const { data } = supabase.storage.from(bucket).getPublicUrl(path);
  return data.publicUrl ?? null;
}
