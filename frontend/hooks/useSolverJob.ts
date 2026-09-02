import { useState, useRef, useEffect, useCallback, useLayoutEffect } from 'react';
import { getApiBaseUrl, getWsBaseUrl } from '@/lib/api-config';
import { saveActiveJob, getActiveJob, clearActiveJob } from '@/lib/job-tracker';
import { validateJobResult, type JobResult } from '@/lib/validators';

export type SolverPhase =
  | 'idle'
  | 'uploading'
  | 'ocr'
  | 'parsing'
  | 'solving'
  | 'success'
  | 'error';

export interface JobState {
  phase: SolverPhase;
  progress: number;
  message: string;
  result?: JobResult | null;
  error?: string;
  jobId?: string;
}

export type VideoRenderStatus =
  | 'idle'
  | 'connecting'
  | 'queued'
  | 'generating'
  | 'rendering'
  | 'completed'
  | 'failed';

export interface VideoJobState {
  status: VideoRenderStatus;
  progress: number;
  message: string;
  videoUrl?: string | null;
  error?: string | null;
  jobId?: string;
}

const solveStatusMessages: Record<string, string> = {
  processing: "Đang xử lý bài toán...",
  ocr: "Đang quét dữ liệu ảnh...",
  parsing: "Đang phân tích cấu trúc hình học...",
  solving: "Đang giải hệ phương trình...",
  success: "Hoàn thành!",
  error: "Có lỗi xảy ra."
};

const solveStatusToPhase: Record<string, SolverPhase> = {
  processing: 'ocr',
  ocr: 'ocr',
  parsing: 'parsing',
  solving: 'solving',
  success: 'success',
  error: 'error'
};

const videoStatusMessages: Record<string, string> = {
  connecting: "Đang kết nối với Animation Server...",
  queued: "Đang chờ xử lý trong hàng đợi...",
  rendering_queued: "Đang chờ xử lý trong hàng đợi...",
  generating: "Đang tạo animation...",
  rendering: "Đang render video...",
  completed: "Hoàn thành video animation!",
  success: "Hoàn thành video animation!",
  failed: "Không thể tạo animation.",
  error: "Không thể tạo animation."
};

/** Normalize poll row (Supabase) or WS payload to { status, result, error, video_url }. */
export function normalizeJobPayload(raw: unknown): {
  status?: string;
  result?: unknown;
  error?: string;
  video_url?: string;
} | null {
  if (!raw || typeof raw !== "object") return null;
  const o = raw as Record<string, unknown>;
  const status = typeof o.status === "string" ? o.status : undefined;
  const result = "result" in o ? o.result : undefined;
  const error = typeof o.error === "string" ? o.error : undefined;
  const video_url = typeof o.video_url === "string" ? o.video_url : undefined;
  if (!status) return null;
  return { status, result, error, video_url };
}

