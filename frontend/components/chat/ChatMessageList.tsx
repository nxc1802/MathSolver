import React from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Loader2, Compass, Pencil, Trash2, ListOrdered } from "lucide-react";
import ChatMessageComponent from "./ChatMessage";
import type { ChatMessage } from "@/types/chat";

interface ChatMessageListProps {
  messages: ChatMessage[];
  historyLoading: boolean;
  isTempSession: boolean;
  currentStatus: string | null;
  pendingQueue: { id: string; text: string }[];
  editQueued: (id: string, text: string) => void;
  removeQueued: (id: string) => void;
  messagesEndRef: React.RefObject<HTMLDivElement | null>;
}

export default function ChatMessageList({
  messages,
  historyLoading,
  isTempSession,
  currentStatus,
  pendingQueue,
  editQueued,
  removeQueued,
  messagesEndRef,
}: ChatMessageListProps) {
  return (
    <div className="flex-1 overflow-y-auto p-4 md:p-6 space-y-5 scrollbar-thin">
      {historyLoading && messages.length === 0 && !isTempSession && (
        <div className="flex flex-col items-center justify-center py-16 gap-3 text-[var(--text-muted)] animate-in fade-in duration-500">
          <Loader2 className="w-6 h-6 animate-spin text-indigo-400" />
          <p className="text-xs font-mono uppercase tracking-widest">Đang tải lịch sử hội thoại...</p>
        </div>
      )}

      {messages.map((msg) => (
        <ChatMessageComponent key={msg.id} message={msg} />
      ))}

      {/* Active Solving Status Shimmer Card */}
      <AnimatePresence>
        {currentStatus && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.2 }}
            className="flex gap-3 text-left"
          >
            <div className="w-7 h-7 rounded-lg bg-indigo-500/10 border border-indigo-500/25 flex items-center justify-center flex-shrink-0 mt-0.5 shadow-sm">
              <Compass className="w-3.5 h-3.5 text-indigo-400 animate-spin" />
            </div>
            <div className="bg-[var(--card-bg)] border border-indigo-500/20 rounded-2xl px-4 py-3 flex items-center gap-2.5 shadow-sm">
              <Loader2 className="w-3.5 h-3.5 animate-spin text-indigo-400" />
              <span className="text-xs text-[var(--text-secondary)] font-medium">
                {currentStatus}
              </span>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Pending Queue Cards */}
      <AnimatePresence>
        {pendingQueue.map((q, idx) => (
          <motion.div
            key={q.id}
            initial={{ opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, scale: 0.95 }}
            transition={{ duration: 0.2 }}
            className="flex gap-3 text-left"
          >
            <div className="w-7 h-7 rounded-lg bg-white/5 border border-white/10 flex items-center justify-center flex-shrink-0 mt-0.5">
              <span className="text-[10px] font-mono font-bold text-[var(--text-muted)]">
                Q{idx + 1}
              </span>
            </div>
            <div className="flex-1 max-w-2xl bg-[var(--card-bg)] border border-[var(--border)] rounded-2xl px-4 py-3 flex items-center justify-between group shadow-sm">
              <div className="flex flex-col gap-0.5 min-w-0 pr-3">
                <div className="flex items-center gap-1.5 text-[9px] font-mono font-semibold text-indigo-400 uppercase tracking-wider">
                  <ListOrdered className="w-3 h-3" />
                  <span>Đang xếp hàng ({idx + 1}/{pendingQueue.length})</span>
                </div>
                <p className="text-xs text-[var(--text-secondary)] line-clamp-1 italic">
                  {q.text}
                </p>
              </div>
              <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
                <button
                  type="button"
                  onClick={() => editQueued(q.id, q.text)}
                  className="p-1 hover:bg-white/5 rounded-md text-[var(--text-muted)] hover:text-white transition-colors"
                  title="Chỉnh sửa câu hỏi"
                >
                  <Pencil className="w-3.5 h-3.5" />
                </button>
                <button
                  type="button"
                  onClick={() => removeQueued(q.id)}
                  className="p-1 hover:bg-red-500/10 rounded-md text-[var(--text-muted)] hover:text-red-400 transition-colors"
                  title="Hủy câu hỏi"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          </motion.div>
        ))}
      </AnimatePresence>

      <div ref={messagesEndRef} />
    </div>
  );
}
