import { useState, useRef, useEffect, useCallback } from 'react';
import { getApiBaseUrl, getWsBaseUrl } from '@/lib/api-config';
import { saveActiveJob, getActiveJob, clearActiveJob } from '@/lib/job-tracker';
import { validateJobResult } from '@/lib/validators';

export type SolverPhase = 'idle' | 'uploading' | 'ocr' | 'parsing' | 'solving' | 'rendering_queued' | 'rendering' | 'success' | 'error';

export interface JobState {
  phase: SolverPhase;
  progress: number;
  message: string;
  result?: any;
  error?: string;
  jobId?: string;
}

const statusMessages: Record<string, string> = {
  processing: "Đang xử lý bài toán...",
  solving: "Đang giải hệ phương trình...",
  rendering_queued: "Đã gửi yêu cầu render video...",
  rendering: "Đang dựng animation Manim...",
  success: "Hoàn thành!",
  error: "Có lỗi xảy ra."
};

const statusToPhase: Record<string, SolverPhase> = {
  processing: 'ocr',
  parsing: 'parsing',
  solving: 'solving',
  rendering_queued: 'rendering_queued',
  rendering: 'rendering',
  success: 'success',
  error: 'error'
};

export function useSolverJob(sessionId: string, token?: string | null) {
  const [job, setJob] = useState<JobState>({ phase: 'idle', progress: 0, message: '' });
  const socketRef = useRef<WebSocket | null>(null);
  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const pollAttemptsRef = useRef(0);
  const MAX_POLL_ATTEMPTS = 300;

  const cleanup = useCallback(() => {
    if (socketRef.current) {
      socketRef.current.close();
      socketRef.current = null;
    }
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }
    pollAttemptsRef.current = 0;
  }, []);

  const updateJobState = useCallback((data: any) => {
    if (data.status) {
      const phase = statusToPhase[data.status] || 'solving';
      let progress = job.progress;
      if (phase === 'ocr') progress = 30;
      else if (phase === 'parsing') progress = 50;
      else if (phase === 'solving') progress = 70;
      else if (phase === 'rendering_queued') progress = 80;
      else if (phase === 'rendering') progress = 90;
      else if (phase === 'success') progress = 100;

      setJob(prev => ({ 
        ...prev, 
        phase, 
        progress,
        message: statusMessages[data.status] || prev.message,
        result: data.result ? validateJobResult(data.result) : prev.result
      }));

      if (data.status === 'success' || data.status === 'error') {
        cleanup();
        if (data.job_id || data.jobId) {
            clearActiveJob(sessionId);
        }
      }
    }
  }, [job.progress, cleanup, sessionId]);

  const startPolling = useCallback((jobId: string) => {
    if (pollIntervalRef.current) return;
    
    pollIntervalRef.current = setInterval(async () => {
      pollAttemptsRef.current += 1;
      if (pollAttemptsRef.current > MAX_POLL_ATTEMPTS) {
        setJob(prev => ({ ...prev, phase: 'error', progress: 0, message: 'Time out', error: 'Quá thời gian xử lý' }));
        cleanup();
        clearActiveJob(sessionId);
        return;
      }
      
      try {
        const res = await fetch(`${getApiBaseUrl()}/api/v1/solve/${jobId}`);
        if (!res.ok) return;
        const data = await res.json();
        updateJobState(data);
      } catch (err) {
        console.error("Polling error:", err);
      }
    }, 1500);
  }, [cleanup, sessionId, updateJobState]);

  const connectSocket = useCallback((jobId: string) => {
    try {
      const ws = new WebSocket(`${getWsBaseUrl()}/ws/${jobId}`);
      socketRef.current = ws;

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          updateJobState(data);
        } catch { /* ignore */ }
      };

      ws.onerror = () => {
        console.error("WS closed/error, falling back to polling");
        startPolling(jobId);
      };
      
      ws.onclose = () => {
         // Auto fallback to polling if closed before success/error.
         // Not strictly necessary if updateJobState clears when success/error.
      };
    } catch (err) {
       startPolling(jobId);
    }
  }, [startPolling, updateJobState]);

  const attachToJob = useCallback((jobId: string) => {
    cleanup();
    setJob({ phase: 'solving', progress: 20, message: 'Đang kết nối...', jobId });
    saveActiveJob(sessionId, jobId);
    connectSocket(jobId);
  }, [cleanup, sessionId, connectSocket]);

  const startSolve = useCallback(async (text: string, requestVideo: boolean = false) => {
    if (!token) return;
    cleanup();
    setJob({ phase: 'uploading', progress: 10, message: 'Đang gửi yêu cầu...', result: null, error: undefined });
    
    try {
      const response = await fetch(`${getApiBaseUrl()}/api/v1/sessions/${sessionId}/solve`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ text, request_video: requestVideo }),
      });

      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      if (!data.job_id) throw new Error("Missing job_id");

      attachToJob(data.job_id);
    } catch (err) {
      setJob(prev => ({ ...prev, phase: 'error', progress: 0, message: 'Lỗi khởi tạo', error: String(err) }));
      cleanup();
    }
  }, [sessionId, token, attachToJob, cleanup]);

  // Re-attach if there is an active job when component mounts/switches
  useEffect(() => {
    if (sessionId && !sessionId.startsWith("temp-")) {
      const activeJobId = getActiveJob(sessionId);
      if (activeJobId && job.phase === 'idle') {
        attachToJob(activeJobId);
      }
    }
    return cleanup;
  }, [sessionId, attachToJob, cleanup, job.phase]);

  const resetJob = useCallback(() => {
    cleanup();
    setJob({ phase: 'idle', progress: 0, message: '' });
  }, [cleanup]);

  return { job, startSolve, attachToJob, resetJob };
}
