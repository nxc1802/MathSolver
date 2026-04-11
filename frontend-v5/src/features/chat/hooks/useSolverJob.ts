import { useState, useRef, useEffect, useCallback } from "react";
import { getApiBaseUrl, getWsBaseUrl } from "@/shared/lib/api-config";
import { saveActiveJob } from "@/shared/lib/job-tracker";
import { JobState, SolverPhase, GeometryMetadataSchema } from "@/shared/types/schemas";

export function useSolverJob(sessionId: string) {
  const [job, setJob] = useState<JobState>({ phase: "idle", progress: 0, message: "" });
  const socketRef = useRef<WebSocket | null>(null);
  const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const updateJobState = useCallback((data: any) => {
    const phaseMap: Record<string, SolverPhase> = {
      processing: "processing",
      parsing: "parsing",
      solving: "solving",
      rendering_queued: "rendering_queued",
      rendering: "rendering",
      success: "success",
      error: "error",
    };
    
    let parsedResult = data.result;
    if (data.result) {
        const parseAttempt = GeometryMetadataSchema.safeParse(data.result);
        if (parseAttempt.success) {
            parsedResult = parseAttempt.data;
        } else {
            console.warn("API Metadata parse error:", parseAttempt.error);
        }
    }

    setJob((prev) => ({
      ...prev,
      phase: phaseMap[data.status] || prev.phase,
      result: parsedResult,
      error: data.error,
    }));
  }, []);

  const stopPolling = useCallback(() => {
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }
  }, []);

  const startPolling = useCallback(
    (jobId: string) => {
      if (pollIntervalRef.current) return;
      pollIntervalRef.current = setInterval(async () => {
        try {
          const res = await fetch(`${getApiBaseUrl()}/api/v1/solve/${jobId}`);
          if (!res.ok) return;
          const data = await res.json();
          updateJobState(data);
          if (data.status === "success" || data.status === "error") {
            stopPolling();
          }
        } catch (e) {
          console.error(e);
        }
      }, 1500);
    },
    [updateJobState, stopPolling]
  );

  const connectSocket = useCallback(
    (jobId: string) => {
      stopPolling();
      try {
        const ws = new WebSocket(`${getWsBaseUrl()}/ws/${jobId}`);
        socketRef.current = ws;

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            updateJobState(data);
            if (data.status === "success" || data.status === "error") {
              ws.close();
              stopPolling();
            }
          } catch (e) {
            console.error("WS Parse error:", e);
          }
        };

        ws.onerror = () => startPolling(jobId);
        ws.onclose = () => {
            if (job.phase !== "success" && job.phase !== "error") {
                startPolling(jobId);
            }
        };
      } catch (err) {
        startPolling(jobId);
      }
    },
    [startPolling, stopPolling, updateJobState, job.phase]
  );

  const startSolve = useCallback(
    async (text: string, requestVideo: boolean, token?: string) => {
      setJob({ phase: "uploading", progress: 10, message: "Đang gửi yêu cầu..." });

      try {
        const response = await fetch(`${getApiBaseUrl()}/api/v1/sessions/${sessionId}/solve`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token || ""}`,
          },
          body: JSON.stringify({ text, request_video: requestVideo }),
        });

        if (!response.ok) throw new Error("Solve API Failed");

        const data = await response.json();
        const jobId = data.job_id;
        if (!jobId) throw new Error("No job_id returned");

        saveActiveJob(sessionId, jobId);
        connectSocket(jobId);
        return jobId;
      } catch (err) {
        setJob({ phase: "error", progress: 0, message: "Lỗi khởi tạo", error: String(err) });
        return null;
      }
    },
    [sessionId, connectSocket]
  );

  const attachToJob = useCallback((jobId: string) => {
      setJob({ phase: "processing", progress: 10, message: "Đang phục hồi tiến trình..." });
      connectSocket(jobId);
  }, [connectSocket]);

  const resetJob = useCallback(() => {
    setJob({ phase: "idle", progress: 0, message: "" });
    stopPolling();
    socketRef.current?.close();
  }, [stopPolling]);

  useEffect(() => {
    return () => {
      socketRef.current?.close();
      stopPolling();
    };
  }, [stopPolling]);

  return { job, startSolve, attachToJob, resetJob };
}
