"use client";

import React, { useState, useEffect, useCallback, useRef, useMemo } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { useParams } from "next/navigation";
import { Send, Sparkles, Loader2, Film, Bot, Maximize2 } from "lucide-react";

import useSWR, { useSWRConfig } from "swr";
import ChatSidebar from "@/components/ChatSidebar";
import AnimationPreview from "@/components/AnimationPreview";
import StaticGeometryCanvas from "@/components/StaticGeometryCanvas";
import VersionSwitcher from "@/components/VersionSwitcher";
import ChatMessageComponent from "@/components/ChatMessage";
import { useAuth } from "@/lib/auth-context";
import { getApiBaseUrl, getWsBaseUrl } from "@/lib/api-config";
import { messageFromApi } from "@/lib/chat-messages";
import {
  readSplitPercent,
  writeSplitPercent,
  readMainSplitPercent,
  writeMainSplitPercent,
  readSidebarCollapsed,
  writeSidebarCollapsed,
  SPLIT_MIN_PCT,
  SPLIT_MAX_PCT,
  MAIN_SPLIT_MIN_PCT,
  MAIN_SPLIT_MAX_PCT,
} from "@/lib/session-ui-storage";
import {
  loadGeometryState,
  saveGeometryState,
  type GeometryState,
} from "@/lib/session-geometry-cache";
import {
  saveActiveJob,
  getActiveJob,
  clearActiveJob,
} from "@/lib/job-tracker";
import type { ChatMessage } from "@/types/chat";

const SOLVE_POLL_MAX_ATTEMPTS = 300;
const SOLVE_POLL_INTERVAL_MS = 1000;

