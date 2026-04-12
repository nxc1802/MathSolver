"use client";

import { useMemo, useRef, useState } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { OrbitControls, Stars, Grid, Html, PerspectiveCamera, Center, Float } from "@react-three/drei";
import * as THREE from "three";
import { motion, AnimatePresence } from "framer-motion";
import { ZoomIn, ZoomOut, RotateCcw, Move3D, Maximize2 } from "lucide-react";

interface Interactive3DCanvasProps {
  coordinates?: Record<string, [number, number, number] | [number, number]>;
  drawingPhases?: Array<{
    phase: number;
    label: string;
    points: string[];
    segments: string[][];
  }>;
}

function Point({ position, label }: { position: [number, number, number], label: string }) {
  return (
    <group position={position}>
      <mesh>
        <sphereGeometry args={[0.08, 32, 32]} />
        <meshStandardMaterial color="white" emissive="white" emissiveIntensity={0.5} />
      </mesh>
      <Html distanceFactor={10}>
        <div className="select-none pointer-events-none">
          <span className="px-1.5 py-0.5 bg-black/50 backdrop-blur-md border border-white/20 rounded-md text-[10px] font-bold text-white whitespace-nowrap shadow-xl">
            {label}
          </span>
        </div>
      </Html>
    </group>
  );
}

function Segments({ segments, coordinates, phase }: { segments: string[][], coordinates: Record<string, any>, phase: number }) {
  const linePoints = useMemo(() => {
    const pts: THREE.Vector3[][] = [];
    segments.forEach(([p1, p2]) => {
      const c1 = coordinates[p1];
      const c2 = coordinates[p2];
      if (c1 && c2) {
        pts.push([
          new THREE.Vector3(c1[0], c1[2] || 0, -c1[1]), // Swap Y/Z for Three.js coordinate system
          new THREE.Vector3(c2[0], c2[2] || 0, -c2[1])
        ]);
      }
    });
    return pts;
  }, [segments, coordinates]);

  const isBase = phase === 1;

  return (
    <>
      {linePoints.map((pts, i) => (
        <Line 
          key={`${phase}-${i}`} 
          start={pts[0]} 
          end={pts[1]} 
          dashed={!isBase} 
          color={isBase ? "#6366f1" : "#a78bfa"} 
        />
      ))}
    </>
  );
}

function Line({ start, end, dashed, color }: { start: THREE.Vector3, end: THREE.Vector3, dashed?: boolean, color: string }) {
  const geometry = useMemo(() => {
    const geo = new THREE.BufferGeometry().setFromPoints([start, end]);
    return geo;
  }, [start, end]);

  return (
    <primitive object={new THREE.Line(geometry, dashed ? new THREE.LineDashedMaterial({ 
      color, 
      linewidth: isMobile() ? 1 : 2,
      dashSize: 0.2,
      gapSize: 0.1,
      transparent: true,
      opacity: 0.8
    }) : new THREE.LineBasicMaterial({ 
      color, 
      linewidth: isMobile() ? 1 : 2,
      transparent: true,
      opacity: 0.8
    }))} onUpdate={(line: THREE.Line) => { if (dashed) line.computeLineDistances(); }} />
  );
}

function isMobile() {
  if (typeof window === 'undefined') return false;
  return window.innerWidth < 768;
}

export default function Interactive3DCanvas({ coordinates, drawingPhases }: Interactive3DCanvasProps) {
  const [resetKey, setResetKey] = useState(0);

  const parsedCoordinates = useMemo(() => {
    if (!coordinates) return {};
    return coordinates;
  }, [coordinates]);

  const points = useMemo(() => {
    return Object.entries(parsedCoordinates).map(([label, coords]) => ({
      label,
      position: [coords[0], coords[2] || 0, -coords[1]] as [number, number, number]
    }));
  }, [parsedCoordinates]);

  if (!coordinates || points.length === 0) {
    return (
      <div className="bg-zinc-950 border border-white/5 rounded-3xl aspect-video flex items-center justify-center p-8">
        <p className="text-zinc-500 font-medium animate-pulse">Đang khởi tạo không gian 3D...</p>
      </div>
    );
  }

  return (
    <div className="bg-zinc-950 border border-white/10 rounded-3xl overflow-hidden aspect-video relative group select-none">
      {/* HUD Controls */}
      <div className="absolute top-4 right-4 flex flex-col gap-2 z-20">
        <button 
          onClick={() => setResetKey(k => k + 1)}
          className="p-2 bg-white/5 hover:bg-white/10 border border-white/10 rounded-xl text-zinc-400 hover:text-white transition-all backdrop-blur-md"
          title="Reset View"
        >
          <RotateCcw className="w-4 h-4" />
        </button>
      </div>

      <div className="absolute bottom-4 left-4 flex items-center gap-2 px-3 py-1.5 bg-white/5 border border-white/10 rounded-full backdrop-blur-md z-20 opacity-0 group-hover:opacity-100 transition-opacity">
        <Move3D className="w-3.5 h-3.5 text-zinc-500" />
        <span className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest">Xoay để quan sát • Cuộn để thu phóng</span>
      </div>

      <div className="absolute top-4 left-4 z-20">
        <div className="flex items-center gap-2 px-3 py-1 bg-indigo-500/10 border border-indigo-500/20 rounded-full backdrop-blur-md">
          <div className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-pulse" />
          <span className="text-[10px] font-bold text-indigo-300 uppercase tracking-widest">3D Interactive Mode</span>
        </div>
      </div>

      <Canvas key={resetKey} shadows gl={{ antialias: true }}>
        <PerspectiveCamera makeDefault position={[8, 8, 8]} fov={45} />
        <OrbitControls 
          enableDamping 
          dampingFactor={0.05} 
          minDistance={2} 
          maxDistance={50} 
          makeDefault 
        />
        
        <ambientLight intensity={0.6} />
        <pointLight position={[10, 10, 10]} intensity={1.5} />
        <spotLight position={[-10, 20, 10]} angle={0.15} penumbra={1} intensity={1} castShadow />

        <Stars radius={100} depth={50} count={2000} factor={4} saturation={0} fade speed={1} />
        
        <Grid 
          infiniteGrid 
          fadeDistance={30} 
          sectionSize={1} 
          sectionColor="#27272a" 
          cellColor="#18181b" 
          cellSize={0.5} 
        />
        
        <primitive object={new THREE.AxesHelper(5)} />

        <Center top>
          <group>
            {points.map((p) => (
              <Point key={p.label} position={p.position} label={p.label} />
            ))}

            {drawingPhases?.map((phase, idx) => (
              <Segments 
                key={idx} 
                segments={phase.segments} 
                coordinates={parsedCoordinates} 
                phase={phase.phase} 
              />
            ))}
          </group>
        </Center>
      </Canvas>
    </div>
  );
}
