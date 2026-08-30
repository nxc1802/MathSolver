"use client";

import { motion } from "framer-motion";
import { useMemo, useState, useRef } from "react";
import { ZoomIn, ZoomOut, RotateCcw, Move } from "lucide-react";

interface StaticGeometryCanvasProps {
  coordinates?: Record<string, [number, number]>;
  polygonOrder?: string[];
  circles?: Array<{ center: string; radius: number }>;
  lines?: Array<[string, string]>;
  rays?: Array<[string, string]>;
  drawingPhases?: Array<{
    phase: number;
    label: string;
    points: string[];
    segments: string[][];
  }>;
}

export default function StaticGeometryCanvas({
  coordinates,
  polygonOrder,
  circles,
  lines,
  rays,
  drawingPhases,
}: StaticGeometryCanvasProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [scale, setScale] = useState(1);
  const [offset, setOffset] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const dragStart = useRef({ x: 0, y: 0 });
  const dragStartOffset = useRef({ x: 0, y: 0 });

  const { viewBox, points, phasePaths, circlePaths, linePaths, rayPaths, spanX } = useMemo(() => {
    if (!coordinates || Object.keys(coordinates).length === 0) {
      return { viewBox: "0 0 100 100", points: [], phasePaths: [], circlePaths: [], linePaths: [], rayPaths: [], spanX: 100 };
    }

    const entries = Object.entries(coordinates);
    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;

    const parsedPoints = entries.map(([label, raw]) => {
      const arr = Array.isArray(raw) ? raw : [];
      const px = Number(arr[0]);
      const py = Number(arr[1]) * -1; // Invert Y for SVG coordinates
      minX = Math.min(minX, px);
      maxX = Math.max(maxX, px);
      minY = Math.min(minY, py);
      maxY = Math.max(maxY, py);
      return { label, x: px, y: py };
    });

    const circleParsed = (circles || []).map((c) => {
      const centerCoords = coordinates[c.center];
      if (!centerCoords) return null;
      const r = Number(c.radius);
      const cx = Number(centerCoords[0]);
      const cy = Number(centerCoords[1] ?? 0) * -1;
      minX = Math.min(minX, cx - r);
      maxX = Math.max(maxX, cx + r);
      minY = Math.min(minY, cy - r);
      maxY = Math.max(maxY, cy + r);
      return { cx, cy, r };
    }).filter(Boolean) as Array<{ cx: number; cy: number; r: number }>;

    const padding = Math.max((maxX - minX) * 0.25, (maxY - minY) * 0.25, 12);
    const vb = `${minX - padding} ${minY - padding} ${maxX - minX + padding * 2} ${maxY - minY + padding * 2}`;
    const sX = maxX - minX + padding * 2;

    const resPhasePaths: Array<{ d: string; phase: number }> = [];

    if (drawingPhases && drawingPhases.length > 0) {
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
          resPhasePaths.push({ d: segmentsD.join(" "), phase: phase.phase });
        }
      });
    }

    if (resPhasePaths.length === 0 && polygonOrder && polygonOrder.length >= 2) {
      const ordered = polygonOrder
        .map((label) => parsedPoints.find((p) => p.label === label))
        .filter(Boolean) as typeof parsedPoints;

      if (ordered.length >= 2) {
        let d = ordered.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x} ${p.y}`).join(" ");
        if (ordered.length >= 3) d += " Z";
        resPhasePaths.push({ d, phase: 1 });
      }
    }

    // Lines (Infinite)
    const resLinePaths: string[] = [];
    (lines || []).forEach(([p1, p2]) => {
      const pt1 = parsedPoints.find((p) => p.label === p1);
      const pt2 = parsedPoints.find((p) => p.label === p2);
      if (pt1 && pt2) {
        const dx = pt2.x - pt1.x;
        const dy = pt2.y - pt1.y;
        const x1 = pt1.x - dx * 2000;
        const y1 = pt1.y - dy * 2000;
        const x2 = pt1.x + dx * 2000;
        const y2 = pt1.y + dy * 2000;
        resLinePaths.push(`M ${x1} ${y1} L ${x2} ${y2}`);
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
        const x2 = pt1.x + dx * 2000;
        const y2 = pt1.y + dy * 2000;
        resRayPaths.push(`M ${pt1.x} ${pt1.y} L ${x2} ${y2}`);
      }
    });

    return { viewBox: vb, points: parsedPoints, phasePaths: resPhasePaths, circlePaths: circleParsed, linePaths: resLinePaths, rayPaths: resRayPaths, spanX: sX };
  }, [coordinates, polygonOrder, circles, lines, rays, drawingPhases]);

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

  const r = spanX * 0.012;
  const fontSize = spanX * 0.036;

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

      {/* Navigation Help Bar */}
      <div className="absolute bottom-3 left-3 flex items-center gap-2 px-3 py-1 bg-[var(--panel-glass)] border border-[var(--border)] rounded-full backdrop-blur-md z-20 pointer-events-none opacity-80">
        <Move className="w-3 h-3 text-[var(--text-muted)]" />
        <span className="text-[9px] font-mono text-[var(--text-muted)]">
          Kéo để di chuyển • Ctrl + Cuộn để phóng to
        </span>
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
          {/* Phase Drawing Segments */}
          {phasePaths.map((p, idx) => {
            const isBase = p.phase === 1;
            return (
              <path
                key={`phase-${idx}`}
                d={p.d}
                fill="none"
                stroke={isBase ? "rgba(129, 140, 248, 0.95)" : "rgba(192, 132, 252, 0.85)"}
                strokeWidth={isBase ? "2.2" : "1.6"}
                strokeDasharray={isBase ? "none" : "4 3"}
                vectorEffect="non-scaling-stroke"
                strokeLinejoin="round"
                strokeLinecap="round"
              />
            );
          })}

          {/* Infinite Lines */}
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

          {/* Rays */}
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

          {/* Circles */}
          {circlePaths.map((c, i) => (
            <circle
              key={`circle-${i}`}
              cx={c.cx}
              cy={c.cy}
              r={c.r}
              fill="none"
              stroke="rgba(147, 197, 253, 0.6)"
              strokeWidth="1.4"
              vectorEffect="non-scaling-stroke"
              strokeDasharray="4 2"
            />
          ))}

          {/* Vertex Points and Labels */}
          {points.map((p) => (
            <g key={p.label}>
              <circle
                cx={p.x}
                cy={p.y}
                r={r}
                fill="#ffffff"
                stroke="#6366f1"
                strokeWidth="1.5"
                vectorEffect="non-scaling-stroke"
              />
              <text
                x={p.x + r * 1.8}
                y={p.y - r * 1.8}
                fill="#ffffff"
                fontSize={fontSize}
                fontFamily="var(--font-geist-mono), monospace"
                fontWeight="700"
                className="pointer-events-none select-none drop-shadow-[0_2px_4px_rgba(0,0,0,0.8)]"
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
