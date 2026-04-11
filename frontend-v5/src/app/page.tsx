"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/shared/lib/auth-context";
import { getApiBaseUrl } from "@/shared/lib/api-config";
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
            setError(null);
            const apiUrl = getApiBaseUrl();
            
            // Timeout after 8 seconds
            const controller = new AbortController();
            const id = setTimeout(() => controller.abort(), 8000);

            const res = await fetch(`${apiUrl}/api/v1/sessions`, {
                headers: {
                    "Authorization": `Bearer ${userSession?.access_token}`
                },
                signal: controller.signal
            });
            clearTimeout(id);

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
                    }
                }
            } else {
                throw new Error(`Server returned ${res.status}`);
            }
        } catch (err: any) {
            console.error("Failed to initialize session:", err);
            setError("Không thể kết nối tới máy chủ giải toán. Vui lòng kiểm tra lại URL API (phải dùng https:// trên Vercel).");
        }
    };

    initApp();
  }, [user, userSession, loading, router]);

  const { signOut } = useAuth();

  if (error) {
    return (
        <div className="h-screen w-screen flex flex-col items-center justify-center bg-[#0a0a0f] text-center px-4">
             <div className="bg-red-500/10 border border-red-500/20 p-8 rounded-3xl max-w-md">
                <div className="w-12 h-12 bg-red-500/20 rounded-full flex items-center justify-center mx-auto mb-4">
                    <Loader2 className="w-6 h-6 text-red-500" />
                </div>
                <h2 className="text-xl font-bold text-white mb-2">Lỗi kết nối</h2>
                <p className="text-zinc-400 text-sm mb-6 leading-relaxed">{error}</p>
                <div className="flex flex-col gap-3">
                    <button 
                        onClick={() => window.location.reload()}
                        className="bg-indigo-600 hover:bg-indigo-500 text-white font-bold py-3 rounded-xl transition-all"
                    >
                        Thử lại
                    </button>
                    <button 
                        onClick={() => signOut()}
                        className="text-zinc-500 hover:text-white text-sm font-medium transition-all"
                    >
                        Đăng xuất và quay lại
                    </button>
                </div>
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
