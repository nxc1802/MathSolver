"use client";

import React, { useState } from "react";
import {
  Compass,
  ChevronLeft,
  ChevronRight,
  LogOut,
  User as UserIcon,
  Settings,
} from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import SessionList from "./SessionList";
import SettingsModal from "../settings/SettingsModal";
import { motion } from "framer-motion";

type ChatSidebarProps = {
  /** Narrow rail: icon-only session strip + mini header/footer */
  compact?: boolean;
  onCollapse?: () => void;
  onExpand?: () => void;
};

export default function ChatSidebar({
  compact = false,
  onCollapse,
  onExpand,
}: ChatSidebarProps) {
  const { user, signOut } = useAuth();
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);

  if (compact) {
    return (
      <motion.aside
        layout
        aria-label="Thanh bên rút gọn"
        className="flex flex-col h-full bg-[var(--bg-secondary)] border-r border-[var(--border)] select-none"
      >
        <div className="flex-shrink-0 flex flex-col items-center gap-2.5 pt-3 pb-3 px-1.5 border-b border-[var(--border)]">
          <button
            type="button"
            aria-label="Mở rộng thanh bên"
            title="Mở rộng (Expand)"
            onClick={onExpand}
            className="shrink-0 p-1.5 rounded-lg text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-white/5 active:scale-95 transition-all"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
          <div
            className="w-8 h-8 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 flex items-center justify-center shadow-sm"
            title="MathSolver Studio"
          >
            <Compass className="w-4 h-4" />
          </div>
        </div>

        <div className="flex-1 min-h-0 overflow-hidden px-1 py-1">
          <SessionList compact />
        </div>

        <div className="flex-shrink-0 flex flex-col items-center gap-2.5 py-3 px-1.5 border-t border-[var(--border)] bg-black/20">
          <div
            className="w-8 h-8 rounded-full bg-white/5 border border-white/10 flex items-center justify-center overflow-hidden"
            title={user?.email || "Tài khoản"}
          >
            {user?.user_metadata?.avatar_url ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={user.user_metadata.avatar_url}
                alt=""
                className="w-full h-full object-cover"
              />
            ) : (
              <UserIcon className="w-4 h-4 text-zinc-400" />
            )}
          </div>
          <button
            type="button"
            className="p-1.5 rounded-lg text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-white/5 active:scale-95 transition-all"
            title="Cài đặt"
            onClick={() => setIsSettingsOpen(true)}
          >
            <Settings className="w-4 h-4" />
          </button>
          <button
            type="button"
            onClick={signOut}
            className="p-1.5 rounded-lg text-[var(--text-muted)] hover:text-red-400 hover:bg-red-500/10 active:scale-95 transition-all"
            title="Đăng xuất"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>

        <SettingsModal
          isOpen={isSettingsOpen}
          onClose={() => setIsSettingsOpen(false)}
        />
      </motion.aside>
    );
  }

  return (
    <motion.aside
      layout
      aria-label="Thanh bên chính"
      className="flex flex-col h-full bg-[var(--bg-secondary)] border-r border-[var(--border)] select-none"
    >
      {/* Header */}
      <div className="flex-shrink-0 px-4 py-3.5 border-b border-[var(--border)]">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2.5 min-w-0">
            <div className="w-8 h-8 shrink-0 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 flex items-center justify-center shadow-sm">
              <Compass className="w-4 h-4" />
            </div>
            <div className="min-w-0">
              <div className="flex items-center gap-1.5">
                <span className="text-sm font-semibold tracking-tight text-[var(--text-primary)] truncate">
                  MathSolver
                </span>
                <span className="text-[9px] font-mono px-1.5 py-0.5 rounded-md bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 font-medium">
                  v5.1
                </span>
              </div>
              <p className="text-[10px] text-[var(--text-muted)] tracking-wide truncate">
                Agentic Geometry AI
              </p>
            </div>
          </div>
          {onCollapse && (
            <button
              type="button"
              aria-label="Thu gọn sidebar"
              title="Thu gọn (Collapse)"
              onClick={onCollapse}
              className="shrink-0 p-1.5 rounded-lg text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-white/5 active:scale-95 transition-all"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* Session History */}
      <div className="flex-1 min-h-0 flex flex-col overflow-hidden">
        <div className="px-4 pt-3.5 pb-1 flex items-center justify-between">
          <span className="text-[10px] font-mono font-medium tracking-wider uppercase text-[var(--text-muted)]">
            Phiên giải toán
          </span>
        </div>
        <div className="flex-1 min-h-0 overflow-hidden">
          <SessionList />
        </div>
      </div>

      {/* User Footer */}
      <div className="flex-shrink-0 p-3 border-t border-[var(--border)] bg-black/10">
        <div className="flex items-center justify-between gap-2 p-1.5 rounded-xl bg-[var(--card-bg)] border border-[var(--border)]">
          <div className="flex items-center gap-2.5 min-w-0">
            <div className="w-8 h-8 rounded-full bg-white/5 border border-white/10 flex items-center justify-center overflow-hidden shrink-0">
              {user?.user_metadata?.avatar_url ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={user.user_metadata.avatar_url}
                  alt=""
                  className="w-full h-full object-cover"
                />
              ) : (
                <UserIcon className="w-4 h-4 text-zinc-400" />
              )}
            </div>
            <div className="min-w-0">
              <p className="text-xs font-medium text-[var(--text-primary)] truncate">
                {user?.user_metadata?.full_name ||
                  user?.email?.split("@")[0] ||
                  "Người dùng"}
              </p>
              <p className="text-[10px] text-[var(--text-muted)] font-mono truncate">
                {user?.email}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-0.5 shrink-0">
            <button
              type="button"
              className="p-1.5 text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-white/5 rounded-lg active:scale-95 transition-all"
              title="Cài đặt"
              onClick={() => setIsSettingsOpen(true)}
            >
              <Settings className="w-4 h-4" />
            </button>
            <button
              type="button"
              onClick={signOut}
              className="p-1.5 text-[var(--text-muted)] hover:text-red-400 hover:bg-red-500/10 rounded-lg active:scale-95 transition-all"
              title="Đăng xuất"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      <SettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
      />
    </motion.aside>
  );
}
