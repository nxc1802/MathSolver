"use client";

import React, { useState } from "react";
import { Plus, MessageSquare, Trash2, Loader2, ChevronRight, Check, X } from "lucide-react";
import { useRouter, useParams } from "next/navigation";
import useSWR from "swr";
import { useAuth } from "@/lib/auth-context";
import { getApiBaseUrl } from "@/lib/api-config";

interface Session {
  id: string;
  title: string;
  created_at: string;
}

async function fetchSessions([, token]: [string, string]): Promise<Session[]> {
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
  const { session: userSession } = useAuth();
  const router = useRouter();
  const params = useParams();
  const currentSessionId = params?.sessionId as string;

  const { data: sessions, mutate, isLoading } = useSWR(
    userSession?.access_token ? (["sessions", userSession.access_token] as const) : null,
    fetchSessions,
    { revalidateIfStale: true }
  );

  const handleCreateSession = async () => {
    if (!userSession?.access_token || creating) return;
    setCreating(true);
    try {
      const res = await fetch(`${getApiBaseUrl()}/api/v1/sessions`, {
        method: "POST",
        headers: { Authorization: `Bearer ${userSession.access_token}` },
      });
      if (res.ok) {
        const newSession = (await res.json()) as Session;
        await mutate((prev) => [newSession, ...(prev ?? [])], { revalidate: false });
        router.replace(`/chat/${newSession.id}`);
      }
    } catch (err) {
      console.error("Create session error:", err);
    } finally {
      setCreating(false);
    }
  };

  const handleDeleteSession = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    if (!userSession?.access_token) return;
    
    // Confirm state check
    if (deletingId !== id) {
      setDeletingId(id);
      return;
    }

    const listBefore = sessions ?? [];
    const wasCurrent = currentSessionId === id;
    const remaining = listBefore.filter((s) => s.id !== id);

    // Optimistic: remove from list instantly
    mutate(remaining, { revalidate: false });
    setDeletingId(null); // Clear confirm state immediately

    // If current, navigate away immediately to next or home
    if (wasCurrent) {
      const next = remaining[0];
      if (next) {
        router.replace(`/chat/${next.id}`);
      } else {
        router.replace("/");
      }
    }

    try {
      const res = await fetch(`${getApiBaseUrl()}/api/v1/sessions/${id}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${userSession.access_token}` },
      });
      
      if (!res.ok) throw new Error("delete failed");
      
      // If we deleted the last one and navigated to home, maybe create a new auto-session
      if (wasCurrent && remaining.length === 0) {
        const createRes = await fetch(`${getApiBaseUrl()}/api/v1/sessions`, {
          method: "POST",
          headers: { Authorization: `Bearer ${userSession.access_token}` },
        });
        if (createRes.ok) {
          const newSession = (await createRes.json()) as Session;
          await mutate([newSession], { revalidate: false });
          router.replace(`/chat/${newSession.id}`);
        }
      }
    } catch (err) {
      console.error("Delete session error:", err);
      // Rollback on error
      await mutate();
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
          className="w-9 h-9 shrink-0 rounded-xl bg-[var(--input-bg)] border border-[var(--border)] hover:bg-[var(--card-bg)] flex items-center justify-center text-indigo-500 transition-colors disabled:opacity-50"
        >
          {creating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
        </button>

        <div className="flex-1 w-full overflow-y-auto overflow-x-hidden flex flex-col items-center gap-1.5 px-1 scrollbar-thin">
          {isLoading ? (
            <Loader2 className="w-5 h-5 animate-spin text-zinc-600 my-2" />
          ) : list.length === 0 ? (
            <span title="Chưa có bài">
              <MessageSquare className="w-5 h-5 text-zinc-700 mt-2" aria-hidden />
            </span>
          ) : (
            list.map((s) => (
              <div key={s.id} className="relative group w-full flex justify-center">
                <button
                  type="button"
                  title={s.title}
                  onClick={() => router.replace(`/chat/${s.id}`)}
                  className={`w-9 h-9 rounded-xl flex items-center justify-center transition-all ${
                    currentSessionId === s.id
                      ? "bg-indigo-500/20 text-indigo-500 ring-1 ring-indigo-500/30"
                      : "bg-[var(--input-bg)] text-[var(--text-muted)] hover:bg-[var(--card-bg)] hover:text-[var(--text-primary)]"
                  }`}
                >
                  <MessageSquare className="w-4 h-4" />
                </button>
                <button
                  type="button"
                  title={deletingId === s.id ? "Xác nhận xoá" : "Xoá"}
                  onClick={(e) => handleDeleteSession(e, s.id)}
                  className={`absolute -right-0.5 -top-0.5 w-5 h-5 rounded-full border shadow-sm transition-all flex items-center justify-center z-10 ${
                    deletingId === s.id 
                      ? "bg-red-500 border-red-400 text-white scale-110 opacity-100" 
                      : "bg-[var(--card-bg)] border-[var(--border)] text-[var(--text-muted)] hover:text-red-400 opacity-0 group-hover:opacity-100"
                  }`}
                >
                  {deletingId === s.id ? <Check className="w-3 h-3" /> : <Trash2 className="w-2.5 h-2.5" />}
                </button>
                {deletingId === s.id && (
                  <button
                    type="button"
                    title="Hủy"
                    onClick={(e) => {
                      e.stopPropagation();
                      setDeletingId(null);
                    }}
                    className="absolute -left-0.5 -top-0.5 w-5 h-5 rounded-full bg-[var(--card-bg)] border border-[var(--border)] text-[var(--text-muted)] hover:text-[var(--text-primary)] shadow-sm z-10 flex items-center justify-center animate-in zoom-in-50 duration-200"
                  >
                    <X className="w-3 h-3" />
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
      <div className="px-4 py-3">
        <button
          type="button"
          onClick={handleCreateSession}
          disabled={creating}
          className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl bg-[var(--input-bg)] border border-[var(--border)] hover:bg-[var(--card-bg)] text-sm font-bold text-[var(--text-primary)] transition-all group"
        >
          {creating ? (
            <Loader2 className="w-4 h-4 animate-spin text-indigo-500" />
          ) : (
            <Plus className="w-4 h-4 text-indigo-500 group-hover:scale-110 transition-transform" />
          )}
          Tạo bài toán mới
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-2 py-2 space-y-1 scrollbar-none">
        {isLoading ? (
          <div className="flex flex-col items-center justify-center py-10 opacity-30">
            <Loader2 className="w-6 h-6 animate-spin mb-2" />
            <p className="text-[10px] uppercase font-bold tracking-widest">Đang tải...</p>
          </div>
        ) : list.length === 0 ? (
          <div className="py-10 text-center opacity-30">
            <MessageSquare className="w-8 h-8 mx-auto mb-2" />
            <p className="text-[10px] uppercase font-bold tracking-widest">Chưa có bài toán nào</p>
          </div>
        ) : (
          list.map((s) => (
            <div
              key={s.id}
              role="button"
              tabIndex={0}
              onClick={() => router.replace(`/chat/${s.id}`)}
              onKeyDown={(e) => e.key === "Enter" && router.replace(`/chat/${s.id}`)}
              className={`group relative flex items-center gap-3 px-3 py-3 rounded-xl cursor-pointer transition-all ${
                currentSessionId === s.id
                  ? "bg-indigo-500/5 border border-indigo-500/20 shadow-lg"
                  : "hover:bg-[var(--card-bg)] border border-transparent"
              }`}
            >
              <div
                className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${
                  currentSessionId === s.id ? "bg-indigo-500/20 text-indigo-400" : "bg-[var(--input-bg)] text-[var(--text-muted)]"
                }`}
              >
                <MessageSquare className="w-4 h-4" />
              </div>

              <div className="flex-1 min-w-0">
                <p
                  className={`text-sm font-medium truncate ${
                    currentSessionId === s.id ? "text-indigo-400 font-bold" : "text-[var(--text-secondary)] group-hover:text-[var(--text-primary)]"
                  }`}
                >
                  {s.title}
                </p>
                <p className="text-[10px] text-zinc-700 font-bold uppercase mt-0.5">
                  {new Date(s.created_at).toLocaleDateString("vi-VN")}
                </p>
              </div>

              <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-all">
                {deletingId === s.id ? (
                  <>
                    <button
                      type="button"
                      title="Xác nhận xoá"
                      onClick={(e) => handleDeleteSession(e, s.id)}
                      className="p-1.5 bg-red-500/10 text-red-500 hover:bg-red-500/20 rounded-md transition-all animate-in slide-in-from-right-2 duration-200"
                    >
                      <Check className="w-3.5 h-3.5" />
                    </button>
                    <button
                      type="button"
                      title="Hủy"
                      onClick={(e) => {
                        e.stopPropagation();
                        setDeletingId(null);
                      }}
                      className="p-1.5 hover:bg-[var(--border)] text-[var(--text-muted)] rounded-md transition-all animate-in slide-in-from-right-1 duration-200"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  </>
                ) : (
                  <button
                    type="button"
                    onClick={(e) => handleDeleteSession(e, s.id)}
                    className="p-1.5 hover:bg-red-500/10 hover:text-red-400 rounded-md text-[var(--text-muted)] transition-all"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>

              {currentSessionId === s.id && <ChevronRight className="w-3.5 h-3.5 text-indigo-500/50" />}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
