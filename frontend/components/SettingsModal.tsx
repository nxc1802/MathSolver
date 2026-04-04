"use client";

import React, { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, Moon, Sun, Monitor, Bell, Shield, Eye } from "lucide-react";

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function SettingsModal({ isOpen, onClose }: SettingsModalProps) {
  const [theme, setTheme] = useState<"light" | "dark">("dark");

  useEffect(() => {
    const savedTheme = localStorage.getItem("mathsolver-theme") as "light" | "dark" | null;
    if (savedTheme) {
      setTheme(savedTheme);
      document.documentElement.setAttribute("data-theme", savedTheme);
    }
  }, []);

  const toggleTheme = (newTheme: "light" | "dark") => {
    setTheme(newTheme);
    localStorage.setItem("mathsolver-theme", newTheme);
    document.documentElement.setAttribute("data-theme", newTheme);
  };

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
        {/* Backdrop */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
          className="absolute inset-0 bg-black/60 backdrop-blur-md"
        />

        {/* Modal Content */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 20 }}
          className="relative w-full max-w-2xl bg-[var(--card-bg)] border border-[var(--border)] rounded-[2.5rem] shadow-2xl overflow-hidden flex flex-col md:flex-row h-[500px]"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Sidebar */}
          <div className="w-full md:w-56 bg-black/5 border-r border-[var(--border)] p-6 flex flex-col gap-2">
            <h2 className="text-xl font-black text-[var(--text-primary)] mb-6 tracking-tight">Cài đặt</h2>
            
            <button className="flex items-center gap-3 px-4 py-3 rounded-2xl bg-indigo-500/10 text-indigo-500 border border-indigo-500/20 text-sm font-bold transition-all">
              <Monitor className="w-4 h-4" />
              Giao diện
            </button>
            <button className="flex items-center gap-3 px-4 py-3 rounded-2xl text-zinc-500 hover:bg-white/5 hover:text-white text-sm font-bold transition-all opacity-50 cursor-not-allowed">
              <Bell className="w-4 h-4" />
              Thông báo
            </button>
            <button className="flex items-center gap-3 px-4 py-3 rounded-2xl text-zinc-500 hover:bg-white/5 hover:text-white text-sm font-bold transition-all opacity-50 cursor-not-allowed">
              <Shield className="w-4 h-4" />
              Bảo mật
            </button>
          </div>

          {/* Main Area */}
          <div className="flex-1 p-8 overflow-y-auto">
            <div className="flex items-center justify-between mb-8">
              <div>
                <h3 className="text-lg font-bold text-[var(--text-primary)]">Chủ đề hiển thị</h3>
                <p className="text-xs text-[var(--text-secondary)] mt-1">Chọn phong cách phù hợp với đôi mắt của bạn</p>
              </div>
              <button 
                onClick={onClose}
                className="p-2 hover:bg-white/5 rounded-xl text-zinc-500 hover:text-white transition-all"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <button
                onClick={() => toggleTheme("dark")}
                className={`group relative p-4 rounded-3xl border transition-all text-left overflow-hidden ${
                  theme === "dark" 
                    ? "border-indigo-500 bg-indigo-500/5 ring-4 ring-indigo-500/10" 
                    : "border-white/5 bg-white/5 hover:border-white/10"
                }`}
              >
                <div className="flex items-center justify-between mb-4">
                  <div className={`p-3 rounded-2xl ${theme === "dark" ? "bg-indigo-600 text-white" : "bg-zinc-800 text-zinc-400"}`}>
                    <Moon className="w-5 h-5" />
                  </div>
                  {theme === "dark" && <div className="w-2 h-2 rounded-full bg-indigo-500" />}
                </div>
                <p className="font-bold text-[var(--text-primary)] text-sm">Chế độ tối</p>
                <p className="text-xs text-[var(--text-secondary)] mt-1">Tiết kiệm pin, bảo vệ mắt</p>
                
                {/* Visual Preview */}
                <div className="mt-4 h-20 rounded-xl bg-black/40 border border-white/5 p-2 space-y-2 opacity-60">
                   <div className="h-1.5 w-full bg-white/5 rounded-full" />
                   <div className="h-1.5 w-2/3 bg-white/5 rounded-full" />
                </div>
              </button>

              <button
                onClick={() => toggleTheme("light")}
                className={`group relative p-4 rounded-3xl border transition-all text-left overflow-hidden ${
                  theme === "light" 
                    ? "border-indigo-500 bg-indigo-500/5 ring-4 ring-indigo-500/10" 
                    : "border-white/5 bg-white/5 hover:border-white/10"
                }`}
              >
                <div className="flex items-center justify-between mb-4">
                  <div className={`p-3 rounded-2xl ${theme === "light" ? "bg-indigo-600 text-white" : "bg-zinc-200 text-zinc-500"}`}>
                    <Sun className="w-5 h-5" />
                  </div>
                  {theme === "light" && <div className="w-2 h-2 rounded-full bg-indigo-500" />}
                </div>
                <p className="font-bold text-[var(--text-primary)] text-sm">Chế độ sáng</p>
                <p className="text-xs text-[var(--text-secondary)] mt-1">Sắc nét, thanh tao</p>

                {/* Visual Preview */}
                <div className="mt-4 h-20 rounded-xl bg-zinc-100 border border-zinc-200 p-2 space-y-2 opacity-60">
                   <div className="h-1.5 w-full bg-zinc-300 rounded-full" />
                   <div className="h-1.5 w-2/3 bg-zinc-300 rounded-full" />
                </div>
              </button>
            </div>

            <div className="mt-10 pt-6 border-t border-white/5">
               <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                     <div className="w-10 h-10 rounded-2xl bg-black/5 flex items-center justify-center">
                        <Eye className="w-5 h-5 text-indigo-500" />
                     </div>
                     <div>
                        <p className="text-sm font-bold text-[var(--text-primary)]">Animations</p>
                        <p className="text-[10px] text-[var(--text-muted)] uppercase tracking-widest font-bold">Bật hiệu ứng chuyển động</p>
                     </div>
                  </div>
                  <div className="w-12 h-6 rounded-full bg-indigo-600 relative px-1 flex items-center">
                     <div className="w-4 h-4 rounded-full bg-white shadow-lg ml-auto" />
                  </div>
               </div>
            </div>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
}
