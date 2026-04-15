"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { getApiBaseUrl } from "@/lib/api-config";
import { Loader2 } from "lucide-react";

const FETCH_TIMEOUT_MS = 8000;

async function fetchWithTimeout(
  url: string,
  init: RequestInit,
  ms: number
): Promise<Response> {
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), ms);
  try {
    return await fetch(url, { ...init, signal: controller.signal });
  } finally {
    clearTimeout(id);
  }
}

/**
 * Root page redirects to the most recent session or creates a new one.
 */
export default function IndexPage() {
  const { user, session: userSession, loading } = useAuth();
  const router = useRouter();

  const [error, setError] = useState<string | null>(null);
  const [retryKey, setRetryKey] = useState(0);
  const tokenRef = useRef<string | null>(null);

  useEffect(() => {
    tokenRef.current = userSession?.access_token ?? null;
  }, [userSession?.access_token]);

  const retryInit = useCallback(() => {
    setError(null);
    setRetryKey((k) => k + 1);
  }, []);

  useEffect(() => {
    if (loading) return;

    if (!user) {
      router.push("/login");
      return;
    }

    let cancelled = false;

    const initApp = async () => {
      try {
        setError(null);
        const apiUrl = getApiBaseUrl();
        const token = tokenRef.current;
        if (!token) {
          throw new Error("Missing auth token");
        }

        const res = await fetchWithTimeout(
          `${apiUrl}/api/v1/sessions`,
          { headers: { Authorization: `Bearer ${token}` } },
          FETCH_TIMEOUT_MS
        );

        if (cancelled) return;

        if (res.ok) {
          const sessions = await res.json();
          if (sessions.length > 0) {
            router.push(`/chat/${sessions[0].id}`);
          } else {
            const createRes = await fetchWithTimeout(
              `${apiUrl}/api/v1/sessions`,
              {
                method: "POST",
                headers: { Authorization: `Bearer ${token}` },
              },
              FETCH_TIMEOUT_MS
            );
            if (cancelled) return;
            if (createRes.ok) {
              const newSession = await createRes.json();
              router.push(`/chat/${newSession.id}`);
            } else {
              throw new Error(`Create session failed: ${createRes.status}`);
            }
          }
        } else {
          throw new Error(`Server returned ${res.status}`);
        }
      } catch (err: unknown) {
        if (cancelled) return;
        console.error("Failed to initialize session:", err);
        setError(
          "Không thể kết nối tới máy chủ giải toán. Vui lòng kiểm tra lại URL API (phải dùng https:// trên Vercel)."
        );
      }
    };

    void initApp();
    return () => {
      cancelled = true;
    };
  }, [user?.id, loading, router, retryKey]);

  const { signOut } = useAuth();

  if (error) {
    return (
      <div className="h-screen w-screen flex flex-col items-center justify-center bg-[#0a0a0f] text-center px-4">
        <div className="bg-red-500/10 border border-red-500/20 p-8 rounded-3xl max-w-md">
          <div className="w-12 h-12 bg-red-500/20 rounded-full flex items-center justify-center mx-auto mb-4">
            <Loader2 className="w-6 h-6 text-red-500" />
          </div>
          <h2 className="text-xl font-bold text-white mb-2">Lỗi kết nối</h2>
          <p className="text-zinc-400 text-sm mb-6 leading-relaxed">{error}</p>
          <div className="flex flex-col gap-3">
            <button
              type="button"
              onClick={retryInit}
              className="bg-indigo-600 hover:bg-indigo-500 text-white font-bold py-3 rounded-xl transition-all"
            >
              Thử lại
            </button>
            <button
              type="button"
              onClick={() => signOut()}
              className="text-zinc-500 hover:text-white text-sm font-medium transition-all"
            >
              Đăng xuất và quay lại
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen w-screen flex items-center justify-center bg-[#0a0a0f]">
      <div className="flex flex-col items-center gap-4">
        <Loader2 className="w-10 h-10 animate-spin text-indigo-500" />
        <p className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest animate-pulse">
          Đang khởi tạo không gian giải toán...
        </p>
      </div>
    </div>
  );
}
