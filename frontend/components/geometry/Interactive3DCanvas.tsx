"use client";

import React, { useMemo, useState } from "react";
import { Canvas } from "@react-three/fiber";
import { OrbitControls, Stars, Grid, Html, PerspectiveCamera, Center } from "@react-three/drei";
import * as THREE from "three";
import { RotateCcw, Eye, Layers, Compass } from "lucide-react";
import type {
  VisualizationGraph,
  VisAuxiliaryConstruction,
  DrawingPhase,
  PerpendicularMark,
  AngleMark,
  EqualTickMark,
} from "@/types/geometry";
import {
  triangulate3DPolygon,
  computeRightAngleSegments3D,
  computeEqualTickSegments3D,
} from "@/lib/geometry-display";

interface SolidMeta {
  type: string;
  center?: string;
  center1?: string;
  center2?: string;
  apex?: string;
  radius?: number;
  height?: number;
  base?: string[];
  base1?: string[];
  base2?: string[];
  points?: string[];
  [key: string]: unknown;
}

interface Interactive3DCanvasProps {
  coordinates?: Record<string, [number, number, number] | [number, number] | number[]>;
  drawingPhases?: DrawingPhase[];
  faces?: string[][];
  solids?: SolidMeta[];
  visualizationGraph?: VisualizationGraph | null;
  auxiliary?: VisAuxiliaryConstruction[] | null;
}

// Convert Mathematical Coordinate [X, Y, Z] to Three.js Coordinate [X, Z, -Y]
// (Math Z = Up, Three.js Y = Up)
function toVector3(coords: [number, number, number] | [number, number] | number[]): THREE.Vector3 {
  const x = Number(coords[0]) || 0;
  const y = Number(coords[1]) || 0;
  const z = Number(coords[2]) || 0;
  return new THREE.Vector3(x, z, -y);
}

function toTuple3(coords: [number, number, number] | [number, number] | number[]): [number, number, number] {
  const x = Number(coords[0]) || 0;
  const y = Number(coords[1]) || 0;
  const z = Number(coords[2]) || 0;
  return [x, z, -y];
}

/**
 * 3D Vertex Point with billboarded label badge
 */
function Point3D({
  position,
  label,
  role = "vertex",
  kind = "PRIMARY",
  showLabel = true,
}: {
  position: [number, number, number];
  label: string;
  role?: string;
  kind?: string;
  showLabel?: boolean;
}) {
  const isAuxiliary = kind === "AUXILIARY" || role === "foot" || role === "midpoint" || role === "center";
  const isApex = role === "apex";

  const pointColor = isApex ? "#818cf8" : isAuxiliary ? "#fbbf24" : "#ffffff";
  const emissiveColor = isApex ? "#6366f1" : isAuxiliary ? "#f59e0b" : "#818cf8";
  const sphereRadius = isApex ? 0.095 : isAuxiliary ? 0.075 : 0.08;

  return (
    <group position={position}>
      <mesh>
        <sphereGeometry args={[sphereRadius, 24, 24]} />
        <meshStandardMaterial
          color={pointColor}
          emissive={emissiveColor}
          emissiveIntensity={0.7}
          roughness={0.2}
        />
      </mesh>
      {showLabel && (
        <Html distanceFactor={13} zIndexRange={[100, 0]}>
          <div className="select-none pointer-events-none -translate-x-1/2 -translate-y-6">
            <span
              className={`px-1.5 py-0.5 rounded-md text-[10px] font-mono font-bold whitespace-nowrap shadow-xl border backdrop-blur-md transition-all ${
                isAuxiliary
                  ? "bg-amber-950/85 text-amber-300 border-amber-500/30"
                  : isApex
                  ? "bg-indigo-950/85 text-indigo-300 border-indigo-500/30"
                  : "bg-black/80 text-white border-white/20"
              }`}
            >
              {label}
            </span>
          </div>
        </Html>
      )}
    </group>
  );
}

/**
 * Single 3D Edge with Dynamic Hidden-Line Rendering
 * - Unoccluded (in front): Renders crisp solid (LessEqualDepth)
 * - Occluded (behind translucent faces): Renders dimmed dashed (GreaterDepth)
 */
