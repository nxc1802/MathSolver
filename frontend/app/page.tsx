"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { Loader2 } from "lucide-react";

/**
 * Root page redirects to the most recent session or creates a new one.
 */
export default function IndexPage() {
  const { user, session: userSession, loading } = useAuth();
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (loading) return;

    if (!user) {
        router.push("/login");
        return;
    }

    const initApp = async () => {
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
                    // Redirect to most recent
                    router.push(`/chat/${sessions[0].id}`);
                } else {
                    // Create first session
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
                      setError("Không thể tạo phiên làm việc mới.");
                    }
                }
            } else {
                setError("Không thể kết nối với máy chủ giải toán.");
            }
        } catch (err) {
            console.error("Failed to initialize session:", err);
            setError("Lỗi kết nối mạng hoặc máy chủ chưa sẵn sàng.");
        }
    };

    initApp();
  }, [user, userSession, loading, router]);

  if (error) {
    return (
      <div className="h-screen w-screen flex items-center justify-center bg-[#0a0a0f] p-6 text-center">
        <div className="max-w-sm space-y-6">
          <div className="w-16 h-16 bg-red-500/10 rounded-2xl flex items-center justify-center mx-auto">
            <div className="w-8 h-8 border-2 border-red-500/50 rounded-full flex items-center justify-center text-red-500">!</div>
          </div>
          <div className="space-y-2">
            <h3 className="text-white font-bold text-lg">Lỗi khởi tạo</h3>
            <p className="text-zinc-500 text-sm leading-relaxed">
              {error}. Hãy đảm bảo bạn đã cấu hình `NEXT_PUBLIC_API_URL` trên Vercel.
            </p>
          </div>
          <button 
            onClick={() => window.location.reload()}
            className="w-full py-3 bg-white/5 hover:bg-white/10 text-white rounded-xl text-sm font-bold transition-all border border-white/5"
          >
            Thử lại
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen w-screen flex items-center justify-center bg-[#0a0a0f]">
       <div className="flex flex-col items-center gap-4">
            <Loader2 className="w-10 h-10 animate-spin text-indigo-500" />
            <p className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest animate-pulse">
                Đang khởi tạo không gian giải toán...
            </p>
       </div>
    </div>
  );
}
