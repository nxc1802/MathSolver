"use client";

import React, { useState } from "react";
import { motion } from "framer-motion";
import { Compass, Mail, Lock, ArrowRight } from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { supabase } from "@/lib/supabase";

export default function LoginPage() {
  const { signInWithGoogle, signInWithGithub } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isLogin, setIsLogin] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleEmailAuth = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      if (isLogin) {
        const { error: authError } = await supabase.auth.signInWithPassword({
          email,
          password,
        });
        if (authError) throw authError;
      } else {
        const { error: authError } = await supabase.auth.signUp({
          email,
          password,
          options: {
            data: {
              full_name: email.split("@")[0],
            },
          },
        });
        if (authError) throw authError;
        alert("Kiểm tra email của bạn để xác nhận đăng ký tài khoản!");
      }
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("Đã có lỗi xảy ra trong quá trình xác thực");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen w-full flex items-center justify-center bg-[var(--background)] relative overflow-hidden select-none p-4">
      {/* Background ambient lighting */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] bg-indigo-600/10 rounded-full blur-[150px] pointer-events-none" />
      <div className="absolute inset-0 bg-grid-pattern opacity-40 pointer-events-none" />

      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
        className="w-full max-w-md p-6 md:p-8 rounded-3xl bg-[var(--card-bg)] border border-[var(--border)] shadow-2xl z-10"
      >
        {/* Branding */}
        <div className="text-center mb-8">
          <div className="w-12 h-12 mx-auto mb-4 rounded-2xl bg-indigo-500/10 border border-indigo-500/25 flex items-center justify-center shadow-md">
            <Compass className="w-6 h-6 text-indigo-400" />
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-[var(--text-primary)]">
            MathSolver Studio
          </h1>
          <p className="text-xs font-mono text-[var(--text-muted)] mt-1.5 uppercase tracking-wider">
            Agentic AI Geometry & Solver Platform
          </p>
        </div>

        {/* Tab Switcher */}
        <div className="bg-black/30 border border-[var(--border)] p-1 rounded-2xl mb-6 flex">
          <button
            type="button"
            onClick={() => setIsLogin(true)}
            className={`flex-1 py-2 rounded-xl text-xs font-semibold transition-all ${
              isLogin
                ? "bg-indigo-600/20 border border-indigo-500/30 text-indigo-200 shadow-sm"
                : "text-[var(--text-muted)] hover:text-white"
            }`}
          >
            Đăng nhập
          </button>
          <button
            type="button"
            onClick={() => setIsLogin(false)}
            className={`flex-1 py-2 rounded-xl text-xs font-semibold transition-all ${
              !isLogin
                ? "bg-indigo-600/20 border border-indigo-500/30 text-indigo-200 shadow-sm"
                : "text-[var(--text-muted)] hover:text-white"
            }`}
          >
            Đăng ký
          </button>
        </div>

        {/* Auth Form */}
        <form onSubmit={handleEmailAuth} className="space-y-3.5">
          <div className="relative">
            <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" />
            <input
              type="email"
              placeholder="Email của bạn"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full bg-[var(--input-bg)] border border-[var(--border)] rounded-xl py-3 pl-10 pr-3.5 text-xs md:text-sm text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:outline-none focus:border-indigo-500/50 focus:ring-1 focus:ring-indigo-500/20 transition-all"
            />
          </div>

          <div className="relative">
            <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" />
            <input
              type="password"
              placeholder="Mật khẩu"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full bg-[var(--input-bg)] border border-[var(--border)] rounded-xl py-3 pl-10 pr-3.5 text-xs md:text-sm text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:outline-none focus:border-indigo-500/50 focus:ring-1 focus:ring-indigo-500/20 transition-all"
            />
          </div>

          {error && (
            <p className="text-red-400 text-xs px-1 bg-red-500/10 border border-red-500/20 p-2.5 rounded-xl">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-indigo-600 hover:bg-indigo-500 text-white font-semibold py-3 rounded-xl flex items-center justify-center gap-2 shadow-lg shadow-indigo-600/20 transition-all active:scale-[0.98] disabled:opacity-50 text-xs md:text-sm"
          >
            <span>{loading ? "Đang xử lý..." : isLogin ? "Đăng nhập" : "Tạo tài khoản"}</span>
            {!loading && <ArrowRight className="w-4 h-4" />}
          </button>
        </form>

        {/* Divider */}
        <div className="relative my-6">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-[var(--border)]" />
          </div>
          <div className="relative flex justify-center text-[10px] uppercase font-mono">
            <span className="bg-[var(--card-bg)] px-2.5 text-[var(--text-muted)]">
              Hoặc tiếp tục với
            </span>
          </div>
        </div>

        {/* OAuth Buttons */}
        <div className="grid grid-cols-2 gap-3">
          <button
            type="button"
            onClick={signInWithGoogle}
            className="flex items-center justify-center gap-2 py-2.5 border border-[var(--border)] rounded-xl bg-white/[0.02] hover:bg-white/[0.06] transition-all text-xs font-semibold text-[var(--text-primary)] active:scale-95"
          >
            <svg className="w-3.5 h-3.5" viewBox="0 0 24 24">
              <path
                fill="#EA4335"
                d="M12 5c1.6 0 3 .6 4.1 1.7l3.1-3.1C17.3 1.8 14.8 1 12 1 7.5 1 3.7 3.6 1.9 7.3l3.7 2.9C6.5 7.4 9 5 12 5z"
              />
              <path
                fill="#4285F4"
                d="M23.5 12.3c0-.8-.1-1.6-.2-2.3H12v4.5h6.5c-.3 1.5-1.1 2.8-2.4 3.7l3.7 2.9c2.2-2 3.7-5 3.7-8.8z"
              />
              <path
                fill="#FBBC05"
                d="M5.6 14.8c-.2-.7-.4-1.5-.4-2.3 0-.8.2-1.6.4-2.3L1.9 7.3C.7 9.7 0 12.3 0 15.2c0 2.8.7 5.5 1.9 7.8l3.7-2.9z"
              />
              <path
                fill="#34A853"
                d="M12 23.5c3.2 0 6-1.1 8-3l-3.7-2.9c-1.1.7-2.5 1.2-4.3 1.2-3 0-5.5-2.4-6.4-5.2L1.9 16.5C3.7 20.2 7.5 23.5 12 23.5z"
              />
            </svg>
            Google
          </button>
          <button
            type="button"
            onClick={signInWithGithub}
            className="flex items-center justify-center gap-2 py-2.5 border border-[var(--border)] rounded-xl bg-white/[0.02] hover:bg-white/[0.06] transition-all text-xs font-semibold text-[var(--text-primary)] active:scale-95"
          >
            <svg className="w-3.5 h-3.5 fill-current text-white" viewBox="0 0 24 24">
              <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z" />
            </svg>
            GitHub
          </button>
        </div>

        <p className="mt-6 text-center text-[10px] text-[var(--text-muted)] leading-relaxed">
          Bằng việc đăng nhập, bạn đồng ý với Điều khoản và Chính sách của MathSolver Studio.
        </p>
      </motion.div>
    </div>
  );
}
