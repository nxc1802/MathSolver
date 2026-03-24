"use client";

import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from "framer-motion";
import Header from "@/components/Header";
import SolverForm from "@/components/SolverForm";
import StatusStepper from "@/components/StatusStepper";
import ResultCard from "@/components/ResultCard";
import AnimationPreview from "@/components/AnimationPreview";

export default function Home() {
  const [inputText, setInputText] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [mounted, setMounted] = useState(false);
  const [status, setStatus] = useState("idle");

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (!jobId || !mounted) return;

    const wsUrl = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000';
    const ws = new WebSocket(`${wsUrl}/ws/${jobId}`);

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      console.log("WS Update:", data);
      setStatus(data.status);
      if (data.result) setResult(data.result);
    };

    return () => ws.close();
  }, [jobId, mounted]);

  const handleSolve = async () => {
    if (!inputText.trim()) return;
    setLoading(true);
    setResult(null);
    setJobId(null);
    setStatus("processing");

    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    try {
      const response = await fetch(`${apiUrl}/api/v1/solve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: inputText }),
      });
      const data = await response.json();
      setJobId(data.job_id);
    } catch (err) {
      console.error(err);
      setStatus("error");
    } finally {
      setLoading(false);
    }
  };

  if (!mounted) return null;

  return (
    <div className="min-h-screen pb-20">
      <Header />
      
      <main className="max-w-7xl mx-auto px-6 pt-32">
        <div className="text-center mb-16">
          <motion.h1 
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-6xl md:text-7xl font-black tracking-tight text-white mb-6"
          >
            Giải Toán Hình <br/>
            <span className="text-gradient">Agentic Intelligence</span>
          </motion.h1>
          <motion.p 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.2 }}
            className="text-zinc-400 text-lg max-w-2xl mx-auto"
          >
            Sử dụng hệ thống Multi-Agent để phân tích, giải toán và tự động minh họa bằng Manim Engine.
          </motion.p>
        </div>

        <SolverForm 
          input={inputText}
          setInput={setInputText}
          loading={loading}
          onSolve={handleSolve}
          onExample={() => setInputText("Cho tam giác ABC đều cạnh bằng 5.")}
        />

        <AnimatePresence>
          {(jobId || status !== "idle") && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
            >
              <StatusStepper status={status} />
            </motion.div>
          )}
        </AnimatePresence>

        <AnimatePresence>
          {result && (
            <motion.div 
              initial={{ opacity: 0, y: 40 }}
              animate={{ opacity: 1, y: 0 }}
              className="mt-20 grid grid-cols-1 lg:grid-cols-2 gap-8 items-start"
            >
              <div className="space-y-6">
                <ResultCard 
                  title="Semantic Analysis" 
                  content={result.semantic_analysis || result.semantic?.text || "Đang phân tích..."} 
                />
                <ResultCard 
                  title="Geometry DSL" 
                  content={result.geometry_dsl || "Đang tạo DSL..."} 
                  delay={0.1}
                />
              </div>

              <AnimationPreview 
                videoUrl={result.video_url} 
                loading={status === "rendering"}
              />
            </motion.div>
          )}
        </AnimatePresence>
      </main>

      <footer className="mt-32 text-center text-zinc-600 text-[10px] font-bold uppercase tracking-[0.3em]">
        © 2026 VISUAL MATH SOLVER | ADVANCED AGENTIC ENGINE
      </footer>
    </div>
  );
}
