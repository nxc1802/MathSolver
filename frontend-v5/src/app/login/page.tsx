"use client";

import React, { useState } from "react";
import { motion } from "framer-motion";
import { Calculator, Code, Mail, Lock, ArrowRight, Globe } from "lucide-react";
import { useAuth } from "@/shared/lib/auth-context";
import { supabase } from "@/shared/lib/supabase";

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
        const { error } = await supabase.auth.signInWithPassword({ email, password });
        if (error) throw error;
      } else {
        const { error } = await supabase.auth.signUp({ 
          email, 
          password,
          options: {
            data: {
              full_name: email.split('@')[0],
            }
          }
        });
        if (error) throw error;
        alert("Kiểm tra email của bạn để xác nhận đăng ký!");
      }
    } catch (err: any) {
      setError(err.message || "Đã có lỗi xảy ra");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen w-full flex items-center justify-center bg-[#050508] relative overflow-hidden">
      {/* Background Orbs */}
      <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-indigo-600/10 rounded-full blur-[120px]" />
      <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-purple-600/10 rounded-full blur-[120px]" />

      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-md p-8 z-10"
      >
        <div className="text-center mb-10">
          <div className="w-16 h-16 mx-auto mb-6 rounded-2xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shadow-2xl shadow-indigo-500/20">
            <Calculator className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-3xl font-bold text-white tracking-tight">MathSolver v4.0</h1>
          <p className="text-zinc-500 mt-2 text-sm font-medium uppercase tracking-widest">Hệ thống giải toán Agentic AI</p>
        </div>

        <div className="bg-[#0c0c14]/80 border border-white/5 p-1 rounded-2xl mb-8 flex">
            <button 
                onClick={() => setIsLogin(true)}
                className={`flex-1 py-2.5 rounded-xl text-sm font-bold transition-all ${isLogin ? 'bg-white/5 text-white shadow-lg' : 'text-zinc-500 hover:text-zinc-300'}`}
            >
                Đăng nhập
            </button>
            <button 
                onClick={() => setIsLogin(false)}
                className={`flex-1 py-2.5 rounded-xl text-sm font-bold transition-all ${!isLogin ? 'bg-white/5 text-white shadow-lg' : 'text-zinc-500 hover:text-zinc-300'}`}
            >
                Đăng ký
            </button>
        </div>

        <form onSubmit={handleEmailAuth} className="space-y-4">
          <div className="relative">
            <Mail className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" />
            <input 
              type="email" 
              placeholder="Email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full bg-[#0c0c14] border border-white/5 rounded-xl py-3.5 pl-12 pr-4 text-sm text-white placeholder-zinc-600 focus:outline-none focus:border-indigo-500/50 transition-all"
            />
          </div>
          <div className="relative">
            <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" />
            <input 
              type="password" 
              placeholder="Mật khẩu"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full bg-[#0c0c14] border border-white/5 rounded-xl py-3.5 pl-12 pr-4 text-sm text-white placeholder-zinc-600 focus:outline-none focus:border-indigo-500/50 transition-all"
            />
          </div>

          {error && (
            <p className="text-red-400 text-xs px-2">{error}</p>
          )}

          <button 
            type="submit"
            disabled={loading}
            className="w-full bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white font-bold py-3.5 rounded-xl flex items-center justify-center gap-2 shadow-lg shadow-indigo-500/20 transition-all disabled:opacity-50"
          >
            {loading ? "Đang xử lý..." : isLogin ? "Đăng nhập" : "Đăng ký"}
            {!loading && <ArrowRight className="w-4 h-4" />}
          </button>
        </form>

        <div className="relative my-8">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-white/5"></div>
          </div>
          <div className="relative flex justify-center text-xs uppercase">
            <span className="bg-[#050508] px-2 text-zinc-600 font-bold tracking-widest">Hoặc tiếp tục với</span>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <button 
            onClick={signInWithGoogle}
            className="flex items-center justify-center gap-2 py-3 border border-white/5 rounded-xl bg-white/[0.02] hover:bg-white/[0.05] transition-all text-sm font-bold text-zinc-300"
          >
            <Globe className="w-4 h-4 text-red-500" />
            Google
          </button>
          <button 
            onClick={signInWithGithub}
            className="flex items-center justify-center gap-2 py-3 border border-white/5 rounded-xl bg-white/[0.02] hover:bg-white/[0.05] transition-all text-sm font-bold text-zinc-300"
          >
            <Code className="w-4 h-4 text-white" />
            GitHub
          </button>
        </div>

        <p className="mt-8 text-center text-xs text-zinc-600">
          Bằng cách tiếp tục, bạn đồng ý với Điều khoản và Chính sách bảo mật của chúng tôi.
        </p>
      </motion.div>
    </div>
  );
}
