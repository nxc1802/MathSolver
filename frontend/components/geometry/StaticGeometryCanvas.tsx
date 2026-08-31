"use client";

import { motion } from "framer-motion";
import { useMemo, useState, useRef } from "react";
import { ZoomIn, ZoomOut, RotateCcw } from "lucide-react";
import type { VisualizationGraph, VisAuxiliaryConstruction, DrawingPhase } from "@/types/geometry";
import { computeRightAnglePath2D } from "@/lib/geometry-display";

interface StaticGeometryCanvasProps {
  coordinates?: Record<string, [number, number] | number[]>;
  polygonOrder?: string[];
  circles?: Array<{ center: string; radius: number }>;
  lines?: Array<[string, string]>;
  rays?: Array<[string, string]>;
  drawingPhases?: DrawingPhase[];
  visualizationGraph?: VisualizationGraph | null;
  auxiliary?: VisAuxiliaryConstruction[] | null;
}

export default function StaticGeometryCanvas({
  coordinates,
  polygonOrder,
  circles,
  lines,
  rays,
  drawingPhases,
  visualizationGraph,
  auxiliary,
}: StaticGeometryCanvasProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [scale, setScale] = useState(1);
  const [offset, setOffset] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const dragStart = useRef({ x: 0, y: 0 });
  const dragStartOffset = useRef({ x: 0, y: 0 });

  const {
    viewBox,
    points,
    phasePaths,
    polygonFillPath,
    rightAnglePaths,
    circlePaths,
    linePaths,
    rayPaths,
    spanX,
  } = useMemo(() => {
    if (!coordinates || Object.keys(coordinates).length === 0) {
      return {
        viewBox: "0 0 100 100",
        points: [],
        phasePaths: [],
        polygonFillPath: "",
        rightAnglePaths: [],
        circlePaths: [],
        linePaths: [],
        rayPaths: [],
        spanX: 100,
      };
    }

    const entries = Object.entries(coordinates);
    let minX = Infinity,
      maxX = -Infinity,
      minY = Infinity,
      maxY = -Infinity;

    const parsedPoints = entries.map(([label, raw]) => {
      const arr = Array.isArray(raw) ? raw : [];
      const px = Number(arr[0]) || 0;
      const py = (Number(arr[1]) || 0) * -1; // Invert Y for standard Cartesian 2D SVG
      minX = Math.min(minX, px);
      maxX = Math.max(maxX, px);
      minY = Math.min(minY, py);
      maxY = Math.max(maxY, py);

      const vMeta = visualizationGraph?.vertices?.[label];
      const isAux = vMeta?.kind === "AUXILIARY" || vMeta?.role === "foot" || vMeta?.role === "midpoint" || vMeta?.role === "center";

      return {
        label,
        x: px,
        y: py,
        role: vMeta?.role || "vertex",
        isAuxiliary: isAux,
      };
    });

    // Circles
    const circleParsed = (circles || [])
      .map((c) => {
        const centerCoords = coordinates[c.center];
        if (!centerCoords) return null;
        const r = Number(c.radius);
        const cx = Number(centerCoords[0]) || 0;
        const cy = (Number(centerCoords[1]) || 0) * -1;
        minX = Math.min(minX, cx - r);
        maxX = Math.max(maxX, cx + r);
        minY = Math.min(minY, cy - r);
        maxY = Math.max(maxY, cy + r);
        return { cx, cy, r };
      })
      .filter(Boolean) as Array<{ cx: number; cy: number; r: number }>;

    const padding = Math.max((maxX - minX) * 0.25, (maxY - minY) * 0.25, 14);
    const vb = `${minX - padding} ${minY - padding} ${maxX - minX + padding * 2} ${maxY - minY + padding * 2}`;
    const sX = maxX - minX + padding * 2;

    // Polygon Fill Path
    let polyFillD = "";
    const polyPtsOrder = polygonOrder || (visualizationGraph?.faces ? Object.values(visualizationGraph.faces)[0]?.vertices : null);
    if (polyPtsOrder && polyPtsOrder.length >= 3) {
      const ordered = polyPtsOrder
        .map((l) => parsedPoints.find((p) => p.label === l))
        .filter(Boolean) as typeof parsedPoints;
      if (ordered.length >= 3) {
        polyFillD = ordered.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x} ${p.y}`).join(" ") + " Z";
      }
    }

    // Phase Segments (Edges)
    const resPhasePaths: Array<{ d: string; phase: number; isDashed: boolean }> = [];

    // From Visualization Graph edges or drawing phases
    if (visualizationGraph?.edges && Object.keys(visualizationGraph.edges).length > 0) {
      const p1Segs: string[] = [];
      const p2Segs: string[] = [];

      Object.values(visualizationGraph.edges).forEach((e) => {
        const pt1 = parsedPoints.find((p) => p.label === e.source);
        const pt2 = parsedPoints.find((p) => p.label === e.target);
        if (pt1 && pt2) {
          const d = `M ${pt1.x} ${pt1.y} L ${pt2.x} ${pt2.y}`;
          if (e.style === "dashed" || e.kind === "AUXILIARY" || e.role === "altitude" || e.role === "median" || e.role === "projection") {
            p2Segs.push(d);
          } else {
            p1Segs.push(d);
          }
        }
      });

      if (p1Segs.length > 0) resPhasePaths.push({ d: p1Segs.join(" "), phase: 1, isDashed: false });
      if (p2Segs.length > 0) resPhasePaths.push({ d: p2Segs.join(" "), phase: 2, isDashed: true });
    } else if (drawingPhases && drawingPhases.length > 0) {
      drawingPhases.forEach((phase) => {
        if (!phase.segments || phase.segments.length === 0) return;
        const segmentsD: string[] = [];
        phase.segments.forEach(([p1Label, p2Label]) => {
          const pt1 = parsedPoints.find((p) => p.label === p1Label);
          const pt2 = parsedPoints.find((p) => p.label === p2Label);
          if (pt1 && pt2) {
            segmentsD.push(`M ${pt1.x} ${pt1.y} L ${pt2.x} ${pt2.y}`);
          }
        });
        if (segmentsD.length > 0) {
          resPhasePaths.push({ d: segmentsD.join(" "), phase: phase.phase, isDashed: phase.phase >= 2 });
        }
      });
    } else if (polyFillD) {
      resPhasePaths.push({ d: polyFillD, phase: 1, isDashed: false });
    }

    // Right-Angle Markers (Perpendicular feet)
    const rightAngles: string[] = [];
    const auxList = auxiliary || visualizationGraph?.auxiliary || [];
    const markerSize = Math.max(sX * 0.035, 8);

    auxList.forEach((aux) => {
      aux.perpendicular_marks?.forEach((mark) => {
        const vPt = parsedPoints.find((p) => p.label === mark.vertex);
        const p1Pt = parsedPoints.find((p) => p.label === mark.lines[0]);
        const p2Pt = parsedPoints.find((p) => p.label === mark.lines[1]);
        if (vPt && p1Pt && p2Pt) {
          const pathD = computeRightAnglePath2D(vPt, p1Pt, p2Pt, markerSize);
          if (pathD) rightAngles.push(pathD);
        }
      });
    });

    // Infinite Lines
    const resLinePaths: string[] = [];
    (lines || []).forEach(([p1, p2]) => {
      const pt1 = parsedPoints.find((p) => p.label === p1);
      const pt2 = parsedPoints.find((p) => p.label === p2);
      if (pt1 && pt2) {
        const dx = pt2.x - pt1.x;
        const dy = pt2.y - pt1.y;
        resLinePaths.push(`M ${pt1.x - dx * 2000} ${pt1.y - dy * 2000} L ${pt1.x + dx * 2000} ${pt1.y + dy * 2000}`);
      }
    });

    // Rays
    const resRayPaths: string[] = [];
    (rays || []).forEach(([p1, p2]) => {
      const pt1 = parsedPoints.find((p) => p.label === p1);
      const pt2 = parsedPoints.find((p) => p.label === p2);
      if (pt1 && pt2) {
        const dx = pt2.x - pt1.x;
        const dy = pt2.y - pt1.y;
        resRayPaths.push(`M ${pt1.x} ${pt1.y} L ${pt1.x + dx * 2000} ${pt1.y + dy * 2000}`);
      }
    });

    return {
      viewBox: vb,
      points: parsedPoints,
      phasePaths: resPhasePaths,
      polygonFillPath: polyFillD,
      rightAnglePaths: rightAngles,
      circlePaths: circleParsed,
      linePaths: resLinePaths,
      rayPaths: resRayPaths,
      spanX: sX,
    };
  }, [coordinates, polygonOrder, circles, lines, rays, drawingPhases, visualizationGraph, auxiliary]);

  const handleWheel = (e: React.WheelEvent) => {
    if (e.ctrlKey || e.metaKey) {
      e.preventDefault();
      const delta = e.deltaY > 0 ? 0.9 : 1.1;
      setScale((s) => Math.min(Math.max(s * delta, 0.4), 6));
    } else {
      const rect = containerRef.current?.getBoundingClientRect();
      if (!rect) return;
      const vbWidth = Number(viewBox.split(" ")[2]);
      const ratio = vbWidth / rect.width;

      setOffset((prev) => ({
        x: prev.x - (e.deltaX * ratio) / scale,
        y: prev.y - (e.deltaY * ratio) / scale,
      }));
    }
  };

  const handleMouseDown = (e: React.MouseEvent) => {
    if (e.button !== 0) return;
    setIsDragging(true);
    dragStart.current = { x: e.clientX, y: e.clientY };
    dragStartOffset.current = { ...offset };
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDragging || !containerRef.current) return;

    const rect = containerRef.current.getBoundingClientRect();
    const vbWidth = Number(viewBox.split(" ")[2]);
    const ratio = vbWidth / rect.width;

    const dx = ((e.clientX - dragStart.current.x) * ratio) / scale;
    const dy = ((e.clientY - dragStart.current.y) * ratio) / scale;

    setOffset({
      x: dragStartOffset.current.x + dx,
      y: dragStartOffset.current.y + dy,
    });
  };

  const handleMouseUp = () => setIsDragging(false);

  const resetView = () => {
    setScale(1);
    setOffset({ x: 0, y: 0 });
  };

  if (!coordinates || Object.keys(coordinates).length === 0) {
    return (
      <div className="bg-[var(--card-bg)] border border-[var(--border)] rounded-2xl overflow-hidden flex-1 min-h-0 relative flex items-center justify-center p-8">
        <p className="text-xs font-mono text-[var(--text-muted)] animate-pulse">
          Đang khởi tạo tọa độ không gian 2D...
        </p>
      </div>
    );
  }

  const r = Math.max(spanX * 0.014, 2.5);
  const fontSize = Math.max(spanX * 0.038, 7.5);

  return (
    <div
      ref={containerRef}
      className="bg-[var(--card-bg)] border border-[var(--border)] rounded-2xl overflow-hidden flex-1 min-h-0 relative select-none cursor-grab active:cursor-grabbing shadow-inner"
      onWheel={handleWheel}
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseUp}
    >
      {/* Background blueprint grid */}
      <div className="absolute inset-0 bg-grid-pattern opacity-60 pointer-events-none" />

      {/* Floating HUD Controls */}
      <div className="absolute top-3 right-3 flex flex-col gap-1.5 z-20">
        <button
          type="button"
          onClick={() => setScale((s) => Math.min(s * 1.25, 6))}
          className="p-2 bg-[var(--panel-glass)] hover:bg-white/10 border border-[var(--border)] rounded-xl text-zinc-300 hover:text-white backdrop-blur-md shadow-sm active:scale-95 transition-all"
          title="Phóng to (Zoom In)"
        >
          <ZoomIn className="w-3.5 h-3.5" />
        </button>
        <button
          type="button"
          onClick={() => setScale((s) => Math.max(s / 1.25, 0.4))}
          className="p-2 bg-[var(--panel-glass)] hover:bg-white/10 border border-[var(--border)] rounded-xl text-zinc-300 hover:text-white backdrop-blur-md shadow-sm active:scale-95 transition-all"
          title="Thu nhỏ (Zoom Out)"
        >
          <ZoomOut className="w-3.5 h-3.5" />
        </button>
        <button
          type="button"
          onClick={resetView}
          className="p-2 bg-[var(--panel-glass)] hover:bg-white/10 border border-[var(--border)] rounded-xl text-zinc-300 hover:text-white backdrop-blur-md shadow-sm active:scale-95 transition-all"
          title="Căn giữa lại (Reset View)"
        >
          <RotateCcw className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Mode Badge Header */}
      <div className="absolute top-3 left-3 z-20">
        <div className="flex items-center gap-2 px-3 py-1 bg-[var(--panel-glass)] border border-[var(--border)] rounded-full backdrop-blur-md shadow-sm">
          <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
          <span className="text-[10px] font-mono font-semibold text-[var(--text-secondary)] uppercase tracking-wider">
            2D Geometry Canvas
          </span>
        </div>
      </div>

      {/* Main SVG Geometry */}
      <svg
        viewBox={viewBox}
        className="w-full h-full"
        preserveAspectRatio="xMidYMid meet"
      >
        <motion.g
          animate={{
            scale,
            x: offset.x,
            y: offset.y,
          }}
          transition={
            isDragging
              ? { type: "tween", duration: 0 }
              : { type: "spring", stiffness: 350, damping: 32 }
          }
          style={{ originX: "center", originY: "center" }}
        >
          {/* 1. Subtle Polygon Face Fill */}
          {polygonFillPath && (
            <path
              d={polygonFillPath}
              fill="rgba(99, 102, 241, 0.12)"
              stroke="none"
            />
          )}

          {/* 2. Phase Drawing Segments */}
          {phasePaths.map((p, idx) => (
            <path
              key={`phase-${idx}`}
              d={p.d}
              fill="none"
              stroke={p.isDashed ? "rgba(192, 132, 252, 0.9)" : "rgba(129, 140, 248, 0.95)"}
              strokeWidth={p.isDashed ? "1.6" : "2.2"}
              strokeDasharray={p.isDashed ? "4 3" : "none"}
              vectorEffect="non-scaling-stroke"
              strokeLinejoin="round"
              strokeLinecap="round"
            />
          ))}

          {/* 3. Perpendicular Right-Angle Markers */}
          {rightAnglePaths.map((d, i) => (
            <path
              key={`right-angle-${i}`}
              d={d}
              fill="none"
              stroke="#f59e0b"
              strokeWidth="1.6"
              vectorEffect="non-scaling-stroke"
              strokeLinejoin="miter"
            />
          ))}

          {/* 4. Infinite Lines */}
          {linePaths.map((d, i) => (
            <path
              key={`line-${i}`}
              d={d}
              fill="none"
              stroke="rgba(99, 102, 241, 0.5)"
              strokeWidth="1.2"
              vectorEffect="non-scaling-stroke"
              strokeDasharray="8 4"
            />
          ))}

          {/* 5. Rays */}
          {rayPaths.map((d, i) => (
            <path
              key={`ray-${i}`}
              d={d}
              fill="none"
              stroke="rgba(168, 85, 247, 0.5)"
              strokeWidth="1.2"
              vectorEffect="non-scaling-stroke"
              strokeDasharray="6 3"
            />
          ))}

          {/* 6. Circles */}
          {circlePaths.map((c, i) => (
            <circle
              key={`circle-${i}`}
              cx={c.cx}
              cy={c.cy}
              r={c.r}
              fill="rgba(56, 189, 248, 0.06)"
              stroke="rgba(147, 197, 253, 0.7)"
              strokeWidth="1.4"
              vectorEffect="non-scaling-stroke"
              strokeDasharray="4 2"
            />
          ))}

          {/* 7. Vertex Points and Labels */}
          {points.map((p) => (
            <g key={p.label}>
              <circle
                cx={p.x}
                cy={p.y}
                r={p.isAuxiliary ? r * 0.9 : r}
                fill={p.isAuxiliary ? "#fbbf24" : "#ffffff"}
                stroke={p.isAuxiliary ? "#d97706" : "#6366f1"}
                strokeWidth="1.5"
                vectorEffect="non-scaling-stroke"
              />
              <text
                x={p.x + r * 1.8}
                y={p.y - r * 1.8}
                fill={p.isAuxiliary ? "#fef08a" : "#ffffff"}
                fontSize={fontSize}
                fontFamily="var(--font-geist-mono), monospace"
                fontWeight="700"
                className="pointer-events-none select-none drop-shadow-[0_2px_4px_rgba(0,0,0,0.9)]"
              >
                {p.label}
              </text>
            </g>
          ))}
        </motion.g>
      </svg>
    </div>
  );
}
