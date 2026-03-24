"use client";

import { motion } from "framer-motion";
import { Upload, Sparkles, Image as ImageIcon } from "lucide-react";

interface SolverFormProps {
  input: string;
  setInput: (val: string) => void;
  loading: boolean;
  onSolve: () => void;
  onExample: () => void;
}

export default function SolverForm({ input, setInput, loading, onSolve, onExample }: SolverFormProps) {
  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="w-full max-w-2xl mx-auto bg-zinc-900/50 backdrop-blur-xl border border-white/10 rounded-3xl p-8 shadow-2xl"
    >
      <div className="mb-6">
        <label className="text-xs font-semibold text-zinc-500 uppercase tracking-widest mb-3 block">
          Nhập đề bài hình học
        </label>
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ví dụ: Triangle ABC with AB=5, AC=7, angle A=60..."
          className="w-full h-32 bg-black/40 border border-white/5 rounded-2xl p-4 text-zinc-200 placeholder-zinc-600 focus:outline-none focus:border-indigo-500/50 transition-all resize-none text-lg leading-relaxed"
        />
      </div>

      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex gap-2">
          <button 
            type="button"
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-white/5 border border-white/5 text-zinc-400 hover:text-white hover:bg-white/10 transition-all text-sm font-medium group"
          >
            <ImageIcon className="w-4 h-4 group-hover:scale-110 transition-transform" />
            Upload OCR
          </button>
          <button 
            type="button"
            onClick={onExample}
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-white/5 border border-white/5 text-zinc-400 hover:text-white hover:bg-white/10 transition-all text-sm font-medium"
          >
            <Sparkles className="w-4 h-4 text-indigo-400" />
            Dùng ví dụ
          </button>
        </div>

        <button
          onClick={onSolve}
          disabled={loading || !input.trim()}
          className="relative flex items-center gap-2 px-8 py-3 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 text-white font-semibold shadow-lg shadow-indigo-500/20 hover:shadow-indigo-500/40 disabled:opacity-50 disabled:shadow-none transition-all active:scale-95 overflow-hidden group"
        >
          <div className="absolute inset-0 bg-white/10 translate-x-[-100%] group-hover:translate-x-[100%] transition-transform duration-500 skew-x-[-20deg]" />
          {loading ? (
            <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
          ) : (
            <Sparkles className="w-5 h-5" />
          )}
          {loading ? "Đang xử lý..." : "GIẢI NGAY BÂY GIỜ"}
        </button>
      </div>
    </motion.div>
  );
}
