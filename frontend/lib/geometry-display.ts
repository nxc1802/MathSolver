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

/**
 * Triangulate an ordered list of 3D points for Three.js BufferGeometry.
 * Supports triangles, convex quads, and n-gons.
 */
export function triangulate3DPolygon(points: Array<[number, number, number]>): number[] {
  if (points.length < 3) return [];
  const vertices: number[] = [];
  
  // Fan triangulation from index 0
  const v0 = points[0];
  for (let i = 1; i < points.length - 1; i++) {
    const v1 = points[i];
    const v2 = points[i + 1];
    vertices.push(v0[0], v0[1], v0[2]);
    vertices.push(v1[0], v1[1], v1[2]);
    vertices.push(v2[0], v2[1], v2[2]);
  }
  return vertices;
}

/**
 * Compute 3D right-angle indicator segments at vertex V formed by (V->P1) and (V->P2).
 * Returns array of [start, end] vector pairs in Three.js coordinate system.
 */
export function computeRightAngleSegments3D(
  v: [number, number, number],
  p1: [number, number, number],
  p2: [number, number, number],
  size: number = 0.25
): Array<[[number, number, number], [number, number, number]]> {
  const d1 = [p1[0] - v[0], p1[1] - v[1], p1[2] - v[2]];
  const d2 = [p2[0] - v[0], p2[1] - v[1], p2[2] - v[2]];
  const len1 = Math.hypot(d1[0], d1[1], d1[2]);
  const len2 = Math.hypot(d2[0], d2[1], d2[2]);

  if (len1 < 1e-4 || len2 < 1e-4) return [];

  const actualSize = Math.min(size, len1 * 0.25, len2 * 0.25);
  const u = [d1[0] / len1 * actualSize, d1[1] / len1 * actualSize, d1[2] / len1 * actualSize];
  const w = [d2[0] / len2 * actualSize, d2[1] / len2 * actualSize, d2[2] / len2 * actualSize];

  const corner1: [number, number, number] = [v[0] + u[0], v[1] + u[1], v[2] + u[2]];
  const cornerMid: [number, number, number] = [v[0] + u[0] + w[0], v[1] + u[1] + w[1], v[2] + u[2] + w[2]];
  const corner2: [number, number, number] = [v[0] + w[0], v[1] + w[1], v[2] + w[2]];

  return [
    [corner1, cornerMid],
    [cornerMid, corner2],
  ];
}

/**
 * Compute 2D right-angle indicator SVG path string at vertex V formed by (V->P1) and (V->P2).
 */
export function computeRightAnglePath2D(
  v: { x: number; y: number },
  p1: { x: number; y: number },
  p2: { x: number; y: number },
  size: number = 10
): string {
  const dx1 = p1.x - v.x;
  const dy1 = p1.y - v.y;
  const dx2 = p2.x - v.x;
  const dy2 = p2.y - v.y;
  const len1 = Math.hypot(dx1, dy1);
  const len2 = Math.hypot(dx2, dy2);

  if (len1 < 1e-4 || len2 < 1e-4) return "";

  const actualSize = Math.min(size, len1 * 0.25, len2 * 0.25);
  const ux = (dx1 / len1) * actualSize;
  const uy = (dy1 / len1) * actualSize;
  const wx = (dx2 / len2) * actualSize;
  const wy = (dy2 / len2) * actualSize;

  const c1x = v.x + ux;
  const c1y = v.y + uy;
  const cmx = v.x + ux + wx;
  const cmy = v.y + uy + wy;
  const c2x = v.x + wx;
  const c2y = v.y + wy;

  return `M ${c1x} ${c1y} L ${cmx} ${cmy} L ${c2x} ${c2y}`;
}
