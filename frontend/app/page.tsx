"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { Loader2, AlertCircle } from "lucide-react";

/**
 * Root page redirects to the most recent session or creates a new one.
 */
export default function IndexPage() {
  const { user, session: userSession, loading } = useAuth();
  const [initError, setInitError] = useState<string | null>(null);
  const router = useRouter();

  useEffect(() => {
    if (loading) return;

    if (!user) {
        router.push("/login");
        return;
    }

    const initApp = async () => {
        setInitError(null);
        try {
            const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
            const res = await fetch(`${apiUrl}/api/v1/sessions`, {
                headers: {
                    "Authorization": `Bearer ${userSession?.access_token}`
                }
            });

            if (res.ok) {
                const sessions = await res.json();
                if (sessions.length > 0) {
                    router.push(`/chat/${sessions[0].id}`);
                } else {
                    const createRes = await fetch(`${apiUrl}/api/v1/sessions`, {
                        method: "POST",
                        headers: {
                            "Authorization": `Bearer ${userSession?.access_token}`
                        }
                    });
                    if (createRes.ok) {
                        const newSession = await createRes.json();
                        router.push(`/chat/${newSession.id}`);
                    } else {
                        setInitError("Không thể tạo phiên chat mới.");
                    }
                }
            } else {
                setInitError("Server phản hồi lỗi. Vui lòng kiểm tra API URL.");
            }
        } catch (err) {
            console.error("Failed to initialize session:", err);
            setInitError("Không thể kết nối tới máy chủ giải toán. Vui lòng kiểm tra NEXT_PUBLIC_API_URL trên Vercel.");
        }
    };

    initApp();
  }, [user, userSession, loading, router]);

  return (
    <div className="h-screen w-screen flex items-center justify-center bg-[#0a0a0f]">
       <div className="flex flex-col items-center gap-4 max-w-md text-center px-6">
            {!initError ? (
                <>
                    <Loader2 className="w-10 h-10 animate-spin text-indigo-500" />
                    <p className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest animate-pulse">
                        Đang khởi tạo không gian giải toán...
                    </p>
                </>
            ) : (
                <>
                    <div className="w-12 h-12 rounded-2xl bg-red-500/10 flex items-center justify-center mb-2">
                        <AlertCircle className="w-6 h-6 text-red-500" />
                    </div>
                    <p className="text-sm font-bold text-white">Lỗi kết nối Backend</p>
                    <p className="text-xs text-zinc-500 leading-relaxed">
                        {initError}
                    </p>
                    <button 
                        onClick={() => window.location.reload()}
                        className="mt-4 px-6 py-2 bg-white/5 hover:bg-white/10 border border-white/5 rounded-xl text-xs font-bold text-white transition-all"
                    >
                        THỬ LẠI
                    </button>
                </>
            )}
       </div>
    </div>
  );
}
