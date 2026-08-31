"use client";

import { useMemo, useState } from "react";
import { Canvas } from "@react-three/fiber";
import { OrbitControls, Stars, Grid, Html, PerspectiveCamera, Center } from "@react-three/drei";
import * as THREE from "three";
import { RotateCcw } from "lucide-react";

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
}

interface Interactive3DCanvasProps {
  coordinates?: Record<string, [number, number, number] | [number, number]>;
  drawingPhases?: Array<{
    phase: number;
    label: string;
    points: string[];
    segments: string[][];
  }>;
  faces?: string[][];
  solids?: SolidMeta[];
}

function toVector3(coords: [number, number, number] | [number, number]): THREE.Vector3 {
  const x = coords[0] || 0;
  const y = coords[1] || 0;
  const z = (coords as [number, number, number])[2] || 0;
  // Three.js: X=right, Y=up, Z=depth (Math: X, Y=horizontal, Z=up)
  return new THREE.Vector3(x, z, -y);
}

function Point3D({ position, label }: { position: [number, number, number]; label: string }) {
  return (
    <group position={position}>
      <mesh>
        <sphereGeometry args={[0.08, 32, 32]} />
        <meshStandardMaterial color="#ffffff" emissive="#818cf8" emissiveIntensity={0.6} roughness={0.2} />
      </mesh>
      <Html distanceFactor={14}>
        <div className="select-none pointer-events-none -translate-x-1/2 -translate-y-6">
          <span className="px-1.5 py-0.5 bg-black/75 backdrop-blur-md border border-white/20 rounded-md text-[10px] font-mono font-bold text-white whitespace-nowrap shadow-xl">
            {label}
          </span>
        </div>
      </Html>
    </group>
  );
}

function Segments3D({
  segments,
  coordinates,
  phase,
}: {
  segments: string[][];
  coordinates: Record<string, [number, number, number] | [number, number]>;
  phase: number;
}) {
  const linePoints = useMemo(() => {
    const pts: THREE.Vector3[][] = [];
    segments.forEach(([p1, p2]) => {
      const c1 = coordinates[p1];
      const c2 = coordinates[p2];
      if (c1 && c2) {
        pts.push([toVector3(c1), toVector3(c2)]);
      }
    });
    return pts;
  }, [segments, coordinates]);

  const isBase = phase === 1;

  return (
    <>
      {linePoints.map((pts, i) => (
        <Line3D
          key={`${phase}-${i}`}
          start={pts[0]}
          end={pts[1]}
          dashed={!isBase}
          color={isBase ? "#818cf8" : "#c084fc"}
        />
      ))}
    </>
  );
}

function Line3D({
  start,
  end,
  dashed,
  color,
}: {
  start: THREE.Vector3;
  end: THREE.Vector3;
  dashed?: boolean;
  color: string;
}) {
  const geometry = useMemo(() => {
    const geo = new THREE.BufferGeometry().setFromPoints([start, end]);
    return geo;
  }, [start, end]);

  return (
    <primitive
      object={
        new THREE.Line(
          geometry,
          dashed
            ? new THREE.LineDashedMaterial({
                color,
                linewidth: 2,
                dashSize: 0.2,
                gapSize: 0.1,
                transparent: true,
                opacity: 0.85,
              })
            : new THREE.LineBasicMaterial({
                color,
                linewidth: 2,
                transparent: true,
                opacity: 0.9,
              })
        )
      }
      onUpdate={(line: THREE.Line) => {
        if (dashed) line.computeLineDistances();
      }}
    />
  );
}