function DualDepthEdge({
  start,
  end,
  role = "edge",
  isAuxiliary = false,
  forceDashed = false,
}: {
  start: THREE.Vector3;
  end: THREE.Vector3;
  role?: string;
  isAuxiliary?: boolean;
  forceDashed?: boolean;
}) {
  const lineGeo = useMemo(() => {
    const geo = new THREE.BufferGeometry().setFromPoints([start, end]);
    return geo;
  }, [start, end]);

  // Color mapping based on visual role hierarchy
  const isAltitude = role === "altitude" || role === "height";
  const isProjection = role === "projection" || role === "foot";
  const isDiagonal = role === "diagonal";

  const solidColor = isAltitude
    ? "#c084fc"
    : isProjection
    ? "#fbbf24"
    : isDiagonal
    ? "#93c5fd"
    : isAuxiliary
    ? "#a78bfa"
    : "#f1f5f9";

  const dashedColor = isAltitude
    ? "#9333ea"
    : isProjection
    ? "#d97706"
    : isDiagonal
    ? "#60a5fa"
    : isAuxiliary
    ? "#818cf8"
    : "#818cf8";

  // Force dashed mode (e.g. interior altitudes or rear base edges)
  if (forceDashed) {
    return (
      <primitive
        object={
          new THREE.Line(
            lineGeo,
            new THREE.LineDashedMaterial({
              color: dashedColor,
              dashSize: 0.22,
              gapSize: 0.13,
              transparent: true,
              opacity: 0.85,
              depthTest: true,
              depthWrite: false,
            })
          )
        }
        onUpdate={(line: THREE.Line) => {
          line.computeLineDistances();
        }}
      />
    );
  }

  return (
    <group>
      {/* Pass 1: Hidden part (behind faces) -> Renders DASHED with Dimmed Opacity */}
      <primitive
        object={
          new THREE.Line(
            lineGeo,
            new THREE.LineDashedMaterial({
              color: dashedColor,
              dashSize: 0.22,
              gapSize: 0.14,
              transparent: true,
              opacity: 0.55,
              depthTest: true,
              depthFunc: THREE.GreaterDepth,
              depthWrite: false,
            })
          )
        }
        onUpdate={(line: THREE.Line) => {
          line.computeLineDistances();
        }}
      />

      {/* Pass 2: Visible part (in front of faces) -> Renders SOLID with High Brightness */}
      <primitive
        object={
          new THREE.Line(
            lineGeo,
            new THREE.LineBasicMaterial({
              color: solidColor,
              transparent: true,
              opacity: 0.95,
              depthTest: true,
              depthFunc: THREE.LessEqualDepth,
              depthWrite: false,
            })
          )
        }
      />
    </group>
  );
}

/**
 * 3D Translucent Solid Polygonal Faces with Layered Opacity Accumulation
 * Two-pass rendering:
 * 1. Occluder pass: writes to depth buffer for dynamic line occlusion
 * 2. Translucent color pass: DoubleSide frosted glass with natural opacity layering
 */
