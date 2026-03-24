import React, { useState } from 'react';
import Head from 'next/head';

export default function Home() {
  const [inputText, setInputText] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [jobId, setJobId] = useState<string | null>(null);

  // WebSocket for Real-time Updates
  React.useEffect(() => {
    if (!jobId) return;

    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    const wsUrl = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000';

    const ws = new WebSocket(`${wsUrl}/ws/${jobId}`);
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      console.log("WebSocket Update:", data);
      if (data.status === "success" || data.status === "rendering" || data.status === "error") {
        setResult(data.result || data);
      }
    };

    return () => ws.close();
  }, [jobId]);

  const handleSolve = async () => {
    setLoading(true);
    setResult(null);
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
    }
    setLoading(false);
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 font-sans">
      <Head>
        <title>Visual Math Solver v3.0 | AI Geometry Reasoning</title>
      </Head>

      {/* Hero Section */}
      <nav className="p-6 flex justify-between items-center border-b border-slate-800 bg-slate-900/50 backdrop-blur-md sticky top-0 z-50">
        <div className="text-2xl font-bold bg-gradient-to-r from-cyan-400 to-blue-500 bg-clip-text text-transparent">
          MATH SOLVER <span className="text-xs font-mono border border-cyan-500/50 rounded px-1 ml-2">v3.0</span>
        </div>
        <div className="flex gap-6 text-sm text-slate-400">
          <a href="#" className="hover:text-cyan-400 transition-colors">Features</a>
          <a href="#" className="hover:text-cyan-400 transition-colors">Documentation</a>
          <a href="#" className="hover:text-cyan-400 transition-colors">Github</a>
        </div>
      </nav>

      <main className="max-w-6xl mx-auto p-8 py-16">
        <div className="text-center mb-16 space-y-4">
          <h1 className="text-5xl md:text-7xl font-extrabold tracking-tight">
            Giải Toán Hình <br/> 
            <span className="bg-gradient-to-r from-cyan-400 via-blue-500 to-purple-600 bg-clip-text text-transparent">
              Trực Quan Hóa Bằng AI
            </span>
          </h1>
          <p className="text-slate-400 text-lg max-w-2xl mx-auto">
            Hệ thống Multi-Agent tiên tiến giúp bóc tách đề bài, giải toán chính xác và tự động dựng video animation step-by-step.
          </p>
        </div>

        {/* Input Card */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-8 shadow-2xl relative overflow-hidden group">
          <div className="absolute top-0 left-0 w-1 h-full bg-cyan-500 transition-all group-hover:w-2" />
          
          <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
            <span className="w-2 h-2 bg-cyan-500 rounded-full animate-pulse" />
            Nhập đề bài của bạn
          </h2>
          
          <textarea 
            className="w-full h-40 bg-slate-800/50 border border-slate-700 rounded-xl p-4 text-slate-100 focus:outline-none focus:ring-2 focus:ring-cyan-500/50 focus:border-cyan-500/50 transition-all resize-none mb-6"
            placeholder="Ví dụ: Cho tam giác ABC đều cạnh bằng 5..."
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
          />

          <div className="flex justify-between items-center">
            <div className="flex gap-4">
                <button className="flex items-center gap-2 text-sm text-slate-400 hover:text-cyan-400 transition-colors border border-slate-700 rounded-lg px-4 py-2 bg-slate-800/30">
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"></path></svg>
                    Tải ảnh lên (OCR)
                </button>
            </div>
            <button 
                onClick={handleSolve}
                disabled={loading}
                className="bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white font-bold py-3 px-8 rounded-xl shadow-lg shadow-cyan-500/20 transform active:scale-95 transition-all disabled:opacity-50"
            >
              {loading ? "Đang xử lý..." : "PHÂN TÍCH & GIẢI TOÁN"}
            </button>
          </div>
        </div>

        {/* Results Section */}
        {result && (
          <div className="mt-16 grid grid-cols-1 lg:grid-cols-2 gap-8 animate-in fade-in slide-in-from-bottom-8 duration-700">
            {/* Video Player */}
            <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-2xl">
              <div className="p-4 border-b border-slate-800 bg-slate-900/80 font-semibold text-sm tracking-wider flex justify-between items-center">
                ANIMATION PREVIEW
                <span className="text-cyan-400 text-xs font-mono">1080p rendered</span>
              </div>
              <div className="aspect-video bg-black flex items-center justify-center relative group">
                {/* Mocking video view */}
                <img 
                    src="https://images.unsplash.com/photo-1635070041078-e363dbe005cb?q=80&w=2070&auto=format&fit=crop" 
                    className="w-full h-full object-cover opacity-40 group-hover:opacity-60 transition-opacity"
                    alt="Geometry rendering preview"
                />
                <div className="absolute inset-0 flex flex-col items-center justify-center">
                    <button className="w-16 h-16 bg-cyan-500 rounded-full flex items-center justify-center shadow-2xl hover:scale-110 transition-transform">
                        <svg className="w-8 h-8 text-white ml-1" fill="currentColor" viewBox="0 0 20 20"><path d="M4.5 3.5a1 1 0 011 1v11a1 1 0 01-1.707.707l-6-6a1 1 0 010-1.414l6-6A1 1 0 014.5 3.5z"></path><path d="M15.5 16.5a1 1 0 01-1-1v-11a1 1 0 011.707-.707l6 6a1 1 0 010 1.414l-6 6a1 1 0 01-.707.293z"></path></svg>
                    </button>
                    <p className="text-xs text-slate-400 mt-4 font-mono">Video URL: {result.video_url?.substring(0, 40)}...</p>
                </div>
              </div>
            </div>

            {/* Logical Steps / DSL */}
            <div className="space-y-6">
                <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-6 shadow-xl">
                    <h3 className="text-sm font-bold text-slate-500 mb-4 tracking-widest uppercase">Semantic Reasoning</h3>
                    <div className="space-y-2">
                        <div className="p-3 bg-slate-800/40 rounded-lg border border-slate-700/50 flex justify-between items-center shadow-inner">
                            <span className="text-sm font-medium">Shapes Identified</span>
                            <span className="text-xs bg-cyan-500/20 text-cyan-400 px-2 py-1 rounded-md border border-cyan-500/30 uppercase font-bold">{result.semantic?.type}</span>
                        </div>
                        <div className="p-3 bg-slate-800/40 rounded-lg border border-slate-700/50 shadow-inner">
                            <span className="text-sm font-medium block mb-2">Extracted Entities</span>
                            <div className="flex gap-2">
                                {result.semantic?.entities?.map((e: string) => (
                                    <span key={e} className="px-3 py-1 bg-slate-700/50 rounded text-xs font-mono">{e}</span>
                                ))}
                            </div>
                        </div>
                    </div>
                </div>

                <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-6 shadow-xl">
                    <h3 className="text-sm font-bold text-slate-500 mb-4 tracking-widest uppercase">Geometry DSL (Engine Input)</h3>
                    <pre className="bg-slate-950 p-4 rounded-xl border border-slate-800 text-cyan-500 text-xs font-mono overflow-x-auto leading-relaxed shadow-inner">
                        {result.dsl}
                    </pre>
                </div>
            </div>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="mt-32 p-12 border-t border-slate-900 bg-slate-950 text-center space-y-4">
        <p className="text-slate-500 text-sm">© 2026 Visual Math Solver v3.0 | Built with Multi-Agent AI Architecture</p>
      </footer>

      <style jsx global>{`
        @keyframes fade-in { from { opacity: 0; } to { opacity: 1; } }
        @keyframes slide-up { from { transform: translateY(20px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
      `}</style>
    </div>
  );
}
