"use client";

import { motion, AnimatePresence } from "framer-motion";
import { Bot, User, Loader2, AlertCircle, Code2, BrainCircuit, Shapes } from "lucide-react";
import type { ChatMessage as ChatMessageType } from "@/types/chat";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import { ChevronDown, ChevronUp, CheckCircle2 } from "lucide-react";
import { useState } from "react";

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
  const [showSteps, setShowSteps] = useState(false);

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
            ? "bg-blue-500/15 border border-blue-500/20 text-blue-500"
            : isSystem
            ? "bg-[var(--card-bg)] border border-[var(--border)] text-[var(--text-muted)] text-xs italic"
            : "bg-[var(--msg-bot)] border border-[var(--border)] text-[var(--text-primary)] shadow-sm"
        }`}
      >
        {message.type === "status" && (
          <div className="flex items-center gap-2 text-sm">
            {message.content !== "success" && message.content !== "error" && (
              <Loader2 className="w-3.5 h-3.5 animate-spin text-indigo-400 flex-shrink-0" />
            )}
            <span className="text-[var(--text-secondary)]">
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
            <div className="prose prose-invert prose-sm max-w-none text-[var(--text-secondary)]">
              <ReactMarkdown remarkPlugins={[remarkGfm, remarkMath]} rehypePlugins={[rehypeKatex]}>
                {message.content}
              </ReactMarkdown>
            </div>
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
              Đã tính toạ độ hình học {message.metadata?.is_3d ? "3D" : "2D"} — xem bên phải →
            </span>
          </div>
        )}

        {message.type === "text" && (
          <div className="space-y-4">
            {message.role === "assistant" && message.metadata?.semantic_analysis && (
              <div className="space-y-2">
                <div className="flex items-center gap-2 mb-1.5 opacity-60">
                  <BrainCircuit className="w-3.5 h-3.5 text-indigo-400" />
                  <span className="text-[10px] font-bold uppercase tracking-wider text-indigo-400">
                    Phân tích từ AI
                  </span>
                </div>
                <div className="prose prose-invert prose-sm max-w-none italic text-[var(--text-secondary)]">
                  <ReactMarkdown remarkPlugins={[remarkGfm, remarkMath]} rehypePlugins={[rehypeKatex]}>
                    {message.metadata.semantic_analysis}
                  </ReactMarkdown>
                </div>
                <div className="h-px w-full bg-[var(--border)] my-2" />
              </div>
            )}

            {/* Main Content */}
            <div className="prose prose-invert prose-sm max-w-none text-[var(--text-primary)]">
              <ReactMarkdown remarkPlugins={[remarkGfm, remarkMath]} rehypePlugins={[rehypeKatex]}>
                {message.content}
              </ReactMarkdown>
            </div>

            {/* Solver Solution (v5.1) */}
            {message.metadata?.solution && (
              <div className="mt-4 p-4 rounded-xl bg-indigo-500/5 border border-indigo-500/10 space-y-3">
                <div className="flex items-center gap-2 text-indigo-400">
                  <CheckCircle2 className="w-4 h-4" />
                  <span className="text-xs font-bold uppercase tracking-widest">Kết quả giải toán</span>
                </div>
                
                <div className="text-sm font-medium text-indigo-100">
                  <ReactMarkdown remarkPlugins={[remarkGfm, remarkMath]} rehypePlugins={[rehypeKatex]}>
                    {message.metadata.solution.answer}
                  </ReactMarkdown>
                </div>

                {message.metadata.solution.steps && (
                  <div className="pt-2">
                    <button 
                      onClick={() => setShowSteps(!showSteps)}
                      className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider text-zinc-500 hover:text-indigo-400 transition-colors"
                    >
                      {showSteps ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                      {showSteps ? "Ẩn các bước giải" : "Xem các bước giải chi tiết"}
                    </button>
                    
                    <AnimatePresence>
                      {showSteps && (
                        <motion.div
                          initial={{ height: 0, opacity: 0 }}
                          animate={{ height: "auto", opacity: 1 }}
                          exit={{ height: 0, opacity: 0 }}
                          className="overflow-hidden"
                        >
                          <div className="pt-3 space-y-2 border-l border-zinc-800 ml-1.5 pl-4">
                            {message.metadata.solution.steps.map((step, idx) => (
                              <div key={idx} className="mb-4 p-4 bg-amber-500/10 border-2 border-amber-500/40 shadow-[6px_6px_0px_0px_rgba(245,158,11,0.3)] rounded-xl text-sm text-amber-50/90 leading-relaxed font-semibold">
                                <ReactMarkdown remarkPlugins={[remarkGfm, remarkMath]} rehypePlugins={[rehypeKatex]}>
                                  {step}
                                </ReactMarkdown>
                              </div>
                            ))}
                          </div>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>
                )}
              </div>
            )}
            
            {/* Render Image from Metadata */}
            {message.metadata?.image_url && (
              <div className="rounded-xl overflow-hidden border border-white/5 bg-black/20">
                <img 
                  src={message.metadata.image_url} 
                  alt="Math problem" 
                  className="max-w-full h-auto object-contain max-h-64 mx-auto"
                />
              </div>
            )}

            {/* Render Video from Metadata */}
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