function SolidFaces3D({
  faces,
  coordinates,
  opacity = 0.2,
}: {
  faces: string[][];
  coordinates: Record<string, [number, number, number] | [number, number] | number[]>;
  opacity?: number;
}) {
  const { faceGeometries, boundaryLines } = useMemo(() => {
    const geos: Array<{ geo: THREE.BufferGeometry; isBase: boolean }> = [];
    const bLines: Array<[THREE.Vector3, THREE.Vector3]> = [];

    faces.forEach((faceVertices) => {
      const validPoints: Array<[number, number, number]> = [];
      const validVectors: THREE.Vector3[] = [];

      faceVertices.forEach((vId) => {
        const c = coordinates[vId];
        if (c) {
          const vec = toVector3(c);
          validVectors.push(vec);
          validPoints.push([vec.x, vec.y, vec.z]);
        }
      });

      if (validPoints.length >= 3) {
        const isBase = validPoints.every((p) => Math.abs(p[1]) < 0.05); // Y in Three.js = Height (Z in Math)
        const vertices = triangulate3DPolygon(validPoints);
        if (vertices.length > 0) {
          const geo = new THREE.BufferGeometry();
          geo.setAttribute("position", new THREE.Float32BufferAttribute(vertices, 3));
          geo.computeVertexNormals();
          geos.push({ geo, isBase });
        }

        // Add subtle boundary lines
        for (let i = 0; i < validVectors.length; i++) {
          const p1 = validVectors[i];
          const p2 = validVectors[(i + 1) % validVectors.length];
          bLines.push([p1, p2]);
        }
      }
    });

    return { faceGeometries: geos, boundaryLines: bLines };
  }, [faces, coordinates]);

  if (opacity <= 0.001) return null;

  return (
    <group>
      {/* 1. Occluder Pass: Writes to depth buffer with polygonOffset to cleanly occlude hidden lines */}
      {faceGeometries.map(({ geo }, idx) => (
        <mesh key={`occluder-face-${idx}`} geometry={geo}>
          <meshBasicMaterial
            colorWrite={false}
            depthWrite={true}
            side={THREE.FrontSide}
            polygonOffset
            polygonOffsetFactor={1}
            polygonOffsetUnits={1}
          />
        </mesh>
      ))}

      {/* 2. Frosted Shading Pass: DoubleSide with soft translucent accumulation */}
      {faceGeometries.map(({ geo, isBase }, idx) => (
        <mesh key={`solid-face-${idx}`} geometry={geo}>
          <meshStandardMaterial
            color={isBase ? "#4f46e5" : "#6366f1"}
            emissive={isBase ? "#3730a3" : "#4338ca"}
            emissiveIntensity={0.15}
            transparent
            opacity={isBase ? opacity * 0.9 : opacity}
            side={THREE.DoubleSide}
            roughness={0.2}
            metalness={0.1}
            depthWrite={false}
          />
        </mesh>
      ))}

      {/* 3. Subtle Face Boundary Wireframe Edges */}
      {boundaryLines.map(([p1, p2], idx) => (
        <DualDepthEdge key={`face-edge-${idx}`} start={p1} end={p2} role="face_boundary" />
      ))}
    </group>
  );
}

/**
 * 3D Right-Angle L-Bracket Indicators
 */
function RightAngleMarkers3D({
  perpendicularMarks,
  coordinates,
}: {
  perpendicularMarks: PerpendicularMark[];
  coordinates: Record<string, [number, number, number] | [number, number] | number[]>;
}) {
  const markerSegments = useMemo(() => {
    const segs: Array<[THREE.Vector3, THREE.Vector3]> = [];

    perpendicularMarks.forEach((mark) => {
      const vCoords = coordinates[mark.vertex];
      if (!vCoords || !mark.lines || mark.lines.length < 2) return;

      const p1Coords = coordinates[mark.lines[0]];
      const p2Coords = coordinates[mark.lines[1]];
      if (!p1Coords || !p2Coords) return;

      const vT = toTuple3(vCoords);
      const p1T = toTuple3(p1Coords);
      const p2T = toTuple3(p2Coords);

      const computed = computeRightAngleSegments3D(vT, p1T, p2T, 0.28);
      computed.forEach(([start, end]) => {
        segs.push([new THREE.Vector3(...start), new THREE.Vector3(...end)]);
      });
    });

    return segs;
  }, [perpendicularMarks, coordinates]);

  return (
    <group>
      {markerSegments.map(([start, end], idx) => {
        const geo = new THREE.BufferGeometry().setFromPoints([start, end]);
        return (
          <primitive
            key={`right-angle-${idx}`}
            object={
              new THREE.Line(
                geo,
                new THREE.LineBasicMaterial({
                  color: "#f59e0b",
                  linewidth: 1.5,
                  transparent: true,
                  opacity: 0.95,
                  depthTest: true,
                })
              )
            }
          />
        );
      })}
    </group>
  );
}

/**
 * 3D Equal Length Tick Marks
 */
function EqualTicks3D({
  equalTicks,
  coordinates,
}: {
  equalTicks: EqualTickMark[];
  coordinates: Record<string, [number, number, number] | [number, number] | number[]>;
}) {
  const tickSegments = useMemo(() => {
    const segs: Array<[THREE.Vector3, THREE.Vector3]> = [];

    equalTicks.forEach((item) => {
      const [p1Label, p2Label] = item.segment;
      const c1 = coordinates[p1Label];
      const c2 = coordinates[p2Label];
      if (!c1 || !c2) return;

      const p1T = toTuple3(c1);
      const p2T = toTuple3(c2);
      const ticks = computeEqualTickSegments3D(p1T, p2T, item.ticks || 1, 0.18);
      ticks.forEach(([start, end]) => {
        segs.push([new THREE.Vector3(...start), new THREE.Vector3(...end)]);
      });
    });

    return segs;
  }, [equalTicks, coordinates]);

  return (
    <group>
      {tickSegments.map(([start, end], idx) => {
        const geo = new THREE.BufferGeometry().setFromPoints([start, end]);
        return (
          <primitive
            key={`equal-tick-${idx}`}
            object={
              new THREE.Line(
                geo,
                new THREE.LineBasicMaterial({
                  color: "#38bdf8",
                  linewidth: 1.5,
                  transparent: true,
                  opacity: 0.9,
                  depthTest: true,
                })
              )
            }
          />
        );
      })}
    </group>
  );
}

