"use client";

import React, { useState } from "react";
import { Plus, MessageSquare, Trash2, Loader2, ChevronRight, Check, X } from "lucide-react";
import { useRouter, useParams } from "next/navigation";
import useSWR, { useSWRConfig } from "swr";
import { useAuth } from "@/lib/auth-context";
import { getApiBaseUrl } from "@/lib/api-config";
import { supabase } from "@/lib/supabase";

const FETCH_TIMEOUT_MS = 8000;

async function getAccessToken(): Promise<string | null> {
  const {
    data: { session },
  } = await supabase.auth.getSession();
  return session?.access_token ?? null;
}

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

interface Session {
  id: string;
  title: string;
  created_at: string;
}

async function fetchSessions(): Promise<Session[]> {
  const token = await getAccessToken();
  if (!token) throw new Error("Failed to load sessions");
  const res = await fetch(`${getApiBaseUrl()}/api/v1/sessions`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error("Failed to load sessions");
  return res.json();
}

type SessionListProps = {
  /** Icon-only narrow rail (collapsed sidebar) */
  compact?: boolean;
};

export default function SessionList({ compact = false }: SessionListProps) {
  const [creating, setCreating] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const { user } = useAuth();
  const { mutate: globalMutate } = useSWRConfig();
  const router = useRouter();
  const params = useParams();
  const currentSessionId = params?.sessionId as string;

  const { data: sessions, mutate, isLoading } = useSWR(
    user?.id ? (["sessions", user.id] as const) : null,
    fetchSessions,
    { revalidateOnFocus: false, dedupingInterval: 2000 }
  );

  const showErrorToast = (msg: string) => {
    setErrorMessage(msg);
    setTimeout(() => setErrorMessage(null), 4000);
  };

  const handleCreateSession = async () => {
    if (creating) return;
    const token = await getAccessToken();
    if (!token) return;

    setCreating(true);

    // 1. Instant optimistic creation & navigation (P0.2)
    const tempId = `temp-${crypto.randomUUID()}`;
    const tempSession: Session = {
      id: tempId,
      title: "Bài toán mới",
      created_at: new Date().toISOString(),
    };

    // Optimistically update SWR cache
    await mutate((prev) => [tempSession, ...(prev ?? [])], { revalidate: false });
    // Navigate immediately - 0 latency feel
    router.replace(`/chat/${tempId}`);

    // 2. Perform server creation in background
    try {
      const res = await fetchWithTimeout(
        `${getApiBaseUrl()}/api/v1/sessions`,
        {
          method: "POST",
          headers: { Authorization: `Bearer ${token}` },
        },
        FETCH_TIMEOUT_MS
      );

      if (res.ok) {
        const realSession = (await res.json()) as Session;

        const messagesUrl = `${getApiBaseUrl()}/api/v1/sessions/${realSession.id}/messages`;
        const assetsUrl = `${getApiBaseUrl()}/api/v1/sessions/${realSession.id}/assets`;

        await globalMutate([messagesUrl, token], [], { revalidate: false });
        await globalMutate([assetsUrl, token], [], { revalidate: false });

        // Replace temp session with real session in SWR cache
        await mutate((prev) => {
          const list = prev ?? [];
          return list.map((s) => (s.id === tempId ? realSession : s));
        }, { revalidate: false });

        // Update URL to real ID
        router.replace(`/chat/${realSession.id}`);
      } else {
        throw new Error("Không thể tạo phiên trên server");
      }
    } catch (err) {
      console.error("Create session error:", err);
      // Rollback on failure
      await mutate((prev) => (prev ?? []).filter((s) => s.id !== tempId), { revalidate: false });
      showErrorToast("Không thể tạo bài toán mới. Vui lòng thử lại.");
      router.replace("/");
    } finally {
      setCreating(false);
    }
  };

  const handleDeleteSession = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    const token = await getAccessToken();
    if (!token) return;
    
    // Confirm state check
    if (deletingId !== id) {
      setDeletingId(id);
      return;
    }

    const listBefore = sessions ?? [];
    const wasCurrent = currentSessionId === id;
    const remaining = listBefore.filter((s) => s.id !== id);

    // 1. Instant optimistic removal from UI (P0.3)
    mutate(remaining, { revalidate: false });
    setDeletingId(null);

    // 2. Instant optimistic navigation if deleting active session
    if (wasCurrent) {
      const next = remaining[0];
      if (next) {
        router.replace(`/chat/${next.id}`);
      } else {
        router.replace("/");
      }
    }

    // 3. Perform server deletion in background with proper rollback
    try {
      const res = await fetch(`${getApiBaseUrl()}/api/v1/sessions/${id}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });
      
      if (!res.ok) throw new Error("Server deletion failed");
    } catch (err) {
      console.error("Delete session error:", err);
      // Rollback UI to prior state
      await mutate(listBefore, { revalidate: false });
      if (wasCurrent) {
        router.replace(`/chat/${id}`);
      }
      showErrorToast("Không thể xoá bài toán. Dữ liệu đã được khôi phục.");
    }
  };

  const list = sessions ?? [];

  if (compact) {
    return (
      <div className="flex flex-col h-full items-center py-2 gap-2 overflow-hidden">
        <button
          type="button"
          onClick={handleCreateSession}
          disabled={creating}
          title="Tạo bài toán mới"
          className="w-8 h-8 shrink-0 rounded-xl bg-indigo-500/10 border border-indigo-500/25 hover:bg-indigo-500/20 text-indigo-400 flex items-center justify-center transition-all active:scale-95 disabled:opacity-50"
        >
          {creating ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Plus className="w-3.5 h-3.5" />}
        </button>

        <div className="flex-1 w-full overflow-y-auto overflow-x-hidden flex flex-col items-center gap-1.5 px-0.5 scrollbar-none">
          {isLoading ? (
            <div className="py-4">
              <Loader2 className="w-4 h-4 animate-spin text-zinc-600" />
            </div>
          ) : list.length === 0 ? (
            <span title="Chưa có bài" className="opacity-30 pt-3">
              <MessageSquare className="w-4 h-4 text-zinc-500" aria-hidden />
            </span>
          ) : (
            list.map((s) => (
              <div key={s.id} className="relative group w-full flex justify-center">
                <button
                  type="button"
                  title={s.title}
                  onClick={() => router.replace(`/chat/${s.id}`)}
                  className={`w-8 h-8 rounded-xl flex items-center justify-center transition-all active:scale-95 ${
                    currentSessionId === s.id
                      ? "bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 shadow-sm"
                      : "bg-white/[0.02] text-[var(--text-muted)] hover:bg-white/5 hover:text-[var(--text-primary)] border border-transparent"
                  }`}
                >
                  <MessageSquare className="w-3.5 h-3.5" />
                </button>
                <button
                  type="button"
                  title={deletingId === s.id ? "Xác nhận xoá" : "Xoá"}
                  onClick={(e) => handleDeleteSession(e, s.id)}
                  className={`absolute -right-1 -top-1 w-4 h-4 rounded-full border shadow-sm transition-all flex items-center justify-center z-10 ${
                    deletingId === s.id 
                      ? "bg-red-500 border-red-400 text-white scale-110 opacity-100" 
                      : "bg-[var(--card-bg)] border-[var(--border)] text-[var(--text-muted)] hover:text-red-400 opacity-0 group-hover:opacity-100"
                  }`}
                >
                  {deletingId === s.id ? <Check className="w-2.5 h-2.5" /> : <Trash2 className="w-2 h-2" />}
                </button>
                {deletingId === s.id && (
                  <button
                    type="button"
                    title="Hủy"
                    onClick={(e) => {
                      e.stopPropagation();
                      setDeletingId(null);
                    }}
                    className="absolute -left-1 -top-1 w-4 h-4 rounded-full bg-[var(--card-bg)] border border-[var(--border)] text-[var(--text-muted)] hover:text-[var(--text-primary)] shadow-sm z-10 flex items-center justify-center animate-in zoom-in-50 duration-200"
                  >
                    <X className="w-2.5 h-2.5" />
                  </button>
                )}
              </div>
            ))
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      <div className="px-3 py-2">
        <button
          type="button"
          onClick={handleCreateSession}
          disabled={creating}
          className="w-full flex items-center justify-center gap-2 py-2.5 px-3 rounded-xl bg-indigo-500/10 border border-indigo-500/25 hover:bg-indigo-500/20 hover:border-indigo-500/40 text-xs font-semibold text-indigo-300 transition-all group active:scale-[0.98] shadow-sm"
        >
          {creating ? (
            <Loader2 className="w-3.5 h-3.5 animate-spin text-indigo-400" />
          ) : (
            <Plus className="w-3.5 h-3.5 text-indigo-400 group-hover:scale-110 transition-transform" />
          )}
          Tạo bài toán mới
        </button>
      </div>

      {errorMessage && (
        <div className="mx-3 mb-2 p-2 text-[10px] text-red-300 bg-red-500/10 border border-red-500/20 rounded-lg animate-in fade-in">
          {errorMessage}
        </div>
      )}

      <div className="flex-1 overflow-y-auto px-2 py-1 space-y-1 scrollbar-thin">
        {isLoading ? (
          <div className="flex flex-col items-center justify-center py-10 opacity-40 gap-2">
            <Loader2 className="w-4 h-4 animate-spin text-indigo-400" />
            <p className="text-[10px] font-mono tracking-wider text-zinc-500">Đang tải...</p>
          </div>
        ) : list.length === 0 ? (
          <div className="py-12 px-4 text-center opacity-40">
            <MessageSquare className="w-6 h-6 mx-auto mb-2 text-zinc-600" />
            <p className="text-[11px] text-zinc-500">Chưa có bài toán nào</p>
          </div>
        ) : (
          list.map((s) => {
            const isSelected = currentSessionId === s.id;
            return (
              <div
                key={s.id}
                role="button"
                tabIndex={0}
                onClick={() => router.replace(`/chat/${s.id}`)}
                onKeyDown={(e) => e.key === "Enter" && router.replace(`/chat/${s.id}`)}
                className={`group relative flex items-center gap-2.5 px-3 py-2.5 rounded-xl cursor-pointer transition-all text-left ${
                  isSelected
                    ? "bg-indigo-500/10 border border-indigo-500/25 text-indigo-200"
                    : "hover:bg-white/[0.04] border border-transparent text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
                }`}
              >
                {/* Active Indicator Bar */}
                {isSelected && (
                  <div className="absolute left-0 top-2 bottom-2 w-1 bg-indigo-500 rounded-r-full" />
                )}

                <div
                  className={`w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 transition-colors ${
                    isSelected
                      ? "bg-indigo-500/20 text-indigo-300"
                      : "bg-white/[0.03] text-zinc-500 group-hover:text-zinc-300"
                  }`}
                >
                  <MessageSquare className="w-3.5 h-3.5" />
                </div>

                <div className="flex-1 min-w-0">
                  <p
                    className={`text-xs font-medium truncate ${
                      isSelected ? "text-indigo-100 font-semibold" : "text-[var(--text-primary)] opacity-90"
                    }`}
                  >
                    {s.title}
                  </p>
                  <p className="text-[9px] font-mono text-[var(--text-muted)] tracking-wider mt-0.5 tabular-nums">
                    {new Date(s.created_at).toLocaleDateString("vi-VN", {
                      day: "2-digit",
                      month: "2-digit",
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </p>
                </div>

                <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                  {deletingId === s.id ? (
                    <>
                      <button
                        type="button"
                        title="Xác nhận xoá"
                        onClick={(e) => handleDeleteSession(e, s.id)}
                        className="p-1 bg-red-500/20 text-red-400 hover:bg-red-500/30 rounded-md transition-all active:scale-95"
                      >
                        <Check className="w-3 h-3" />
                      </button>
                      <button
                        type="button"
                        title="Hủy"
                        onClick={(e) => {
                          e.stopPropagation();
                          setDeletingId(null);
                        }}
                        className="p-1 hover:bg-white/10 text-zinc-400 rounded-md transition-all active:scale-95"
                      >
                        <X className="w-3 h-3" />
                      </button>
                    </>
                  ) : (
                    <button
                      type="button"
                      onClick={(e) => handleDeleteSession(e, s.id)}
                      className="p-1 hover:bg-red-500/10 hover:text-red-400 rounded-md text-[var(--text-muted)] transition-all active:scale-95"
                    >
                      <Trash2 className="w-3 h-3" />
                    </button>
                  )}
                </div>

                {isSelected && !deletingId && (
                  <ChevronRight className="w-3.5 h-3.5 text-indigo-400/50 shrink-0" />
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
