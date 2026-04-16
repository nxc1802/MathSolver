"use client";

import { useMemo, useState } from "react";
import StaticGeometryCanvas from "@/components/geometry/StaticGeometryCanvas";
import Interactive3DCanvas from "@/components/geometry/Interactive3DCanvas";
import {
  FIXTURE_2D_WITH_TRIPLE_COORDS,
  FIXTURE_3D,
  FIXTURE_FLAG_MISMATCH,
} from "@/lib/geometry-fixtures";
import {
  pickCanvasMode,
  projectCoordinates2D,
  normalizeCoordinates3D,
} from "@/lib/geometry-display";

type FixtureKey = "2d" | "3d" | "mismatch";

type FixtureMeta = {
  is_3d?: boolean;
  coordinates: Record<string, number[]>;
  polygon_order?: string[];
  drawing_phases?: Array<{
    phase: number;
    label: string;
    points: string[];
    segments: string[][];
  }>;
};

const FIXTURES: Record<FixtureKey, FixtureMeta> = {
  "2d": FIXTURE_2D_WITH_TRIPLE_COORDS,
  "3d": FIXTURE_3D,
  mismatch: FIXTURE_FLAG_MISMATCH,
};

export default function GeometryFixturePage() {
  const [key, setKey] = useState<FixtureKey>("2d");
  const meta = FIXTURES[key];
  const mode = useMemo(
    () =>
      pickCanvasMode({
        is_3d: meta.is_3d,
        coordinates: meta.coordinates as Record<string, unknown>,
      }),
    [meta]
  );
  const coords2d = useMemo(
    () => projectCoordinates2D(meta.coordinates as Record<string, unknown>),
    [meta]
  );
  const coords3d = useMemo(
    () => normalizeCoordinates3D(meta.coordinates as Record<string, unknown>),
    [meta]
  );

  return (
    <div className="min-h-screen bg-[#0a0a0f] text-zinc-200 p-8 space-y-6">
      <h1 className="text-lg font-bold">Geometry fixture (dev)</h1>
      <p className="text-sm text-zinc-500 max-w-2xl">
        Regression UI for 2D projection of [x,y,z] payloads and 3D branching. Open{" "}
        <code className="text-indigo-400">/dev/geometry-fixture</code>.
      </p>
      <div className="flex gap-2 flex-wrap">
        {(["2d", "3d", "mismatch"] as const).map((k) => (
          <button
            key={k}
            type="button"
            onClick={() => setKey(k)}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium border ${
              key === k
                ? "border-indigo-500 bg-indigo-500/20 text-indigo-200"
                : "border-white/10 bg-white/5 text-zinc-400"
            }`}
          >
            {k}
          </button>
        ))}
      </div>
      <p className="text-xs font-mono text-zinc-500">
        pickCanvasMode → <span className="text-indigo-400">{mode}</span>
      </p>
      <div className="h-[420px] border border-white/10 rounded-2xl overflow-hidden bg-zinc-950">
        {mode === "3d" ? (
          <Interactive3DCanvas coordinates={coords3d} drawingPhases={meta.drawing_phases || []} />
        ) : (
          <StaticGeometryCanvas
            coordinates={coords2d}
            polygonOrder={meta.polygon_order || []}
            drawingPhases={meta.drawing_phases || []}
            circles={[]}
            lines={[]}
            rays={[]}
          />
        )}
      </div>
    </div>
  );
}
