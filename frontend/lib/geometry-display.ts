/**
 * Single place for 2D vs 3D canvas selection and coordinate normalization.
 * Set NEXT_PUBLIC_DEBUG_GEOMETRY=1 for console diagnostics / BE handoff logs.
 */

export const DEBUG_GEOMETRY =
  process.env.NEXT_PUBLIC_DEBUG_GEOMETRY === "1" ||
  process.env.NEXT_PUBLIC_DEBUG_GEOMETRY === "true";

const Z_EPS = 1e-9;

export type CanvasMode = "2d" | "3d";

export type CoordinatesRaw = Record<string, unknown>;

function coordDim(v: unknown): number {
  return Array.isArray(v) ? v.length : 0;
}

/** True if any point has a third component significantly non-zero. */
export function coordinatesHaveNonZeroZ(coords: CoordinatesRaw): boolean {
  for (const v of Object.values(coords)) {
    if (!Array.isArray(v) || v.length < 3) continue;
    const z = Number(v[2]);
    if (Number.isFinite(z) && Math.abs(z) > Z_EPS) return true;
  }
  return false;
}

/**
 * Pick canvas mode: prefer explicit backend flag; reconcile with actual Z.
 * Flat payloads with is_3d true still use 2D canvas (better UX); log for BE when debug on.
 */
export function pickCanvasMode(meta: {
  is_3d?: boolean;
  is3d?: boolean;
  coordinates?: CoordinatesRaw;
}): CanvasMode {
  const coords = meta.coordinates ?? {};
  const flag = meta.is_3d ?? meta.is3d;
  const hasZ = coordinatesHaveNonZeroZ(coords);

  if (flag === false) return "2d";
  if (flag === true && !hasZ) return "2d";
  if (flag === true && hasZ) return "3d";
  return hasZ ? "3d" : "2d";
}

export function projectCoordinates2D(coords: CoordinatesRaw): Record<string, [number, number]> {
  const out: Record<string, [number, number]> = {};
  for (const [label, v] of Object.entries(coords)) {
    if (!Array.isArray(v) || v.length < 2) continue;
    const x = Number(v[0]);
    const y = Number(v[1]);
    if (!Number.isFinite(x) || !Number.isFinite(y)) continue;
    out[label] = [x, y];
  }
  return out;
}

export function normalizeCoordinates3D(coords: CoordinatesRaw): Record<string, [number, number, number]> {
  const out: Record<string, [number, number, number]> = {};
  for (const [label, v] of Object.entries(coords)) {
    if (!Array.isArray(v) || v.length < 2) continue;
    const x = Number(v[0]);
    const y = Number(v[1]);
    const z = v.length >= 3 ? Number(v[2]) : 0;
    if (!Number.isFinite(x) || !Number.isFinite(y) || !Number.isFinite(z)) continue;
    out[label] = [x, y, z];
  }
  return out;
}

export function logGeometryDebug(context: string, meta: unknown): void {
  if (!DEBUG_GEOMETRY || !meta || typeof meta !== "object") return;
  const m = meta as Record<string, unknown>;
  const coords = (m.coordinates as CoordinatesRaw) ?? {};
  const phases = (m.drawing_phases ?? m.drawingPhases) as unknown[] | undefined;
  const mode = pickCanvasMode({
    is_3d: m.is_3d as boolean | undefined,
    is3d: m.is3d as boolean | undefined,
    coordinates: coords,
  });
  console.info(`[geometry-debug] ${context}`, {
    mode,
    is_3d: m.is_3d,
    is3d: m.is3d,
    hasNonZeroZ: coordinatesHaveNonZeroZ(coords),
    pointDims: Object.fromEntries(Object.entries(coords).map(([k, v]) => [k, coordDim(v)])),
    drawingPhasesLength: Array.isArray(phases) ? phases.length : 0,
  });
}

/** Structured payload for BE when metadata disagrees with geometry (debug only). */
export function logGeometryBeHandoff(reason: string, meta: unknown): void {
  if (!DEBUG_GEOMETRY) return;
  const m = meta && typeof meta === "object" ? (meta as Record<string, unknown>) : {};
  console.warn("[geometry-be-handoff]", {
    reason,
    is_3d: m.is_3d,
    is3d: m.is3d,
    coordinates: m.coordinates,
    polygon_order: m.polygon_order ?? m.polygonOrder,
    drawing_phases: m.drawing_phases ?? m.drawingPhases,
  });
}

export function detectGeometryInconsistency(meta: {
  is_3d?: boolean;
  is3d?: boolean;
  coordinates?: CoordinatesRaw;
}): string | null {
  const coords = meta.coordinates ?? {};
  const flag = meta.is_3d ?? meta.is3d;
  const hasZ = coordinatesHaveNonZeroZ(coords);
  if (flag === false && hasZ) return "is_3d_false_but_nonzero_z";
  if (flag === true && !hasZ) return "is_3d_true_but_all_z_zero";
  return null;
}
