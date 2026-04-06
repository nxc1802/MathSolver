"use client";

import { motion } from "framer-motion";
import { useMemo, useState, useRef, useEffect } from "react";
import { ZoomIn, ZoomOut, RotateCcw, Move } from "lucide-react";

interface StaticGeometryCanvasProps {
  coordinates?: Record<string, [number, number]>;
  polygonOrder?: string[];
  circles?: Array<{ center: string; radius: number }>;
  drawingPhases?: Array<{
    phase: number;
    label: string;
    points: string[];
    segments: string[][];
  }>;
}

export default function StaticGeometryCanvas({ coordinates, polygonOrder, circles, drawingPhases }: StaticGeometryCanvasProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [scale, setScale] = useState(1);
  const [offset, setOffset] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const dragStart = useRef({ x: 0, y: 0 });
  const dragStartOffset = useRef({ x: 0, y: 0 });

  const { viewBox, points, phasePaths, circlePaths, spanX } = useMemo(() => {
    if (!coordinates || Object.keys(coordinates).length === 0) {
      return { viewBox: "0 0 100 100", points: [], phasePaths: [], circlePaths: [], spanX: 100 };
    }

    const entries = Object.entries(coordinates);
    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;

    const parsedPoints = entries.map(([label, [x, y]]) => {
      const px = Number(x);
      const py = Number(y) * -1; // Invert Y for SVG coordinates
      minX = Math.min(minX, px);
      maxX = Math.max(maxX, px);
      minY = Math.min(minY, py);
      maxY = Math.max(maxY, py);
      return { label, x: px, y: py };
    });

    const circleParsed = (circles || []).map(c => {
      const centerCoords = coordinates[c.center];
      if (!centerCoords) return null;
      const r = Number(c.radius);
      const cx = Number(centerCoords[0]);
      const cy = Number(centerCoords[1]) * -1;
      minX = Math.min(minX, cx - r);
      maxX = Math.max(maxX, cx + r);
      minY = Math.min(minY, cy - r);
      maxY = Math.max(maxY, cy + r);
      return { cx, cy, r };
    }).filter(Boolean) as Array<{ cx: number, cy: number, r: number }>;

    const padding = Math.max((maxX - minX) * 0.2, (maxY - minY) * 0.2, 10);
    const vb = `${minX - padding} ${minY - padding} ${maxX - minX + padding * 2} ${maxY - minY + padding * 2}`;
    const sX = maxX - minX + padding * 2;

    const resPhasePaths: Array<{ d: string, phase: number }> = [];

    if (drawingPhases && drawingPhases.length > 0) {
      // Trust backend drawing_phases — only render phases that actually have segments.
      drawingPhases.forEach(phase => {
        if (!phase.segments || phase.segments.length === 0) return; // skip empty phases
        const segmentsD: string[] = [];
        phase.segments.forEach(([p1Label, p2Label]) => {
          const pt1 = parsedPoints.find(p => p.label === p1Label);
          const pt2 = parsedPoints.find(p => p.label === p2Label);
          if (pt1 && pt2) {
            segmentsD.push(`M ${pt1.x} ${pt1.y} L ${pt2.x} ${pt2.y}`);
          }
        });
        if (segmentsD.length > 0) {
          resPhasePaths.push({ d: segmentsD.join(" "), phase: phase.phase });
        }
      });
    }

    // Fallback: only use polygonOrder — NEVER auto-connect all points (avoids nonsensical lines)
    if (resPhasePaths.length === 0 && polygonOrder && polygonOrder.length >= 2) {
      const ordered = polygonOrder
        .map(label => parsedPoints.find(p => p.label === label))
        .filter(Boolean) as typeof parsedPoints;

      if (ordered.length >= 2) {
        let d = ordered.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(" ");
        if (ordered.length >= 3) d += " Z";
        resPhasePaths.push({ d, phase: 1 });
      }
    }

    return { viewBox: vb, points: parsedPoints, phasePaths: resPhasePaths, circlePaths: circleParsed, spanX: sX };
  }, [coordinates, polygonOrder, circles, drawingPhases]);

  const handleWheel = (e: React.WheelEvent) => {
    if (e.ctrlKey || e.metaKey) {
      e.preventDefault();
      const delta = e.deltaY > 0 ? 0.9 : 1.1;
      setScale(s => Math.min(Math.max(s * delta, 0.5), 5));
    } else {
      // Scale move by viewbox ratio
      const rect = containerRef.current?.getBoundingClientRect();
      if (!rect) return;
      const vbWidth = Number(viewBox.split(" ")[2]);
      const ratio = vbWidth / rect.width;

      setOffset(prev => ({
        x: prev.x - (e.deltaX * ratio) / scale,
        y: prev.y - (e.deltaY * ratio) / scale
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

    const dx = (e.clientX - dragStart.current.x) * ratio / scale;
    const dy = (e.clientY - dragStart.current.y) * ratio / scale;

    setOffset({
      x: dragStartOffset.current.x + dx,
      y: dragStartOffset.current.y + dy
    });
  };

  const handleMouseUp = () => setIsDragging(false);

  const resetView = () => {
    setScale(1);
    setOffset({ x: 0, y: 0 });
  };

  if (!coordinates || Object.keys(coordinates).length === 0) {
    return (
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        className="bg-zinc-950 border border-white/5 rounded-3xl overflow-hidden aspect-video relative flex items-center justify-center p-8"
      >
        <p className="text-zinc-500 font-medium animate-pulse">Hệ thống đang dựng tọa độ...</p>
      </motion.div>
    );
  }

  const r = spanX * 0.012;
  const fontSize = spanX * 0.035;

  return (
    <div 
      ref={containerRef}
      className="bg-zinc-950 border border-white/10 rounded-3xl overflow-hidden aspect-video relative group select-none cursor-grab active:cursor-grabbing"
      onWheel={handleWheel}
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseUp}
    >
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(99,102,241,0.05)_0%,transparent_100%)] pointer-events-none" />
      
      {/* Controls */}
      <div className="absolute top-4 right-4 flex flex-col gap-2 z-20">
        <button 
          onClick={() => setScale(s => Math.min(s * 1.2, 5))}
          className="p-2 bg-white/5 hover:bg-white/10 border border-white/10 rounded-xl text-zinc-400 hover:text-white transition-all backdrop-blur-md"
          title="Zoom In"
        >
          <ZoomIn className="w-4 h-4" />
        </button>
        <button 
          onClick={() => setScale(s => Math.max(s / 1.2, 0.5))}
          className="p-2 bg-white/5 hover:bg-white/10 border border-white/10 rounded-xl text-zinc-400 hover:text-white transition-all backdrop-blur-md"
          title="Zoom Out"
        >
          <ZoomOut className="w-4 h-4" />
        </button>
        <button 
          onClick={resetView}
          className="p-2 bg-white/5 hover:bg-white/10 border border-white/10 rounded-xl text-zinc-400 hover:text-white transition-all backdrop-blur-md"
          title="Reset View"
        >
          <RotateCcw className="w-4 h-4" />
        </button>
      </div>

      <div className="absolute bottom-4 left-4 flex items-center gap-2 px-3 py-1.5 bg-white/5 border border-white/10 rounded-full backdrop-blur-md z-20 opacity-0 group-hover:opacity-100 transition-opacity">
        <Move className="w-3.5 h-3.5 text-zinc-500" />
        <span className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest">Kéo để di chuyển • Ctrl+Cuộn để phóng to</span>
      </div>
      
      <svg 
        viewBox={viewBox} 
        className="w-full h-full"
        preserveAspectRatio="xMidYMid meet"
      >
        <motion.g
          animate={{ 
            scale,
            x: offset.x,
            y: offset.y
          }}
          transition={isDragging ? { type: "tween", duration: 0 } : { type: "spring", stiffness: 300, damping: 30 }}
          style={{ originX: "center", originY: "center" }}
        >
          {phasePaths.map((p, idx) => {
            const isBase = p.phase === 1;
            return (
              <path 
                key={`phase-${idx}`}
                d={p.d} 
                fill="none" 
                stroke={isBase ? "rgba(99, 102, 241, 0.9)" : "rgba(167, 139, 250, 0.7)"} 
                strokeWidth={isBase ? "2.5" : "1.8"}
                strokeDasharray={isBase ? "none" : "4 3"}
                vectorEffect="non-scaling-stroke"
                strokeLinejoin="round"
                strokeLinecap="round"
              />
            );
          })}
          
          {circlePaths.map((c, i) => (
            <circle 
              key={`circle-${i}`}
              cx={c.cx}
              cy={c.cy}
              r={c.r}
              fill="none"
              stroke="rgba(167, 139, 250, 0.6)"
              strokeWidth="1.5"
              vectorEffect="non-scaling-stroke"
              strokeDasharray="5 3"
            />
          ))}
          
          {points.map((p) => (
            <g key={p.label}>
              <circle 
                cx={p.x} 
                cy={p.y} 
                r={r} 
                fill="white"
                className="drop-shadow-[0_0_4px_rgba(255,255,255,0.5)]"
              />
              <text 
                x={p.x + r * 1.8} 
                y={p.y - r * 1.8} 
                fill="white" 
                fontSize={fontSize} 
                fontWeight="800"
                className="pointer-events-none drop-shadow-lg"
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
