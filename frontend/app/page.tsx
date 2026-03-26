"use client";

import React, { useState, useEffect, useCallback, useRef } from "react";
import { AnimatePresence, motion } from "framer-motion";
import ChatSidebar from "@/components/ChatSidebar";
import AnimationPreview from "@/components/AnimationPreview";
import StaticGeometryCanvas from "@/components/StaticGeometryCanvas";
import type { ChatMessage } from "@/types/chat";

function genId() {
  return Math.random().toString(36).slice(2, 10) + Date.now().toString(36);
}

export default function Home() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputText, setInputText] = useState("");
  const [loading, setLoading] = useState(false);
  const [mounted, setMounted] = useState(false);
  const [requestVideo, setRequestVideo] = useState(false);
  const [currentStatus, setCurrentStatus] = useState<string | null>(null);

  // Media state (latest from messages)
  const [coordinates, setCoordinates] = useState<Record<string, [number, number]> | null>(null);
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const [renderingVideo, setRenderingVideo] = useState(false);

  // Resizable splitter
  const [splitPercent, setSplitPercent] = useState(38);
  const isDragging = useRef(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setMounted(true);
  }, []);

  // Resizable splitter mouse handlers
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
      setSplitPercent(Math.min(Math.max(pct, 25), 65));
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

  // Helper to push a message
  const pushMessage = useCallback((msg: Omit<ChatMessage, "id" | "timestamp">) => {
    setMessages((prev) => [
      ...prev,
      { ...msg, id: genId(), timestamp: Date.now() },
    ]);
  }, []);

  // Handle solve
  const handleSolve = async () => {
    if (!inputText.trim()) return;
    setLoading(true);
    setCoordinates(null);
    setVideoUrl(null);
    setRenderingVideo(false);

    // User message
    pushMessage({ role: "user", type: "text", content: inputText });
    setCurrentStatus("processing");

    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    try {
      const response = await fetch(`${apiUrl}/api/v1/solve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: inputText, request_video: requestVideo }),
      });
      const data = await response.json();
      const jobId = data.job_id;

      // Connect WebSocket
      let wsUrl = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000";
      if (typeof window !== "undefined" && window.location.protocol === "https:" && !wsUrl.startsWith("wss://")) {
        wsUrl = wsUrl.replace("ws://", "wss://");
      }

      const ws = new WebSocket(`${wsUrl}/ws/${jobId}`);

      ws.onmessage = (event) => {
        const wsData = JSON.parse(event.data);
        console.log("WS Update:", wsData);

        if (wsData.status) {
          setCurrentStatus(wsData.status);

          if (wsData.status === "rendering" || wsData.status === "rendering_queued") {
            setRenderingVideo(true);
          }
        }

        if (wsData.result) {
          const r = wsData.result;
          // Semantic analysis
          if (r.semantic_analysis || r.semantic?.text) {
            pushMessage({
              role: "assistant",
              type: "analysis",
              content: r.semantic_analysis || r.semantic?.text,
            });
          }
          // DSL
          if (r.geometry_dsl) {
            pushMessage({ role: "assistant", type: "dsl", content: r.geometry_dsl });
          }
          // Coordinates
          if (r.coordinates) {
            setCoordinates(r.coordinates);
            pushMessage({
              role: "assistant",
              type: "coordinates",
              content: JSON.stringify(r.coordinates),
              metadata: { coordinates: r.coordinates },
            });
          }
          // Video
          if (r.video_url) {
            setVideoUrl(r.video_url);
            setRenderingVideo(false);
            setCurrentStatus(null);
            pushMessage({
              role: "assistant",
              type: "text",
              content: "🎬 Video animation đã sẵn sàng — xem bên phải →",
              metadata: { videoUrl: r.video_url },
            });
          }
        }
      };

      // Polling fallback
      let pollInterval: any;
      const startPolling = () => {
        pollInterval = setInterval(async () => {
          try {
            const res = await fetch(`${apiUrl}/api/v1/solve/${jobId}`);
            if (!res.ok) {
              console.warn(`[Poll] Backend returned ${res.status}. Retrying...`);
              return;
            }
            const polled = await res.json();
            if (polled.status === "success" || polled.status === "error") {
              clearInterval(pollInterval);
              const r = polled.result || {};

              if (polled.status === "success") {
                setCurrentStatus(null);
              } else {
                setCurrentStatus(null);
                pushMessage({
                  role: "assistant",
                  type: "error",
                  content: r.error || "Đã xảy ra lỗi trong quá trình xử lý.",
                });
              }

              if (r.semantic_analysis) {
                pushMessage({ role: "assistant", type: "analysis", content: r.semantic_analysis });
              }
              if (r.geometry_dsl) {
                pushMessage({ role: "assistant", type: "dsl", content: r.geometry_dsl });
              }
              if (r.coordinates) {
                setCoordinates(r.coordinates);
                pushMessage({
                  role: "assistant",
                  type: "coordinates",
                  content: JSON.stringify(r.coordinates),
                  metadata: { coordinates: r.coordinates },
                });
              }
              if (r.video_url) {
                setVideoUrl(r.video_url);
                setRenderingVideo(false);
                setCurrentStatus(null);
                pushMessage({
                  role: "assistant",
                  type: "text",
                  content: "🎬 Video animation đã sẵn sàng — xem bên phải →",
                  metadata: { videoUrl: r.video_url },
                });
              }
              ws.close();
            }
          } catch (err) {
            console.error("[Poll] Network error (possibly backend reloading):", err);
          }
        }, 3000);
      };

      // Start polling after a short delay to give WS time
      setTimeout(startPolling, 5000);

      ws.onclose = () => {
        // If poll is still running, it will clean up
      };

      setInputText("");
    } catch (err) {
      console.error(err);
      pushMessage({
        role: "assistant",
        type: "error",
        content: "Không thể kết nối đến server. Vui lòng thử lại.",
      });
    } finally {
      setLoading(false);
    }
  };

  if (!mounted) return null;

  const hasMedia = coordinates || videoUrl || renderingVideo;

  return (
    <div
      ref={containerRef}
      className="h-screen w-screen flex overflow-hidden bg-[#0a0a0f]"
    >
      {/* Left: Chat Sidebar */}
      <div
        className="h-full flex-shrink-0 border-r border-white/5 bg-[#0c0c14]/80"
        style={{ width: `${splitPercent}%` }}
      >
        <ChatSidebar
          messages={messages}
          input={inputText}
          setInput={setInputText}
          loading={loading}
          onSolve={handleSolve}
          requestVideo={requestVideo}
          setRequestVideo={setRequestVideo}
          currentStatus={currentStatus}
        />
      </div>

      {/* Drag Handle */}
      <div
        onMouseDown={handleMouseDown}
        className="w-1.5 flex-shrink-0 cursor-col-resize bg-transparent hover:bg-indigo-500/30 active:bg-indigo-500/50 transition-colors relative group z-10"
      >
        <div className="absolute inset-y-0 -left-1 -right-1" />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-1 h-8 rounded-full bg-zinc-700 group-hover:bg-indigo-400 transition-colors" />
      </div>

      {/* Right: Media Panel */}
      <div className="flex-1 h-full flex flex-col bg-[#08080d] overflow-hidden">
        {/* Panel Header */}
        <div className="flex-shrink-0 px-6 py-4 border-b border-white/5">
          <h2 className="text-xs font-bold text-zinc-500 uppercase tracking-[0.2em]">
            {videoUrl ? "Video Animation" : coordinates ? "Hình Vẽ Minh Họa" : "Khu Vực Hiển Thị"}
          </h2>
        </div>

        {/* Content */}
        <div className="flex-1 flex items-center justify-center p-6 overflow-auto">
          <AnimatePresence mode="wait">
            {videoUrl ? (
              <motion.div
                key="video"
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.95 }}
                className="w-full max-w-3xl"
              >
                <AnimationPreview videoUrl={videoUrl} loading={false} />
              </motion.div>
            ) : coordinates ? (
              <motion.div
                key="canvas"
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.95 }}
                className="w-full max-w-3xl relative"
              >
                <StaticGeometryCanvas coordinates={coordinates} />
                {renderingVideo && (
                  <div className="absolute inset-0 bg-black/40 backdrop-blur-[2px] rounded-xl flex items-center justify-center border border-white/5">
                    <div className="text-center space-y-3">
                      <div className="w-10 h-10 border-2 border-indigo-500/30 border-t-indigo-500 rounded-full animate-spin mx-auto" />
                      <p className="text-xs font-bold text-white uppercase tracking-widest">🎬 Đang tạo video...</p>
                    </div>
                  </div>
                )}
              </motion.div>
            ) : renderingVideo ? (
              <motion.div
                key="rendering"
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.95 }}
                className="w-full max-w-3xl"
              >
                <AnimationPreview loading={true} />
              </motion.div>
            ) : (
              <motion.div
                key="empty"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="text-center space-y-4"
              >
                <div className="w-20 h-20 mx-auto rounded-3xl bg-white/[0.02] border border-white/5 flex items-center justify-center">
                  <svg
                    className="w-10 h-10 text-zinc-800"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    strokeWidth={1}
                  >
                    <path d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                  </svg>
                </div>
                <div>
                  <p className="text-zinc-500 text-sm font-medium">
                    Hình vẽ & Animation
                  </p>
                  <p className="text-zinc-700 text-xs mt-1">
                    Kết quả trực quan sẽ hiển thị tại đây
                  </p>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Footer */}
        <div className="flex-shrink-0 px-6 py-3 border-t border-white/5 text-center">
          <span className="text-[9px] text-zinc-700 font-bold uppercase tracking-[0.3em]">
            © 2026 Visual Math Solver — Agentic Engine
          </span>
        </div>
      </div>
    </div>
  );
}
