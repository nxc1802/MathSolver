"use client";

import React from "react";
import { Compass, Box, ScanLine, ArrowUpRight, Sparkles } from "lucide-react";
import { motion } from "framer-motion";

interface HeroWelcomeProps {
  onSuggestionClick?: (text: string) => void;
}

const SUGGESTIONS = [
  {
    title: "Hình học phẳng 2D",
    desc: "Đường tròn ngoại tiếp, hệ thức lượng, tính chất tam giác & tứ giác.",
    prompt: "Cho hình chữ nhật ABCD có AB = 5, AD = 10. Tính diện tích và bán kính đường tròn ngoại tiếp.",
    icon: Compass,
    badge: "2D Solver",
    accent: "indigo",
  },
  {
    title: "Hình học không gian 3D",
    desc: "Hình chóp, lăng trụ, góc giữa hai mặt phẳng, thể tích khối đa diện.",
    prompt: "Cho hình chóp S.ABCD có đáy là hình vuông cạnh 6, chiều cao SO = 8 vuông góc với đáy. Tính thể tích.",
    icon: Box,
    badge: "3D Space & Three.js",
    accent: "violet",
  },
  {
    title: "Nhận diện ảnh đề (OCR)",
    desc: "Dán trực tiếp (Ctrl+V) hoặc kéo thả ảnh đề chụp vào khung nhập để giải tự động.",
    prompt: "Cho tam giác ABC vuông tại A có AB = 3cm, AC = 4cm. Tính độ dài đường cao AH.",
    icon: ScanLine,
    badge: "Vision OCR",
    accent: "sky",
  },
];

export default function HeroWelcome({ onSuggestionClick }: HeroWelcomeProps) {
  return (
    <div className="h-full flex flex-col items-center justify-center text-center px-6 py-8 relative overflow-hidden select-none">
      {/* Ambient background glow */}
      <div className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-indigo-600/10 rounded-full blur-[140px] pointer-events-none" />

      {/* Main Intro Badge & Title */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
        className="flex flex-col items-center max-w-lg mb-8"
      >
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-xs font-mono mb-4 shadow-sm">
          <Sparkles className="w-3.5 h-3.5" />
          <span>Multi-Agent Visual Math Engine</span>
        </div>

        <h1 className="text-2xl md:text-3xl font-semibold tracking-tight text-[var(--text-primary)] text-balance">
          Không gian Giải toán & Mô phỏng Hình học
        </h1>

        <p className="text-xs md:text-sm text-[var(--text-secondary)] mt-2.5 max-w-md leading-relaxed text-balance">
          Nhập đề bài, kéo thả ảnh bài tập hoặc chọn nhanh các chủ đề mẫu bên dưới để bắt đầu giải và dựng hình 2D/3D.
        </p>
      </motion.div>

      {/* Suggestion Cards Grid */}
      <motion.div
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.1, ease: [0.16, 1, 0.3, 1] }}
        className="grid grid-cols-1 md:grid-cols-3 gap-3.5 max-w-3xl w-full text-left"
      >
        {SUGGESTIONS.map((item, idx) => {
          const Icon = item.icon;
          return (
            <motion.div
              key={idx}
              whileHover={{ y: -3 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => onSuggestionClick?.(item.prompt)}
              className="group relative p-4 rounded-2xl bg-[var(--card-bg)] border border-[var(--border)] hover:border-indigo-500/30 hover:bg-[var(--card-hover)] transition-all cursor-pointer flex flex-col justify-between shadow-sm"
            >
              <div>
                <div className="flex items-center justify-between mb-3">
                  <div className="w-8 h-8 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 flex items-center justify-center group-hover:scale-105 transition-transform">
                    <Icon className="w-4 h-4" />
                  </div>
                  <span className="text-[9px] font-mono font-medium px-2 py-0.5 rounded-full bg-white/[0.04] border border-white/5 text-[var(--text-muted)] group-hover:text-indigo-300 transition-colors">
                    {item.badge}
                  </span>
                </div>

                <h2 className="text-sm font-semibold text-[var(--text-primary)] group-hover:text-indigo-200 transition-colors flex items-center gap-1">
                  {item.title}
                  <ArrowUpRight className="w-3 h-3 opacity-0 group-hover:opacity-100 transition-opacity text-indigo-400" />
                </h2>

                <p className="text-xs text-[var(--text-muted)] leading-relaxed mt-1.5 line-clamp-2">
                  {item.desc}
                </p>
              </div>

              <div className="mt-4 pt-3 border-t border-[var(--border-subtle)] flex items-center text-[10px] font-mono text-[var(--text-secondary)] opacity-80 group-hover:opacity-100 group-hover:text-indigo-300 transition-colors truncate">
                <span className="truncate">Thử: &quot;{item.prompt}&quot;</span>
              </div>
            </motion.div>
          );
        })}
      </motion.div>
    </div>
  );
}
