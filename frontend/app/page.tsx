"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { Loader2 } from "lucide-react";

/**
 * Root page redirects to the most recent session or creates a new one.
 */
export default function IndexPage() {
  const { user, session: userSession, loading } = useAuth();
  const router = useRouter();

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
                    }
                }
            }
        } catch (err) {
            console.error("Failed to initialize session:", err);
        }
    };

    initApp();
  }, [user, userSession, loading, router]);

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