async function fetchChatMessages([url, token]: [string, string]): Promise<ChatMessage[]> {
  const res = await fetch(url, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error("Failed to fetch messages");
  const data = await res.json();
  return data.map(messageFromApi);
}

async function fetchSessionAssets([url, token]: [string, string]): Promise<any[]> {
  const res = await fetch(url, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) return [];
  return res.json();
}

export default function ChatSessionPage() {
  const params = useParams();
  const sessionId = params?.sessionId as string;
  const { session: userSession } = useAuth();
  const { mutate: globalMutate } = useSWRConfig();

  const messagesKey = userSession?.access_token && sessionId 
    ? [`${getApiBaseUrl()}/api/v1/sessions/${sessionId}/messages`, userSession.access_token] as const 
    : null;

  const assetsKey = userSession?.access_token && sessionId 
    ? [`${getApiBaseUrl()}/api/v1/sessions/${sessionId}/assets`, userSession.access_token] as const 
    : null;

  const isTempSession = sessionId?.startsWith("temp-");

  const { data: messages = [], isLoading: historyLoadingRaw, mutate: mutateMessages } = useSWR(
    !isTempSession ? messagesKey : null,
    fetchChatMessages,
    { 
      revalidateOnFocus: false, 
      revalidateIfStale: true,
      dedupingInterval: 2000 
    }
  );

  const historyLoading = !isTempSession && historyLoadingRaw;

  const { data: sessionAssets = [], mutate: mutateAssets } = useSWR(
    !isTempSession ? assetsKey : null,
    fetchSessionAssets,
    { revalidateOnFocus: false }
  );

  const [inputText, setInputText] = useState("");
  const [solveLoading, setSolveLoading] = useState(false);
  const [ocrLoading, setOcrLoading] = useState(false);
  const [requestVideo, setRequestVideo] = useState(false);
  const [currentStatus, setCurrentStatus] = useState<string | null>(null);

  const [coordinates, setCoordinates] = useState<Record<string, [number, number]> | null>(null);
  const [polygonOrder, setPolygonOrder] = useState<string[] | null>(null);
  const [circles, setCircles] = useState<any[] | null>(null);
  const [lines, setLines] = useState<any[] | null>(null);
  const [rays, setRays] = useState<any[] | null>(null);
  const [drawingPhases, setDrawingPhases] = useState<any[] | null>(null);
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const [renderingVideo, setRenderingVideo] = useState(false);
  
  const [videoVersion, setVideoVersion] = useState(1);
  const [activeJobId, setActiveJobId] = useState<string | null>(null);

  const geometrySnapshots = useMemo(() => {
    return [...messages]
      .filter((m) => m.role === "assistant" && m.type !== "error" && m.metadata?.coordinates)
      .reverse();
  }, [messages]);

  const [splitPercent, setSplitPercent] = useState(14.3);
  const [mainSplitPercent, setMainSplitPercent] = useState(50);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [uiHydrated, setUiHydrated] = useState(false);

  const draggingType = useRef<'sidebar' | 'main' | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const pollAttemptsRef = useRef(0);
  const solveWsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    setSplitPercent(readSplitPercent(14.3));
    setMainSplitPercent(readMainSplitPercent(50));
    setSidebarCollapsed(readSidebarCollapsed());
    setUiHydrated(true);
  }, []);

  useEffect(() => {
    if (!uiHydrated) return;
    writeSplitPercent(splitPercent);
    writeMainSplitPercent(mainSplitPercent);
  }, [splitPercent, mainSplitPercent, uiHydrated]);

  useEffect(() => {
    if (!uiHydrated) return;
    writeSidebarCollapsed(sidebarCollapsed);
  }, [sidebarCollapsed, uiHydrated]);

  const statusLabels: Record<string, string> = {
    processing: "🔄 Đang xử lý bài toán...",
    solving: "🧮 Đang giải hệ phương trình...",
    rendering_queued: "🎬 Đã gửi yêu cầu render video...",
    rendering: "🎬 Đang dựng animation Manim...",
    success: "✅ Hoàn thành!",
    error: "❌ Có lỗi xảy ra.",
  };

  const clearSolvePoll = useCallback(() => {
    if (pollIntervalRef.current !== null) {
      clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }
    pollAttemptsRef.current = 0;
  }, []);

  useEffect(() => () => clearSolvePoll(), [clearSolvePoll]);

  const setGeometryFromSnapshot = useCallback((snapshot: ChatMessage) => {
    if (snapshot?.metadata) {
      const meta = snapshot.metadata;
      setCoordinates(meta.coordinates || null);
      setPolygonOrder(meta.polygon_order || null);
      setCircles(meta.circles || null);
      setLines(meta.lines || null);
      setRays(meta.rays || null);
      setDrawingPhases(meta.drawing_phases || null);
      setVideoUrl(meta.video_url || null);
      if (meta.job_id) setActiveJobId(meta.job_id);
    }
  }, []);

  useEffect(() => {
    if (geometrySnapshots.length > 0) {
      // Default to version 1 (latest) if out of bounds
      const safeVersion = Math.min(Math.max(videoVersion, 1), geometrySnapshots.length);
      setGeometryFromSnapshot(geometrySnapshots[safeVersion - 1]);
    } else {
      // No geometry
      setCoordinates(null);
      setPolygonOrder(null);
      setCircles(null);
      setLines(null);
      setRays(null);
      setDrawingPhases(null);
      setVideoUrl(null);
    }
  }, [geometrySnapshots, videoVersion, setGeometryFromSnapshot]);

  useEffect(() => {
    // When assets change, updating the current video if appropriate
    if (sessionAssets.length > 0) {
      // By default, if we are not in the middle of a solve, use the latest asset
      if (!currentStatus) {
        setVideoUrl(sessionAssets[0].public_url);
        setVideoVersion(1);
      }
    }
  }, [sessionAssets, currentStatus]);

  // Bug 1 + 4 Fix: When switching sessions, restore from sessionStorage cache instead of
  // blanking out immediately. Only reset to null if nothing is cached.
  const prevSessionIdRef = useRef<string | null>(null);
  useEffect(() => {
    if (!sessionId || sessionId === prevSessionIdRef.current) return;
    prevSessionIdRef.current = sessionId;

    // Reset transient solve state (not geometry — that comes from cache)
    setCurrentStatus(null);
    setVideoVersion(1);

    if (sessionId.startsWith("temp-")) {
      // Temp sessions have no data at all — clear geometry immediately
      setCoordinates(null);
      setPolygonOrder(null);
      setCircles(null);
      setLines(null);
      setRays(null);
      setDrawingPhases(null);
      setVideoUrl(null);
      setActiveJobId(null);
      return;
    }

    // Try to restore from cache for instant display (Bug 4)
    const cached = loadGeometryState(sessionId);
    if (cached) {
      setCoordinates(cached.coordinates);
      setPolygonOrder(cached.polygonOrder);
      setCircles(cached.circles);
      setLines(cached.lines || null);
      setRays(cached.rays || null);
      setDrawingPhases(cached.drawingPhases);
      setVideoUrl(cached.videoUrl);
      setActiveJobId(cached.activeJobId);
    } else {
      // No cache — blank out and wait for messages to load
      setCoordinates(null);
      setPolygonOrder(null);
      setCircles(null);
      setLines(null);
      setRays(null);
      setDrawingPhases(null);
      setVideoUrl(null);
      setActiveJobId(null);
    }

    // Bug 2 Fix: Check for active jobs and re-attach
    const activeJobIdForSession = getActiveJob(sessionId);
    if (activeJobIdForSession) {
      void attachToJob(activeJobIdForSession);
    }
  }, [sessionId]);

  const handleNextVersion = () => {
    if (videoVersion > 1) {
      setVideoVersion(videoVersion - 1);
    }
  };

  const handlePrevVersion = () => {
    if (videoVersion < geometrySnapshots.length) {
      setVideoVersion(videoVersion + 1);
    }
  };

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, currentStatus]);

  const runOcrOnFile = async (file: File) => {
    if (!file.type.startsWith("image/")) return;
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
      const extracted = data.text;
      if (extracted) {
        setInputText((prev) => (prev ? `${prev}\n${extracted}` : extracted));
      }
    } catch (err) {
      console.error("OCR Error:", err);
    } finally {
      setOcrLoading(false);
    }
  };

  const onPasteImages = (e: React.ClipboardEvent) => {
    const items = e.clipboardData?.items;
    if (!items?.length) return;
    for (let i = 0; i < items.length; i++) {
      const item = items[i];
      if (item.kind === "file" && item.type.startsWith("image/")) {
        e.preventDefault();
        const file = item.getAsFile();
        if (file) void runOcrOnFile(file);
        return;
      }
    }
  };

  const onDragOverInput = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const onDropInput = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    const file = e.dataTransfer?.files?.[0];
    if (file?.type.startsWith("image/")) void runOcrOnFile(file);
  };

  const applyJobRow = useCallback((job: { status?: string; result?: Record<string, any> }) => {
    const r = job.result || {};
    const newCoords = r.coordinates && typeof r.coordinates === "object"
      ? (r.coordinates as Record<string, [number, number]>)
      : null;
    const newPolygonOrder = r.polygon_order ?? null;
    const newCircles = r.circles ?? null;
    const newLines = r.lines ?? null;
    const newRays = r.rays ?? null;
    const newPhases = r.drawing_phases ?? null;
    const newVideoUrl = typeof r.video_url === "string" && r.video_url ? r.video_url : null;

    if (newCoords) setCoordinates(newCoords);
    if (newPolygonOrder) setPolygonOrder(newPolygonOrder);
    if (newCircles) setCircles(newCircles);
    if (newLines) setLines(newLines);
    if (newRays) setRays(newRays);
    if (newPhases) setDrawingPhases(newPhases);
    if (newVideoUrl) {
      setVideoUrl(newVideoUrl);
      setRenderingVideo(false);
    }

    if (sessionId && !sessionId.startsWith("temp-")) {
      const geoState: GeometryState = {
        coordinates: newCoords,
        polygonOrder: newPolygonOrder,
        circles: newCircles,
        lines: newLines,
        rays: newRays,
        drawingPhases: newPhases,
        videoUrl: newVideoUrl,
        activeJobId: activeJobId,
      };
      saveGeometryState(sessionId, geoState);
    }
  }, [sessionId, activeJobId]);

  const finishSolveFlow = useCallback(() => {
    clearSolvePoll();
    void mutateMessages();
    void mutateAssets();
    setCurrentStatus(null);
    setSolveLoading(false);
    setRenderingVideo(false);
    clearActiveJob(sessionId);
    try {
      solveWsRef.current?.close();
      solveWsRef.current = null;
    } catch { /* ignore */ }
  }, [sessionId, mutateMessages, mutateAssets, clearSolvePoll]);

  const attachToJob = useCallback(async (jobId: string) => {
    clearSolvePoll();
    setActiveJobId(jobId);
    saveActiveJob(sessionId, jobId);

    const runPollTick = async () => {
      pollAttemptsRef.current += 1;
      if (pollAttemptsRef.current > SOLVE_POLL_MAX_ATTEMPTS) {
        finishSolveFlow();
        return;
      }
      try {
        const res = await fetch(`${getApiBaseUrl()}/api/v1/solve/${jobId}`);
        if (!res.ok) return;
        const job = await res.json();
        applyJobRow(job);
        if (job.status === "success" || job.status === "error") {
          finishSolveFlow();
        } else {
          setCurrentStatus(job.status);
        }
      } catch { /* ignore */ }
    };

    clearSolvePoll();
    pollIntervalRef.current = setInterval(() => {
      void runPollTick();
    }, SOLVE_POLL_INTERVAL_MS);

    try {
      if (solveWsRef.current) {
        solveWsRef.current.close();
      }
      const ws = new WebSocket(`${getWsBaseUrl()}/ws/${jobId}`);
      solveWsRef.current = ws;
      
      ws.onmessage = (event) => {
        let wsData: any;
        try { wsData = JSON.parse(event.data); } catch { return; }

        if (wsData.status) {
          setCurrentStatus(wsData.status);
          if (wsData.status === "rendering" || wsData.status === "rendering_queued") {
            setRenderingVideo(true);
          }
        }
        if (wsData.status === "error") {
          finishSolveFlow();
          return;
        }
        if (wsData.result) {
          applyJobRow({ status: wsData.status, result: wsData.result });
        }
        if (wsData.status === "success") {
          finishSolveFlow();
        }
      };
    } catch (err) {
      console.error("WS error:", err);
    }
  }, [sessionId, clearSolvePoll, finishSolveFlow, applyJobRow]);

  const handleSolve = async () => {
    if (!inputText.trim() || !userSession?.access_token) return;
    setSolveLoading(true);
    setCurrentStatus("processing");
    
    const textPayload = inputText;
    const tempMsg: ChatMessage = {
      id: "temp-" + Date.now(),
      role: "user",
      type: "text",
      content: textPayload,
      timestamp: Date.now(),
    };
    
    await mutateMessages((prev) => [...(prev || []), tempMsg], { revalidate: false });
    setInputText("");

    try {
      const response = await fetch(`${getApiBaseUrl()}/api/v1/sessions/${sessionId}/solve`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${userSession.access_token}`,
        },
        body: JSON.stringify({ text: textPayload, request_video: requestVideo }),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = (await response.json()) as { job_id?: string };
      if (!data.job_id) throw new Error("Missing job_id");

      await attachToJob(data.job_id);
    } catch (err) {
      console.error(err);
      setCurrentStatus("error");
      setSolveLoading(false);
      void mutateMessages();
    }
  };

  const handleMouseDown = useCallback((type: 'sidebar' | 'main') => (e: React.MouseEvent) => {
    e.preventDefault();
    draggingType.current = type;
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
  }, []);

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!draggingType.current || !containerRef.current) return;
      
      const rect = containerRef.current.getBoundingClientRect();
      const x = e.clientX - rect.left;
      
      if (draggingType.current === 'sidebar' && !sidebarCollapsed) {
        const pct = (x / rect.width) * 100;
        setSplitPercent(Math.min(Math.max(pct, SPLIT_MIN_PCT), SPLIT_MAX_PCT));
      } else if (draggingType.current === 'main') {
        const sidebarWidth = sidebarCollapsed ? 52 : (rect.width * splitPercent) / 100;
        const remainingWidth = rect.width - sidebarWidth;
        const relativeX = x - sidebarWidth;
        const pct = (relativeX / remainingWidth) * 100;
        setMainSplitPercent(Math.min(Math.max(pct, MAIN_SPLIT_MIN_PCT), MAIN_SPLIT_MAX_PCT));
      }
    };
    const handleMouseUp = () => {
      draggingType.current = null;
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    };
    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", handleMouseUp);
    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
    };
  }, [sidebarCollapsed, splitPercent]);

  return (
    <div ref={containerRef} className="h-screen w-screen flex bg-[var(--background)] text-[var(--foreground)] overflow-hidden">
      <div
        className={`h-full min-w-0 flex flex-col shrink-0 border-r border-[var(--border)] ${sidebarCollapsed ? "w-[52px]" : ""}`}
        style={sidebarCollapsed ? undefined : { width: `${splitPercent}%` }}
      >
        <ChatSidebar
          compact={sidebarCollapsed}
          onCollapse={() => setSidebarCollapsed(true)}
          onExpand={() => setSidebarCollapsed(false)}
        />
      </div>

      {!sidebarCollapsed && (
        <div
          role="separator"
          onMouseDown={handleMouseDown('sidebar')}
          className="w-1 cursor-col-resize hover:bg-indigo-500/30 active:bg-indigo-500/50 transition-colors z-10 flex-shrink-0"
        />
      )}

      <div className="flex-1 flex flex-col min-w-0 bg-[var(--bg-secondary)]">
        <div className="flex-1 flex overflow-hidden">
          <div 
            className="flex flex-col border-r border-[var(--border)] min-w-0 bg-[var(--panel-bg)]"
            style={{ width: `${mainSplitPercent}%` }}
          >
            <div className="flex-1 overflow-y-auto p-4 space-y-6 scrollbar-thin">
              {historyLoading && messages.length === 0 && (
                <div className="flex flex-col items-center justify-center py-16 gap-3 text-zinc-500">
                  <Loader2 className="w-8 h-8 animate-spin text-indigo-500" />
                  <p className="text-xs font-medium uppercase tracking-widest">Đang tải hội thoại...</p>
                </div>
              )}

              {!historyLoading && messages.length === 0 && (
                <div className="h-full flex flex-col items-center justify-center text-center gap-4 opacity-50">
                  <Sparkles className="w-12 h-12 text-indigo-500/30" />
                  <div>
                    <p className="text-sm font-bold text-white">Bắt đầu bài toán của bạn</p>
                    <p className="text-xs text-zinc-600 mt-1 max-w-xs">
                      Nhập đề, dán ảnh đề bài (OCR tự chạy), hoặc kéo thả ảnh vào ô nhập.
                    </p>
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

            <div className="p-4 border-t border-[var(--border)] bg-[var(--panel-bg)]">
              <div className="max-w-3xl mx-auto space-y-3">
                <div className="flex items-center gap-2 px-1">
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
                  {ocrLoading && (
                    <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-indigo-500/10 border border-indigo-500/20 text-[10px] font-bold text-indigo-400 animate-pulse">
                      <Loader2 className="w-3 h-3 animate-spin" />
                      ĐANG QUÉT ẢNH...
                    </div>
                  )}
                </div>

                <div className="flex gap-3 items-stretch">
                  <div className="relative flex-1 min-w-0" onDragOver={onDragOverInput} onDrop={onDropInput}>
                    <textarea
                      value={inputText}
                      onChange={(e) => setInputText(e.target.value)}
                      placeholder="Nhập đề hoặc dán / kéo ảnh đề..."
                      rows={1}
                      onPaste={onPasteImages}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" && !e.shiftKey) {
                          e.preventDefault();
                          void handleSolve();
                        }
                      }}
                      className="w-full h-14 min-h-[3.5rem] max-h-14 resize-none overflow-y-auto bg-[var(--input-bg)] border border-[var(--border)] rounded-2xl px-4 py-3 text-sm text-[var(--foreground)] leading-snug focus:outline-none focus:border-indigo-500/50 transition-all"
                    />
                  </div>
                  <button
                    type="button"
                    onClick={handleSolve}
                    disabled={solveLoading || !inputText.trim()}
                    className="h-14 w-14 shrink-0 rounded-2xl bg-indigo-600 text-white flex items-center justify-center hover:bg-indigo-500 transition-all disabled:opacity-30 shadow-lg shadow-indigo-500/20"
                  >
                    {solveLoading ? (
                      <Loader2 className="w-6 h-6 animate-spin" />
                    ) : (
                      <Send className="w-6 h-6" />
                    )}
                  </button>
                </div>
              </div>
            </div>
          </div>

          <div
            role="separator"
            onMouseDown={handleMouseDown('main')}
            className="w-1 cursor-col-resize hover:bg-indigo-500/30 active:bg-indigo-500/50 transition-colors z-10 flex-shrink-0"
          />

          <div className="flex-1 flex flex-col bg-[var(--panel-bg)] overflow-hidden">
            <div className="flex-1 overflow-y-auto px-6 py-6 space-y-10 scrollbar-thin">
              <AnimatePresence mode="popLayout">
                {coordinates && (
                  <motion.div key="static" initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} className="space-y-4">
                    <div className="flex items-center gap-2">
                      <div className="w-1 h-3 bg-indigo-500 rounded-full" />
                      <span className="text-[10px] font-bold text-zinc-400 uppercase tracking-[0.2em]">Hình vẽ mô phỏng</span>
                    </div>
                    <div className="bg-[var(--card-bg)] rounded-3xl border border-[var(--border)] p-1 shadow-2xl overflow-hidden self-center relative group/canvas">
                      <StaticGeometryCanvas 
                        coordinates={coordinates} 
                        polygonOrder={polygonOrder || undefined}
                        circles={circles || undefined}
                        lines={lines || undefined}
                        rays={rays || undefined}
                        drawingPhases={drawingPhases || undefined}
                      />
                      {geometrySnapshots.length > 1 && (
                        <div className="absolute top-4 left-1/2 -translate-x-1/2 z-30 opacity-0 group-hover/canvas:opacity-100 transition-opacity">
                          <VersionSwitcher 
                            currentVersion={videoVersion}
                            totalVersions={geometrySnapshots.length}
                            onNext={handleNextVersion}
                            onPrev={handlePrevVersion}
                          />
                        </div>
                      )}
                    </div>
                  </motion.div>
                )}

                {(videoUrl || renderingVideo) && (
                  <motion.div key="video" initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} className="space-y-4">
                    <div className="flex items-center gap-2">
                      <div className="w-1 h-3 bg-purple-500 rounded-full" />
                      <span className="text-[10px] font-bold text-zinc-400 uppercase tracking-[0.2em]">
                        {videoUrl ? "🎬 Phim minh họa" : "🎨 Đang dựng hình..."}
                      </span>
                    </div>
                    <div className="bg-[var(--card-bg)] rounded-3xl border border-[var(--border)] p-1 shadow-2xl relative overflow-hidden group/video">
                      <AnimationPreview 
                        videoUrl={videoUrl || undefined} 
                        loading={renderingVideo} 
                        currentVersion={videoVersion}
                        totalVersions={geometrySnapshots.length}
                        onNext={handleNextVersion}
                        onPrev={handlePrevVersion}
                      />
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
