"use client";

import React, { useState, useEffect, useRef, useMemo } from "react";
import { useParams } from "next/navigation";
import { AnimatePresence, motion } from "framer-motion";
import useSWR, { useSWRConfig } from "swr";
import { useAuth } from "@/lib/auth-context";
import { getApiBaseUrl } from "@/lib/api-config";
import { messageFromApi } from "@/lib/chat-messages";
import type { ChatMessage } from "@/types/chat";

import ChatSidebar from "../../../components/layout/ChatSidebar";
import ChatInput from "../../../components/chat/ChatInput";
import ChatMessageList from "../../../components/chat/ChatMessageList";
import HeroWelcome from "../../../components/chat/HeroWelcome";
import StaticGeometryCanvas from "../../../components/geometry/StaticGeometryCanvas";
import Interactive3DCanvas from "../../../components/geometry/Interactive3DCanvas";
import AnimationPreview from "../../../components/media/AnimationPreview";
import VersionSwitcher from "../../../components/geometry/VersionSwitcher";

import { useSolverJob } from "@/hooks/useSolverJob";
import { loadGeometryState, saveGeometryState, type GeometryState } from "@/lib/session-geometry-cache";
import { getPendingQueue, savePendingQueue } from "@/lib/job-tracker";
import {
  readSplitPercent, writeSplitPercent,
  readMainSplitPercent, writeMainSplitPercent,
  readSidebarCollapsed, writeSidebarCollapsed,
  SPLIT_MIN_PCT, SPLIT_MAX_PCT,
  MAIN_SPLIT_MIN_PCT, MAIN_SPLIT_MAX_PCT,
} from "@/lib/session-ui-storage";

async function fetchChatMessages([url, token]: [string, string]): Promise<ChatMessage[]> {
  const res = await fetch(url, { headers: { Authorization: `Bearer ${token}` }});
  if (!res.ok) throw new Error("Failed to fetch messages");
  return (await res.json()).map(messageFromApi);
}

async function fetchSessionAssets([url, token]: [string, string]): Promise<any[]> {
  const res = await fetch(url, { headers: { Authorization: `Bearer ${token}` }});
  if (!res.ok) return [];
  return res.json();
}

