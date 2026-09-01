"use client";

import { motion, AnimatePresence } from "framer-motion";
import {
  Compass,
  User,
  Loader2,
  AlertCircle,
  Code2,
  BrainCircuit,
  Shapes,
  ChevronDown,
  ChevronUp,
  CheckCircle2,
} from "lucide-react";
import type { ChatMessage as ChatMessageType } from "@/types/chat";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import { useState } from "react";

import { formatMathMarkdown } from "@/lib/math-format";

interface ChatMessageProps {
  message: ChatMessageType;
}

const STATUS_LABELS: Record<string, string> = {
  processing: "Đang phân tích cấu trúc đề bài...",
  solving: "Đang giải hệ phương trình hình học & tọa độ...",
  rendering_queued: "Đã đưa vào hàng chờ render video...",
  rendering: "Đang khởi tạo animation Manim 60fps...",
  success: "Hoàn tất giải toán",
  error: "Xảy ra lỗi trong quá trình xử lý",
};

export default function ChatMessageComponent({ message }: ChatMessageProps) {
  const isUser = message.role === "user";
  const isSystem = message.role === "system";
  const [showSteps, setShowSteps] = useState(true);

  const solution = message.metadata?.solution;
  const imageUrl = message.metadata?.image_url;
  const videoUrl = message.metadata?.video_url ?? message.metadata?.videoUrl;

  const renderSolutionBlock = () => {
    if (!solution) return null;
    return (
      <div className="mt-4 p-4 rounded-2xl bg-indigo-500/[0.04] border border-indigo-500/20 space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-indigo-400">
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            <span className="text-xs font-semibold tracking-wide text-indigo-300">
              Kết quả giải toán
            </span>
          </div>
          {solution.steps && solution.steps.length > 0 && (
            <button
              type="button"
              onClick={() => setShowSteps(!showSteps)}
              className="inline-flex items-center gap-1 text-[11px] font-mono text-[var(--text-muted)] hover:text-indigo-300 transition-colors"
            >
              <span>{showSteps ? "Thu gọn bước" : "Xem các bước"}</span>
              {showSteps ? (
                <ChevronUp className="w-3 h-3" />
              ) : (
                <ChevronDown className="w-3 h-3" />
              )}
            </button>
          )}
        </div>

        {/* Final Answer */}
        <div className="p-3 rounded-xl bg-black/20 border border-indigo-500/10 text-sm font-medium text-[var(--text-primary)]">
          <ReactMarkdown
            remarkPlugins={[remarkGfm, remarkMath]}
            rehypePlugins={[rehypeKatex]}
          >
            {formatMathMarkdown(solution.answer || "")}
          </ReactMarkdown>
        </div>

        {/* Detailed Steps Accordion */}
        {solution.steps && solution.steps.length > 0 && (
          <AnimatePresence>
            {showSteps && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: "auto", opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                className="overflow-hidden space-y-2 pt-1"
              >
                {solution.steps.map((step, idx) => {
                  const cleanedStep = step.replace(/^(?:Bước\s*\d+|Step\s*\d+)[:.]\s*/i, "");
                  return (
                    <div
                      key={idx}
                      className="p-3 rounded-xl bg-[var(--card-bg)] border border-[var(--border)] text-xs text-[var(--text-secondary)] leading-relaxed space-y-1.5"
                    >
                      <div className="flex items-center gap-2">
                        <span className="text-[9px] font-mono font-semibold px-1.5 py-0.5 rounded bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
                          BƯỚC {idx + 1}
                        </span>
                      </div>
                      <div className="pt-0.5 text-[var(--text-primary)]">
                        <ReactMarkdown
                          remarkPlugins={[remarkGfm, remarkMath]}
                          rehypePlugins={[rehypeKatex]}
                        >
                          {formatMathMarkdown(cleanedStep)}
                        </ReactMarkdown>
                      </div>
                    </div>
                  );
                })}
              </motion.div>
            )}
          </AnimatePresence>
        )}
      </div>
    );
  };

  const renderAttachments = () => (
    <>
      {/* Attached Image Thumbnail */}
      {imageUrl && (
        <div className="rounded-xl overflow-hidden border border-[var(--border)] bg-black/30 p-1 mt-3">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={imageUrl}
            alt="Đề bài đính kèm"
            className="max-w-full h-auto object-contain max-h-64 rounded-lg mx-auto"
          />
        </div>
      )}

      {/* Attached Video Output */}
      {videoUrl && (
        <div className="rounded-xl overflow-hidden border border-[var(--border)] bg-black/40 mt-3">
          <video
            src={videoUrl}
            controls
            className="w-full h-auto aspect-video rounded-lg"
          />
        </div>
      )}
    </>
  );

  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
      className={`flex gap-3 text-left ${isUser ? "flex-row-reverse" : "flex-row"}`}
    >
      {/* Avatar Icon */}
      <div
        className={`w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5 border shadow-sm transition-all ${
          isUser
            ? "bg-indigo-600/10 border-indigo-500/30 text-indigo-400"
            : "bg-white/5 border-white/10 text-zinc-300"
        }`}
      >
        {isUser ? (
          <User className="w-3.5 h-3.5" />
        ) : (
          <Compass className="w-3.5 h-3.5 text-indigo-400" />
        )}
      </div>

      {/* Bubble Content */}
      <div
        className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed transition-all ${
          isUser
            ? "bg-indigo-600/10 border border-indigo-500/25 text-[var(--text-primary)]"
            : isSystem
            ? "bg-[var(--card-bg)] border border-[var(--border)] text-[var(--text-muted)] text-xs italic"
            : "bg-[var(--msg-bot)] border border-[var(--border)] text-[var(--text-primary)] shadow-sm"
        }`}
      >
        {/* Status Indicator */}
        {message.type === "status" && (
          <div className="flex items-center gap-2 text-xs font-mono">
            {message.content !== "success" && message.content !== "error" && (
              <Loader2 className="w-3.5 h-3.5 animate-spin text-indigo-400 flex-shrink-0" />
            )}
            <span className="text-[var(--text-secondary)]">
              {STATUS_LABELS[message.content] || message.content}
            </span>
          </div>
        )}

        {/* Error Indicator */}
        {message.type === "error" && (
          <div className="flex items-start gap-2.5 text-xs text-red-300 bg-red-500/10 border border-red-500/20 p-3 rounded-xl">
            <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5 text-red-400" />
            <span>{message.content}</span>
          </div>
        )}

        {/* Semantic Analysis Block */}
        {message.type === "analysis" && (
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <BrainCircuit className="w-3.5 h-3.5 text-indigo-400" />
              <span className="text-[10px] font-mono font-semibold text-indigo-300 uppercase tracking-wider">
                Phân tích ngữ nghĩa đề bài
              </span>
            </div>
            <div className="prose prose-invert prose-sm max-w-none text-[var(--text-secondary)] leading-relaxed">
              <ReactMarkdown
                remarkPlugins={[remarkGfm, remarkMath]}
                rehypePlugins={[rehypeKatex]}
              >
                {formatMathMarkdown(message.content)}
              </ReactMarkdown>
            </div>
            {renderSolutionBlock()}
            {renderAttachments()}
          </div>
        )}

        {/* Geometry DSL Block */}
        {message.type === "dsl" && (
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Code2 className="w-3.5 h-3.5 text-emerald-400" />
                <span className="text-[10px] font-mono font-semibold text-emerald-300 uppercase tracking-wider">
                  Geometry DSL Representation
                </span>
              </div>
            </div>
            <pre className="text-xs font-mono text-emerald-300/90 bg-black/40 rounded-xl p-3 overflow-x-auto border border-emerald-500/20">
              <code>{message.content}</code>
            </pre>
            {renderSolutionBlock()}
            {renderAttachments()}
          </div>
        )}

        {/* Coordinates ready banner */}
        {message.type === "coordinates" && (
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-xs text-[var(--text-secondary)]">
              <Shapes className="w-3.5 h-3.5 text-indigo-400" />
              <span>
                Đã dựng toạ độ không gian {message.metadata?.is_3d ? "3D" : "2D"} (Xem chi tiết trên bảng mô phỏng bên phải)
              </span>
            </div>
            {renderSolutionBlock()}
            {renderAttachments()}
          </div>
        )}

        {/* Main Text Content */}
        {message.type === "text" && (
          <div className="space-y-3.5">
            {/* Inline Semantic Analysis preview */}
            {message.role === "assistant" && message.metadata?.semantic_analysis && (
              <div className="space-y-1.5 pb-2 border-b border-[var(--border-subtle)]">
                <div className="flex items-center gap-1.5 opacity-70">
                  <BrainCircuit className="w-3 h-3 text-indigo-400" />
                  <span className="text-[10px] font-mono font-medium uppercase tracking-wider text-indigo-400">
                    Phân tích đề
                  </span>
                </div>
                <div className="prose prose-invert prose-sm max-w-none text-xs text-[var(--text-muted)] italic leading-normal">
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm, remarkMath]}
                    rehypePlugins={[rehypeKatex]}
                  >
                    {formatMathMarkdown(message.metadata.semantic_analysis)}
                  </ReactMarkdown>
                </div>
              </div>
            )}

            {/* Markdown Message Text */}
            <div className="prose prose-invert prose-sm max-w-none text-[var(--text-primary)] leading-relaxed">
              <ReactMarkdown
                remarkPlugins={[remarkGfm, remarkMath]}
                rehypePlugins={[rehypeKatex]}
              >
                {formatMathMarkdown(message.content)}
              </ReactMarkdown>
            </div>

            {renderSolutionBlock()}
            {renderAttachments()}
          </div>
        )}

        {/* Timestamp */}
        <div
          className={`text-[9px] font-mono mt-1.5 tabular-nums ${
            isUser ? "text-indigo-300/50 text-right" : "text-[var(--text-muted)]"
          }`}
        >
          {new Date(message.timestamp).toLocaleTimeString("vi-VN", {
            hour: "2-digit",
            minute: "2-digit",
          })}
        </div>
      </div>
    </motion.div>
  );
}
