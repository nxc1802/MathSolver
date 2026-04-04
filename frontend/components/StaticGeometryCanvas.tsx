"use client";

import { motion } from "framer-motion";
import { useMemo } from "react";

interface StaticGeometryCanvasProps {
  coordinates?: Record<string, [number, number]>;
  polygonOrder?: string[];
  circles?: Array<{ center: string; radius: number }>;
}

export default function StaticGeometryCanvas({ coordinates, polygonOrder, circles }: StaticGeometryCanvasProps) {
  const { viewBox, points, paths, circlePaths, spanX } = useMemo(() => {
    if (!coordinates || Object.keys(coordinates).length === 0) {
      return { viewBox: "0 0 100 100", points: [], paths: "", circlePaths: [], spanX: 100 };
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

    // Circles bounds
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

    const padding = Math.max((maxX - minX) * 0.2, (maxY - minY) * 0.2, 3);
    const vb = `${minX - padding} ${minY - padding} ${maxX - minX + padding * 2} ${maxY - minY + padding * 2}`;
    const sX = maxX - minX + padding * 2;

    let pathsStr = "";
    if (polygonOrder && polygonOrder.length > 0) {
      // Use explicit order
      const ordered = polygonOrder
        .map(label => parsedPoints.find(p => p.label === label))
        .filter(Boolean) as typeof parsedPoints;
      
      if (ordered.length >= 2) {
        pathsStr = ordered.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(" ");
        if (ordered.length >= 3) pathsStr += " Z";
      }
    } else if (parsedPoints.length >= 3) {
      // Default order (fallback)
      pathsStr = parsedPoints.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(" ") + " Z";
    } else if (parsedPoints.length === 2) {
      pathsStr = `M ${parsedPoints[0].x} ${parsedPoints[0].y} L ${parsedPoints[1].x} ${parsedPoints[1].y}`;
    }

    return { viewBox: vb, points: parsedPoints, paths: pathsStr, circlePaths: circleParsed, spanX: sX };
  }, [coordinates, polygonOrder, circles]);

  if (!coordinates || Object.keys(coordinates).length === 0) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-zinc-950 border border-white/10 rounded-3xl overflow-hidden aspect-video relative flex items-center justify-center p-8"
      >
        <p className="text-zinc-500">Đang tạo hình vẽ...</p>
      </motion.div>
    );
  }

  const r = spanX * 0.015;
  const fontSize = spanX * 0.04;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-zinc-950 border border-white/10 rounded-3xl overflow-hidden aspect-video relative group flex items-center justify-center p-4 lg:p-12"
    >
      <div className="absolute inset-0 bg-gradient-to-br from-indigo-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
      
      <svg 
        viewBox={viewBox} 
        className="w-full h-full drop-shadow-[0_0_8px_rgba(99,102,241,0.5)]"
        preserveAspectRatio="xMidYMid meet"
      >
        {paths && (
          <path 
            d={paths} 
            fill="none" 
            stroke="rgba(99, 102, 241, 0.8)" 
            strokeWidth="2"
            vectorEffect="non-scaling-stroke"
            strokeLinejoin="round"
          />
        )}
        
        {circlePaths.map((c, i) => (
          <circle 
            key={`circle-${i}`}
            cx={c.cx}
            cy={c.cy}
            r={c.r}
            fill="none"
            stroke="rgba(167, 139, 250, 0.7)"
            strokeWidth="1.5"
            vectorEffect="non-scaling-stroke"
            strokeDasharray="4 2"
          />
        ))}
        
        {points.map((p) => (
          <g key={p.label}>
            <circle 
              cx={p.x} 
              cy={p.y} 
              r={r} 
              fill="white"
            />
            <text 
              x={p.x + r * 1.5} 
              y={p.y - r * 1.5} 
              fill="white" 
              fontSize={fontSize} 
              fontWeight="600"
            >
              {p.label}
            </text>
          </g>
        ))}
      </svg>
    </motion.div>
  );
}
