/**
 * job-tracker.ts
 * 
 * Persistent (localStorage) mapping of sessionId -> { jobId, timestamp }
 * and sessionId -> pendingQueue.
 * Separated to ensure active job lifecycle and pending queue lifecycle
 * do not interfere with each other.
 */

interface ActiveJob {
  jobId: string;
  timestamp: number;
}

const ACTIVE_JOBS_KEY = "mathsolver_active_jobs";
const PENDING_QUEUES_KEY = "mathsolver_pending_queues";
const MAX_STALE_MS = 30 * 60 * 1000; // 30 minutes

function getAllJobs(): Record<string, ActiveJob> {
  if (typeof window === "undefined") return {};
  try {
    const raw = localStorage.getItem(ACTIVE_JOBS_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}

function saveAllJobs(jobs: Record<string, ActiveJob>) {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(ACTIVE_JOBS_KEY, JSON.stringify(jobs));
  } catch {
    // ignore
  }
}

function getAllQueues(): Record<string, { id: string; text: string }[]> {
  if (typeof window === "undefined") return {};
  try {
    const raw = localStorage.getItem(PENDING_QUEUES_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}

function saveAllQueues(queues: Record<string, { id: string; text: string }[]>) {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(PENDING_QUEUES_KEY, JSON.stringify(queues));
  } catch {
    // ignore
  }
}

/**
 * Save an active job for a session.
 */
export function saveActiveJob(sessionId: string, jobId: string) {
  const jobs = getAllJobs();
  jobs[sessionId] = { jobId, timestamp: Date.now() };
  saveAllJobs(jobs);
}

/**
 * Get the active job for a session. 
 * Returns null if no job or if it's stale (> 30 min).
 */
export function getActiveJob(sessionId: string): string | null {
  const jobs = getAllJobs();
  const job = jobs[sessionId];
  if (!job) return null;
  
  if (Date.now() - job.timestamp > MAX_STALE_MS) {
    clearActiveJob(sessionId);
    return null;
  }
  
  return job.jobId;
}

/**
 * Stop tracking a job for a session (Success / Error / Completion).
 */
export function clearActiveJob(sessionId: string) {
  const jobs = getAllJobs();
  if (jobs[sessionId]) {
    delete jobs[sessionId];
    saveAllJobs(jobs);
  }
}

/**
 * Save the pending queue for a session.
 */
export function savePendingQueue(sessionId: string, queue: { id: string; text: string }[]) {
  const queues = getAllQueues();
  if (queue.length === 0) {
    delete queues[sessionId];
  } else {
    queues[sessionId] = queue;
  }
  saveAllQueues(queues);
}

/**
 * Get the pending queue for a session.
 */
export function getPendingQueue(sessionId: string): { id: string; text: string }[] {
  const queues = getAllQueues();
  return queues[sessionId] || [];
}

/**
 * Clear the pending queue for a session.
 */
export function clearPendingQueue(sessionId: string) {
  const queues = getAllQueues();
  if (queues[sessionId]) {
    delete queues[sessionId];
    saveAllQueues(queues);
  }
}
