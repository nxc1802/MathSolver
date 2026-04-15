"use client";

import React, { useState, useEffect, useRef, useMemo } from "react";
import { useParams } from "next/navigation";
import { AnimatePresence, motion } from "framer-motion";
import { Film, Loader2 } from "lucide-react";
import useSWR, { useSWRConfig } from "swr";
import { useAuth } from "@/lib/auth-context";
import { getApiBaseUrl } from "@/lib/api-config";
import { messageFromApi } from "@/lib/chat-messages";
import type { ChatMessage } from "@/types/chat";

import ChatSidebar from "../../../components/layout/ChatSidebar";
import ChatInput from "../../../components/chat/ChatInput";
import ChatMessageList from "../../../components/chat/ChatMessageList";
import HeroWelcome from "../../../components/chat/HeroWelcome";
import OcrConfirmCard from "../../../components/chat/OcrConfirmCard";
import {
  type DraftImage,
  createDraftImage,
  revokeDraftImages,
  buildCombinedMessage,
} from "@/lib/chat-attachments";
import { preprocessImageForOcr } from "@/lib/image-prep";
import { postOcr, postOcrPreview } from "@/lib/ocr-api";
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

type OcrFlowState =
  | { status: "idle" }
  | {
      status: "ocr_loading";
      attachments: DraftImage[];
      userTextSnapshot: string;
    }
  | {
      status: "confirm";
      attachments: DraftImage[];
      userTextSnapshot: string;
      ocrParts: string[];
      combinedText: string;
    };

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
  const [pendingDraftImages, setPendingDraftImages] = useState<DraftImage[]>([]);
  const [ocrFlow, setOcrFlow] = useState<OcrFlowState>({ status: "idle" });
  const [confirmEditText, setConfirmEditText] = useState("");
  const [ocrFlowError, setOcrFlowError] = useState<string | null>(null);
  const [pendingQueue, setPendingQueue] = useState<{ id: string; text: string }[]>([]);
  const [queueNotice, setQueueNotice] = useState<string | null>(null);

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
  const [activeSnapshotJobId, setActiveSnapshotJobId] = useState<string | null>(null);
  const prevSnapshotsCountRef = useRef(0);

  // Job Hooks
  const { job, startSolve, startRenderVideo, resetJob } = useSolverJob(sessionId, userSession?.access_token);

  const geometrySnapshots = useMemo(() => {
    return messages?.filter((m) => m.role === "assistant" && m.type !== "error" && m.metadata?.coordinates) || [];
  }, [messages]);

  const isQueueFull = pendingQueue.length >= 5;
  const queueFullBlock = job.phase !== "idle" && isQueueFull;
  const ocrPreviewBlocking = ocrFlow.status !== "idle";

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
    setActiveSnapshotJobId(meta.job_id || meta.jobId || null);
  };

  // Restore cache on session change; reset composer attachments
  useEffect(() => {
    setPendingDraftImages((prev) => {
      revokeDraftImages(prev);
      return [];
    });
    setOcrFlow((f) => {
      if (f.status !== "idle") revokeDraftImages(f.attachments);
      return { status: "idle" };
    });
    setConfirmEditText("");
    setOcrFlowError(null);

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
    if (job.phase === "idle" && pendingQueue.length > 0) {
      const next = pendingQueue[0];
      setPendingQueue((prev) => {
        const n = prev.slice(1);
        if (!isTempSession) savePendingQueue(sessionId, n);
        return n;
      });
      startSolve(next.text);
    }
  }, [job.phase, pendingQueue, startSolve, sessionId, isTempSession]);

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
  }, [messages, job.phase, pendingQueue, ocrFlow.status]);

  const addDraftImages = (files: File[]) => {
    if (!files.length) return;
    setPendingDraftImages((prev) => [...prev, ...files.map(createDraftImage)]);
  };

  const removeDraftImage = (id: string) => {
    setPendingDraftImages((prev) => {
      const t = prev.find((d) => d.id === id);
      if (t) revokeDraftImages([t]);
      return prev.filter((d) => d.id !== id);
    });
  };

  const runOcrChain = async (
    attachments: DraftImage[],
    userTextSnapshot: string
  ): Promise<{ ocrParts: string[]; combinedText: string }> => {
    const parts: string[] = [];
    const token = userSession?.access_token;

    if (!isTempSession && sessionId) {
      let combinedText = "";
      for (let i = 0; i < attachments.length; i++) {
        const prep = await preprocessImageForOcr(attachments[i].file);
        const userMsg = i === 0 ? userTextSnapshot : null;
        const r = await postOcrPreview(sessionId, prep, userMsg, token);
        parts.push((r.ocr_text ?? "").trim());
        const block = (r.combined_draft ?? "").trim();
        if (i === 0) combinedText = block;
        else if (block) combinedText = combinedText ? `${combinedText}\n\n${block}` : block;
      }
      return { ocrParts: parts, combinedText };
    }

    for (const d of attachments) {
      const prep = await preprocessImageForOcr(d.file);
      const t = await postOcr(prep, token);
      parts.push(t);
    }
    return {
      ocrParts: parts,
      combinedText: buildCombinedMessage(userTextSnapshot, parts),
    };
  };

  const cancelOcrFlow = () => {
    if (ocrFlow.status === "ocr_loading" || ocrFlow.status === "confirm") {
      setPendingDraftImages(ocrFlow.attachments);
      setInputText(ocrFlow.userTextSnapshot);
    }
    setOcrFlow({ status: "idle" });
    setConfirmEditText("");
    setOcrFlowError(null);
  };

  const handleRetryOcr = async () => {
    if (ocrFlow.status !== "confirm") return;
    const snapshot = ocrFlow;
    const { attachments, userTextSnapshot } = snapshot;
    setOcrFlowError(null);
    setOcrFlow({ status: "ocr_loading", attachments, userTextSnapshot });
    try {
      const { ocrParts, combinedText } = await runOcrChain(attachments, userTextSnapshot);
      setOcrFlow({
        status: "confirm",
        attachments,
        userTextSnapshot,
        ocrParts,
        combinedText,
      });
      setConfirmEditText(combinedText);
    } catch (e) {
      setOcrFlowError(e instanceof Error ? e.message : "OCR thất bại");
      setOcrFlow({
        status: "confirm",
        attachments: snapshot.attachments,
        userTextSnapshot: snapshot.userTextSnapshot,
        ocrParts: snapshot.ocrParts,
        combinedText: snapshot.combinedText,
      });
    }
  };

  const confirmOcrAndSolve = async () => {
    if (ocrFlow.status !== "confirm") return;
    const text = confirmEditText.trim();
    if (!text) return;
    const attachments = ocrFlow.attachments;
    revokeDraftImages(attachments);
    setOcrFlow({ status: "idle" });
    setConfirmEditText("");
    setOcrFlowError(null);
    await mutateMessages(
      (prev) => [
        ...(prev || []),
        {
          id: "temp",
          role: "user",
          type: "text",
          content: text,
          timestamp: Date.now(),
        },
      ],
      { revalidate: false }
    );
    // API.md: after ocr_preview + user edit, send text only — omit image_url to avoid double OCR.
    startSolve(text, false, undefined);
  };

  const handleComposerSend = async (text?: string) => {
    if (ocrFlow.status !== "idle") return;

    const userSnap = text !== undefined ? text : inputText;
    const payloadTrim = userSnap.trim();
    const drafts = [...pendingDraftImages];
    const hasImages = drafts.length > 0;
    if (!payloadTrim && !hasImages) return;

    if (job.phase !== "idle" && text === undefined) {
      if (hasImages) {
        setQueueNotice(
          "Không thể xếp hàng kèm ảnh. Đợi xử lý xong hoặc chỉ gửi nội dung chữ."
        );
        window.setTimeout(() => setQueueNotice(null), 4500);
        return;
      }
      if (pendingQueue.length >= 5) {
        setQueueNotice("Hàng đợi tối đa 5 câu khi đang xử lý. Đợi xong rồi gửi thêm.");
        window.setTimeout(() => setQueueNotice(null), 4500);
        return;
      }
      setPendingQueue((prev) => {
        const newQ = [...prev, { id: "q-" + Date.now(), text: payloadTrim }];
        if (!isTempSession) savePendingQueue(sessionId, newQ);
        return newQ;
      });
      setInputText("");
      return;
    }

    if (hasImages) {
      setOcrFlowError(null);
      setOcrFlow({
        status: "ocr_loading",
        attachments: drafts,
        userTextSnapshot: userSnap,
      });
      setPendingDraftImages([]);
      if (text === undefined) setInputText("");
      try {
        const { ocrParts, combinedText } = await runOcrChain(drafts, userSnap);
        setOcrFlow({
          status: "confirm",
          attachments: drafts,
          userTextSnapshot: userSnap,
          ocrParts,
          combinedText,
        });
        setConfirmEditText(combinedText);
      } catch (e) {
        setOcrFlowError(e instanceof Error ? e.message : "OCR thất bại");
        setPendingDraftImages(drafts);
        setInputText(userSnap);
        setOcrFlow({ status: "idle" });
      }
      return;
    }

    if (text === undefined) setInputText("");
    await mutateMessages(
      (prev) => [
        ...(prev || []),
        {
          id: "temp",
          role: "user",
          type: "text",
          content: payloadTrim,
          timestamp: Date.now(),
        },
      ],
      { revalidate: false }
    );
    startSolve(payloadTrim);
  };

  const editQueued = (id: string, text: string) => {
    setPendingQueue((prev) => {
      const n = prev.filter((q) => q.id !== id);
      if (!isTempSession) savePendingQueue(sessionId, n);
      return n;
    });
    setInputText(text);
  };
  const removeQueued = (id: string) => {
    setPendingQueue((prev) => {
      const n = prev.filter((q) => q.id !== id);
      if (!isTempSession) savePendingQueue(sessionId, n);
      return n;
    });
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
            {messages.length === 0 &&
            pendingQueue.length === 0 &&
            !historyLoadingRaw &&
            ocrFlow.status === "idle" ? (
              <HeroWelcome onSuggestionClick={(text) => {
                setInputText(text);
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
            {queueNotice && (
              <div className="px-4 pt-2 max-w-3xl mx-auto">
                <p className="text-xs text-amber-400/90 bg-amber-500/10 border border-amber-500/20 rounded-xl px-3 py-2">
                  {queueNotice}
                </p>
              </div>
            )}
            {ocrFlow.status !== "idle" && (
              <div className="px-4 pb-2 shrink-0">
                <OcrConfirmCard
                  previewUrls={ocrFlow.attachments.map((a) => a.previewUrl)}
                  combinedText={
                    ocrFlow.status === "confirm" ? confirmEditText : ""
                  }
                  onChangeCombined={setConfirmEditText}
                  ocrLoading={ocrFlow.status === "ocr_loading"}
                  error={ocrFlowError}
                  onConfirm={confirmOcrAndSolve}
                  onCancel={cancelOcrFlow}
                  onRetryOcr={handleRetryOcr}
                />
              </div>
            )}
            <ChatInput
              inputText={inputText}
              setInputText={setInputText}
              queueFullBlock={queueFullBlock}
              solveLoading={job.phase !== "idle"}
              ocrLoading={ocrFlow.status === "ocr_loading"}
              ocrPreviewBlocking={ocrPreviewBlocking}
              pendingImages={pendingDraftImages}
              onRemoveImage={removeDraftImage}
              onAddImageFiles={addDraftImages}
              onSolve={handleComposerSend}
            />
          </div>
          <div role="separator" onMouseDown={() => { draggingType.current = 'main'; document.body.style.cursor = "col-resize"; }} className="w-1 cursor-col-resize hover:bg-indigo-500/30 z-10 shrink-0" />

          <div className="flex-1 flex flex-col bg-black/40 overflow-hidden relative">
            <div className="flex-1 flex flex-col p-6 space-y-6 overflow-hidden">
              <AnimatePresence mode="popLayout">
                {coordinates && (
                  <motion.div key="static" initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} className="flex-1 flex flex-col min-h-0 space-y-3">
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-3">
                        <span className="text-[10px] font-bold text-zinc-400 uppercase tracking-[0.2em]">HÌNH VẼ MÔ PHỎNG</span>
                        
                        {coordinates && !videoUrl && (
                          <button
                            onClick={() => startRenderVideo(activeSnapshotJobId || undefined)}
                            disabled={job.phase === 'rendering' || job.phase === 'rendering_queued'}
                            className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-[9px] font-bold text-indigo-400 hover:bg-indigo-500/20 transition-all disabled:opacity-50"
                          >
                            {job.phase === 'rendering' || job.phase === 'rendering_queued' ? (
                              <Loader2 className="w-3 h-3 animate-spin" />
                            ) : (
                              <Film className="w-3 h-3" />
                            )}
                            TẠO ANIMATION
                          </button>
                        )}
                      </div>

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
                     <div className="bg-zinc-900 border border-white/5 rounded-2xl p-2 flex-1 min-h-0 relative overflow-hidden shadow-2xl">
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
