"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { getApiBaseUrl } from "@/lib/api-config";
import { Compass, AlertCircle, RotateCcw, LogOut } from "lucide-react";

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
  const { user, session: userSession, loading, signOut } = useAuth();
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
          "Không thể kết nối tới máy chủ giải toán. Vui lòng kiểm tra lại kết nối mạng hoặc máy chủ."
        );
      }
    };

    void initApp();
    return () => {
      cancelled = true;
    };
  }, [user, loading, router, retryKey]);

  if (error) {
    return (
      <div className="h-screen w-screen flex flex-col items-center justify-center bg-[var(--background)] text-center px-4 select-none">
        <div className="bg-[var(--card-bg)] border border-red-500/30 p-8 rounded-3xl max-w-md shadow-2xl space-y-4">
          <div className="w-12 h-12 bg-red-500/10 border border-red-500/20 rounded-2xl flex items-center justify-center mx-auto text-red-400">
            <AlertCircle className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-base font-bold text-[var(--text-primary)]">Lỗi kết nối máy chủ</h2>
            <p className="text-[var(--text-muted)] text-xs mt-1.5 leading-relaxed">{error}</p>
          </div>
          <div className="flex flex-col gap-2 pt-2">
            <button
              type="button"
              onClick={retryInit}
              className="inline-flex items-center justify-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white font-semibold py-2.5 px-4 rounded-xl text-xs transition-all active:scale-95 shadow-md"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              Thử kết nối lại
            </button>
            <button
              type="button"
              onClick={() => signOut()}
              className="inline-flex items-center justify-center gap-2 text-[var(--text-muted)] hover:text-white text-xs font-medium py-2 rounded-xl transition-all"
            >
              <LogOut className="w-3.5 h-3.5" />
              Đăng xuất và quay lại
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen w-screen flex flex-col items-center justify-center bg-[var(--background)] select-none">
      <div className="flex flex-col items-center gap-4">
        <div className="w-12 h-12 rounded-2xl bg-indigo-500/10 border border-indigo-500/25 flex items-center justify-center shadow-lg shadow-indigo-500/10">
          <Compass className="w-6 h-6 text-indigo-400 animate-spin" />
        </div>
        <div className="text-center">
          <p className="text-xs font-mono font-medium text-[var(--text-secondary)] tracking-wider">
            MathSolver Studio v5.1
          </p>
          <p className="text-[10px] font-mono text-[var(--text-muted)] uppercase tracking-widest mt-1 animate-pulse">
            Đang khởi tạo không gian làm việc...
          </p>
        </div>
      </div>
    </div>
  );
}