function Faces3D({
  faces,
  coordinates,
}: {
  faces: string[][];
  coordinates: Record<string, [number, number, number] | [number, number]>;
}) {
  const faceGeometries = useMemo(() => {
    const geos: THREE.BufferGeometry[] = [];
    faces.forEach((facePts) => {
      const validVectors = facePts
        .map((p) => (coordinates[p] ? toVector3(coordinates[p]) : null))
        .filter((v): v is THREE.Vector3 => Boolean(v));
      if (validVectors.length >= 3) {
        const vertices: number[] = [];
        for (let i = 1; i < validVectors.length - 1; i++) {
          const v0 = validVectors[0];
          const v1 = validVectors[i];
          const v2 = validVectors[i + 1];
          vertices.push(v0.x, v0.y, v0.z, v1.x, v1.y, v1.z, v2.x, v2.y, v2.z);
        }
        const geo = new THREE.BufferGeometry();
        geo.setAttribute("position", new THREE.Float32BufferAttribute(vertices, 3));
        geo.computeVertexNormals();
        geos.push(geo);
      }
    });
    return geos;
  }, [faces, coordinates]);

  return (
    <>
      {faceGeometries.map((geo, idx) => (
        <mesh key={idx} geometry={geo}>
          <meshStandardMaterial
            color="#6366f1"
            transparent
            opacity={0.18}
            side={THREE.DoubleSide}
            depthWrite={false}
          />
        </mesh>
      ))}
    </>
  );
}

function SolidMeshes3D({
  solids,
  coordinates,
}: {
  solids: SolidMeta[];
  coordinates: Record<string, [number, number, number] | [number, number]>;
}) {
  return (
    <>
      {solids.map((solid, idx) => {
        if (solid.type === "sphere" && solid.center && coordinates[solid.center]) {
          const pos = toVector3(coordinates[solid.center]);
          const r = solid.radius || 3;
          return (
            <mesh key={`sphere-${idx}`} position={pos}>
              <sphereGeometry args={[r, 32, 32]} />
              <meshStandardMaterial
                color="#38bdf8"
                transparent
                opacity={0.2}
                side={THREE.DoubleSide}
              />
            </mesh>
          );
        }
        return null;
      })}
    </>
  );
}

export default function Interactive3DCanvas({
  coordinates,
  drawingPhases,
  faces,
  solids,
}: Interactive3DCanvasProps) {
  const [resetKey, setResetKey] = useState(0);

  const parsedCoordinates = useMemo(() => {
    return coordinates ?? {};
  }, [coordinates]);

  const points = useMemo(() => {
    return Object.entries(parsedCoordinates).map(([label, coords]) => {
      const z = (coords as [number, number, number])[2] || 0;
      return {
        label,
        position: [coords[0], z, -coords[1]] as [number, number, number],
      };
    });
  }, [parsedCoordinates]);

  if (!coordinates || points.length === 0) {
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
      <div className="absolute top-3 right-3 flex flex-col gap-1.5 z-20">
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
            3D Spatial Engine
          </span>
        </div>
      </div>

      {/* 3D Canvas Fiber Scene */}
      <Canvas key={resetKey} shadows gl={{ antialias: true }}>
        <PerspectiveCamera makeDefault position={[10, 10, 10]} fov={45} />
        <OrbitControls
          enableDamping
          dampingFactor={0.06}
          minDistance={2}
          maxDistance={60}
          makeDefault
        />

        <ambientLight intensity={0.8} />
        <pointLight position={[15, 20, 15]} intensity={2.0} />
        <spotLight position={[-15, 25, 10]} angle={0.25} penumbra={1} intensity={1.5} castShadow />

        <Stars radius={90} depth={40} count={1200} factor={3} saturation={0} fade speed={0.8} />

        <Grid
          infiniteGrid
          fadeDistance={30}
          sectionSize={1}
          sectionColor="#27272a"
          cellColor="#141418"
          cellSize={0.5}
        />

        <primitive object={new THREE.AxesHelper(5)} />

        <Center top>
          <group>
            {points.map((p) => (
              <Point3D key={p.label} position={p.position} label={p.label} />
            ))}

            {drawingPhases?.map((phase, idx) => (
              <Segments3D
                key={idx}
                segments={phase.segments}
                coordinates={parsedCoordinates}
                phase={phase.phase}
              />
            ))}

            {faces && faces.length > 0 && (
              <Faces3D faces={faces} coordinates={parsedCoordinates} />
            )}

            {solids && solids.length > 0 && (
              <SolidMeshes3D solids={solids} coordinates={parsedCoordinates} />
            )}
          </group>
        </Center>
      </Canvas>
    </div>
  );
}
