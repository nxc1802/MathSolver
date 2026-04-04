"use client";

import { motion } from "framer-motion";
import { Bot, User, Loader2, AlertCircle, Code2, BrainCircuit, Shapes } from "lucide-react";
import type { ChatMessage as ChatMessageType } from "@/types/chat";

interface ChatMessageProps {
  message: ChatMessageType;
}

const statusLabels: Record<string, string> = {
  processing: "🔄 Đang xử lý bài toán...",
  solving: "🧮 Đang giải hệ phương trình...",
  rendering_queued: "🎬 Đã gửi yêu cầu render video...",
  rendering: "🎬 Đang dựng animation Manim...",
  success: "✅ Hoàn thành!",
  error: "❌ Có lỗi xảy ra.",
};

export default function ChatMessageComponent({ message }: ChatMessageProps) {
  const isUser = message.role === "user";
  const isSystem = message.role === "system";

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
      className={`flex gap-3 ${isUser ? "flex-row-reverse" : "flex-row"}`}
    >
      {/* Avatar */}
      <div
        className={`w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0 ${
          isUser
            ? "bg-gradient-to-br from-blue-500 to-cyan-500 shadow-lg shadow-blue-500/20"
            : "bg-gradient-to-br from-indigo-500 to-purple-600 shadow-lg shadow-indigo-500/20"
        }`}
      >
        {isUser ? (
          <User className="w-4 h-4 text-white" />
        ) : (
          <Bot className="w-4 h-4 text-white" />
        )}
      </div>

      {/* Bubble */}
      <div
        className={`max-w-[85%] rounded-2xl px-4 py-3 ${
          isUser
            ? "bg-blue-500/15 border border-blue-500/20 text-blue-100"
            : isSystem
            ? "bg-zinc-800/50 border border-white/5 text-zinc-400 text-xs italic"
            : "bg-zinc-900/60 border border-white/8 text-zinc-200"
        }`}
      >
        {message.type === "status" && (
          <div className="flex items-center gap-2 text-sm">
            {message.content !== "success" && message.content !== "error" && (
              <Loader2 className="w-3.5 h-3.5 animate-spin text-indigo-400 flex-shrink-0" />
            )}
            <span className="text-zinc-300">
              {statusLabels[message.content] || message.content}
            </span>
          </div>
        )}

        {message.type === "error" && (
          <div className="flex items-start gap-2 text-sm text-red-300">
            <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5 text-red-400" />
            <span>{message.content}</span>
          </div>
        )}

        {message.type === "analysis" && (
          <div>
            <div className="flex items-center gap-2 mb-2">
              <BrainCircuit className="w-4 h-4 text-purple-400" />
              <span className="text-xs font-semibold text-purple-300 uppercase tracking-wider">
                Phân tích ngữ nghĩa
              </span>
            </div>
            <p className="text-sm text-zinc-300 leading-relaxed whitespace-pre-wrap">
              {message.content}
            </p>
          </div>
        )}

        {message.type === "dsl" && (
          <div>
            <div className="flex items-center gap-2 mb-2">
              <Code2 className="w-4 h-4 text-emerald-400" />
              <span className="text-xs font-semibold text-emerald-300 uppercase tracking-wider">
                Geometry DSL
              </span>
            </div>
            <pre className="text-xs font-mono text-emerald-200/80 bg-black/40 rounded-xl p-3 overflow-x-auto border border-white/5">
              {message.content}
            </pre>
          </div>
        )}

        {message.type === "coordinates" && (
          <div className="flex items-center gap-2 text-sm">
            <Shapes className="w-4 h-4 text-amber-400" />
            <span className="text-zinc-300">
              Đã tính toạ độ hình học — xem bên phải →
            </span>
          </div>
        )}

        {message.type === "text" && (
          <div className="space-y-3">
            {message.role === "assistant" && message.metadata?.semantic_analysis ? (
              <div className="space-y-2">
                <div className="flex items-center gap-2 mb-1.5 opacity-60">
                  <BrainCircuit className="w-3.5 h-3.5 text-indigo-400" />
                  <span className="text-[10px] font-bold uppercase tracking-wider text-indigo-300">
                    Phân tích từ AI
                  </span>
                </div>
                <p className="text-sm leading-relaxed whitespace-pre-wrap text-indigo-50/90 italic">
                  {message.metadata.semantic_analysis}
                </p>
                <div className="h-px w-full bg-white/5 my-2" />
                <p className="text-sm leading-relaxed whitespace-pre-wrap">
                  {message.content}
                </p>
              </div>
            ) : (
              <p className="text-sm leading-relaxed whitespace-pre-wrap">
                {message.content}
              </p>
            )}
            
            {/* Render Image from Metadata (User upload or AI result) */}
            {message.metadata?.image_url && (
              <div className="rounded-xl overflow-hidden border border-white/5 bg-black/20">
                <img 
                  src={message.metadata.image_url} 
                  alt="Math problem" 
                  className="max-w-full h-auto object-contain max-h-64 mx-auto"
                />
              </div>
            )}

            {/* Render Video from Metadata (AI Animation Result); API uses video_url */}
            {(message.metadata?.video_url ?? message.metadata?.videoUrl) && (
              <div className="rounded-xl overflow-hidden border border-white/5 bg-black/20">
                <video 
                  src={message.metadata?.video_url ?? message.metadata?.videoUrl} 
                  controls 
                  className="w-full h-auto aspect-video"
                />
              </div>
            )}
          </div>
        )}

        {/* Timestamp */}
        <div className={`text-[10px] mt-1.5 ${isUser ? "text-blue-400/40 text-right" : "text-zinc-600"}`}>
          {new Date(message.timestamp).toLocaleTimeString("vi-VN", {
            hour: "2-digit",
            minute: "2-digit",
          })}
        </div>
      </div>
    </motion.div>
  );
}
