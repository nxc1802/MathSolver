"use client";

import React, { useState, useEffect, useCallback, useRef, useMemo } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { useParams } from "next/navigation";
import { Send, Sparkles, Loader2, Film, Bot, Maximize2, Trash2, Check, X, Pencil } from "lucide-react";

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
  savePendingQueue,
  getPendingQueue,
  clearPendingQueue,
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
  // --- 1. Params & Context ---
  const params = useParams();
  const sessionId = params?.sessionId as string;
  const { session: userSession } = useAuth();
  const { mutate: globalMutate } = useSWRConfig();
  const isTempSession = sessionId?.startsWith("temp-");

  // --- 2. Keys & SWR ---
  const messagesKey = userSession?.access_token && sessionId 
    ? [`${getApiBaseUrl()}/api/v1/sessions/${sessionId}/messages`, userSession.access_token] as const 
    : null;

  const assetsKey = userSession?.access_token && sessionId 
    ? [`${getApiBaseUrl()}/api/v1/sessions/${sessionId}/assets`, userSession.access_token] as const 
    : null;

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

  // --- 3. State ---
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
  const [pendingQueue, setPendingQueue] = useState<{ id: string; text: string }[]>([]);

  const [splitPercent, setSplitPercent] = useState(14.3);
  const [mainSplitPercent, setMainSplitPercent] = useState(50);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [uiHydrated, setUiHydrated] = useState(false);

  // --- 4. Refs ---
  const draggingType = useRef<'sidebar' | 'main' | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const pollAttemptsRef = useRef(0);
  const solveWsRef = useRef<WebSocket | null>(null);
  const isProcessingRef = useRef(false);
  const prevSessionIdRef = useRef<string | null>(null);
  const prevSnapshotsCountRef = useRef(0);

  // --- 5. Memos ---
  const userQueryCount = useMemo(() => {
    const historicalUsers = messages.filter((m) => m.role === "user").length;
    return historicalUsers + pendingQueue.length;
  }, [messages, pendingQueue]);

  const isLimitReached = userQueryCount >= 5;

  const geometrySnapshots = useMemo(() => {
    return [...messages]
      .filter((m) => m.role === "assistant" && m.type !== "error" && m.metadata?.coordinates);
  }, [messages]);

  const statusLabels: Record<string, string> = {
    processing: "🔄 Đang xử lý bài toán...",
    solving: "🧮 Đang giải hệ phương trình...",
    rendering_queued: "🎬 Đã gửi yêu cầu render video...",
    rendering: "🎬 Đang dựng animation Manim...",
    success: "✅ Hoàn thành!",
    error: "❌ Có lỗi xảy ra.",
  };

  // --- 6. Callbacks ---
  const clearSolvePoll = useCallback(() => {
    if (pollIntervalRef.current !== null) {
      clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }
    pollAttemptsRef.current = 0;
  }, []);

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
    isProcessingRef.current = false;
    setRenderingVideo(false);
    clearActiveJob(sessionId);
    clearPendingQueue(sessionId);
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

  const attachToJobWithLoading = useCallback(async (jobId: string) => {
    isProcessingRef.current = true;
    setSolveLoading(true);
    return attachToJob(jobId);
  }, [attachToJob]);

  const handleSolve = async (input?: string | React.MouseEvent | React.KeyboardEvent) => {
    const isQueued = typeof input === "string";
    const textToUse = isQueued ? input : inputText;
    
    if (!textToUse.trim() || !userSession?.access_token || isLimitReached) return;

    if (isProcessingRef.current && !isQueued) {
      setPendingQueue((prev) => [...prev, { id: "q-" + Date.now(), text: textToUse }]);
      setInputText("");
      return;
    }

    isProcessingRef.current = true;
    setSolveLoading(true);
    setCurrentStatus("processing");
    
    const textPayload = textToUse;
    const tempMsg: ChatMessage = {
      id: "temp-" + Date.now(),
      role: "user",
      type: "text",
      content: textPayload,
      timestamp: Date.now(),
    };
    
    await mutateMessages((prev) => [...(prev || []), tempMsg], { revalidate: false });
    if (!isQueued) setInputText("");

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

      // Once job is sent to BE, we can clear this item from our local pending queue 
      // (if it was from the queue) or just proceed. 
      // In handleSolve, the item is already removed from pendingQueue state by the useEffect 
      // that triggers handleSolve(next.text).
      
      await attachToJob(data.job_id);
    } catch (err) {
      console.error(err);
      setCurrentStatus("error");
      setSolveLoading(false);
      void mutateMessages();
    }
  };

  const removeQueued = (id: string) => {
    setPendingQueue((prev) => {
      const next = prev.filter((q) => q.id !== id);
      savePendingQueue(sessionId, next);
      return next;
    });
  };

  const editQueued = (id: string, text: string) => {
    removeQueued(id);
    setInputText(text);
  };

  const handleMouseDown = useCallback((type: 'sidebar' | 'main') => (e: React.MouseEvent) => {
    e.preventDefault();
    draggingType.current = type;
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
  }, []);

  const handleNextVersion = () => {
    if (videoVersion < geometrySnapshots.length) {
      setVideoVersion((v) => v + 1);
    }
  };

  const handlePrevVersion = () => {
    if (videoVersion > 1) {
      setVideoVersion((v) => v - 1);
    }
  };

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

  // --- 7. Effects ---
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

  useEffect(() => () => clearSolvePoll(), [clearSolvePoll]);

  useEffect(() => {
    if (geometrySnapshots.length > 0) {
      const safeVersion = Math.min(Math.max(videoVersion, 1), geometrySnapshots.length);
      setGeometryFromSnapshot(geometrySnapshots[safeVersion - 1]);
    } else {
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
    if (geometrySnapshots.length > prevSnapshotsCountRef.current) {
      setVideoVersion(geometrySnapshots.length);
    }
    prevSnapshotsCountRef.current = geometrySnapshots.length;
  }, [geometrySnapshots.length]);

  useEffect(() => {
    if (sessionAssets.length > 0) {
      if (!currentStatus && !videoUrl) {
        setVideoUrl(sessionAssets[0].public_url);
      }
    }
  }, [sessionAssets.length, currentStatus, !!videoUrl]);

  useEffect(() => {
    if (!sessionId || sessionId === prevSessionIdRef.current) return;
    prevSessionIdRef.current = sessionId;
    prevSnapshotsCountRef.current = 0; // CRITICAL: Reset snapshot tracking for new session
    setCurrentStatus(null);
    setVideoVersion(1);
    
    // Reset processing state on switch unless specialized below
    isProcessingRef.current = false;
    setSolveLoading(false);

    if (sessionId.startsWith("temp-")) {
      setCoordinates(null);
      setPolygonOrder(null);
      setCircles(null);
      setLines(null);
      setRays(null);
      setDrawingPhases(null);
      setVideoUrl(null);
      setActiveJobId(null);
      setPendingQueue([]);
      return;
    }

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
      setCoordinates(null);
      setPolygonOrder(null);
      setCircles(null);
      setLines(null);
      setRays(null);
      setDrawingPhases(null);
      setVideoUrl(null);
      setActiveJobId(null);
    }

    // Restore pending queue
    const savedQueue = getPendingQueue(sessionId);
    setPendingQueue(savedQueue);

    const activeJobIdForSession = getActiveJob(sessionId);
    if (activeJobIdForSession) {
      void attachToJobWithLoading(activeJobIdForSession);
    }
  }, [sessionId, attachToJobWithLoading]);

  useEffect(() => {
    if (!solveLoading && pendingQueue.length > 0) {
      const next = pendingQueue[0];
      setPendingQueue((prev) => {
        const remaining = prev.slice(1);
        savePendingQueue(sessionId, remaining);
        return remaining;
      });
      void handleSolve(next.text);
    }
  }, [solveLoading, pendingQueue, sessionId]);

  // Sync queue to storage on change (redundant but safe)
  useEffect(() => {
    if (sessionId && !sessionId.startsWith("temp-")) {
      savePendingQueue(sessionId, pendingQueue);
    }
  }, [pendingQueue, sessionId]);

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

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length, currentStatus, pendingQueue.length]);

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
              {historyLoading && messages.length === 0 && !isTempSession && (
                <div className="flex flex-col items-center justify-center py-16 gap-3 text-zinc-500 animate-in fade-in duration-700 delay-500">
                  <Loader2 className="w-8 h-8 animate-spin text-indigo-500" />
                  <p className="text-xs font-medium uppercase tracking-widest">Đang tải hội thoại...</p>
                </div>
              )}

              {((!historyLoading && messages.length === 0) || isTempSession) && (
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
                {pendingQueue.map((q, idx) => (
                  <motion.div
                    key={q.id}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, scale: 0.95 }}
                    className="flex gap-4"
                  >
                    <div className="w-9 h-9 rounded-xl bg-zinc-800 flex items-center justify-center flex-shrink-0">
                      <div className="text-[10px] font-bold text-zinc-500">{idx + 1}</div>
                    </div>
                    <div className="flex-1 max-w-2xl bg-zinc-900/40 border border-white/5 rounded-2xl px-5 py-4 flex items-center justify-between group">
                      <div className="flex flex-col gap-1">
                        <span className="text-[10px] font-bold text-indigo-400 uppercase tracking-widest">Hàng đợi (Queued)</span>
                        <p className="text-sm text-zinc-400 line-clamp-1 italic">{q.text}</p>
                      </div>
                      <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                        <button
                          onClick={() => editQueued(q.id, q.text)}
                          className="p-1.5 hover:bg-white/5 rounded-lg text-zinc-500 hover:text-white transition-colors"
                          title="Sửa"
                        >
                          <Pencil className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => removeQueued(q.id)}
                          className="p-1.5 hover:bg-red-500/10 rounded-lg text-zinc-500 hover:text-red-400 transition-colors"
                          title="Hủy"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  </motion.div>
                ))}
              </AnimatePresence>

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
                      placeholder={isLimitReached ? "Bạn đã đạt giới hạn 5 câu hỏi cho phiên này." : "Nhập đề hoặc dán / kéo ảnh đề..."}
                      disabled={isLimitReached}
                      rows={1}
                      onPaste={onPasteImages}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" && !e.shiftKey && !isLimitReached) {
                          e.preventDefault();
                          void handleSolve();
                        }
                      }}
                      className={`w-full h-14 min-h-[3.5rem] max-h-14 resize-none overflow-y-auto bg-[var(--input-bg)] border border-[var(--border)] rounded-2xl px-4 py-3 text-sm text-[var(--foreground)] leading-snug focus:outline-none focus:border-indigo-500/50 transition-all ${isLimitReached ? "opacity-50 cursor-not-allowed" : ""}`}
                    />
                  </div>
                  <button
                    type="button"
                    onClick={handleSolve}
                    disabled={isLimitReached || !inputText.trim()}
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
                    <div className="flex items-center justify-between gap-2">
                       <div className="flex items-center gap-2">
                         <div className="w-1 h-3 bg-indigo-500 rounded-full" />
                         <span className="text-[10px] font-bold text-zinc-400 uppercase tracking-[0.2em]">
                           HÌNH VẼ MÔ PHỎNG {geometrySnapshots.length > 1 ? `(VERSION ${videoVersion}/${geometrySnapshots.length})` : ""}
                         </span>
                       </div>
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
                        <div className="absolute top-4 left-1/2 -translate-x-1/2 z-30">
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
                        {videoUrl ? `🎬 Phim minh họa (VERSION ${videoVersion}/${geometrySnapshots.length})` : "🎨 Đang dựng hình..."}
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
              </AnimatePresence>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
