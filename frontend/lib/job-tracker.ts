/**
 * job-tracker.ts
 * 
 * Persistent (localStorage) mapping of sessionId -> { jobId, timestamp }.
 * Used to "re-attach" to a running solve if the user switches sessions.
 */

interface ActiveJob {
  jobId: string;
  timestamp: number;
}

const STORAGE_KEY = "mathsolver_active_jobs";
const MAX_STALE_MS = 30 * 60 * 1000; // 30 minutes

function getAllJobs(): Record<string, ActiveJob> {
  if (typeof window === "undefined") return {};
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}

function saveAllJobs(jobs: Record<string, ActiveJob>) {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(jobs));
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
