'use client';

import React, { useEffect, useRef, useState } from 'react';

interface Point {
    name: string;
    x: number;
    y: number;
}

interface GeometryCanvasProps {
    dsl?: string;
    width?: number;
    height?: number;
}

export default function GeometryCanvas({ dsl, width = 400, height = 400 }: GeometryCanvasProps) {
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const [points, setPoints] = useState<Point[]>([]);
    const [triangles, setTriangles] = useState<string[][]>([]);
    const [currentStep, setCurrentStep] = useState(0);
    const [steps, setSteps] = useState<string[]>([]);

    // Parse DSL and extract commands
    useEffect(() => {
        if (!dsl) return;

        const parsedPoints: Point[] = [];
        const parsedTriangles: string[][] = [];
        const parsedSteps: string[] = [];

        const lines = dsl.split('\n');
        for (const line of lines) {
            const trimmed = line.trim();
            if (!trimmed || trimmed.startsWith('#')) continue;

            // Parse POINT(name, x, y)
            const pointMatch = trimmed.match(/POINT\((\w+),\s*([-\d.]+),\s*([-\d.]+)\)/);
            if (pointMatch) {
                parsedPoints.push({
                    name: pointMatch[1],
                    x: parseFloat(pointMatch[2]),
                    y: parseFloat(pointMatch[3]),
                });
            }

            // Parse TRIANGLE(name, A, B, C)
            const triangleMatch = trimmed.match(/TRIANGLE\((\w+),\s*(\w+),\s*(\w+),\s*(\w+)\)/);
            if (triangleMatch) {
                parsedTriangles.push([triangleMatch[2], triangleMatch[3], triangleMatch[4]]);
            }

            // Parse STEP("description")
            const stepMatch = trimmed.match(/STEP\(["'](.+)["']\)/);
            if (stepMatch) {
                parsedSteps.push(stepMatch[1]);
            }
        }

        setPoints(parsedPoints);
        setTriangles(parsedTriangles);
        setSteps(parsedSteps);
        setCurrentStep(0);
    }, [dsl]);

    // Draw on canvas
    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        if (!ctx) return;

        // Clear canvas
        ctx.clearRect(0, 0, width, height);

        // Calculate bounds and scale
        if (points.length === 0) {
            // Draw placeholder
            ctx.fillStyle = '#4a4a6a';
            ctx.font = '16px Inter, sans-serif';
            ctx.textAlign = 'center';
            ctx.fillText('Hình sẽ được vẽ tại đây', width / 2, height / 2);
            return;
        }

        const padding = 60;
        const xs = points.map(p => p.x);
        const ys = points.map(p => p.y);
        const minX = Math.min(...xs);
        const maxX = Math.max(...xs);
        const minY = Math.min(...ys);
        const maxY = Math.max(...ys);

        const rangeX = maxX - minX || 1;
        const rangeY = maxY - minY || 1;
        const scale = Math.min((width - 2 * padding) / rangeX, (height - 2 * padding) / rangeY);

        const offsetX = padding + ((width - 2 * padding) - rangeX * scale) / 2;
        const offsetY = padding + ((height - 2 * padding) - rangeY * scale) / 2;

        const transformX = (x: number) => offsetX + (x - minX) * scale;
        const transformY = (y: number) => height - (offsetY + (y - minY) * scale); // Flip Y

        // Draw triangles
        ctx.strokeStyle = '#6366f1';
        ctx.lineWidth = 2;
        ctx.fillStyle = 'rgba(99, 102, 241, 0.1)';

        for (const triangle of triangles) {
            const triPoints = triangle.map(name => points.find(p => p.name === name)).filter(Boolean) as Point[];
            if (triPoints.length === 3) {
                ctx.beginPath();
                ctx.moveTo(transformX(triPoints[0].x), transformY(triPoints[0].y));
                ctx.lineTo(transformX(triPoints[1].x), transformY(triPoints[1].y));
                ctx.lineTo(transformX(triPoints[2].x), transformY(triPoints[2].y));
                ctx.closePath();
                ctx.fill();
                ctx.stroke();
            }
        }

        // Draw points
        for (const point of points) {
            const px = transformX(point.x);
            const py = transformY(point.y);

            // Point circle
            ctx.beginPath();
            ctx.arc(px, py, 6, 0, Math.PI * 2);
            ctx.fillStyle = '#22d3ee';
            ctx.fill();
            ctx.strokeStyle = '#0f766e';
            ctx.lineWidth = 2;
            ctx.stroke();

            // Point label
            ctx.fillStyle = '#f0f0f0';
            ctx.font = 'bold 14px Inter, sans-serif';
            ctx.textAlign = 'center';
            ctx.fillText(point.name, px, py - 15);
        }

    }, [points, triangles, width, height, currentStep]);

    // Auto-advance steps
    useEffect(() => {
        if (steps.length === 0) return;

        const timer = setInterval(() => {
            setCurrentStep(prev => (prev + 1) % steps.length);
        }, 3000);

        return () => clearInterval(timer);
    }, [steps.length]);

    return (
        <div className="w-full">
            <div className="geometry-canvas" style={{ width, height }}>
                <canvas
                    ref={canvasRef}
                    width={width}
                    height={height}
                    className="relative z-10"
                />
            </div>

            {/* Step indicator */}
            {steps.length > 0 && (
                <div className="mt-4 text-center">
                    <p className="text-sm text-gray-400">
                        Bước {currentStep + 1}/{steps.length}
                    </p>
                    <p className="text-primary-light font-medium mt-1">
                        {steps[currentStep]}
                    </p>
                </div>
            )}
        </div>
    );
}
