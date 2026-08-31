"use client";

import React, { useMemo, useState } from "react";
import { Canvas } from "@react-three/fiber";
import { OrbitControls, Stars, Grid, Html, PerspectiveCamera, Center } from "@react-three/drei";
import * as THREE from "three";
import { RotateCcw, Eye } from "lucide-react";
import type { VisualizationGraph, VisAuxiliaryConstruction, DrawingPhase } from "@/types/geometry";
import { triangulate3DPolygon, computeRightAngleSegments3D } from "@/lib/geometry-display";

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
 * 3D Vertex Point with billboarded label
 */
function Point3D({
  position,
  label,
  role = "vertex",
  kind = "PRIMARY",
}: {
  position: [number, number, number];
  label: string;
  role?: string;
  kind?: string;
}) {
  const isAuxiliary = kind === "AUXILIARY" || role === "foot" || role === "midpoint" || role === "center";
  const isApex = role === "apex";

  const pointColor = isApex ? "#818cf8" : isAuxiliary ? "#fbbf24" : "#ffffff";
  const emissiveColor = isApex ? "#6366f1" : isAuxiliary ? "#f59e0b" : "#818cf8";
  const sphereRadius = isApex ? 0.09 : isAuxiliary ? 0.075 : 0.08;

  return (
    <group position={position}>
      <mesh>
        <sphereGeometry args={[sphereRadius, 24, 24]} />
        <meshStandardMaterial
          color={pointColor}
          emissive={emissiveColor}
          emissiveIntensity={0.65}
          roughness={0.2}
        />
      </mesh>
      <Html distanceFactor={13} zIndexRange={[100, 0]}>
        <div className="select-none pointer-events-none -translate-x-1/2 -translate-y-6">
          <span
            className={`px-1.5 py-0.5 rounded-md text-[10px] font-mono font-bold whitespace-nowrap shadow-xl border backdrop-blur-md ${
              isAuxiliary
                ? "bg-amber-950/80 text-amber-300 border-amber-500/30"
                : isApex
                ? "bg-indigo-950/80 text-indigo-300 border-indigo-500/30"
                : "bg-black/75 text-white border-white/20"
            }`}
          >
            {label}
          </span>
        </div>
      </Html>
    </group>
  );
}

