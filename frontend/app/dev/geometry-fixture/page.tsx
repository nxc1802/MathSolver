"use client";

import { useMemo, useState } from "react";
import StaticGeometryCanvas from "@/components/geometry/StaticGeometryCanvas";
import Interactive3DCanvas from "@/components/geometry/Interactive3DCanvas";
import {
  FIXTURE_2D_WITH_TRIPLE_COORDS,
  FIXTURE_3D_PYRAMID,
  FIXTURE_3D_PRISM,
  FIXTURE_FLAG_MISMATCH,
} from "@/lib/geometry-fixtures";
import {
  pickCanvasMode,
  projectCoordinates2D,
  normalizeCoordinates3D,
} from "@/lib/geometry-display";
import type { VisAuxiliaryConstruction, DrawingPhase } from "@/types/geometry";

type FixtureKey = "2d" | "3d-pyramid" | "3d-prism" | "mismatch";

type FixtureMeta = {
  is_3d?: boolean;
  coordinates: Record<string, number[]>;
  polygon_order?: string[];
  faces?: string[][];
  drawing_phases?: DrawingPhase[];
  auxiliary?: VisAuxiliaryConstruction[];
};

const FIXTURES: Record<FixtureKey, FixtureMeta> = {
  "2d": FIXTURE_2D_WITH_TRIPLE_COORDS,
  "3d-pyramid": FIXTURE_3D_PYRAMID,
  "3d-prism": FIXTURE_3D_PRISM,
  mismatch: FIXTURE_FLAG_MISMATCH,
};

export default function GeometryFixturePage() {
  const [key, setKey] = useState<FixtureKey>("3d-pyramid");
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
      <h1 className="text-lg font-bold">Geometry Diagram Fixtures (3D Solids & 2D)</h1>
      <p className="text-sm text-zinc-500 max-w-2xl">
        Dev verification page for semi-transparent 3D solids, dynamic hidden-line rendering, and auxiliary right-angle markers.
      </p>
      <div className="flex gap-2 flex-wrap">
        {(["3d-pyramid", "3d-prism", "2d", "mismatch"] as const).map((k) => (
          <button
            key={k}
            type="button"
            onClick={() => setKey(k)}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium border transition-all ${
              key === k
                ? "border-indigo-500 bg-indigo-500/20 text-indigo-200 shadow-md"
                : "border-white/10 bg-white/5 text-zinc-400 hover:bg-white/10"
            }`}
          >
            {k}
          </button>
        ))}
      </div>
      <p className="text-xs font-mono text-zinc-500">
        Engine Mode → <span className="text-indigo-400 font-bold">{mode.toUpperCase()}</span>
      </p>
      <div className="h-[520px] border border-white/10 rounded-2xl overflow-hidden bg-zinc-950 shadow-2xl">
        {mode === "3d" ? (
          <Interactive3DCanvas
            coordinates={coords3d}
            drawingPhases={meta.drawing_phases || []}
            faces={meta.faces || []}
            auxiliary={meta.auxiliary || []}
          />
        ) : (
          <StaticGeometryCanvas
            coordinates={coords2d}
            polygonOrder={meta.polygon_order || []}
            drawingPhases={meta.drawing_phases || []}
            auxiliary={meta.auxiliary || []}
            circles={[]}
            lines={[]}
            rays={[]}
          />
        )}
      </div>
    </div>
  );
}
