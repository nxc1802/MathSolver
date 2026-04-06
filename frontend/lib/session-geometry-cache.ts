/**
 * session-geometry-cache.ts
 *
 * Persist & restore geometry state per sessionId using sessionStorage.
 * Data lives for the duration of the browser tab session (cleared on close).
 */

export interface GeometryState {
  coordinates: Record<string, [number, number]> | null;
  polygonOrder: string[] | null;
  circles: Array<{ center: string; radius: number }> | null;
  drawingPhases: Array<{
    phase: number;
    label: string;
    points: string[];
    segments: string[][];
  }> | null;
  videoUrl: string | null;
  activeJobId: string | null;
}

const PREFIX = "mathsolver_geo_";

function storageKey(sessionId: string): string {
  return `${PREFIX}${sessionId}`;
}

/**
 * Save geometry state for a given session into sessionStorage.
 * Silently ignores quota / parse errors.
 */
export function saveGeometryState(sessionId: string, state: GeometryState): void {
  if (typeof window === "undefined") return;
  try {
    const serialized = JSON.stringify(state);
    sessionStorage.setItem(storageKey(sessionId), serialized);
  } catch {
    // Quota exceeded or serialisation error — degrade gracefully
  }
}

/**
 * Load geometry state for a given session from sessionStorage.
 * Returns null if nothing is cached or if data is corrupt.
 */
export function loadGeometryState(sessionId: string): GeometryState | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = sessionStorage.getItem(storageKey(sessionId));
    if (!raw) return null;
    return JSON.parse(raw) as GeometryState;
  } catch {
    return null;
  }
}

/**
 * Remove cached geometry state for a specific session.
 */
export function clearGeometryState(sessionId: string): void {
  if (typeof window === "undefined") return;
  try {
    sessionStorage.removeItem(storageKey(sessionId));
  } catch {
    // ignore
  }
}