export default function ChatSessionPage() {
  const params = useParams();
  const sessionId = params?.sessionId as string;
  const isTempSession = sessionId?.startsWith("temp-");
  const { session: userSession } = useAuth();
  const { mutate: globalMutate } = useSWRConfig();

  const messagesKey = userSession?.access_token && !isTempSession 
    ? [`${getApiBaseUrl()}/api/v1/sessions/${sessionId}/messages`, userSession.access_token] as const : null;
  const assetsKey = userSession?.access_token && !isTempSession 
    ? [`${getApiBaseUrl()}/api/v1/sessions/${sessionId}/assets`, userSession.access_token] as const : null;

  const { data: messages = [], isLoading: historyLoadingRaw, mutate: mutateMessages } = useSWR(
    messagesKey, fetchChatMessages, { revalidateOnFocus: false, dedupingInterval: 2000 }
  );
  const { data: sessionAssets = [], mutate: mutateAssets } = useSWR(assetsKey, fetchSessionAssets, { revalidateOnFocus: false });

  const [inputText, setInputText] = useState("");
  const [requestVideo, setRequestVideo] = useState(false);
  const [ocrLoading, setOcrLoading] = useState(false);
  const [pendingQueue, setPendingQueue] = useState<{ id: string; text: string }[]>([]);

  // UI States
  const [splitPercent, setSplitPercent] = useState(14.3);
  const [mainSplitPercent, setMainSplitPercent] = useState(50);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [uiHydrated, setUiHydrated] = useState(false);
  const draggingType = useRef<'sidebar' | 'main' | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Geometry Cache States
  const [coordinates, setCoordinates] = useState<any>(null);
  const [is3d, setIs3d] = useState(false);
  const [polygonOrder, setPolygonOrder] = useState<string[] | null>(null);
  const [drawingPhases, setDrawingPhases] = useState<any[] | null>(null);
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const [videoVersion, setVideoVersion] = useState(1);
  const prevSnapshotsCountRef = useRef(0);

  // Job Hooks
  const { job, startSolve, resetJob } = useSolverJob(sessionId, userSession?.access_token);

  const geometrySnapshots = useMemo(() => {
    return messages?.filter((m) => m.role === "assistant" && m.type !== "error" && m.metadata?.coordinates) || [];
  }, [messages]);

  const userQueryCount = useMemo(() => {
    return messages.filter((m) => m.role === "user").length + pendingQueue.length;
  }, [messages, pendingQueue]);
  const isLimitReached = userQueryCount >= 5;

  const applyGeometryFromSnapshot = (meta: any) => {
    if (!meta) return;
    setCoordinates(meta.coordinates || null);
    
    // 3D detection: trust backend flag, fallback to coordinates check
    const backendIs3d = meta.is_3d !== undefined ? meta.is_3d : meta.is3d;
    const coords = meta.coordinates || {};
    const hasZ = Object.values(coords).some(
      (c: any) => Array.isArray(c) && c.length === 3 && c[2] !== 0
    );
    
    setIs3d(backendIs3d ?? hasZ);
    setPolygonOrder(meta.polygon_order || meta.polygonOrder || null);
    setDrawingPhases(meta.drawing_phases || meta.drawingPhases || null);
    setVideoUrl(meta.video_url || meta.videoUrl || null);
  };

  // Restore cache on session change
  useEffect(() => {
    if (isTempSession) return;
    const cached = loadGeometryState(sessionId);
    if (cached) {
      applyGeometryFromSnapshot(cached);
    }
    setPendingQueue(getPendingQueue(sessionId));
  }, [sessionId, isTempSession]);

  // Sync latest snapshots
  useEffect(() => {
    if (geometrySnapshots.length > prevSnapshotsCountRef.current) {
      setVideoVersion(geometrySnapshots.length);
      applyGeometryFromSnapshot(geometrySnapshots[geometrySnapshots.length - 1].metadata);
    }
    prevSnapshotsCountRef.current = geometrySnapshots.length;
  }, [geometrySnapshots]);

  useEffect(() => {
    if (job.phase === 'success' || job.phase === 'error') {
      void mutateMessages();
      void mutateAssets();
      if (job.result) {
        applyGeometryFromSnapshot(job.result);
        if (!isTempSession) {
          saveGeometryState(sessionId, { 
            coordinates: job.result.coordinates, 
            polygonOrder: job.result.polygon_order, 
            drawingPhases: job.result.drawing_phases, 
            is_3d: job.result.is_3d, 
            videoUrl: job.result.video_url 
          } as GeometryState);
        }
      }
      setTimeout(resetJob, 1000);
    }
  }, [job.phase, job.result, mutateMessages, mutateAssets, resetJob, sessionId, isTempSession]);

  // Queue Processing
  useEffect(() => {
    if (job.phase === 'idle' && pendingQueue.length > 0) {
      const next = pendingQueue[0];
      setPendingQueue(prev => prev.slice(1));
      startSolve(next.text, requestVideo);
    }
  }, [job.phase, pendingQueue, startSolve, requestVideo]);

  // Layout dragging
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!draggingType.current || !containerRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      const x = e.clientX - rect.left;
      if (draggingType.current === 'sidebar' && !sidebarCollapsed) {
        setSplitPercent(Math.min(Math.max((x / rect.width) * 100, SPLIT_MIN_PCT), SPLIT_MAX_PCT));
      } else if (draggingType.current === 'main') {
        const sidebarWidth = sidebarCollapsed ? 52 : (rect.width * splitPercent) / 100;
        const relativeX = x - sidebarWidth;
        setMainSplitPercent(Math.min(Math.max((relativeX / (rect.width - sidebarWidth)) * 100, MAIN_SPLIT_MIN_PCT), MAIN_SPLIT_MAX_PCT));
      }
    };
    const handleMouseUp = () => { draggingType.current = null; document.body.style.cursor = ""; };
    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", handleMouseUp);
    return () => { window.removeEventListener("mousemove", handleMouseMove); window.removeEventListener("mouseup", handleMouseUp); };
  }, [sidebarCollapsed, splitPercent]);

  useEffect(() => {
    setSplitPercent(readSplitPercent(14.3));
    setMainSplitPercent(readMainSplitPercent(50));
    setSidebarCollapsed(readSidebarCollapsed());
    setUiHydrated(true);
  }, []);

  useEffect(() => {
    if (uiHydrated) { writeSplitPercent(splitPercent); writeMainSplitPercent(mainSplitPercent); writeSidebarCollapsed(sidebarCollapsed); }
  }, [splitPercent, mainSplitPercent, sidebarCollapsed, uiHydrated]);

  // Auto-scroll to bottom
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, job.phase, pendingQueue]);

  const handleSolve = async (text?: string) => {
    const payload = text || inputText;
    if (!payload.trim() || isLimitReached) return;
    
    if (job.phase !== 'idle' && !text) {
      setPendingQueue(prev => {
        const newQ = [...prev, { id: "q-" + Date.now(), text: payload }];
        if (!isTempSession) savePendingQueue(sessionId, newQ);
        return newQ;
      });
      setInputText("");
      return;
    }
    
    if (!text) setInputText("");
    await mutateMessages((prev) => [...(prev || []), { id: "temp", role: "user", type: "text", content: payload, timestamp: Date.now() }], { revalidate: false });
    startSolve(payload, requestVideo);
  };

  const handleOcr = async (file: File) => {
    setOcrLoading(true);
    const formData = new FormData(); formData.append("file", file);
    try {
      const res = await fetch(`${getApiBaseUrl()}/api/v1/ocr`, { method: "POST", body: formData });
      const data = await res.json();
      if (data.text) setInputText(prev => prev ? `${prev}\n${data.text}` : data.text);
    } catch { /* ignore */ } finally { setOcrLoading(false); }
  };

  const editQueued = (id: string, text: string) => {
    setPendingQueue(prev => prev.filter(q => q.id !== id));
    setInputText(text);
  };
  const removeQueued = (id: string) => {
    setPendingQueue(prev => prev.filter(q => q.id !== id));
  };

  return (
    <div ref={containerRef} className="h-[100dvh] w-screen flex bg-[#0a0a0f] text-[var(--foreground)] overflow-hidden">
      <div className={`h-full flex flex-col shrink-0 border-r border-white/5 ${sidebarCollapsed ? "w-[52px]" : ""}`} style={sidebarCollapsed ? undefined : { width: `${splitPercent}%` }}>
        <ChatSidebar compact={sidebarCollapsed} onCollapse={() => setSidebarCollapsed(true)} onExpand={() => setSidebarCollapsed(false)} />
      </div>
      {!sidebarCollapsed && <div role="separator" onMouseDown={() => { draggingType.current = 'sidebar'; document.body.style.cursor = "col-resize"; }} className="w-1 cursor-col-resize hover:bg-indigo-500/30 z-10 shrink-0" />}

      <div className="flex-1 flex flex-col min-w-0 bg-[var(--bg-secondary)]">
        <div className="flex-1 flex overflow-hidden">
          <div className="flex flex-col border-r border-white/5 min-w-0 bg-[var(--panel-bg)]" style={{ width: `${mainSplitPercent}%` }}>
            {messages.length === 0 && pendingQueue.length === 0 && !historyLoadingRaw ? (
              <HeroWelcome onSuggestionClick={(text) => {
                setInputText(text);
                // Optionally auto-solve: handleSolve(text);
              }} />
            ) : (
              <ChatMessageList
                messages={messages}
                historyLoading={historyLoadingRaw && !isTempSession}
                isTempSession={isTempSession}
                currentStatus={job.phase !== 'idle' && job.phase !== 'success' ? job.message : null}
                pendingQueue={pendingQueue}
                editQueued={editQueued}
                removeQueued={removeQueued}
                messagesEndRef={messagesEndRef}
              />
            )}
            <ChatInput
              inputText={inputText}
              setInputText={setInputText}
              requestVideo={requestVideo}
              setRequestVideo={setRequestVideo}
              isLimitReached={isLimitReached}
              solveLoading={job.phase !== 'idle'}
              ocrLoading={ocrLoading}
              onSolve={handleSolve}
              onRunOcr={handleOcr}
            />
          </div>
          <div role="separator" onMouseDown={() => { draggingType.current = 'main'; document.body.style.cursor = "col-resize"; }} className="w-1 cursor-col-resize hover:bg-indigo-500/30 z-10 shrink-0" />

          <div className="flex-1 flex flex-col bg-black/40 overflow-hidden relative">
            <div className="flex-1 flex flex-col p-6 space-y-6 overflow-hidden">
              <AnimatePresence mode="popLayout">
                {coordinates && (
                  <motion.div key="static" initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} className="flex-1 flex flex-col min-h-0 space-y-3">
                     <div className="flex items-center justify-between gap-2">
                       <span className="text-[10px] font-bold text-zinc-400 uppercase tracking-[0.2em]">HÌNH VẼ MÔ PHỎNG</span>
                       <VersionSwitcher currentVersion={videoVersion} totalVersions={geometrySnapshots.length} onPrev={() => {
                         if (videoVersion > 1) {
                           setVideoVersion(v => v - 1);
                           applyGeometryFromSnapshot(geometrySnapshots[videoVersion - 2].metadata);
                         }
                       }} onNext={() => {
                         if (videoVersion < geometrySnapshots.length) {
                           setVideoVersion(v => v + 1);
                           applyGeometryFromSnapshot(geometrySnapshots[videoVersion].metadata);
                         }
                       }} />
                     </div>
                     <div className="bg-zinc-900 border border-white/5 rounded-2xl p-2 flex-1 min-h-0 flex items-center justify-center relative overflow-hidden shadow-2xl">
                       {is3d ? (
                         <Interactive3DCanvas coordinates={coordinates} drawingPhases={drawingPhases || []} />
                       ) : (
                         <StaticGeometryCanvas coordinates={coordinates} polygonOrder={polygonOrder || []} drawingPhases={drawingPhases || []} circles={[]} lines={[]} rays={[]} />
                       )}
                     </div>
                  </motion.div>
                )}
                {(videoUrl || job.phase === 'rendering' || job.phase === 'rendering_queued') && (
                  <motion.div key="animation" initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} className="flex-1 flex flex-col min-h-0 space-y-3">
                     <span className="text-[10px] font-bold text-zinc-400 uppercase tracking-[0.2em]">ANIMATION MANIM</span>
                     <AnimationPreview videoUrl={videoUrl || undefined} loading={job.phase === 'rendering' || job.phase === 'rendering_queued'} />
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
