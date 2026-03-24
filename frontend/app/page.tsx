"use client";

import React, { useState, useEffect, useRef } from 'react';
import Head from 'next/head';

// --- Icons ---
const IconSparkles = () => <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z"/></svg>;
const IconBrain = () => <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"/></svg>;
const IconCode = () => <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4"/></svg>;
const IconMonitor = () => <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/></svg>;

export default function Home() {
  const [inputText, setInputText] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [mounted, setMounted] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);

  // Fix hydration issues
  useEffect(() => {
    setMounted(true);
  }, []);

  // WebSocket for Real-time Updates
  useEffect(() => {
    if (!jobId || !mounted) return;

    const wsUrl = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000';
    const ws = new WebSocket(`${wsUrl}/ws/${jobId}`);

    ws.onopen = () => console.log("WebSocket connected:", jobId);
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      console.log("WebSocket Update:", data);
      
      // Update result and steps
      if (data.status === "processing") setCurrentStep(1);
      if (data.status === "solving") setCurrentStep(2);
      if (data.status === "rendering") {
        setCurrentStep(3);
        setResult(data.result || data);
      }
      if (data.status === "success" || data.status === "error") {
        setCurrentStep(data.status === "success" ? 4 : -1);
        setResult(data.result || data);
      }
    };

    ws.onerror = (err) => console.error("WebSocket Error:", err);
    ws.onclose = () => console.log("WebSocket closed");

    return () => ws.close();
  }, [jobId, mounted]);

  const handleSolve = async () => {
    if (!inputText.trim()) return;
    
    setLoading(true);
    setResult(null);
    setJobId(null);
    setCurrentStep(1);
    
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    try {
      const response = await fetch(`${apiUrl}/api/v1/solve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: inputText }),
      });
      const data = await response.json();
      setJobId(data.job_id);
    } catch (error) {
      console.error("Error solving:", error);
      setCurrentStep(-1);
    } finally {
      setLoading(false);
    }
  };

  if (!mounted) return <div className="min-h-screen bg-slate-950" />;

  return (
    <div className="min-h-screen bg-[#020617] text-slate-100 font-sans selection:bg-cyan-500/30">
      <Head>
        <title>MathSolver v3.0 | AI Geometry Reasoning</title>
      </Head>

      {/* --- Header --- */}
      <nav className="p-5 flex justify-between items-center border-b border-white/5 bg-slate-900/40 backdrop-blur-xl sticky top-0 z-50">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-gradient-to-br from-cyan-400 to-blue-600 rounded-xl flex items-center justify-center shadow-lg shadow-cyan-500/20">
            <IconSparkles />
          </div>
          <div className="text-xl font-black tracking-tighter">
            MATH<span className="text-cyan-400">SOLVER</span>
            <span className="text-[10px] font-mono border border-cyan-500/30 rounded px-1.5 py-0.5 ml-2 text-cyan-500 bg-cyan-500/5">v3.0</span>
          </div>
        </div>
        <div className="hidden md:flex gap-8 text-sm font-medium text-slate-400">
          <a href="#" className="hover:text-white transition-all transform hover:scale-105">Engine</a>
          <a href="#" className="hover:text-white transition-all transform hover:scale-105">Docs</a>
          <a href="https://github.com" className="hover:text-white transition-all transform hover:scale-105">GitHub</a>
        </div>
      </nav>

      <main className="max-w-7xl mx-auto px-6 py-12 md:py-20">
        {/* --- Hero Section --- */}
        <div className="text-center mb-16 space-y-6">
          <h1 className="text-5xl md:text-8xl font-black tracking-tight leading-[1.1]">
            Giải Toán Hình <br/> 
            <span className="bg-gradient-to-r from-cyan-400 via-blue-500 to-indigo-600 bg-clip-text text-transparent drop-shadow-sm">
              Trực Quan Hóa AI
            </span>
          </h1>
          <p className="text-slate-400 text-lg md:text-xl max-w-3xl mx-auto font-medium">
            Hệ thống Multi-Agent bóc tách đề bài, giải toán chính xác <br className="hidden md:block"/> và tự động dựng animation step-by-step.
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12">
          {/* --- Left Column: Input --- */}
          <div className="lg:col-span-7 space-y-8">
            <div className="group relative bg-slate-900/50 border border-white/10 rounded-[2rem] p-8 shadow-2xl backdrop-blur-sm transition-all hover:border-cyan-500/30">
              <div className="absolute -top-4 -right-4 w-24 h-24 bg-cyan-500/10 blur-3xl rounded-full" />
              
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-lg font-bold flex items-center gap-3">
                  <span className="w-2.5 h-2.5 bg-cyan-500 rounded-full shadow-[0_0_10px_rgba(6,182,212,0.5)]" />
                  Đề bài của bạn
                </h2>
                <div className="text-[10px] uppercase tracking-widest font-bold text-slate-500">Geometry Input</div>
              </div>
              
              <div className="relative">
                <textarea 
                  className="w-full h-56 bg-white/5 border border-white/5 rounded-2xl p-6 text-slate-100 placeholder:text-slate-600 focus:outline-none focus:ring-2 focus:ring-cyan-500/20 focus:border-cyan-500/30 transition-all resize-none mb-6 text-lg leading-relaxed shadow-inner"
                  placeholder="Ví dụ: Cho tam giác ABC vuông tại A, có AB=3, AC=4. Tính BC..."
                  value={inputText}
                  onChange={(e) => setInputText(e.target.value)}
                />
                {!inputText && (
                  <div className="absolute bottom-10 right-6 pointer-events-none opacity-20">
                    <IconBrain />
                  </div>
                )}
              </div>

              <div className="flex flex-col sm:flex-row justify-between items-center gap-4">
                <div className="flex gap-3">
                    <button className="flex items-center gap-2.5 text-xs font-bold text-slate-400 hover:text-white transition-all border border-white/10 rounded-xl px-5 py-3 bg-white/5 hover:bg-white/10 active:scale-95">
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"></path></svg>
                        Upload OCR
                    </button>
                    <button className="flex items-center gap-2.5 text-xs font-bold text-slate-400 hover:text-white transition-all border border-white/10 rounded-xl px-5 py-3 bg-white/5 hover:bg-white/10 active:scale-95" onClick={() => setInputText("Cho tam giác ABC đều cạnh bằng 5.")}>
                        Dùng ví dụ
                    </button>
                </div>
                <button 
                    onClick={handleSolve}
                    disabled={loading || !inputText.trim()}
                    className="w-full sm:w-auto bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white font-black py-4 px-10 rounded-2xl shadow-xl shadow-cyan-500/25 transform active:scale-[0.98] transition-all disabled:opacity-30 disabled:grayscale uppercase tracking-wider text-sm"
                >
                  {loading ? (
                    <span className="flex items-center gap-2">
                      <svg className="animate-spin h-4 w-4 text-white" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      ĐANG PHÂN TÍCH...
                    </span>
                  ) : "Giải ngay bây giờ"}
                </button>
              </div>
            </div>

            {/* --- Progress Stepper --- */}
            {(jobId || loading) && (
              <div className="bg-slate-900/30 border border-white/5 rounded-3xl p-8 backdrop-blur-sm">
                <div className="flex justify-between items-start">
                  {[
                    { label: 'OCR', icon: <IconSparkles /> },
                    { label: 'Parser', icon: <IconBrain /> },
                    { label: 'Solver', icon: <IconCode /> },
                    { label: 'Render', icon: <IconMonitor /> }
                  ].map((step, idx) => (
                    <div key={idx} className="flex flex-col items-center gap-4 relative group">
                      <div className={`w-14 h-14 rounded-2xl flex items-center justify-center transition-all duration-700 z-10 ${
                        currentStep > idx ? 'bg-cyan-500 text-white shadow-lg shadow-cyan-500/40' : 
                        currentStep === idx ? 'bg-slate-800 text-cyan-400 ring-2 ring-cyan-500/50 animate-pulse' : 
                        'bg-slate-800/40 text-slate-600'
                      }`}>
                        {step.icon}
                      </div>
                      <span className={`text-[10px] font-bold uppercase tracking-widest ${currentStep >= idx ? 'text-cyan-400' : 'text-slate-600'}`}>
                        {step.label}
                      </span>
                      {idx < 3 && (
                        <div className={`absolute top-7 left-14 w-[calc(100%+1rem)] h-0.5 transition-colors duration-1000 ${
                          currentStep > idx ? 'bg-cyan-500' : 'bg-slate-800'
                        }`} />
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* --- Right Column: Results --- */}
          <div className="lg:col-span-5">
            {!result ? (
              <div className="h-full min-h-[400px] border-2 border-dashed border-white/5 rounded-[2.5rem] flex flex-col items-center justify-center text-slate-600 space-y-4 bg-slate-900/20">
                <div className="p-5 bg-white/5 rounded-full border border-white/5">
                  <IconBrain />
                </div>
                <p className="text-sm font-medium tracking-wide">Kết quả sẽ hiển thị tại đây...</p>
              </div>
            ) : (
              <div className="space-y-6 animate-in fade-in slide-in-from-right-10 duration-1000">
                {/* --- Video/Preview Card --- */}
                <div className="bg-slate-900 border border-white/10 rounded-[2.5rem] overflow-hidden shadow-2xl relative">
                  <div className="p-5 border-b border-white/5 bg-slate-900/60 backdrop-blur-md flex justify-between items-center">
                    <div className="flex items-center gap-2">
                        <IconMonitor />
                        <span className="text-xs font-black uppercase tracking-tighter">Render Engine</span>
                    </div>
                    {currentStep < 4 ? (
                        <span className="flex items-center gap-1.5 text-[10px] font-bold text-amber-500 bg-amber-500/10 px-2 py-1 rounded-lg border border-amber-500/20">
                            <span className="w-1.5 h-1.5 bg-amber-500 rounded-full animate-ping" />
                            Rendering...
                        </span>
                    ) : (
                        <span className="text-[10px] font-bold text-cyan-400 bg-cyan-400/10 px-3 py-1 rounded-lg border border-cyan-400/20 uppercase tracking-widest">
                            Ready
                        </span>
                    )}
                  </div>
                  
                  <div className="aspect-square bg-black flex items-center justify-center relative group">
                    <img 
                        src="https://images.unsplash.com/photo-1635070041078-e363dbe005cb?q=80&w=2070&auto=format&fit=crop" 
                        className="w-full h-full object-cover opacity-30 group-hover:opacity-50 transition-all duration-700 blur-[2px] group-hover:blur-0"
                        alt="Geometry rendering preview"
                    />
                    <div className="absolute inset-0 flex flex-col items-center justify-center transition-transform group-hover:scale-105 duration-700">
                        <button className="w-20 h-20 bg-gradient-to-br from-cyan-400 to-blue-600 rounded-full flex items-center justify-center shadow-[0_0_50px_rgba(6,182,212,0.4)] hover:shadow-cyan-500/60 transition-all active:scale-90 border-4 border-white/20">
                            <svg className="w-8 h-8 text-white ml-1.5" fill="currentColor" viewBox="0 0 20 20"><path d="M4.5 3.5a1 1 0 011 1v11a1 1 0 01-1.707.707l-6-6a1 1 0 010-1.414l6-6A1 1 0 014.5 3.5z"></path></svg>
                        </button>
                        <p className="text-[10px] text-slate-500 mt-6 font-mono tracking-tight bg-black/60 px-3 py-1 rounded-full backdrop-blur-md border border-white/5">
                            VIDEO_RES: 1080x1080 (MANIM_CORE)
                        </p>
                    </div>
                  </div>
                </div>

                {/* --- Logic Breakdown --- */}
                <div className="bg-slate-900 border border-white/10 rounded-[2.5rem] p-8 space-y-8 shadow-2xl relative overflow-hidden">
                    <div className="absolute top-0 right-0 w-32 h-32 bg-blue-500/5 blur-3xl opacity-50" />
                    
                    <div>
                        <h3 className="text-[10px] font-black text-slate-500 mb-5 tracking-[0.2em] uppercase flex items-center gap-2">
                             Semantic Analysis 
                        </h3>
                        <div className="grid grid-cols-2 gap-4">
                            <div className="p-5 bg-white/5 rounded-2xl border border-white/5 group hover:border-cyan-500/30 transition-all">
                                <span className="text-[10px] font-bold text-slate-500 block mb-1 uppercase tracking-widest">Master Shape</span>
                                <span className="text-xl font-black text-white group-hover:text-cyan-400 transition-colors uppercase tracking-tight">{result.semantic?.type || 'N/A'}</span>
                            </div>
                            <div className="p-5 bg-white/5 rounded-2xl border border-white/5 group hover:border-blue-500/30 transition-all">
                                <span className="text-[10px] font-bold text-slate-500 block mb-1 uppercase tracking-widest">Points List</span>
                                <div className="flex gap-2.5 mt-2">
                                    {result.semantic?.entities?.map((e: string) => (
                                        <span key={e} className="w-8 h-8 flex items-center justify-center bg-slate-800 rounded-lg text-xs font-black text-white border border-white/5">{e}</span>
                                    ))}
                                </div>
                            </div>
                        </div>
                    </div>

                    <div>
                        <h3 className="text-[10px] font-black text-slate-500 mb-5 tracking-[0.2em] uppercase">Geometry DSL</h3>
                        <div className="relative group">
                            <div className="absolute -inset-1 bg-gradient-to-r from-cyan-500 to-blue-600 rounded-2xl opacity-5 group-hover:opacity-10 transition-opacity blur" />
                            <pre className="relative bg-[#0a0f1e] p-6 rounded-2xl border border-white/5 text-cyan-400 text-xs font-mono overflow-x-auto leading-relaxed shadow-inner">
                                {result.dsl}
                            </pre>
                        </div>
                    </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </main>

      <footer className="mt-20 p-12 border-t border-white/5 bg-slate-950/50 text-center">
        <div className="flex items-center justify-center gap-4 mb-4 opacity-50">
            <div className="w-1.5 h-1.5 bg-slate-500 rounded-full" />
            <div className="w-1.5 h-1.5 bg-slate-500 rounded-full" />
            <div className="w-1.5 h-1.5 bg-slate-500 rounded-full" />
        </div>
        <p className="text-slate-500 text-xs font-bold tracking-[0.2em] uppercase">© 2026 Visual Math Solver | Advanced Agentic Engine</p>
      </footer>
    </div>
  );
}
