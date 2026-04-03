"use client";

import React, { useState } from "react";
import { Plus, MessageSquare, Trash2, Loader2, ChevronRight } from "lucide-react";
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

export default function SessionList() {
  const [creating, setCreating] = useState(false);
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
        await mutate(
          (prev) => [newSession, ...(prev ?? [])],
          { revalidate: false }
        );
        router.push(`/chat/${newSession.id}`);
      }
    } catch (err) {
      console.error("Create session error:", err);
    } finally {
      setCreating(false);
    }
  };

  const handleDeleteSession = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    if (!userSession?.access_token || !confirm("Bạn có chắc chắn muốn xóa session này?")) return;
    await mutate(
      (p) => (p ?? []).filter((s) => s.id !== id),
      { revalidate: false }
    );
    try {
      const res = await fetch(`${getApiBaseUrl()}/api/v1/sessions/${id}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${userSession.access_token}` },
      });
      if (!res.ok) throw new Error("delete failed");
      if (currentSessionId === id) router.push("/");
      await mutate();
    } catch (err) {
      console.error("Delete session error:", err);
      await mutate();
    }
  };

  const list = sessions ?? [];

  return (
    <div className="flex flex-col h-full">
      <div className="px-4 py-3">
        <button
          type="button"
          onClick={handleCreateSession}
          disabled={creating}
          className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl bg-white/5 border border-white/5 hover:bg-white/10 text-sm font-bold text-white transition-all group"
        >
          {creating ? (
            <Loader2 className="w-4 h-4 animate-spin text-indigo-400" />
          ) : (
            <Plus className="w-4 h-4 text-indigo-400 group-hover:scale-110 transition-transform" />
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
              onClick={() => router.push(`/chat/${s.id}`)}
              onKeyDown={(e) => e.key === "Enter" && router.push(`/chat/${s.id}`)}
              className={`group relative flex items-center gap-3 px-3 py-3 rounded-xl cursor-pointer transition-all ${
                currentSessionId === s.id
                  ? "bg-indigo-500/10 border border-indigo-500/20 shadow-lg"
                  : "hover:bg-white/5 border border-transparent"
              }`}
            >
              <div
                className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${
                  currentSessionId === s.id ? "bg-indigo-500/20 text-indigo-400" : "bg-white/5 text-zinc-600"
                }`}
              >
                <MessageSquare className="w-4 h-4" />
              </div>

              <div className="flex-1 min-w-0">
                <p
                  className={`text-sm font-medium truncate ${
                    currentSessionId === s.id ? "text-white" : "text-zinc-500 group-hover:text-zinc-300"
                  }`}
                >
                  {s.title}
                </p>
                <p className="text-[10px] text-zinc-700 font-bold uppercase mt-0.5">
                  {new Date(s.created_at).toLocaleDateString("vi-VN")}
                </p>
              </div>

              <button
                type="button"
                onClick={(e) => handleDeleteSession(e, s.id)}
                className="opacity-0 group-hover:opacity-100 p-1.5 hover:bg-red-500/10 hover:text-red-400 rounded-md text-zinc-700 transition-all"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>

              {currentSessionId === s.id && <ChevronRight className="w-3.5 h-3.5 text-indigo-500/50" />}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
