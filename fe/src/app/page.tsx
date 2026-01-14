'use client';

import { useState } from 'react';
import ImageUploader from '@/components/ImageUploader';
import SolutionDisplay from '@/components/SolutionDisplay';
import GeometryCanvas from '@/components/GeometryCanvas';
import { solveWithImage, solveWithText, SolveResponse } from '@/lib/api';

export default function Home() {
  const [isLoading, setIsLoading] = useState(false);
  const [solution, setSolution] = useState<SolveResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleImageSelect = async (file: File) => {
    setIsLoading(true);
    setError(null);
    setSolution(null);

    try {
      const result = await solveWithImage(file);
      setSolution(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Có lỗi xảy ra');
    } finally {
      setIsLoading(false);
    }
  };

  const handleTextSubmit = async (text: string) => {
    setIsLoading(true);
    setError(null);
    setSolution(null);

    try {
      const result = await solveWithText(text);
      setSolution(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Có lỗi xảy ra');
    } finally {
      setIsLoading(false);
    }
  };

  const handleReset = () => {
    setSolution(null);
    setError(null);
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-3xl">📐</span>
            <h1 className="text-xl font-bold gradient-text">Visual Math Solver</h1>
          </div>
          <nav className="flex items-center gap-4">
            <a href="http://localhost:8000/docs" target="_blank" className="text-gray-400 hover:text-white transition-colors text-sm">
              API Docs
            </a>
          </nav>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 py-12">
        {!solution ? (
          /* Upload Section */
          <div className="text-center mb-12">
            <h2 className="text-4xl md:text-5xl font-bold mb-4">
              <span className="gradient-text">Giải toán thông minh</span>
            </h2>
            <p className="text-xl text-gray-400 max-w-2xl mx-auto mb-8">
              Upload ảnh bài toán hoặc nhập đề bài. AI sẽ giải chi tiết từng bước và vẽ hình minh họa.
            </p>

            <ImageUploader
              onImageSelect={handleImageSelect}
              onTextSubmit={handleTextSubmit}
              isLoading={isLoading}
            />

            {/* Error Display */}
            {error && (
              <div className="mt-6 max-w-md mx-auto p-4 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400">
                <p className="flex items-center gap-2">
                  <span>⚠️</span>
                  {error}
                </p>
              </div>
            )}

            {/* Features */}
            <div className="mt-16 grid grid-cols-1 md:grid-cols-3 gap-6 max-w-4xl mx-auto">
              <div className="glass-card p-6 text-center">
                <div className="text-4xl mb-4">📷</div>
                <h3 className="font-semibold mb-2">OCR Thông Minh</h3>
                <p className="text-sm text-gray-400">Nhận diện công thức và hình vẽ từ ảnh chụp</p>
              </div>
              <div className="glass-card p-6 text-center">
                <div className="text-4xl mb-4">🧠</div>
                <h3 className="font-semibold mb-2">AI Reasoning</h3>
                <p className="text-sm text-gray-400">Sử dụng DeepSeek-R1 để lập luận toán học</p>
              </div>
              <div className="glass-card p-6 text-center">
                <div className="text-4xl mb-4">📊</div>
                <h3 className="font-semibold mb-2">Trực Quan Hóa</h3>
                <p className="text-sm text-gray-400">Vẽ hình 2D/3D và animation từng bước</p>
              </div>
            </div>
          </div>
        ) : (
          /* Solution Section */
          <div>
            <button
              onClick={handleReset}
              className="btn-secondary mb-8 flex items-center gap-2"
            >
              ← Giải bài mới
            </button>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
              {/* Solution Display */}
              <div>
                <SolutionDisplay
                  problem={solution.problem}
                  solution={solution.solution}
                  geometryDsl={solution.geometry_dsl}
                />
              </div>

              {/* Geometry Visualization */}
              <div className="lg:sticky lg:top-8">
                <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                  <span className="text-secondary">📐</span>
                  Hình minh họa
                </h3>
                <div className="glass-card p-6">
                  <GeometryCanvas
                    dsl={solution.geometry_dsl}
                    width={400}
                    height={400}
                  />
                </div>

                {/* Metadata */}
                <div className="mt-4 text-sm text-gray-500">
                  <p>Model: {solution.metadata.model}</p>
                  <p>Thời gian: {solution.metadata.processing_time_ms}ms</p>
                </div>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-border mt-20">
        <div className="max-w-7xl mx-auto px-4 py-8 text-center text-gray-500 text-sm">
          <p>Visual Math Solver © 2026 | Powered by DeepSeek-R1 via MegaLLM</p>
        </div>
      </footer>
    </div>
  );
}
