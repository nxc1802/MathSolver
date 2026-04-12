import React from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Loader2, Bot, Pencil, Trash2 } from "lucide-react";
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
  messagesEndRef
}: ChatMessageListProps) {
  return (
    <motion.div 
      initial="hidden"
      animate="visible"
      variants={{
        visible: {
          transition: {
            staggerChildren: 0.1
          }
        }
      }}
      className="flex-1 overflow-y-auto p-4 space-y-6 scrollbar-thin"
    >
      {historyLoading && messages.length === 0 && !isTempSession && (
        <div className="flex flex-col items-center justify-center py-16 gap-3 text-zinc-500 animate-in fade-in duration-700 delay-500">
          <Loader2 className="w-8 h-8 animate-spin text-indigo-500" />
          <p className="text-xs font-medium uppercase tracking-widest">Đang tải hội thoại...</p>
        </div>
      )}

      {messages.map((msg) => (
        <ChatMessageComponent key={msg.id} message={msg} />
      ))}

      <AnimatePresence>
        {currentStatus && currentStatus !== "success" && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="flex gap-4"
          >
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center animate-pulse flex-shrink-0">
              <Bot className="w-5 h-5 text-white" />
            </div>
            <div className="bg-zinc-900/60 border border-white/5 rounded-2xl px-5 py-4 flex items-center gap-3">
              <Loader2 className="w-4 h-4 animate-spin text-indigo-400" />
              <span className="text-sm text-zinc-400 italic font-medium">
                {currentStatus}
              </span>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {pendingQueue.map((q, idx) => (
          <motion.div
            key={q.id}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, scale: 0.95 }}
            className="flex gap-4"
          >
            <div className="w-9 h-9 rounded-xl bg-zinc-800 flex items-center justify-center flex-shrink-0">
              <div className="text-[10px] font-bold text-zinc-500">{idx + 1}</div>
            </div>
            <div className="flex-1 max-w-2xl bg-zinc-900/40 border border-white/5 rounded-2xl px-5 py-4 flex items-center justify-between group">
              <div className="flex flex-col gap-1">
                <span className="text-[10px] font-bold text-indigo-400 uppercase tracking-widest">Hàng đợi (Queued)</span>
                <p className="text-sm text-zinc-400 line-clamp-1 italic">{q.text}</p>
              </div>
              <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                <button
                  onClick={() => editQueued(q.id, q.text)}
                  className="p-1.5 hover:bg-white/5 rounded-lg text-zinc-500 hover:text-white transition-colors"
                  title="Sửa"
                >
                  <Pencil className="w-4 h-4" />
                </button>
                <button
                  onClick={() => removeQueued(q.id)}
                  className="p-1.5 hover:bg-red-500/10 rounded-lg text-zinc-500 hover:text-red-400 transition-colors"
                  title="Hủy"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          </motion.div>
        ))}
      </AnimatePresence>
      <div ref={messagesEndRef} />
    </motion.div>
  );
}
