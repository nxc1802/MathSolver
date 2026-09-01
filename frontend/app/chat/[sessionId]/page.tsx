"use client";

import React, { useState, useEffect, useRef, useMemo } from "react";
import { useParams } from "next/navigation";
import { AnimatePresence, motion } from "framer-motion";
import { Film } from "lucide-react";
import useSWR from "swr";
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
import {
  loadGeometryState,
  saveGeometryState,
  type GeometryState,
} from "@/lib/session-geometry-cache";
import {
  pickCanvasMode,
  projectCoordinates2D,
  normalizeCoordinates3D,
  logGeometryDebug,
  logGeometryBeHandoff,
  detectGeometryInconsistency,
} from "@/lib/geometry-display";
import { getPendingQueue, savePendingQueue } from "@/lib/job-tracker";
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

async function fetchChatMessages([url, token]: [string, string]): Promise<ChatMessage[]> {
  const res = await fetch(url, { headers: { Authorization: `Bearer ${token}` } });
  if (!res.ok) throw new Error("Failed to fetch messages");
  return (await res.json()).map(messageFromApi);
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

  const messagesKey =
    userSession?.access_token && !isTempSession
      ? ([
          `${getApiBaseUrl()}/api/v1/sessions/${sessionId}/messages`,
          userSession.access_token,
        ] as const)
      : null;

  const {
    data: messages = [],
    isLoading: historyLoadingRaw,
    mutate: mutateMessages,
  } = useSWR(messagesKey, fetchChatMessages, {
    revalidateOnFocus: false,
    dedupingInterval: 2000,
  });

  const [inputText, setInputText] = useState("");
  const [pendingDraftImages, setPendingDraftImages] = useState<DraftImage[]>([]);
  const [ocrFlow, setOcrFlow] = useState<OcrFlowState>({ status: "idle" });
  const [confirmEditText, setConfirmEditText] = useState("");
  const [ocrFlowError, setOcrFlowError] = useState<string | null>(null);
  const [pendingQueue, setPendingQueue] = useState<{ id: string; text: string }[]>([]);
  const [queueNotice, setQueueNotice] = useState<string | null>(null);

  // UI Resizing States
  const [splitPercent, setSplitPercent] = useState(14.3);
  const [mainSplitPercent, setMainSplitPercent] = useState(50);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [uiHydrated, setUiHydrated] = useState(false);
  const draggingType = useRef<"sidebar" | "main" | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Geometry Cache States
  const [coordinates, setCoordinates] = useState<Record<string, [number, number, number] | [number, number]> | null>(null);
  const [is3d, setIs3d] = useState(false);
  const [polygonOrder, setPolygonOrder] = useState<string[] | null>(null);
  const [drawingPhases, setDrawingPhases] = useState<Array<{ phase: number; label: string; points: string[]; segments: string[][] }> | null>(null);
  const [faces, setFaces] = useState<string[][] | null>(null);
  const [solids, setSolids] = useState<Array<{ type: string; [key: string]: unknown }> | null>(null);
  const [circles, setCircles] = useState<Array<{ center: string; radius: number }> | null>(null);
  const [lines, setLines] = useState<Array<[string, string]> | null>(null);
  const [rays, setRays] = useState<Array<[string, string]> | null>(null);
  const [visGraph, setVisGraph] = useState<import("@/types/geometry").VisualizationGraph | null>(null);
  const [auxiliary, setAuxiliary] = useState<import("@/types/geometry").VisAuxiliaryConstruction[] | null>(null);
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const [videoVersion, setVideoVersion] = useState(1);
  const [activeSnapshotJobId, setActiveSnapshotJobId] = useState<string | null>(null);
  const prevSnapshotsCountRef = useRef(0);
  const prevRouteSessionIdRef = useRef<string | undefined>(undefined);

  // Job Hooks
  const { job, videoJob, startSolve, startRenderVideo, resetJob } = useSolverJob(
    sessionId,
    userSession?.access_token
  );

  const geometrySnapshots = useMemo(() => {
    return (
      messages?.filter(
        (m) =>
          m.role === "assistant" &&
          m.type !== "error" &&
          m.metadata?.coordinates
      ) || []
    );
  }, [messages]);

  const isQueueFull = pendingQueue.length >= 5;
  const queueFullBlock = job.phase !== "idle" && isQueueFull;
  const ocrPreviewBlocking = ocrFlow.status !== "idle";

  const authoritativeJobIdRef = useRef<string | null>(null);
  const authoritativeResultRef = useRef<Record<string, unknown> | null>(null);

  const applyGeometryFromSnapshot = (
    meta: Record<string, unknown> | null | undefined,
    options?: { isExplicitSwitch?: boolean }
  ) => {
    if (!meta) return;
    logGeometryDebug("applyGeometryFromSnapshot", meta);
    const rawCoords = (meta.coordinates || {}) as Record<string, unknown>;
    if (Object.keys(rawCoords).length === 0 && !options?.isExplicitSwitch) {
      return;
    }

    const mode = pickCanvasMode({
      is_3d: meta.is_3d as boolean | undefined,
      is3d: meta.is3d as boolean | undefined,
      coordinates: rawCoords,
    });
    const inconsistency = detectGeometryInconsistency({
      is_3d: meta.is_3d as boolean | undefined,
      is3d: meta.is3d as boolean | undefined,
      coordinates: rawCoords,
    });
    if (inconsistency) logGeometryBeHandoff(inconsistency, meta);

    if (mode === "3d") {
      setCoordinates(normalizeCoordinates3D(rawCoords));
      setIs3d(true);
    } else {
      setCoordinates(projectCoordinates2D(rawCoords));
      setIs3d(false);
    }

    const isExplicit = options?.isExplicitSwitch;

    // 1. Polygon Order (Merge or reset on explicit switch)
    const metaPolygonOrder = (meta.polygon_order as string[]) || (meta.polygonOrder as string[]) || null;
    if (metaPolygonOrder && metaPolygonOrder.length > 0) {
      setPolygonOrder(metaPolygonOrder);
    } else if (isExplicit) {
      setPolygonOrder(null);
    }

    // 2. Drawing Phases
    const metaPhases =
      (meta.drawing_phases as Array<{ phase: number; label: string; points: string[]; segments: string[][] }>) ||
      (meta.drawingPhases as Array<{ phase: number; label: string; points: string[]; segments: string[][] }>) ||
      null;
    if (metaPhases && metaPhases.length > 0) {
      setDrawingPhases(metaPhases);
    } else if (isExplicit) {
      setDrawingPhases(null);
    }

    // 3. Faces (Preserve topology instead of resetting to null)
    const metaFaces = (meta.faces as string[][]) || null;
    if (metaFaces && metaFaces.length > 0) {
      setFaces(metaFaces);
    } else if (isExplicit) {
      setFaces(null);
    }

    // 4. Solids
    const metaSolids = (meta.solids as Array<{ type: string; [key: string]: unknown }>) || null;
    if (metaSolids && metaSolids.length > 0) {
      setSolids(metaSolids);
    } else if (isExplicit) {
      setSolids(null);
    }

    // 5. Circles
    const metaCircles = (meta.circles as Array<{ center: string; radius: number }>) || null;
    if (metaCircles && metaCircles.length > 0) {
      setCircles(metaCircles);
    } else if (isExplicit) {
      setCircles(null);
    }

    // 6. Lines
    const metaLines = (meta.lines as Array<[string, string]>) || null;
    if (metaLines && metaLines.length > 0) {
      setLines(metaLines);
    } else if (isExplicit) {
      setLines(null);
    }

    // 7. Rays
    const metaRays = (meta.rays as Array<[string, string]>) || null;
    if (metaRays && metaRays.length > 0) {
      setRays(metaRays);
    } else if (isExplicit) {
      setRays(null);
    }

    // 8. Visualization Graph
    const metaVisGraph =
      (meta.visualization_graph as import("@/types/geometry").VisualizationGraph) ||
      (meta.visualizationGraph as import("@/types/geometry").VisualizationGraph) ||
      null;
    if (metaVisGraph && Object.keys(metaVisGraph).length > 0) {
      setVisGraph(metaVisGraph);
    } else if (isExplicit) {
      setVisGraph(null);
    }

    // 9. Auxiliary
    const metaAux = (meta.auxiliary as import("@/types/geometry").VisAuxiliaryConstruction[]) || null;
    if (metaAux && metaAux.length > 0) {
      setAuxiliary(metaAux);
    } else if (isExplicit) {
      setAuxiliary(null);
    }

    // 10. Video URL & Job ID
    const metaVideoUrl = (meta.video_url as string) || (meta.videoUrl as string) || null;
    if (metaVideoUrl) {
      setVideoUrl(metaVideoUrl);
    } else if (isExplicit) {
      setVideoUrl(null);
    }

    const metaJobId = (meta.job_id as string) || (meta.jobId as string) || null;
    if (metaJobId) {
      setActiveSnapshotJobId(metaJobId);
    }
  };

  // Restore cache on session change
  useEffect(() => {
    const prev = prevRouteSessionIdRef.current;
    prevRouteSessionIdRef.current = sessionId;
    const tempToReal =
      Boolean(prev?.startsWith("temp-")) &&
      Boolean(sessionId && !sessionId.startsWith("temp-"));

    if (tempToReal) {
      const cached = loadGeometryState(sessionId);
      if (cached) applyGeometryFromSnapshot(cached as unknown as Record<string, unknown>, { isExplicitSwitch: true });
      else {
        setCoordinates(null);
        setIs3d(false);
        setPolygonOrder(null);
        setDrawingPhases(null);
        setVideoUrl(null);
        setActiveSnapshotJobId(null);
      }
      setPendingQueue(getPendingQueue(sessionId));
      return;
    }

    setPendingDraftImages((prevDrafts) => {
      revokeDraftImages(prevDrafts);
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
      applyGeometryFromSnapshot(cached as unknown as Record<string, unknown>, { isExplicitSwitch: true });
    }
    setPendingQueue(getPendingQueue(sessionId));
  }, [sessionId, isTempSession]);

  // Sync latest snapshots from messages (SWR) with authoritative result guard
  useEffect(() => {
    if (geometrySnapshots.length > prevSnapshotsCountRef.current) {
      setVideoVersion(geometrySnapshots.length);
      const latestSnapshot = geometrySnapshots[geometrySnapshots.length - 1];
      const meta = (latestSnapshot?.metadata as Record<string, unknown>) || {};
      const snapJobId = (meta.job_id as string) || (meta.jobId as string);

      // If we have authoritative result for this job from job.success, merge onto it
      if (authoritativeJobIdRef.current && snapJobId === authoritativeJobIdRef.current && authoritativeResultRef.current) {
        applyGeometryFromSnapshot({
          ...meta,
          ...authoritativeResultRef.current,
        });
      } else {
        applyGeometryFromSnapshot(meta);
      }
    }
    prevSnapshotsCountRef.current = geometrySnapshots.length;
  }, [geometrySnapshots]);

  // Handle job completion with authoritative solver result
  useEffect(() => {
    if (job.phase !== "success" && job.phase !== "error") return;
    const resultSnap = job.result;
    let cancelled = false;

    if (resultSnap) {
      const jobId = (resultSnap.job_id as string) || (resultSnap.jobId as string) || job.jobId || null;
      if (jobId) {
        authoritativeJobIdRef.current = jobId;
      }
      authoritativeResultRef.current = resultSnap as unknown as Record<string, unknown>;

      // Apply authoritative geometry immediately with full topology
      applyGeometryFromSnapshot(resultSnap as unknown as Record<string, unknown>);

      if (!isTempSession) {
        saveGeometryState(sessionId, {
          coordinates: resultSnap.coordinates,
          polygonOrder: resultSnap.polygon_order,
          drawingPhases: resultSnap.drawing_phases,
          faces: resultSnap.faces,
          solids: resultSnap.solids,
          lines: resultSnap.lines,
          rays: resultSnap.rays,
          visualizationGraph: resultSnap.visualization_graph,
          auxiliary: resultSnap.auxiliary,
          is_3d: resultSnap.is_3d,
          videoUrl: resultSnap.video_url,
        } as GeometryState);
      }
    }

    const run = async () => {
      try {
        await mutateMessages(undefined, { revalidate: true });
      } catch (e) {
        console.error("Revalidate messages after job:", e);
      } finally {
        if (cancelled) return;
        setTimeout(resetJob, 1000);
      }
    };
    void run();
    return () => {
      cancelled = true;
    };
  }, [job.phase, job.result, job.jobId, mutateMessages, resetJob, sessionId, isTempSession]);

  // Queue Processing
  useEffect(() => {
    if (job.phase === "idle" && pendingQueue.length > 0) {
      const next = pendingQueue[0];
      setPendingQueue((prev) => {
        const n = prev.slice(1);
        if (!isTempSession) savePendingQueue(sessionId, n);
        return n;
      });
      const clientMessageId = crypto.randomUUID();
      void mutateMessages(
        (prev) => [
          ...(prev || []),
          {
            id: clientMessageId,
            role: "user",
            type: "text",
            content: next.text,
            timestamp: Date.now(),
          },
        ],
        { revalidate: false }
      );
      startSolve(next.text, false, null, clientMessageId);
    }
  }, [job.phase, pendingQueue, startSolve, sessionId, isTempSession, mutateMessages]);

  // Layout dragging
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!draggingType.current || !containerRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      const x = e.clientX - rect.left;
      if (draggingType.current === "sidebar" && !sidebarCollapsed) {
        setSplitPercent(
          Math.min(Math.max((x / rect.width) * 100, SPLIT_MIN_PCT), SPLIT_MAX_PCT)
        );
      } else if (draggingType.current === "main") {
        const sidebarWidth = sidebarCollapsed ? 52 : (rect.width * splitPercent) / 100;
        const relativeX = x - sidebarWidth;
        setMainSplitPercent(
          Math.min(
            Math.max((relativeX / (rect.width - sidebarWidth)) * 100, MAIN_SPLIT_MIN_PCT),
            MAIN_SPLIT_MAX_PCT
          )
        );
      }
    };
    const handleMouseUp = () => {
      draggingType.current = null;
      document.body.style.cursor = "";
    };
    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", handleMouseUp);
    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
    };
  }, [sidebarCollapsed, splitPercent]);

  useEffect(() => {
    setSplitPercent(readSplitPercent(14.3));
    setMainSplitPercent(readMainSplitPercent(50));
    setSidebarCollapsed(readSidebarCollapsed());
    setUiHydrated(true);
  }, []);

  useEffect(() => {
    if (uiHydrated) {
      writeSplitPercent(splitPercent);
      writeMainSplitPercent(mainSplitPercent);
      writeSidebarCollapsed(sidebarCollapsed);
    }
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
    const token = userSession?.access_token;
    const parts: string[] = [];
    let combinedText = "";

    const useLegacyOcr = isTempSession || sessionId.startsWith("temp-");

    if (useLegacyOcr) {
      for (const d of attachments) {
        const prep = await preprocessImageForOcr(d.file);
        const t = await postOcr(prep, token);
        parts.push(t);
      }
      combinedText = buildCombinedMessage(userTextSnapshot, parts);
      return { ocrParts: parts, combinedText };
    }

    for (let i = 0; i < attachments.length; i++) {
      const prep = await preprocessImageForOcr(attachments[i].file);
      const userMsg = i === 0 ? userTextSnapshot : undefined;
      const r = await postOcrPreview(sessionId, prep, userMsg, token);
      parts.push((r.ocr_text ?? "").trim());
      if (i === 0) {
        combinedText = (r.combined_draft ?? "").trim();
      } else {
        const o = (r.ocr_text ?? "").trim();
        if (o) {
          combinedText = combinedText.trim()
            ? `${combinedText.trim()}\n\n${o}`
            : o;
        }
      }
    }
    return { ocrParts: parts, combinedText };
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
    const clientMessageId = crypto.randomUUID();
    await mutateMessages(
      (prev) => [
        ...(prev || []),
        {
          id: clientMessageId,
          role: "user",
          type: "text",
          content: text,
          timestamp: Date.now(),
        },
      ],
      { revalidate: false }
    );
    startSolve(text, false, null, clientMessageId);
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
    const clientMessageId = crypto.randomUUID();
    await mutateMessages(
      (prev) => [
        ...(prev || []),
        {
          id: clientMessageId,
          role: "user",
          type: "text",
          content: payloadTrim,
          timestamp: Date.now(),
        },
      ],
      { revalidate: false }
    );
    startSolve(payloadTrim, false, null, clientMessageId);
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

  const hasVisualization = Boolean(
    coordinates ||
    videoUrl ||
    (videoJob && videoJob.status !== "idle")
  );

  return (
    <div
      ref={containerRef}
      className="h-[100dvh] w-screen flex bg-[var(--background)] text-[var(--foreground)] overflow-hidden"
    >
      {/* Sidebar Rail */}
      <div
        className={`h-full flex flex-col shrink-0 border-r border-[var(--border)] transition-all ${
          sidebarCollapsed ? "w-[52px]" : ""
        }`}
        style={sidebarCollapsed ? undefined : { width: `${splitPercent}%` }}
      >
        <ChatSidebar
          compact={sidebarCollapsed}
          onCollapse={() => setSidebarCollapsed(true)}
          onExpand={() => setSidebarCollapsed(false)}
        />
      </div>

      {/* Sidebar Drag Resizer */}
      {!sidebarCollapsed && (
        <div
          role="separator"
          onMouseDown={() => {
            draggingType.current = "sidebar";
            document.body.style.cursor = "col-resize";
          }}
          className="w-1 cursor-col-resize hover:bg-indigo-500/40 z-10 shrink-0 transition-colors"
        />
      )}

      {/* Main App Canvas */}
      <div className="flex-1 flex flex-col min-w-0 bg-[var(--bg-secondary)]">
        <div className="flex-1 flex overflow-hidden">
          {/* Chat Column */}
          <div
            className={`flex flex-col min-w-0 bg-[var(--panel-bg)] transition-all duration-300 ${
              hasVisualization ? "border-r border-[var(--border)]" : "w-full flex-1"
            }`}
            style={hasVisualization ? { width: `${mainSplitPercent}%` } : undefined}
          >
            <div className={`flex-1 flex flex-col min-w-0 overflow-hidden ${!hasVisualization ? "max-w-4xl w-full mx-auto" : ""}`}>
              {messages.length === 0 &&
              pendingQueue.length === 0 &&
              !historyLoadingRaw &&
              ocrFlow.status === "idle" ? (
                <HeroWelcome
                  onSuggestionClick={(text) => {
                    setInputText(text);
                  }}
                />
              ) : (
                <ChatMessageList
                  messages={messages}
                  historyLoading={historyLoadingRaw && !isTempSession}
                  isTempSession={isTempSession}
                  currentStatus={
                    job.phase !== "idle" && job.phase !== "success" ? job.message : null
                  }
                  pendingQueue={pendingQueue}
                  editQueued={editQueued}
                  removeQueued={removeQueued}
                  messagesEndRef={messagesEndRef}
                />
              )}

              {queueNotice && (
                <div className="px-4 pt-2 max-w-3xl mx-auto w-full">
                  <p className="text-xs text-amber-300 bg-amber-500/10 border border-amber-500/20 rounded-xl px-3 py-2">
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
          </div>

          {/* Main Column Drag Resizer & Workspace (Only rendered when hasVisualization is true) */}
          {hasVisualization && (
            <>
              <div
                role="separator"
                onMouseDown={() => {
                  draggingType.current = "main";
                  document.body.style.cursor = "col-resize";
                }}
                className="w-1 cursor-col-resize hover:bg-indigo-500/40 z-10 shrink-0 transition-colors"
              />

              {/* Geometry & Animation Workspace */}
              <div className="flex-1 flex flex-col bg-black/30 overflow-hidden relative">
                <div className="flex-1 flex flex-col p-4 md:p-6 space-y-4 overflow-hidden">
                  <AnimatePresence mode="popLayout">
                    {coordinates && (
                      <motion.div
                        key="static"
                        initial={{ opacity: 0, scale: 0.98 }}
                        animate={{ opacity: 1, scale: 1 }}
                        className="flex-1 flex flex-col min-h-0 space-y-2.5"
                      >
                        <div className="flex items-center justify-between gap-2 px-1">
                          <div className="flex items-center gap-2.5">
                            <span className="text-[10px] font-mono font-semibold text-[var(--text-secondary)] uppercase tracking-wider">
                              Mô hình Hình học {is3d ? "3D" : "2D"}
                            </span>

                            {coordinates && !videoUrl && videoJob.status === "idle" && (
                              <button
                                type="button"
                                onClick={() =>
                                  startRenderVideo(activeSnapshotJobId || undefined)
                                }
                                className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/25 text-[10px] font-mono font-semibold text-indigo-300 hover:bg-indigo-500/20 active:scale-95 transition-all"
                              >
                                <Film className="w-3 h-3 text-indigo-400" />
                                Tạo Animation
                              </button>
                            )}
                          </div>

                          <VersionSwitcher
                            currentVersion={videoVersion}
                            totalVersions={geometrySnapshots.length}
                            onPrev={() => {
                              if (videoVersion > 1) {
                                setVideoVersion((v) => v - 1);
                                applyGeometryFromSnapshot(
                                  geometrySnapshots[videoVersion - 2]
                                    .metadata as Record<string, unknown>,
                                  { isExplicitSwitch: true }
                                );
                              }
                            }}
                            onNext={() => {
                              if (videoVersion < geometrySnapshots.length) {
                                setVideoVersion((v) => v + 1);
                                applyGeometryFromSnapshot(
                                  geometrySnapshots[videoVersion]
                                    .metadata as Record<string, unknown>,
                                  { isExplicitSwitch: true }
                                );
                              }
                            }}
                          />
                        </div>

                        <div className="flex-1 min-h-0 relative overflow-hidden">
                          {is3d ? (
                            <Interactive3DCanvas
                              coordinates={coordinates}
                              drawingPhases={drawingPhases || []}
                              faces={faces || []}
                              solids={solids || []}
                              visualizationGraph={visGraph}
                              auxiliary={auxiliary}
                            />
                          ) : (
                            <StaticGeometryCanvas
                              coordinates={
                                coordinates as Record<string, [number, number]>
                              }
                              polygonOrder={polygonOrder || []}
                              faces={faces || []}
                              drawingPhases={drawingPhases || []}
                              circles={circles || []}
                              lines={lines || []}
                              rays={rays || []}
                              visualizationGraph={visGraph}
                              auxiliary={auxiliary}
                            />
                          )}
                        </div>
                      </motion.div>
                    )}

                    {(videoUrl || videoJob.status !== "idle") && (
                      <motion.div
                        key="animation"
                        initial={{ opacity: 0, scale: 0.98 }}
                        animate={{ opacity: 1, scale: 1 }}
                        className="flex-1 flex flex-col min-h-0 space-y-2.5"
                      >
                        <div className="flex items-center justify-between px-1">
                          <span className="text-[10px] font-mono font-semibold text-[var(--text-secondary)] uppercase tracking-wider">
                            Animation Manim Video
                          </span>
                        </div>
                        <AnimationPreview
                          videoUrl={videoUrl || videoJob.videoUrl || undefined}
                          videoState={videoJob}
                          onRetry={() => startRenderVideo(activeSnapshotJobId || undefined)}
                          onRequestRender={() => startRenderVideo(activeSnapshotJobId || undefined)}
                        />
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
