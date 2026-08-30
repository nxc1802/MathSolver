"use client";

import React, { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, Moon, Sun, Info } from "lucide-react";

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function SettingsModal({ isOpen, onClose }: SettingsModalProps) {
  const [theme, setTheme] = useState<"light" | "dark">(() => {
    if (typeof window !== "undefined") {
      const saved = localStorage.getItem("mathsolver-theme") as "light" | "dark" | null;
      return saved || "dark";
    }
    return "dark";
  });

  const [enableAnimations, setEnableAnimations] = useState(true);

  useEffect(() => {
    if (typeof document !== "undefined") {
      document.documentElement.setAttribute("data-theme", theme);
    }
  }, [theme]);

  const toggleTheme = (newTheme: "light" | "dark") => {
    setTheme(newTheme);
    if (typeof window !== "undefined") {
      localStorage.setItem("mathsolver-theme", newTheme);
    }
  };

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 select-none">
        {/* Backdrop */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
          className="absolute inset-0 bg-black/70 backdrop-blur-md"
        />

        {/* Modal Window */}
        <motion.div
          initial={{ opacity: 0, scale: 0.96, y: 12 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.96, y: 12 }}
          transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
          className="relative w-full max-w-xl bg-[var(--card-bg)] border border-[var(--border)] rounded-3xl shadow-2xl overflow-hidden flex flex-col max-h-[85vh]"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-[var(--border)]">
            <div className="flex items-center gap-2">
              <h2 className="text-base font-semibold text-[var(--text-primary)]">
                Cài đặt hệ thống
              </h2>
            </div>
            <button
              type="button"
              onClick={onClose}
              className="p-1.5 hover:bg-white/10 rounded-lg text-[var(--text-muted)] hover:text-white transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Body Content */}
          <div className="p-6 space-y-6 overflow-y-auto scrollbar-thin">
            {/* Theme Section */}
            <div>
              <h3 className="text-xs font-mono font-semibold uppercase tracking-wider text-[var(--text-secondary)] mb-3">
                Giao diện & Chủ đề
              </h3>
              <div className="grid grid-cols-2 gap-3.5">
                {/* Dark Theme Option */}
                <button
                  type="button"
                  onClick={() => toggleTheme("dark")}
                  className={`p-4 rounded-2xl border transition-all text-left flex flex-col justify-between ${
                    theme === "dark"
                      ? "border-indigo-500/50 bg-indigo-500/10 ring-1 ring-indigo-500/30"
                      : "border-[var(--border)] bg-white/[0.02] hover:bg-white/[0.05]"
                  }`}
                >
                  <div className="flex items-center justify-between mb-3">
                    <div className="w-8 h-8 rounded-xl bg-indigo-600/20 text-indigo-400 flex items-center justify-center">
                      <Moon className="w-4 h-4" />
                    </div>
                    {theme === "dark" && (
                      <div className="w-2 h-2 rounded-full bg-indigo-400 shadow-sm" />
                    )}
                  </div>
                  <div>
                    <p className="text-xs font-semibold text-[var(--text-primary)]">
                      Chế độ Tối (Dark)
                    </p>
                    <p className="text-[10px] text-[var(--text-muted)] mt-0.5">
                      Tối ưu độ tương phản hình học
                    </p>
                  </div>
                </button>

                {/* Light Theme Option */}
                <button
                  type="button"
                  onClick={() => toggleTheme("light")}
                  className={`p-4 rounded-2xl border transition-all text-left flex flex-col justify-between ${
                    theme === "light"
                      ? "border-indigo-500/50 bg-indigo-500/10 ring-1 ring-indigo-500/30"
                      : "border-[var(--border)] bg-white/[0.02] hover:bg-white/[0.05]"
                  }`}
                >
                  <div className="flex items-center justify-between mb-3">
                    <div className="w-8 h-8 rounded-xl bg-amber-500/20 text-amber-400 flex items-center justify-center">
                      <Sun className="w-4 h-4" />
                    </div>
                    {theme === "light" && (
                      <div className="w-2 h-2 rounded-full bg-indigo-400 shadow-sm" />
                    )}
                  </div>
                  <div>
                    <p className="text-xs font-semibold text-[var(--text-primary)]">
                      Chế độ Sáng (Light)
                    </p>
                    <p className="text-[10px] text-[var(--text-muted)] mt-0.5">
                      Sắc nét và thanh thoát
                    </p>
                  </div>
                </button>
              </div>
            </div>

            {/* Animation Toggle */}
            <div className="pt-4 border-t border-[var(--border)]">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs font-semibold text-[var(--text-primary)]">
                    Hiệu ứng chuyển động mượt (60fps)
                  </p>
                  <p className="text-[10px] text-[var(--text-muted)] mt-0.5">
                    Kích hoạt các chuyển động hoạt họa của biểu đồ & cửa sổ
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => setEnableAnimations(!enableAnimations)}
                  className={`w-11 h-6 rounded-full p-0.5 transition-colors ${
                    enableAnimations ? "bg-indigo-600" : "bg-zinc-700"
                  }`}
                >
                  <div
                    className={`w-5 h-5 rounded-full bg-white transition-transform ${
                      enableAnimations ? "translate-x-5" : "translate-x-0"
                    }`}
                  />
                </button>
              </div>
            </div>

            {/* Platform Info */}
            <div className="p-3.5 rounded-2xl bg-white/[0.02] border border-[var(--border)] flex items-start gap-3">
              <Info className="w-4 h-4 text-indigo-400 shrink-0 mt-0.5" />
              <div className="text-[11px] text-[var(--text-muted)] leading-relaxed">
                <span className="font-semibold text-[var(--text-primary)]">
                  MathSolver Engine v5.1
                </span>{" "}
                — Tích hợp mô hình hình học 2D Canvas SVG, 3D WebGL Three.js và trình dựng video Manim Animation tự động.
              </div>
            </div>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
}
