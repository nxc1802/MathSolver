"use client";

import React, { useRef, useState, useEffect } from "react";
import { motion } from "framer-motion";
import {
  Send,
  Image as ImageIcon,
  Sparkles,
  Loader2,
  Film,
  Calculator,
} from "lucide-react";
import type { ChatMessage } from "@/types/chat";
import ChatMessageComponent from "./ChatMessage";

interface ChatSidebarProps {
  messages: ChatMessage[];
  input: string;
  setInput: (val: string) => void;
  loading: boolean;
  onSolve: () => void;
  requestVideo: boolean;
  setRequestVideo: (val: boolean) => void;
}

export default function ChatSidebar({
  messages,
  input,
  setInput,
  loading,
  onSolve,
  requestVideo,
  setRequestVideo,
}: ChatSidebarProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [ocrLoading, setOcrLoading] = useState(false);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setOcrLoading(true);
    const formData = new FormData();
    formData.append("file", file);

    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    try {
      const res = await fetch(`${apiUrl}/api/v1/ocr`, {
        method: "POST",
        body: formData,
      });
      const data = await res.json();
      if (data.text) setInput(data.text);
    } catch (err) {
      console.error("OCR Error:", err);
    } finally {
      setOcrLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (input.trim() && !loading) onSolve();
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex-shrink-0 px-5 py-4 border-b border-white/5">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shadow-lg shadow-indigo-500/20">
            <Calculator className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-base font-bold text-white tracking-tight">
              MathSolver
            </h1>
            <p className="text-[10px] text-zinc-500 font-medium uppercase tracking-widest">
              Agentic AI v3.1
            </p>
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4 scrollbar-thin">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center gap-4 opacity-60">
            <Sparkles className="w-10 h-10 text-indigo-500/50" />
            <div>
              <p className="text-sm text-zinc-400 font-medium">
                Nhập đề bài hình học
              </p>
              <p className="text-xs text-zinc-600 mt-1">
                Ví dụ: &quot;Cho tam giác ABC đều cạnh 5&quot;
              </p>
            </div>
          </div>
        )}

        {messages.map((msg) => (
          <ChatMessageComponent key={msg.id} message={msg} />
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="flex-shrink-0 p-3 border-t border-white/5 bg-black/20">
        {/* Toolbar */}
        <div className="flex items-center gap-1.5 mb-2 px-1">
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileChange}
            className="hidden"
            accept="image/*"
          />
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={ocrLoading}
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-white/5 border border-white/5 text-zinc-500 hover:text-white hover:bg-white/10 transition-all text-xs font-medium disabled:opacity-50"
            title="Upload ảnh (OCR)"
          >
            {ocrLoading ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin text-indigo-400" />
            ) : (
              <ImageIcon className="w-3.5 h-3.5" />
            )}
            OCR
          </button>

          <button
            type="button"
            onClick={() => setRequestVideo(!requestVideo)}
            className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border transition-all text-xs font-medium ${
              requestVideo
                ? "bg-indigo-500/20 border-indigo-500/40 text-indigo-300"
                : "bg-white/5 border-white/5 text-zinc-500 hover:text-white hover:bg-white/10"
            }`}
            title="Bật/tắt video animation"
          >
            <Film className="w-3.5 h-3.5" />
            Video
          </button>

          <button
            type="button"
            onClick={() => setInput("Cho tam giác ABC đều cạnh bằng 5.")}
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-white/5 border border-white/5 text-zinc-500 hover:text-white hover:bg-white/10 transition-all text-xs font-medium"
            title="Dùng ví dụ"
          >
            <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
            Ví dụ
          </button>
        </div>

        {/* Text Input + Send */}
        <div className="flex items-end gap-2">
          <div className="flex-1 relative">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Nhập đề bài hình học..."
              rows={1}
              className="w-full bg-zinc-900/80 border border-white/8 rounded-xl px-4 py-3 pr-4 text-sm text-zinc-200 placeholder-zinc-600 focus:outline-none focus:border-indigo-500/40 transition-all resize-none leading-relaxed"
              style={{ minHeight: "44px", maxHeight: "120px" }}
            />
          </div>
          <motion.button
            whileTap={{ scale: 0.92 }}
            onClick={onSolve}
            disabled={loading || !input.trim()}
            className="flex-shrink-0 w-11 h-11 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 text-white flex items-center justify-center shadow-lg shadow-indigo-500/20 hover:shadow-indigo-500/40 disabled:opacity-40 disabled:shadow-none transition-all"
          >
            {loading ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <Send className="w-5 h-5" />
            )}
          </motion.button>
        </div>
      </div>
    </div>
  );
}
