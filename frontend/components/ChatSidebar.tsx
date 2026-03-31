"use client";

import React from "react";
import { 
  Calculator, 
  LogOut, 
  User as UserIcon,
  Settings,
  HelpCircle
} from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import SessionList from "./SessionList";

export default function ChatSidebar() {
  const { user, signOut } = useAuth();

  return (
    <div className="flex flex-col h-full bg-[#0c0c14]/80">
      {/* Header / Logo */}
      <div className="flex-shrink-0 px-5 py-6 border-b border-white/5">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shadow-lg shadow-indigo-500/20">
            <Calculator className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-white tracking-tight leading-none">
              MathSolver
            </h1>
            <p className="text-[10px] text-zinc-500 font-bold uppercase tracking-[0.2em] mt-1.5">
              v4.0 Agentic AI
            </p>
          </div>
        </div>
      </div>

      {/* Sessions History */}
      <div className="flex-1 overflow-hidden">
        <div className="px-5 pt-6 pb-2">
          <h2 className="text-[10px] font-bold text-zinc-600 uppercase tracking-widest">Lịch sử bài toán</h2>
        </div>
        <SessionList />
      </div>

      {/* Footer / User Profile */}
      <div className="flex-shrink-0 p-4 border-t border-white/5 bg-black/20">
        <div className="group relative flex items-center gap-3 p-2 rounded-xl hover:bg-white/5 transition-all">
          <div className="w-9 h-9 rounded-full bg-gradient-to-br from-zinc-700 to-zinc-800 flex items-center justify-center border border-white/10">
            {user?.user_metadata?.avatar_url ? (
                <img src={user.user_metadata.avatar_url} alt="avatar" className="w-full h-full rounded-full" />
            ) : (
                <UserIcon className="w-5 h-5 text-zinc-400" />
            )}
          </div>
          
          <div className="flex-1 min-w-0">
            <p className="text-sm font-bold text-white truncate">
                {user?.user_metadata?.full_name || user?.email?.split('@')[0] || "Người dùng"}
            </p>
            <p className="text-[10px] text-zinc-500 truncate">{user?.email}</p>
          </div>

          <button 
            onClick={signOut}
            className="p-2 hover:bg-red-500/10 hover:text-red-400 rounded-lg text-zinc-600 transition-all"
            title="Đăng xuất"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>

        <div className="mt-4 flex items-center justify-around px-2 py-2">
            <button className="text-zinc-600 hover:text-white transition-colors" title="Cài đặt">
                <Settings className="w-4 h-4" />
            </button>
            <button className="text-zinc-600 hover:text-white transition-colors" title="Trợ giúp">
                <HelpCircle className="w-4 h-4" />
            </button>
        </div>
      </div>
    </div>
  );
}