export function useSolverJob(sessionId: string, token?: string | null) {
  const [job, setJob] = useState<JobState>({ phase: 'idle', progress: 0, message: '' });
  const [videoJob, setVideoJob] = useState<VideoJobState>({
    status: 'idle',
    progress: 0,
    message: '',
    videoUrl: null,
    error: null,
  });

  const solverSocketRef = useRef<WebSocket | null>(null);
  const solverPollIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const solverPollAttemptsRef = useRef(0);
  const solverTerminalRef = useRef(false);

  const videoSocketRef = useRef<WebSocket | null>(null);
  const videoPollIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const videoPollAttemptsRef = useRef(0);
  const videoTerminalRef = useRef(false);

  const MAX_POLL_ATTEMPTS = 300;

  // Cleanup solver subscriptions
  const cleanupSolver = useCallback(() => {
    if (solverSocketRef.current) {
      solverSocketRef.current.close();
      solverSocketRef.current = null;
    }
    if (solverPollIntervalRef.current) {
      clearInterval(solverPollIntervalRef.current);
      solverPollIntervalRef.current = null;
    }
    solverPollAttemptsRef.current = 0;
  }, []);

  // Cleanup video subscriptions
  const cleanupVideo = useCallback(() => {
    if (videoSocketRef.current) {
      videoSocketRef.current.close();
      videoSocketRef.current = null;
    }
    if (videoPollIntervalRef.current) {
      clearInterval(videoPollIntervalRef.current);
      videoPollIntervalRef.current = null;
    }
    videoPollAttemptsRef.current = 0;
  }, []);

  const cleanupAll = useCallback(() => {
    cleanupSolver();
    cleanupVideo();
  }, [cleanupSolver, cleanupVideo]);

  // Solver updates handler
  const updateSolverJobState = useCallback(
    (raw: unknown) => {
      const data = normalizeJobPayload(raw);
      if (!data?.status) return;

      setJob((prev) => {
        const phase = solveStatusToPhase[data.status!] || "solving";
        let progress = prev.progress;
        if (phase === "ocr") progress = 30;
        else if (phase === "parsing") progress = 50;
        else if (phase === "solving") progress = 75;
        else if (phase === "success") progress = 100;

        return {
          ...prev,
          phase,
          progress,
          message: solveStatusMessages[data.status!] || prev.message,
          error: data.error || prev.error,
          result:
            data.result !== undefined && data.result !== null
              ? validateJobResult(data.result)
              : prev.result,
        };
      });

      // Also check if result has video_url
      if (data.status === "success" && data.result) {
        const validated = validateJobResult(data.result);
        if (validated?.video_url) {
          setVideoJob({
            status: 'completed',
            progress: 100,
            message: 'Đã hoàn thành video!',
            videoUrl: validated.video_url,
            error: null,
          });
        }
      }

      if (data.status === "success" || data.status === "error") {
        solverTerminalRef.current = true;
        cleanupSolver();
        clearActiveJob(sessionId);
      }
    },
    [cleanupSolver, sessionId]
  );

  // Video updates handler
  const updateVideoJobState = useCallback(
    (raw: unknown) => {
      const data = normalizeJobPayload(raw);
      if (!data?.status) return;

      const st = data.status.toLowerCase();
      setVideoJob((prev) => {
        let status: VideoRenderStatus = prev.status;
        let progress = prev.progress;
        let videoUrl = prev.videoUrl;
        let error = prev.error;

        if (st === "queued" || st === "rendering_queued") {
          status = "queued";
          progress = 30;
        } else if (st === "generating") {
          status = "generating";
          progress = 60;
        } else if (st === "rendering") {
          status = "rendering";
          progress = 85;
        } else if (st === "completed" || st === "success") {
          status = "completed";
          progress = 100;
          videoUrl = data.video_url || (data.result as Record<string, unknown>)?.video_url as string || prev.videoUrl;
          error = null;
        } else if (st === "failed" || st === "error") {
          status = "failed";
          progress = 0;
          error = data.error || (data.result as Record<string, unknown>)?.error as string || "Không thể tạo animation.";
        }

        return {
          ...prev,
          status,
          progress,
          message: videoStatusMessages[st] || prev.message,
          videoUrl,
          error,
        };
      });

      if (st === "completed" || st === "success" || st === "failed" || st === "error") {
        videoTerminalRef.current = true;
        cleanupVideo();
      }
    },
    [cleanupVideo]
  );

  const startSolverPolling = useCallback((jobId: string) => {
    if (solverPollIntervalRef.current) return;

    solverPollIntervalRef.current = setInterval(async () => {
      solverPollAttemptsRef.current += 1;
      if (solverPollAttemptsRef.current > MAX_POLL_ATTEMPTS) {
        setJob(prev => ({ ...prev, phase: 'error', progress: 0, message: 'Time out', error: 'Quá thời gian xử lý' }));
        cleanupSolver();
        clearActiveJob(sessionId);
        return;
      }

      try {
        const headers: Record<string, string> = {};
        if (token) headers.Authorization = `Bearer ${token}`;
        const res = await fetch(`${getApiBaseUrl()}/api/v1/solve/${jobId}`, { headers });
        if (!res.ok) return;
        const data = await res.json();
        updateSolverJobState(data);
      } catch (err) {
        console.error("[SolverPolling] error:", err);
      }
    }, 1500);
  }, [cleanupSolver, sessionId, token, updateSolverJobState]);

  const startVideoPolling = useCallback((jobId: string) => {
    if (videoPollIntervalRef.current) return;

    videoPollIntervalRef.current = setInterval(async () => {
      videoPollAttemptsRef.current += 1;
      if (videoPollAttemptsRef.current > MAX_POLL_ATTEMPTS) {
        setVideoJob(prev => ({
          ...prev,
          status: 'failed',
          progress: 0,
          message: 'Không thể tạo animation.',
          error: 'Quá thời gian xử lý video',
        }));
        cleanupVideo();
        return;
      }

      try {
        const headers: Record<string, string> = {};
        if (token) headers.Authorization = `Bearer ${token}`;
        const res = await fetch(`${getApiBaseUrl()}/api/v1/solve/${jobId}`, { headers });
        if (!res.ok) {
          if (res.status === 404 || res.status >= 500) {
            setVideoJob(prev => ({
              ...prev,
              status: 'failed',
              error: `Server phản hồi lỗi HTTP ${res.status}`,
            }));
            cleanupVideo();
          }
          return;
        }
        const data = await res.json();
        updateVideoJobState(data);
      } catch (err) {
        console.error("[VideoPolling] error:", err);
      }
    }, 1500);
  }, [cleanupVideo, token, updateVideoJobState]);

  const attachToSolverJob = useCallback((jobId: string) => {
    cleanupSolver();
    solverTerminalRef.current = false;
    setJob({ phase: 'solving', progress: 20, message: 'Đang xử lý bài toán...', jobId });
    saveActiveJob(sessionId, jobId);

    // Always start HTTP polling alongside WebSocket as a robust fallback
    startSolverPolling(jobId);

    try {
      const ws = new WebSocket(`${getWsBaseUrl()}/ws/${jobId}`);
      solverSocketRef.current = ws;

      let pingInterval: NodeJS.Timeout | null = null;
      ws.onopen = () => {
        pingInterval = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            try { ws.send("ping"); } catch { /* ignore */ }
          }
        }, 5000);
      };

      ws.onmessage = (event) => {
        try {
          if (event.data === "pong") return;
          const data = JSON.parse(event.data);
          updateSolverJobState(data);
        } catch { /* ignore */ }
      };

      ws.onerror = () => {
        if (pingInterval) clearInterval(pingInterval);
        startSolverPolling(jobId);
      };

      ws.onclose = () => {
        if (pingInterval) clearInterval(pingInterval);
        if (solverTerminalRef.current) return;
        if (solverSocketRef.current !== null && solverSocketRef.current !== ws) return;
        startSolverPolling(jobId);
      };
    } catch {
      startSolverPolling(jobId);
    }
  }, [cleanupSolver, sessionId, startSolverPolling, updateSolverJobState]);

  const attachToVideoJob = useCallback((jobId: string) => {
    cleanupVideo();
    videoTerminalRef.current = false;
    setVideoJob(prev => ({
      ...prev,
      status: 'connecting',
      progress: 20,
      message: 'Đang tạo video animation...',
      jobId,
      error: null,
    }));

    // Always start HTTP polling alongside WebSocket as a robust fallback
    startVideoPolling(jobId);

    try {
      const ws = new WebSocket(`${getWsBaseUrl()}/ws/${jobId}`);
      videoSocketRef.current = ws;

      let pingInterval: NodeJS.Timeout | null = null;
      ws.onopen = () => {
        pingInterval = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            try { ws.send("ping"); } catch { /* ignore */ }
          }
        }, 5000);
      };

      ws.onmessage = (event) => {
        try {
          if (event.data === "pong") return;
          const data = JSON.parse(event.data);
          updateVideoJobState(data);
        } catch { /* ignore */ }
      };

      ws.onerror = () => {
        if (pingInterval) clearInterval(pingInterval);
        startVideoPolling(jobId);
      };

      ws.onclose = () => {
        if (pingInterval) clearInterval(pingInterval);
        if (videoTerminalRef.current) return;
        if (videoSocketRef.current !== null && videoSocketRef.current !== ws) return;
        startVideoPolling(jobId);
      };
    } catch {
      startVideoPolling(jobId);
    }
  }, [cleanupVideo, startVideoPolling, updateVideoJobState]);

  const attachToSolverJobRef = useRef(attachToSolverJob);
  useLayoutEffect(() => {
    attachToSolverJobRef.current = attachToSolverJob;
  }, [attachToSolverJob]);

  const startSolve = useCallback(
    async (
      text: string,
      requestVideo: boolean = false,
      imageUrl?: string | null,
      clientMessageId?: string | null
    ) => {
      if (!token) return;
      cleanupSolver();
      setJob({ phase: 'uploading', progress: 10, message: 'Đang gửi yêu cầu...', result: null, error: undefined });

      try {
        const body: Record<string, unknown> = { text, request_video: requestVideo };
        if (imageUrl) body.image_url = imageUrl;
        if (clientMessageId) body.client_message_id = clientMessageId;
        const response = await fetch(`${getApiBaseUrl()}/api/v1/sessions/${sessionId}/solve`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify(body),
        });

        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();
        if (!data.job_id) throw new Error("Missing job_id");

        attachToSolverJob(data.job_id);
      } catch (err) {
        setJob(prev => ({ ...prev, phase: 'error', progress: 0, message: 'Lỗi khởi tạo', error: String(err) }));
        cleanupSolver();
      }
    },
    [sessionId, token, attachToSolverJob, cleanupSolver]
  );

  const startRenderVideo = useCallback(async (targetJobId?: string) => {
    if (!token) return;
    cleanupVideo();
    setVideoJob({
      status: 'connecting',
      progress: 15,
      message: 'Đang kết nối với Animation Server...',
      videoUrl: null,
      error: null,
    });

    try {
      const response = await fetch(`${getApiBaseUrl()}/api/v1/sessions/${sessionId}/render_video`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ job_id: targetJobId }),
      });

      if (!response.ok) {
        const errText = await response.text().catch(() => "");
        let cleanErr = `HTTP ${response.status}`;
        try {
          const jsonErr = JSON.parse(errText);
          if (jsonErr.detail) cleanErr = jsonErr.detail;
          if (jsonErr.error) cleanErr = jsonErr.error;
        } catch {
          if (errText.includes("429")) cleanErr = "Server Manim đang quá tải (Rate limit 429). Vui lòng thử lại sau giây lát.";
        }
        throw new Error(cleanErr);
      }

      const data = await response.json();
      if (!data.job_id) throw new Error("Missing job_id");

      // If backend returned immediate completed video_url
      if (data.status === "completed" && data.video_url) {
        setVideoJob({
          status: 'completed',
          progress: 100,
          message: 'Hoàn thành video animation!',
          videoUrl: data.video_url,
          error: null,
          jobId: data.job_id,
        });
        return;
      }

      attachToVideoJob(data.job_id);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setVideoJob({
        status: 'failed',
        progress: 0,
        message: 'Không thể tạo animation.',
        error: msg,
      });
      cleanupVideo();
    }
  }, [sessionId, token, attachToVideoJob, cleanupVideo]);

  // Restore active job on session change - verify with DB first
  useEffect(() => {
    if (!sessionId || sessionId.startsWith("temp-")) return;
    const activeJobId = getActiveJob(sessionId);
    if (!activeJobId) return;

    let cancelled = false;
    const verifyAndAttach = async () => {
      try {
        const headers: Record<string, string> = {};
        if (token) headers.Authorization = `Bearer ${token}`;
        const res = await fetch(`${getApiBaseUrl()}/api/v1/solve/${activeJobId}`, { headers });
        if (cancelled) return;
        if (!res.ok) {
          clearActiveJob(sessionId);
          return;
        }
        const data = await res.json();
        const payload = normalizeJobPayload(data);
        if (!payload || payload.status === "success" || payload.status === "error") {
          clearActiveJob(sessionId);
          return;
        }
        attachToSolverJobRef.current(activeJobId);
      } catch (err) {
        console.warn("[useSolverJob] Error verifying active job:", err);
      }
    };

    void verifyAndAttach();

    return cleanupAll;
  }, [sessionId, token, cleanupAll]);

  const resetJob = useCallback(() => {
    cleanupAll();
    solverTerminalRef.current = false;
    videoTerminalRef.current = false;
    setJob({ phase: 'idle', progress: 0, message: '' });
    setVideoJob({
      status: 'idle',
      progress: 0,
      message: '',
      videoUrl: null,
      error: null,
    });
  }, [cleanupAll]);

  return { job, videoJob, startSolve, startRenderVideo, attachToSolverJob, resetJob, setVideoJob };
}
