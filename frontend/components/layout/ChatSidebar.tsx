"use client";

import React from "react";
import { Calculator, ChevronLeft, ChevronRight, LogOut, User as UserIcon, Settings } from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import SessionList from "./SessionList";
import SettingsModal from "../settings/SettingsModal";
import { useState } from "react";
import { motion } from "framer-motion";

type ChatSidebarProps = {
  /** Narrow rail: icon-only session strip + mini header/footer */
  compact?: boolean;
  onCollapse?: () => void;
  onExpand?: () => void;
};

export default function ChatSidebar({ compact = false, onCollapse, onExpand }: ChatSidebarProps) {
  const { user, signOut } = useAuth();
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);

  if (compact) {
    return (
      <motion.div 
        layout
        className="flex flex-col h-full bg-[var(--card-bg)] border-r border-[var(--border)]"
      >
        <div className="flex-shrink-0 flex flex-col items-center gap-2 pt-2 pb-3 px-1 border-b border-[var(--border)]">
          <button
            type="button"
            aria-label="Mở rộng sidebar"
            title="Mở rộng"
            onClick={onExpand}
            className="shrink-0 p-1 rounded-md text-zinc-500 hover:text-indigo-300 hover:bg-white/5 transition-colors"
          >
            <ChevronRight className="w-3.5 h-3.5" />
          </button>
          <div
            className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shadow-md shadow-indigo-500/15"
            title="MathSolver"
          >
            <Calculator className="w-4 h-4 text-white" />
          </div>
        </div>

        <div className="flex-1 min-h-0 overflow-hidden px-0.5">
          <SessionList compact />
        </div>

        <div className="flex-shrink-0 flex flex-col items-center gap-2 py-3 px-1 border-t border-white/5 bg-black/20">
          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-zinc-700 to-zinc-800 flex items-center justify-center border border-white/10 overflow-hidden">
            {user?.user_metadata?.avatar_url ? (
              <img src={user.user_metadata.avatar_url} alt="" className="w-full h-full object-cover" />
            ) : (
              <UserIcon className="w-4 h-4 text-zinc-400" />
            )}
          </div>
          <button
            type="button"
            onClick={signOut}
            className="p-1.5 rounded-lg text-zinc-600 hover:text-red-400 hover:bg-red-500/10 transition-colors"
            title="Đăng xuất"
          >
            <LogOut className="w-3.5 h-3.5" />
          </button>
          <button 
            type="button" 
            className="p-1 text-zinc-600 hover:text-white transition-colors" 
            title="Cài đặt"
            onClick={() => setIsSettingsOpen(true)}
          >
            <Settings className="w-3.5 h-3.5" />
          </button>
        </div>

        <SettingsModal isOpen={isSettingsOpen} onClose={() => setIsSettingsOpen(false)} />
      </motion.div>
    );
  }

  return (
    <motion.div 
      layout
      className="flex flex-col h-full bg-[var(--card-bg)]"
    >
      <div className="flex-shrink-0 px-4 py-4 border-b border-[var(--border)]">
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-2.5 min-w-0">
            <div className="w-9 h-9 shrink-0 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shadow-lg shadow-indigo-500/20">
              <Calculator className="w-5 h-5 text-white" />
            </div>
            <div className="min-w-0">
              <h1 className="text-base font-bold text-white tracking-tight leading-none truncate">MathSolver</h1>
              <p className="text-[10px] text-zinc-500 font-bold uppercase tracking-[0.2em] mt-1">v5.1 Agentic AI</p>
            </div>
          </div>
          {onCollapse && (
            <button
              type="button"
              aria-label="Thu gọn sidebar"
              title="Thu gọn"
              onClick={onCollapse}
              className="shrink-0 p-1.5 rounded-lg text-zinc-500 hover:text-zinc-200 hover:bg-white/5 transition-colors"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      <div className="flex-1 overflow-hidden">
        <div className="px-5 pt-6 pb-2">
          <h2 className="text-[10px] font-bold text-zinc-600 uppercase tracking-widest">Lịch sử bài toán</h2>
        </div>
        <SessionList />
      </div>

      <div className="flex-shrink-0 p-4 border-t border-[var(--border)] bg-black/5">
        <div className="group relative flex items-center gap-3 p-2 rounded-xl hover:bg-white/5 transition-all">
          <div className="w-9 h-9 rounded-full bg-gradient-to-br from-zinc-700 to-zinc-800 flex items-center justify-center border border-[var(--border)]">
            {user?.user_metadata?.avatar_url ? (
              <img src={user.user_metadata.avatar_url} alt="" className="w-full h-full rounded-full" />
            ) : (
              <UserIcon className="w-5 h-5 text-zinc-400" />
            )}
          </div>

          <div className="flex-1 min-w-0">
            <p className="text-sm font-bold text-white truncate">
              {user?.user_metadata?.full_name || user?.email?.split("@")[0] || "Người dùng"}
            </p>
            <p className="text-[10px] text-[var(--text-muted)] truncate">{user?.email}</p>
          </div>

          <button
            type="button"
            onClick={signOut}
            className="p-2 hover:bg-red-500/10 hover:text-red-400 rounded-lg text-zinc-600 transition-all"
            title="Đăng xuất"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>

        <div className="mt-4 flex items-center justify-start px-2 py-2">
          <button 
            type="button" 
            className="text-zinc-600 hover:text-white transition-colors p-1" 
            title="Cài đặt"
            onClick={() => setIsSettingsOpen(true)}
          >
            <Settings className="w-4 h-4" />
          </button>
        </div>

        <SettingsModal isOpen={isSettingsOpen} onClose={() => setIsSettingsOpen(false)} />
      </div>
    </motion.div>
  );
}
