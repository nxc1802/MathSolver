"use client";

import { motion } from "framer-motion";
import { useMemo, useState, useRef } from "react";
import { ZoomIn, ZoomOut, RotateCcw, Eye, Layers, Compass } from "lucide-react";
import type {
  VisualizationGraph,
  VisAuxiliaryConstruction,
  DrawingPhase,
  PerpendicularMark,
  AngleMark,
  EqualTickMark,
  ParallelMark,
} from "@/types/geometry";
import {
  computeRightAnglePath2D,
  computeAngleArc2D,
  computeEqualTickSegments2D,
  computeParallelArrow2D,
} from "@/lib/geometry-display";

interface StaticGeometryCanvasProps {
  coordinates?: Record<string, [number, number] | [number, number, number] | number[]>;
  polygonOrder?: string[];
  faces?: string[][];
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
  faces,
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
  const [showFaces, setShowFaces] = useState(true);
  const [showAuxiliary, setShowAuxiliary] = useState(true);
  const [showLabels, setShowLabels] = useState(true);

  const dragStart = useRef({ x: 0, y: 0 });
  const dragStartOffset = useRef({ x: 0, y: 0 });

  const {
    viewBox,
    points,
    faceFills,
    phasePaths,
    rightAnglePaths,
    angleArcs,
    equalTicks,
    parallelArrows,
    circlePaths,
    linePaths,
    rayPaths,
    spanX,
  } = useMemo(() => {
    if (!coordinates || Object.keys(coordinates).length === 0) {
      return {
        viewBox: "0 0 100 100",
        points: [],
        faceFills: [],
        phasePaths: [],
        rightAnglePaths: [],
        angleArcs: [],
        equalTicks: [],
        parallelArrows: [],
        circlePaths: [],
        linePaths: [],
        rayPaths: [],
        spanX: 100,
      };
    }

    let minX = Infinity,
      maxX = -Infinity,
      minY = Infinity,
      maxY = -Infinity;

    const parsedPoints = Object.entries(coordinates).map(([label, raw]) => {
      const arr = Array.isArray(raw) ? raw : [];
      const px = Number(arr[0]) || 0;
      const py = (Number(arr[1]) || 0) * -1; // Invert Y for standard Cartesian 2D SVG
      minX = Math.min(minX, px);
      maxX = Math.max(maxX, px);
      minY = Math.min(minY, py);
      maxY = Math.max(maxY, py);

      const vMeta = visualizationGraph?.vertices?.[label];
      const isAux =
        vMeta?.kind === "AUXILIARY" ||
        vMeta?.role === "foot" ||
        vMeta?.role === "midpoint" ||
        vMeta?.role === "center";
      const isApex = vMeta?.role === "apex";

      return {
        label,
        x: px,
        y: py,
        role: vMeta?.role || "vertex",
        isAuxiliary: isAux,
        isApex,
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

    const rawSpanX = Math.max(maxX - minX, 1);
    const rawSpanY = Math.max(maxY - minY, 1);
    const maxSpan = Math.max(rawSpanX, rawSpanY);
    const padding = maxSpan * 0.22;
    const vb = `${minX - padding} ${minY - padding} ${maxX - minX + padding * 2} ${maxY - minY + padding * 2}`;
    const sX = maxX - minX + padding * 2;
    const markerSize = sX * 0.045;

    // 1. Multi-Face Semi-Transparent Fills
    const allFaces: Array<{ d: string; role: string; opacity: number }> = [];

    const faceSource =
      faces && faces.length > 0
        ? faces.map((verts) => ({ vertices: verts, role: "polygon_face", opacity: 0.12 }))
        : visualizationGraph?.faces && Object.keys(visualizationGraph.faces).length > 0
        ? Object.values(visualizationGraph.faces)
        : polygonOrder && polygonOrder.length >= 3
        ? [{ vertices: polygonOrder, role: "polygon_face", opacity: 0.12 }]
        : [];

    faceSource.forEach((f) => {
      const ordered = f.vertices
        .map((l) => parsedPoints.find((p) => p.label === l))
        .filter(Boolean) as typeof parsedPoints;
      if (ordered.length >= 3) {
        const d = ordered.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x} ${p.y}`).join(" ") + " Z";
        allFaces.push({
          d,
          role: f.role || "polygon_face",
          opacity: f.opacity || 0.12,
        });
      }
    });

    // 2. Phase Segments
    const resPhasePaths: Array<{ d: string; role: string; isDashed: boolean; isAuxiliary: boolean; strokeColor: string }> = [];

    if (visualizationGraph?.edges && Object.keys(visualizationGraph.edges).length > 0) {
      Object.values(visualizationGraph.edges).forEach((e) => {
        const pt1 = parsedPoints.find((p) => p.label === e.source);
        const pt2 = parsedPoints.find((p) => p.label === e.target);
        if (pt1 && pt2) {
          const d = `M ${pt1.x} ${pt1.y} L ${pt2.x} ${pt2.y}`;
          const isDashed = Boolean(e.is_hidden) || e.style === "dashed";
          const isAlt = e.role === "altitude" || e.role === "height";
          const isDiag = e.role === "diagonal";
          const isProj = e.role === "projection";
          const isAux = e.kind === "AUXILIARY" || isAlt || isProj || isDiag || e.role === "auxiliary";

          const color = isAlt ? "#c084fc" : isProj ? "#fbbf24" : isDiag ? "#93c5fd" : isDashed ? "#818cf8" : "#e0e7ff";

          resPhasePaths.push({ d, role: e.role, isDashed, isAuxiliary: isAux, strokeColor: color });
        }
      });
    } else if (drawingPhases && drawingPhases.length > 0) {
      drawingPhases.forEach((phase) => {
        if (!phase.segments || phase.segments.length === 0) return;
        const isAux = phase.phase >= 2;
        phase.segments.forEach(([p1Label, p2Label]) => {
          const pt1 = parsedPoints.find((p) => p.label === p1Label);
          const pt2 = parsedPoints.find((p) => p.label === p2Label);
          if (pt1 && pt2) {
            resPhasePaths.push({
              d: `M ${pt1.x} ${pt1.y} L ${pt2.x} ${pt2.y}`,
              role: isAux ? "auxiliary" : "edge",
              isDashed: isAux,
              isAuxiliary: isAux,
              strokeColor: isAux ? "#c084fc" : "#e0e7ff",
            });
          }
        });
      });
    }

    // 3. Right-Angle Markers
    const rightAngles: string[] = [];
    const perpList: PerpendicularMark[] = [...(visualizationGraph?.perpendicular_marks || []), ...(auxiliary || visualizationGraph?.auxiliary || []).flatMap(a => a.perpendicular_marks || [])];
    perpList.forEach((mark) => {
      const vPt = parsedPoints.find((p) => p.label === mark.vertex);
      const p1Pt = parsedPoints.find((p) => p.label === mark.lines[0]);
      const p2Pt = parsedPoints.find((p) => p.label === mark.lines[1]);
      if (vPt && p1Pt && p2Pt) {
        const pathD = computeRightAnglePath2D(vPt, p1Pt, p2Pt, markerSize);
        if (pathD) rightAngles.push(pathD);
      }
    });

    // 4. Angle Arcs
    const arcs: Array<{ path: string; labelX: number; labelY: number; label: string }> = [];
    const angleList: AngleMark[] = [...(visualizationGraph?.angle_marks || []), ...(auxiliary || visualizationGraph?.auxiliary || []).flatMap(a => a.angle_marks || [])];
    angleList.forEach((mark) => {
      const vPt = parsedPoints.find((p) => p.label === mark.vertex);
      const p1Pt = parsedPoints.find((p) => p.label === mark.lines[0]);
      const p2Pt = parsedPoints.find((p) => p.label === mark.lines[1]);
      if (vPt && p1Pt && p2Pt) {
        const arcData = computeAngleArc2D(vPt, p1Pt, p2Pt, markerSize * 1.2);
        if (arcData && arcData.path) {
          arcs.push({
            ...arcData,
            label: mark.label || (mark.degrees ? `${mark.degrees}°` : ""),
          });
        }
      }
    });

    // 5. Equal Length Ticks
    const equalTickSegs: Array<{ x1: number; y1: number; x2: number; y2: number }> = [];
    const tickList: EqualTickMark[] = [...(visualizationGraph?.equal_ticks || []), ...(auxiliary || visualizationGraph?.auxiliary || []).flatMap(a => a.equal_ticks || [])];
    tickList.forEach((mark) => {
      if (mark.segment && mark.segment.length >= 2) {
        const pt1 = parsedPoints.find((p) => p.label === mark.segment[0]);
        const pt2 = parsedPoints.find((p) => p.label === mark.segment[1]);
        if (pt1 && pt2) {
          const segs = computeEqualTickSegments2D(pt1, pt2, mark.ticks || 1, markerSize * 0.4);
          equalTickSegs.push(...segs);
        }
      }
    });

    // 6. Parallel Arrows
    const parallelPaths: string[] = [];
    const parList: ParallelMark[] = [...(visualizationGraph?.parallel_marks || []), ...(auxiliary || visualizationGraph?.auxiliary || []).flatMap(a => a.parallel_marks || [])];
    parList.forEach((mark) => {
      mark.segments.forEach(([p1Label, p2Label]) => {
        const pt1 = parsedPoints.find((p) => p.label === p1Label);
        const pt2 = parsedPoints.find((p) => p.label === p2Label);
        if (pt1 && pt2) {
          const arrowPath = computeParallelArrow2D(pt1, pt2, markerSize * 0.45);
          if (arrowPath) parallelPaths.push(arrowPath);
        }
      });
    });

    // 7. Infinite lines
    const resLinePaths: string[] = [];
    (lines || []).forEach(([p1Label, p2Label]) => {
      const pt1 = parsedPoints.find((p) => p.label === p1Label);
      const pt2 = parsedPoints.find((p) => p.label === p2Label);
      if (pt1 && pt2) {
        const dx = pt2.x - pt1.x;
        const dy = pt2.y - pt1.y;
        resLinePaths.push(`M ${pt1.x - dx * 10} ${pt1.y - dy * 10} L ${pt2.x + dx * 10} ${pt2.y + dy * 10}`);
      }
    });

    // 8. Rays
    const resRayPaths: string[] = [];
    (rays || []).forEach(([originLabel, throughLabel]) => {
      const pt1 = parsedPoints.find((p) => p.label === originLabel);
      const pt2 = parsedPoints.find((p) => p.label === throughLabel);
      if (pt1 && pt2) {
        const dx = pt2.x - pt1.x;
        const dy = pt2.y - pt1.y;
        resRayPaths.push(`M ${pt1.x} ${pt1.y} L ${pt1.x + dx * 10} ${pt1.y + dy * 10}`);
      }
    });

    return {
      viewBox: vb,
      points: parsedPoints,
      faceFills: allFaces,
      phasePaths: resPhasePaths,
      rightAnglePaths: rightAngles,
      angleArcs: arcs,
      equalTicks: equalTickSegs,
      parallelArrows: parallelPaths,
      circlePaths: circleParsed,
      linePaths: resLinePaths,
      rayPaths: resRayPaths,
      spanX: sX,
    };
  }, [coordinates, polygonOrder, faces, circles, lines, rays, drawingPhases, visualizationGraph, auxiliary]);

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
    setOffset({ x: dragStartOffset.current.x + dx, y: dragStartOffset.current.y + dy });
  };

  const handleMouseUp = () => setIsDragging(false);
  const resetView = () => { setScale(1); setOffset({ x: 0, y: 0 }); };

  if (!coordinates || Object.keys(coordinates).length === 0) {
    return (
      <div className="bg-[var(--card-bg)] border border-[var(--border)] rounded-2xl overflow-hidden flex-1 min-h-0 relative flex items-center justify-center p-8">
        <p className="text-xs font-mono text-[var(--text-muted)] animate-pulse">Đang khởi tạo tọa độ...</p>
      </div>
    );
  }

  const r = spanX * 0.016;
  const fontSize = spanX * 0.045;
  const visiblePhasePaths = showAuxiliary ? phasePaths : phasePaths.filter((p) => !p.isAuxiliary);
  const visiblePoints = showAuxiliary ? points : points.filter((p) => !p.isAuxiliary);

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
      <div className="absolute inset-0 bg-grid-pattern opacity-60 pointer-events-none" />

      <div className="absolute top-3 right-3 flex items-center gap-1.5 z-20">
        <button
          type="button"
          onClick={() => setShowFaces((s) => !s)}
          className={`p-2 border rounded-xl backdrop-blur-md shadow-sm active:scale-95 transition-all text-xs flex items-center gap-1 ${
            showFaces ? "bg-indigo-950/80 text-indigo-300 border-indigo-500/40" : "bg-zinc-800/90 text-zinc-500 border-zinc-700"
          }`}
          title="Ẩn/Hiện bề mặt"
        >
          <Eye className={`w-3.5 h-3.5 ${showFaces ? "text-indigo-400" : "text-zinc-500"}`} />
        </button>
        <button
          type="button"
          onClick={() => setShowAuxiliary((s) => !s)}
          className={`p-2 border rounded-xl backdrop-blur-md shadow-sm active:scale-95 transition-all text-xs flex items-center gap-1 ${
            showAuxiliary ? "bg-indigo-950/80 text-amber-300 border-amber-500/40" : "bg-zinc-800/90 text-zinc-500 border-zinc-700"
          }`}
          title="Ẩn/Hiện đường phụ"
        >
          <Layers className={`w-3.5 h-3.5 ${showAuxiliary ? "text-amber-400" : "text-zinc-500"}`} />
        </button>
        <button
          type="button"
          onClick={() => setShowLabels((s) => !s)}
          className={`p-2 border rounded-xl backdrop-blur-md shadow-sm active:scale-95 transition-all text-xs flex items-center gap-1 ${
            showLabels ? "bg-indigo-950/80 text-indigo-300 border-indigo-500/40" : "bg-zinc-800/90 text-zinc-500 border-zinc-700"
          }`}
          title="Ẩn/Hiện nhãn"
        >
          <Compass className={`w-3.5 h-3.5 ${showLabels ? "text-indigo-400" : "text-zinc-500"}`} />
        </button>
        <button type="button" onClick={() => setScale((s) => Math.min(s * 1.25, 6))} className="p-2 bg-[var(--panel-glass)] border border-[var(--border)] rounded-xl" title="Zoom In"><ZoomIn className="w-3.5 h-3.5" /></button>
        <button type="button" onClick={() => setScale((s) => Math.max(s / 1.25, 0.4))} className="p-2 bg-[var(--panel-glass)] border border-[var(--border)] rounded-xl" title="Zoom Out"><ZoomOut className="w-3.5 h-3.5" /></button>
        <button type="button" onClick={resetView} className="p-2 bg-[var(--panel-glass)] border border-[var(--border)] rounded-xl" title="Reset"><RotateCcw className="w-3.5 h-3.5" /></button>
      </div>

      <svg viewBox={viewBox} className="w-full h-full block" preserveAspectRatio="xMidYMid meet">
        <defs>
          <linearGradient id="baseFaceGrad" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stopColor="#4f46e5" stopOpacity="0.18" /><stop offset="100%" stopColor="#6366f1" stopOpacity="0.08" /></linearGradient>
        </defs>
        <motion.g animate={{ scale, x: offset.x, y: offset.y }} transition={{ type: "spring", stiffness: 350, damping: 32 }} style={{ originX: "center", originY: "center" }}>
          {showFaces && faceFills.map((f, i) => <path key={i} d={f.d} fill="url(#baseFaceGrad)" stroke="rgba(99, 102, 241, 0.25)" strokeWidth="1" vectorEffect="non-scaling-stroke" />)}
          {visiblePhasePaths.map((p, i) => <path key={i} d={p.d} fill="none" stroke={p.strokeColor} strokeWidth="2" strokeDasharray={p.isDashed ? "6 4" : "none"} vectorEffect="non-scaling-stroke" />)}
          {showAuxiliary && rightAnglePaths.map((d, i) => <path key={i} d={d} fill="none" stroke="#f59e0b" strokeWidth="1.6" vectorEffect="non-scaling-stroke" />)}
          {showAuxiliary && angleArcs.map((a, i) => <g key={i}><path d={a.path} fill="none" stroke="#38bdf8" strokeWidth="1.4" vectorEffect="non-scaling-stroke" />{showLabels && <text x={a.labelX} y={a.labelY} fill="#38bdf8" fontSize={fontSize * 0.8} fontWeight="600" textAnchor="middle" dominantBaseline="central">{a.label}</text>}</g>)}
          {showAuxiliary && equalTicks.map((s, i) => <line key={i} x1={s.x1} y1={s.y1} x2={s.x2} y2={s.y2} stroke="#38bdf8" strokeWidth="1.6" vectorEffect="non-scaling-stroke" />)}
          {showAuxiliary && parallelArrows.map((d, i) => <path key={i} d={d} fill="none" stroke="#a78bfa" strokeWidth="1.5" vectorEffect="non-scaling-stroke" />)}
          {linePaths.map((d, i) => <path key={i} d={d} fill="none" stroke="rgba(99, 102, 241, 0.5)" strokeWidth="1.2" strokeDasharray="8 4" vectorEffect="non-scaling-stroke" />)}
          {rayPaths.map((d, i) => <path key={i} d={d} fill="none" stroke="rgba(168, 85, 247, 0.5)" strokeWidth="1.2" strokeDasharray="6 3" vectorEffect="non-scaling-stroke" />)}
          {circlePaths.map((c, i) => <circle key={i} cx={c.cx} cy={c.cy} r={c.r} fill="none" stroke="rgba(147, 197, 253, 0.7)" strokeWidth="1.4" strokeDasharray="4 2" vectorEffect="non-scaling-stroke" />)}
          {visiblePoints.map((p) => (
            <g key={p.label}>
              <circle cx={p.x} cy={p.y} r={p.isApex ? r * 1.15 : r} fill="#ffffff" stroke="#6366f1" strokeWidth="1.5" vectorEffect="non-scaling-stroke" />
              {showLabels && <text x={p.x + r * 1.8} y={p.y - r * 1.8} fill="#ffffff" fontSize={fontSize} fontWeight="700" className="pointer-events-none select-none drop-shadow-[0_2px_4px_rgba(0,0,0,0.9)]">{p.label}</text>}
            </g>
          ))}
        </motion.g>
      </svg>
    </div>
  );
}