/**
 * Single 3D Edge with Dynamic Hidden-Line Rendering
 * - When in front/unoccluded: Renders solid (LessEqualDepth)
 * - When occluded behind semi-transparent faces: Renders dashed (GreaterDepth)
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

  // Color mapping based on visual hierarchy
  const isAltitude = role === "altitude" || role === "height";
  const solidColor = isAltitude ? "#c084fc" : isAuxiliary ? "#a78bfa" : "#e0e7ff";
  const dashedColor = isAltitude ? "#9333ea" : isAuxiliary ? "#818cf8" : "#818cf8";

  // If forceDashed (e.g. interior altitude or diagonals inside the solid base), render purely dashed
  if (forceDashed) {
    return (
      <primitive
        object={
          new THREE.Line(
            lineGeo,
            new THREE.LineDashedMaterial({
              color: dashedColor,
              dashSize: 0.22,
              gapSize: 0.14,
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
      {/* Pass 1: Hidden part (behind faces) -> Renders DASHED */}
      <primitive
        object={
          new THREE.Line(
            lineGeo,
            new THREE.LineDashedMaterial({
              color: dashedColor,
              dashSize: 0.24,
              gapSize: 0.15,
              transparent: true,
              opacity: 0.65,
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

      {/* Pass 2: Visible part (in front of faces) -> Renders SOLID */}
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
 * 3D Semi-transparent Solid Polygonal Faces
 * Rendered with polygonOffset and depthWrite: true to act as geometric occluders for hidden lines.
 */
function SolidFaces3D({
  faces,
  coordinates,
  opacity = 0.18,
}: {
  faces: string[][];
  coordinates: Record<string, [number, number, number] | [number, number] | number[]>;
  opacity?: number;
}) {
  const { faceGeometries, boundaryLines } = useMemo(() => {
    const geos: THREE.BufferGeometry[] = [];
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
        // Triangulate polygonal face (supports quads, triangles, n-gons)
        const vertices = triangulate3DPolygon(validPoints);
        if (vertices.length > 0) {
          const geo = new THREE.BufferGeometry();
          geo.setAttribute("position", new THREE.Float32BufferAttribute(vertices, 3));
          geo.computeVertexNormals();
          geos.push(geo);
        }

        // Add boundary segments
        for (let i = 0; i < validVectors.length; i++) {
          const p1 = validVectors[i];
          const p2 = validVectors[(i + 1) % validVectors.length];
          bLines.push([p1, p2]);
        }
      }
    });

    return { faceGeometries: geos, boundaryLines: bLines };
  }, [faces, coordinates]);

  return (
    <group>
      {/* 1. Semi-transparent Faces with Depth Write for Dynamic Hidden-Line Occlusion */}
      {faceGeometries.map((geo, idx) => (
        <mesh key={`solid-face-${idx}`} geometry={geo}>
          <meshStandardMaterial
            color="#6366f1"
            transparent
            opacity={opacity}
            side={THREE.DoubleSide}
            roughness={0.4}
            metalness={0.1}
            polygonOffset
            polygonOffsetFactor={1}
            polygonOffsetUnits={1}
            depthWrite={true}
          />
        </mesh>
      ))}

      {/* 2. Subtle Face Boundary Edges */}
      {boundaryLines.map(([p1, p2], idx) => (
        <DualDepthEdge key={`face-edge-${idx}`} start={p1} end={p2} role="face_boundary" />
      ))}
    </group>
  );
}

/**
 * 3D Right-Angle Corner Indicators (Perpendicularity Marker)
 */
function RightAngleMarkers3D({
  perpendicularMarks,
  coordinates,
}: {
  perpendicularMarks: Array<{ vertex: string; lines: string[] }>;
  coordinates: Record<string, [number, number, number] | [number, number] | number[]>;
}) {
  const markerSegments = useMemo(() => {
    const segs: Array<[THREE.Vector3, THREE.Vector3]> = [];

    perpendicularMarks.forEach((mark) => {
      const vCoords = coordinates[mark.vertex];
      if (!vCoords || mark.lines.length < 2) return;

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
 * Standard 3D Curved Solids (e.g. Sphere)
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
                roughness={0.3}
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
  const [faceOpacity, setFaceOpacity] = useState(0.18);

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

  // Extract faces (from visualization_graph.faces or direct faces prop)
  const effectiveFaces = useMemo(() => {
    if (faces && faces.length > 0) return faces;
    if (visualizationGraph?.faces && Object.keys(visualizationGraph.faces).length > 0) {
      return Object.values(visualizationGraph.faces).map((f) => f.vertices);
    }
    return [];
  }, [faces, visualizationGraph]);

  // Extract perpendicular marks
  const perpendicularMarks = useMemo(() => {
    const marks: Array<{ vertex: string; lines: string[] }> = [];

    // From auxiliary constructions
    const auxList = auxiliary || visualizationGraph?.auxiliary || [];
    auxList.forEach((aux) => {
      if (aux.perpendicular_marks && aux.perpendicular_marks.length > 0) {
        marks.push(...aux.perpendicular_marks);
      }
    });

    return marks;
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
          onClick={() => setFaceOpacity((o) => (o > 0.1 ? 0.08 : 0.22))}
          className="p-2 bg-[var(--panel-glass)] hover:bg-white/10 border border-[var(--border)] rounded-xl text-zinc-300 hover:text-white backdrop-blur-md shadow-sm active:scale-95 transition-all"
          title="Điều chỉnh độ mờ mặt đa diện"
        >
          <Eye className="w-3.5 h-3.5" />
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
      <div className="absolute top-3 left-3 z-20">
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
            {/* 1. Solid Semi-transparent Faces (Actual closed 3D solids) */}
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
            {perpendicularMarks.length > 0 && (
              <RightAngleMarkers3D
                perpendicularMarks={perpendicularMarks}
                coordinates={parsedCoordinates}
              />
            )}

            {/* 4. Curved Solids (Spheres, etc.) */}
            {solids && solids.length > 0 && (
              <Spheres3D solids={solids} coordinates={parsedCoordinates} />
            )}

            {/* 5. Vertices and Labels */}
            {vertices.map((v) => (
              <Point3D
                key={v.id}
                position={v.position}
                label={v.label}
                role={v.role}
                kind={v.kind}
              />
            ))}
          </group>
        </Center>
      </Canvas>
    </div>
  );
}
