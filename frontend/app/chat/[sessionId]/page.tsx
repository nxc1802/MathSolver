"use client";

import React, { useState, useEffect, useCallback, useRef } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { useParams } from "next/navigation";
import {
  Send,
  Image as ImageIcon,
  Sparkles,
  Loader2,
  Film,
  Bot,
  Maximize2,
} from "lucide-react";

import ChatSidebar from "@/components/ChatSidebar";
import AnimationPreview from "@/components/AnimationPreview";
import StaticGeometryCanvas from "@/components/StaticGeometryCanvas";
import ChatMessageComponent from "@/components/ChatMessage";
import { useAuth } from "@/lib/auth-context";
import { getApiBaseUrl, getWsBaseUrl } from "@/lib/api-config";
import { messageFromApi } from "@/lib/chat-messages";
import type { ChatMessage } from "@/types/chat";

const SOLVE_POLL_MAX_ATTEMPTS = 150;
const SOLVE_POLL_INTERVAL_MS = 2000;

export default function ChatSessionPage() {
  const params = useParams();
  const sessionId = params?.sessionId as string;
  const { session: userSession } = useAuth();

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputText, setInputText] = useState("");
  const [loading, setLoading] = useState(false);
  const [ocrLoading, setOcrLoading] = useState(false);
  const [requestVideo, setRequestVideo] = useState(false);
  const [currentStatus, setCurrentStatus] = useState<string | null>(null);

  // Media state
  const [coordinates, setCoordinates] = useState<Record<string, [number, number]> | null>(null);
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const [renderingVideo, setRenderingVideo] = useState(false);

  // Side panel resizing
  const [splitPercent, setSplitPercent] = useState(38);
  const isDragging = useRef(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const pollAttemptsRef = useRef(0);

  const statusLabels: Record<string, string> = {
    processing: "🔄 Đang xử lý...",
    solving: "🧮 Đang giải...",
    rendering_queued: "🎬 Đã gửi lệnh render...",
    rendering: "🎬 Đang dựng video...",
    success: "✅ Hoàn thành!",
    error: "❌ Lỗi hệ thống.",
  };

  const clearSolvePoll = useCallback(() => {
    if (pollIntervalRef.current !== null) {
      clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }
    pollAttemptsRef.current = 0;
  }, []);

  useEffect(() => () => clearSolvePoll(), [clearSolvePoll]);

  // Fetch Session History
  const fetchHistory = useCallback(async () => {
    if (!userSession?.access_token || !sessionId) return;
    setLoading(true);
    try {
      const apiUrl = getApiBaseUrl();
      const res = await fetch(`${apiUrl}/api/v1/sessions/${sessionId}/messages`, {
        headers: { Authorization: `Bearer ${userSession.access_token}` },
      });
      if (res.ok) {
        const data = (await res.json()) as Array<{
          id: string;
          role: string;
          type: string;
          content: string;
          created_at: string;
          metadata?: Record<string, unknown> | null;
        }>;
        const formatted = data.map(messageFromApi);
        setMessages(formatted);

        const lastWithMedia = [...formatted]
          .reverse()
          .find((m) => m.metadata?.coordinates || m.metadata?.video_url);
        if (lastWithMedia?.metadata) {
          if (lastWithMedia.metadata.coordinates) {
            setCoordinates(lastWithMedia.metadata.coordinates);
          }
          if (lastWithMedia.metadata.video_url) {
            setVideoUrl(lastWithMedia.metadata.video_url);
          }
        }
      }
    } catch (err) {
      console.error("Fetch history error:", err);
    } finally {
      setLoading(false);
    }
  }, [userSession, sessionId]);

  useEffect(() => {
    fetchHistory();
  }, [fetchHistory]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, currentStatus]);

  // Handlers
  const handleSolve = async () => {
    if (!inputText.trim() || !userSession?.access_token) return;
    clearSolvePoll();
    setLoading(true);
    setCurrentStatus("processing");

    const textPayload = inputText;

    const tempMsg: ChatMessage = {
      id: "temp-" + Date.now(),
      role: "user",
      type: "text",
      content: textPayload,
      timestamp: Date.now(),
    };
    setMessages((prev) => [...prev, tempMsg]);
    setInputText("");

    const apiUrl = getApiBaseUrl();
    const wsBase = getWsBaseUrl();

    let solveWs: WebSocket | null = null;

    const applyJobRow = (job: { status?: string; result?: Record<string, unknown> }) => {
      const r = job.result || {};
      if (r.coordinates && typeof r.coordinates === "object") {
        setCoordinates(r.coordinates as Record<string, [number, number]>);
      }
      if (typeof r.video_url === "string" && r.video_url) {
        setVideoUrl(r.video_url);
        setRenderingVideo(false);
      }
    };

    const finishSolveFlow = () => {
      clearSolvePoll();
      fetchHistory();
      setCurrentStatus(null);
      try {
        solveWs?.close();
      } catch {
        /* ignore */
      }
    };

    const runPollTick = async (jobId: string) => {
      pollAttemptsRef.current += 1;
      if (pollAttemptsRef.current > SOLVE_POLL_MAX_ATTEMPTS) {
        clearSolvePoll();
        setRenderingVideo(false);
        setCurrentStatus(null);
        return;
      }
      try {
        const res = await fetch(`${apiUrl}/api/v1/solve/${jobId}`);
        if (!res.ok) return;
        const job = await res.json();
        applyJobRow(job);
        if (job.status === "success" || job.status === "error") {
          finishSolveFlow();
        }
      } catch {
        /* ignore transient poll errors */
      }
    };

    const startSolvePolling = (jobId: string) => {
      clearSolvePoll();
      pollIntervalRef.current = setInterval(() => {
        void runPollTick(jobId);
      }, SOLVE_POLL_INTERVAL_MS);
    };

    try {
      const response = await fetch(`${apiUrl}/api/v1/sessions/${sessionId}/solve`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${userSession.access_token}`,
        },
        body: JSON.stringify({ text: textPayload, request_video: requestVideo }),
      });

      if (!response.ok) {
        let detail = `HTTP ${response.status}`;
        try {
          const errBody = (await response.json()) as { detail?: unknown };
          if (errBody.detail !== undefined) {
            detail = typeof errBody.detail === "string" ? errBody.detail : JSON.stringify(errBody.detail);
          }
        } catch {
          /* ignore */
        }
        throw new Error(detail);
      }

      const data = (await response.json()) as { job_id?: string };
      const jobId = data.job_id;
      if (!jobId) {
        throw new Error("Thiếu job_id từ máy chủ");
      }

      solveWs = new WebSocket(`${wsBase}/ws/${jobId}`);

      solveWs.onmessage = (event) => {
        let wsData: {
          status?: string;
          message?: string;
          result?: { coordinates?: unknown; video_url?: string };
        };
        try {
          wsData = JSON.parse(event.data) as typeof wsData;
        } catch {
          return;
        }

        if (wsData.status) {
          setCurrentStatus(wsData.status);
          if (wsData.status === "rendering" || wsData.status === "rendering_queued") {
            setRenderingVideo(true);
            // Worker does not send a second WS message when video is ready (see backend); poll GET /solve/{job_id}
            startSolvePolling(jobId);
          }
        }

        if (wsData.status === "error") {
          setRenderingVideo(false);
          clearSolvePoll();
          fetchHistory();
          setCurrentStatus(null);
          try {
            solveWs?.close();
          } catch {
            /* ignore */
          }
          return;
        }

        if (wsData.result) {
          const r = wsData.result;
          if (r.coordinates && typeof r.coordinates === "object") {
            setCoordinates(r.coordinates as Record<string, [number, number]>);
          }
          if (r.video_url) {
            setVideoUrl(r.video_url);
            setRenderingVideo(false);
          }
        }

        if (wsData.status === "success") {
          finishSolveFlow();
        }
      };

      solveWs.onerror = () => {
        // API.md: fallback polling when WebSocket fails
        startSolvePolling(jobId);
      };
    } catch (err) {
      console.error(err);
      setCurrentStatus("error");
      clearSolvePoll();
    } finally {
      setLoading(false);
    }
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setOcrLoading(true);
    const formData = new FormData();
    formData.append("file", file);
    const apiUrl = getApiBaseUrl();
    try {
      const res = await fetch(`${apiUrl}/api/v1/ocr`, {
        method: "POST",
        body: formData,
      });
      const data = (await res.json()) as { text?: string };
      if (data.text) setInputText(data.text);
    } catch (err) {
      console.error("OCR Error:", err);
    } finally {
      setOcrLoading(false);
    }
  };

  // Resize splitter
  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    isDragging.current = true;
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
  }, []);

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isDragging.current || !containerRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      const pct = ((e.clientX - rect.left) / rect.width) * 100;
      setSplitPercent(Math.min(Math.max(pct, 20), 50));
    };
    const handleMouseUp = () => {
      isDragging.current = false;
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    };
    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", handleMouseUp);
    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
    };
  }, []);

  return (
    <div ref={containerRef} className="h-screen w-screen flex bg-[#0a0a0f] overflow-hidden">
      <div className="h-full border-r border-white/5" style={{ width: `${splitPercent}%` }}>
        <ChatSidebar />
      </div>

      <div
        onMouseDown={handleMouseDown}
        className="w-1 cursor-col-resize hover:bg-indigo-500/30 active:bg-indigo-500/50 transition-colors z-10"
      />

      <div className="flex-1 flex flex-col min-w-0 bg-[#08080d]">
        <div className="flex-1 flex overflow-hidden">
          <div className="flex-1 flex flex-col border-r border-white/5 min-w-0 bg-[#0c0c14]/40">
            <div className="flex-1 overflow-y-auto p-4 space-y-6 scrollbar-thin">
              {messages.length === 0 && !loading && (
                <div className="h-full flex flex-col items-center justify-center text-center gap-4 opacity-50">
                  <Sparkles className="w-12 h-12 text-indigo-500/30" />
                  <div>
                    <p className="text-sm font-bold text-white">Bắt đầu bài toán của bạn</p>
                    <p className="text-xs text-zinc-600 mt-1">Dán đề bài hoặc tải ảnh chứa đề bài hình học.</p>
                  </div>
                </div>
              )}

              {messages.map((msg) => (
                <ChatMessageComponent key={msg.id} message={msg} />
              ))}

              <AnimatePresence>
                {currentStatus && currentStatus !== "success" && (
                  <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0 }}
                    className="flex gap-4"
                  >
                    <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center animate-pulse flex-shrink-0">
                      <Bot className="w-5 h-5 text-white" />
                    </div>
                    <div className="bg-zinc-900/60 border border-white/5 rounded-2xl px-5 py-4 flex items-center gap-3">
                      <Loader2 className="w-4 h-4 animate-spin text-indigo-400" />
                      <span className="text-sm text-zinc-400 italic font-medium">
                        {statusLabels[currentStatus] || currentStatus}
                      </span>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
              <div ref={messagesEndRef} />
            </div>

            <div className="p-4 border-t border-white/5 bg-black/40">
              <div className="max-w-3xl mx-auto space-y-3">
                <div className="flex items-center gap-2 px-1">
                  <input
                    type="file"
                    ref={fileInputRef}
                    onChange={handleFileChange}
                    className="hidden"
                    accept="image/*"
                  />
                  <button
                    type="button"
                    onClick={() => fileInputRef.current?.click()}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/5 text-zinc-500 hover:text-white transition-all text-xs font-bold border border-white/5"
                  >
                    {ocrLoading ? (
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    ) : (
                      <ImageIcon className="w-3.5 h-3.5" />
                    )}
                    SCAN ĐỀ
                  </button>
                  <button
                    type="button"
                    onClick={() => setRequestVideo(!requestVideo)}
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border transition-all text-xs font-bold ${
                      requestVideo
                        ? "bg-indigo-500/20 border-indigo-500/40 text-indigo-300"
                        : "bg-white/5 border-white/5 text-zinc-500 hover:text-white"
                    }`}
                  >
                    <Film className="w-3.5 h-3.5" />
                    MANIM VIDEO
                  </button>
                </div>

                <div className="flex gap-3">
                  <textarea
                    value={inputText}
                    onChange={(e) => setInputText(e.target.value)}
                    placeholder="Cho tam giác ABC cân tại A..."
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && !e.shiftKey) {
                        e.preventDefault();
                        void handleSolve();
                      }
                    }}
                    className="flex-1 bg-zinc-900/80 border border-white/5 rounded-2xl px-5 py-4 text-sm text-white focus:outline-none focus:border-indigo-500/50 transition-all resize-none min-h-[56px] max-h-[160px]"
                  />
                  <button
                    type="button"
                    onClick={handleSolve}
                    disabled={loading || !inputText.trim()}
                    className="w-14 h-14 rounded-2xl bg-indigo-600 text-white flex items-center justify-center hover:bg-indigo-500 transition-all disabled:opacity-30 self-end shadow-lg shadow-indigo-500/20"
                  >
                    {loading ? <Loader2 className="w-6 h-6 animate-spin" /> : <Send className="w-6 h-6" />}
                  </button>
                </div>
              </div>
            </div>
          </div>

          <div className="flex-[1.2] flex flex-col bg-black/40 overflow-hidden">
            <div className="px-6 py-4 border-b border-white/5 flex items-center justify-between">
              <h2 className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest">Bảng trực quan hóa</h2>
              <button
                type="button"
                className="p-2 hover:bg-white/5 rounded-lg text-zinc-600 hover:text-zinc-300 transition-all"
              >
                <Maximize2 className="w-4 h-4" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto px-6 py-6 space-y-10 scrollbar-thin">
              <AnimatePresence mode="popLayout">
                {coordinates && (
                  <motion.div
                    key="static"
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    className="space-y-4"
                  >
                    <div className="flex items-center gap-2">
                      <div className="w-1 h-3 bg-indigo-500 rounded-full" />
                      <span className="text-[10px] font-bold text-zinc-400 uppercase tracking-[0.2em]">Hình vẽ mô phỏng</span>
                    </div>
                    <div className="bg-[#0c0c14] rounded-2xl border border-white/5 p-4 shadow-2xl overflow-hidden">
                      <StaticGeometryCanvas coordinates={coordinates} />
                    </div>
                  </motion.div>
                )}

                {(videoUrl || renderingVideo) && (
                  <motion.div
                    key="video"
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    className="space-y-4"
                  >
                    <div className="flex items-center gap-2">
                      <div className="w-1 h-3 bg-purple-500 rounded-full" />
                      <span className="text-[10px] font-bold text-zinc-400 uppercase tracking-[0.2em]">
                        {videoUrl ? "🎬 Phim minh họa" : "🎨 Đang dựng hình..."}
                      </span>
                    </div>
                    <div className="bg-[#0c0c14] rounded-2xl border border-white/5 p-4 shadow-2xl relative overflow-hidden">
                      <AnimationPreview videoUrl={videoUrl || undefined} loading={renderingVideo} />
                    </div>
                  </motion.div>
                )}

                {!coordinates && !videoUrl && !renderingVideo && (
                  <div className="h-full flex flex-col items-center justify-center opacity-20 py-20 grayscale">
                    <Bot className="w-16 h-16 mb-4" />
                    <p className="text-sm font-bold uppercase tracking-[0.3em]">No Data</p>
                  </div>
                )}
              </AnimatePresence>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