/**
 * Standard 3D Curved Solids (Spheres, etc.)
 */
function Spheres3D({
  solids,
  coordinates,
}: {
  solids: SolidMeta[];
  coordinates: Record<string, [number, number, number] | [number, number] | number[]>;
}) {
  return (
    <group>
      {solids.map((solid, idx) => {
        if (solid.type === "sphere" && solid.center && coordinates[solid.center]) {
          const pos = toVector3(coordinates[solid.center]);
          const r = Number(solid.radius) || 3;
          return (
            <mesh key={`sphere-${idx}`} position={pos}>
              <sphereGeometry args={[r, 32, 32]} />
              <meshStandardMaterial
                color="#38bdf8"
                transparent
                opacity={0.16}
                side={THREE.DoubleSide}
                roughness={0.25}
                depthWrite={true}
              />
            </mesh>
          );
        }
        return null;
      })}
    </group>
  );
}

export default function Interactive3DCanvas({
  coordinates,
  drawingPhases,
  faces,
  solids,
  visualizationGraph,
  auxiliary,
}: Interactive3DCanvasProps) {
  const [resetKey, setResetKey] = useState(0);
  const [opacityMode, setOpacityMode] = useState<"frosted" | "translucent" | "wireframe">("frosted");
  const [showAuxiliary, setShowAuxiliary] = useState(true);
  const [showLabels, setShowLabels] = useState(true);

  const faceOpacity = opacityMode === "frosted" ? 0.2 : opacityMode === "translucent" ? 0.38 : 0.0;

  const parsedCoordinates = useMemo(() => {
    return coordinates ?? {};
  }, [coordinates]);

  // Extract vertices with roles and hierarchy
  const vertices = useMemo(() => {
    if (visualizationGraph?.vertices && Object.keys(visualizationGraph.vertices).length > 0) {
      return Object.values(visualizationGraph.vertices).map((v) => {
        const c = parsedCoordinates[v.id] || v.coordinates || [0, 0, 0];
        return {
          id: v.id,
          label: v.label || v.id,
          position: toTuple3(c),
          role: v.role,
          kind: v.kind || "PRIMARY",
        };
      });
    }

    return Object.entries(parsedCoordinates).map(([label, coords]) => ({
      id: label,
      label,
      position: toTuple3(coords),
      role: "vertex",
      kind: "PRIMARY",
    }));
  }, [visualizationGraph, parsedCoordinates]);

  // Extract edges (combining visualization_graph and drawing_phases)
  const edges = useMemo(() => {
    const edgeMap = new Map<string, { start: THREE.Vector3; end: THREE.Vector3; role: string; isAuxiliary: boolean; forceDashed: boolean }>();

    // 1. From Visualization Graph (if available)
    if (visualizationGraph?.edges && Object.keys(visualizationGraph.edges).length > 0) {
      Object.values(visualizationGraph.edges).forEach((e) => {
        const c1 = parsedCoordinates[e.source];
        const c2 = parsedCoordinates[e.target];
        if (c1 && c2) {
          const key = [e.source, e.target].sort().join("-");
          edgeMap.set(key, {
            start: toVector3(c1),
            end: toVector3(c2),
            role: e.role,
            isAuxiliary: e.kind === "AUXILIARY" || e.role === "altitude" || e.role === "median" || e.role === "projection" || e.role === "diagonal",
            forceDashed: e.style === "dashed" || Boolean(e.is_hidden),
          });
        }
      });
    }

    // 2. From Drawing Phases (if not already captured)
    if (drawingPhases && drawingPhases.length > 0) {
      drawingPhases.forEach((phase) => {
        const isAux = phase.phase >= 2;
        phase.segments.forEach(([p1, p2]) => {
          const c1 = parsedCoordinates[p1];
          const c2 = parsedCoordinates[p2];
          if (c1 && c2) {
            const key = [p1, p2].sort().join("-");
            if (!edgeMap.has(key)) {
              edgeMap.set(key, {
                start: toVector3(c1),
                end: toVector3(c2),
                role: isAux ? "auxiliary" : "edge",
                isAuxiliary: isAux,
                forceDashed: isAux,
              });
            }
          }
        });
      });
    }

    return Array.from(edgeMap.values());
  }, [visualizationGraph, drawingPhases, parsedCoordinates]);

  // Extract faces
  const effectiveFaces = useMemo(() => {
    if (faces && faces.length > 0) return faces;
    if (visualizationGraph?.faces && Object.keys(visualizationGraph.faces).length > 0) {
      return Object.values(visualizationGraph.faces).map((f) => f.vertices);
    }
    return [];
  }, [faces, visualizationGraph]);

  // Extract perpendicular marks
  const perpendicularMarks = useMemo(() => {
    const marks: PerpendicularMark[] = [];
    if (visualizationGraph?.perpendicular_marks && visualizationGraph.perpendicular_marks.length > 0) {
      marks.push(...visualizationGraph.perpendicular_marks);
    }
    const auxList = auxiliary || visualizationGraph?.auxiliary || [];
    auxList.forEach((aux) => {
      if (aux.perpendicular_marks && aux.perpendicular_marks.length > 0) {
        marks.push(...aux.perpendicular_marks);
      }
    });
    return marks;
  }, [auxiliary, visualizationGraph]);

  // Extract equal ticks
  const equalTicks = useMemo(() => {
    const ticks: EqualTickMark[] = [];
    if (visualizationGraph?.equal_ticks && visualizationGraph.equal_ticks.length > 0) {
      ticks.push(...visualizationGraph.equal_ticks);
    }
    const auxList = auxiliary || visualizationGraph?.auxiliary || [];
    auxList.forEach((aux) => {
      if (aux.equal_ticks && aux.equal_ticks.length > 0) {
        ticks.push(...aux.equal_ticks);
      }
    });
    return ticks;
  }, [auxiliary, visualizationGraph]);

  if (!coordinates || Object.keys(coordinates).length === 0 || vertices.length === 0) {
    return (
      <div className="bg-[var(--card-bg)] border border-[var(--border)] rounded-2xl flex-1 min-h-0 flex items-center justify-center p-8">
        <p className="text-xs font-mono text-[var(--text-muted)] animate-pulse">
          Đang khởi tạo không gian hình học 3D...
        </p>
      </div>
    );
  }

  return (
    <div className="bg-[var(--card-bg)] border border-[var(--border)] rounded-2xl overflow-hidden w-full h-full flex-1 min-h-0 relative select-none shadow-inner">
      {/* Floating HUD Controls */}
      <div className="absolute top-3 right-3 flex items-center gap-1.5 z-20">
        <button
          type="button"
          onClick={() =>
            setOpacityMode((m) => (m === "frosted" ? "translucent" : m === "translucent" ? "wireframe" : "frosted"))
          }
          className={`p-2 border rounded-xl backdrop-blur-md shadow-sm active:scale-95 transition-all flex items-center gap-1.5 text-xs font-medium ${
            opacityMode === "wireframe"
              ? "bg-zinc-800/80 text-zinc-400 border-zinc-700"
              : opacityMode === "translucent"
              ? "bg-indigo-950/80 text-indigo-300 border-indigo-500/40"
              : "bg-[var(--panel-glass)] text-zinc-200 hover:text-white border-[var(--border)]"
          }`}
          title={`Chế độ mặt khối: ${opacityMode === "frosted" ? "Mờ nhẹ" : opacityMode === "translucent" ? "Đậm" : "Khung dây"}`}
        >
          <Eye className="w-3.5 h-3.5" />
          <span className="text-[10px] hidden sm:inline">
            {opacityMode === "frosted" ? "Mặt mờ" : opacityMode === "translucent" ? "Mặt đậm" : "Khung dây"}
          </span>
        </button>

        <button
          type="button"
          onClick={() => setShowAuxiliary((s) => !s)}
          className={`p-2 border rounded-xl backdrop-blur-md shadow-sm active:scale-95 transition-all text-xs ${
            showAuxiliary
              ? "bg-[var(--panel-glass)] text-zinc-200 hover:text-white border-[var(--border)]"
              : "bg-zinc-800/80 text-zinc-500 border-zinc-700"
          }`}
          title={showAuxiliary ? "Ẩn đường phụ trợ & góc" : "Hiện đường phụ trợ & góc"}
        >
          <Layers className="w-3.5 h-3.5" />
        </button>

        <button
          type="button"
          onClick={() => setShowLabels((s) => !s)}
          className={`p-2 border rounded-xl backdrop-blur-md shadow-sm active:scale-95 transition-all text-xs ${
            showLabels
              ? "bg-[var(--panel-glass)] text-zinc-200 hover:text-white border-[var(--border)]"
              : "bg-zinc-800/80 text-zinc-500 border-zinc-700"
          }`}
          title={showLabels ? "Ẩn nhãn điểm" : "Hiện nhãn điểm"}
        >
          <Compass className="w-3.5 h-3.5" />
        </button>

        <button
          type="button"
          onClick={() => setResetKey((k) => k + 1)}
          className="p-2 bg-[var(--panel-glass)] hover:bg-white/10 border border-[var(--border)] rounded-xl text-zinc-300 hover:text-white backdrop-blur-md shadow-sm active:scale-95 transition-all"
          title="Đặt lại góc nhìn 3D"
        >
          <RotateCcw className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Badge Header */}
      <div className="absolute top-3 left-3 z-20 pointer-events-none">
        <div className="flex items-center gap-2 px-3 py-1 bg-[var(--panel-glass)] border border-[var(--border)] rounded-full backdrop-blur-md shadow-sm">
          <div className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-pulse" />
          <span className="text-[10px] font-mono font-semibold text-indigo-300 uppercase tracking-wider">
            3D Solid Topology Engine
          </span>
        </div>
      </div>

      {/* 3D Canvas Fiber Scene */}
      <Canvas key={resetKey} shadows gl={{ antialias: true, alpha: true }}>
        <PerspectiveCamera makeDefault position={[9, 8, 10]} fov={45} />
        <OrbitControls
          enableDamping
          dampingFactor={0.06}
          minDistance={2}
          maxDistance={60}
          makeDefault
        />

        <ambientLight intensity={0.85} />
        <directionalLight position={[12, 18, 12]} intensity={1.5} />
        <pointLight position={[-10, 15, -10]} intensity={0.8} />

        <Stars radius={90} depth={40} count={1000} factor={2.5} saturation={0} fade speed={0.6} />

        <Grid
          infiniteGrid
          fadeDistance={30}
          sectionSize={1}
          sectionColor="#27272a"
          cellColor="#141418"
          cellSize={0.5}
        />

        <Center top>
          <group>
            {/* 1. Translucent Solid Faces with Accumulated Shading */}
            {effectiveFaces.length > 0 && (
              <SolidFaces3D
                faces={effectiveFaces}
                coordinates={parsedCoordinates}
                opacity={faceOpacity}
              />
            )}

            {/* 2. Dual-Depth Dynamic Hidden-Line Edges */}
            {edges.map((edge, idx) => (
              <DualDepthEdge
                key={`edge-${idx}`}
                start={edge.start}
                end={edge.end}
                role={edge.role}
                isAuxiliary={edge.isAuxiliary}
                forceDashed={edge.forceDashed}
              />
            ))}

            {/* 3. Auxiliary Perpendicular Right-Angle Markers */}
            {showAuxiliary && perpendicularMarks.length > 0 && (
              <RightAngleMarkers3D
                perpendicularMarks={perpendicularMarks}
                coordinates={parsedCoordinates}
              />
            )}

            {/* 4. Auxiliary Equal Length Ticks */}
            {showAuxiliary && equalTicks.length > 0 && (
              <EqualTicks3D
                equalTicks={equalTicks}
                coordinates={parsedCoordinates}
              />
            )}

            {/* 5. Curved Solids (Spheres, etc.) */}
            {solids && solids.length > 0 && (
              <Spheres3D solids={solids} coordinates={parsedCoordinates} />
            )}

            {/* 6. Vertices and Labels */}
            {vertices.map((v) => (
              <Point3D
                key={v.id}
                position={v.position}
                label={v.label}
                role={v.role}
                kind={v.kind}
                showLabel={showLabels}
              />
            ))}
          </group>
        </Center>
      </Canvas>
    </div>
  );
}
