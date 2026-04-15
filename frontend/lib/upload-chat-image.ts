import { supabase } from "@/lib/supabase";

/**
 * Optional public URL for solve(image_url).
 * Bucket defaults to `image` per docs/API.md + migrations/add_image_bucket_storage.sql.
 * Path uses sessions/{sessionId}/ so storage RLS policies can apply.
 */
export async function uploadChatImageForSolve(
  sessionId: string,
  file: File
): Promise<string | null> {
  const bucket =
    process.env.NEXT_PUBLIC_SUPABASE_IMAGE_BUCKET?.trim() ||
    process.env.NEXT_PUBLIC_SUPABASE_CHAT_BUCKET?.trim() ||
    "image";
  if (!bucket) return null;

  const ext = file.type.includes("png")
    ? "png"
    : file.type.includes("webp")
      ? "webp"
      : "jpg";
  const path = `sessions/${sessionId}/${crypto.randomUUID()}.${ext}`;

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
