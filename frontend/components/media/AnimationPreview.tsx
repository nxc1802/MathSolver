"use client";

import React from "react";
import { Film, Loader2, AlertCircle, RefreshCw, Sparkles, CheckCircle2 } from "lucide-react";
import VersionSwitcher from "../geometry/VersionSwitcher";
import type { VideoJobState } from "@/hooks/useSolverJob";

interface AnimationPreviewProps {
  videoUrl?: string | null;
  videoState?: VideoJobState;
  onRetry?: () => void;
  onRequestRender?: () => void;
  currentVersion?: number;
  totalVersions?: number;
  onNext?: () => void;
  onPrev?: () => void;
}

export default function AnimationPreview({
  videoUrl,
  videoState,
  onRetry,
  onRequestRender,
  currentVersion = 1,
  totalVersions = 1,
  onNext = () => {},
  onPrev = () => {},
}: AnimationPreviewProps) {
  const effectiveVideoUrl = videoUrl || (videoState?.status === "completed" ? videoState.videoUrl : null);
  const status = videoState?.status || (effectiveVideoUrl ? "completed" : "idle");

  return (
    <div className="bg-[var(--card-bg)] border border-[var(--border)] rounded-2xl overflow-hidden flex-1 min-h-0 relative flex items-center justify-center p-3 select-none shadow-inner">
      {/* 1. COMPLETED: Video Player */}
      {effectiveVideoUrl && status === "completed" ? (
        <div className="relative w-full h-full flex items-center justify-center bg-black/50 rounded-xl overflow-hidden group">
          <video
            key={`${effectiveVideoUrl}-${currentVersion}`}
            src={effectiveVideoUrl}
            controls
            playsInline
            className="w-full h-full object-contain rounded-xl"
            autoPlay
            muted
            loop
          />

          <div className="absolute top-3 left-3 z-30 pointer-events-none">
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/25 backdrop-blur-md text-[10px] font-mono font-medium text-emerald-400">
              <CheckCircle2 className="w-3 h-3" />
              <span>Manim Video MP4</span>
            </div>
          </div>

          {totalVersions > 1 && (
            <div className="absolute bottom-4 left-1/2 -translate-x-1/2 z-30 pointer-events-auto">
              <VersionSwitcher
                currentVersion={currentVersion}
                totalVersions={totalVersions}
                onNext={onNext}
                onPrev={onPrev}
              />
            </div>
          )}
        </div>
      ) : status === "failed" ? (
        /* 2. FAILED: Error Card with Retry Button */
        <div className="flex flex-col items-center gap-3 p-6 text-center max-w-md w-full bg-red-500/5 border border-red-500/15 rounded-2xl animate-in fade-in zoom-in-95 duration-300">
          <div className="w-12 h-12 rounded-2xl bg-red-500/10 border border-red-500/20 flex items-center justify-center text-red-400 shadow-sm">
            <AlertCircle className="w-6 h-6" />
          </div>
          <div className="space-y-1 w-full">
            <h4 className="text-sm font-semibold text-red-300">
              Không thể tạo animation
            </h4>
            <p className="text-xs text-[var(--text-muted)] line-clamp-3 leading-relaxed">
              {videoState?.error || "Hệ thống kết xuất video tạm thời không phản hồi."}
            </p>
          </div>

          {onRetry && (
            <button
              type="button"
              onClick={onRetry}
              className="flex items-center gap-2 px-4 py-2 mt-1 rounded-xl bg-red-500/15 hover:bg-red-500/25 border border-red-500/30 text-xs font-semibold text-red-200 active:scale-95 transition-all shadow-sm"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Thử lại</span>
            </button>
          )}
        </div>
      ) : status === "connecting" || status === "queued" || status === "generating" || status === "rendering" ? (
        /* 3. IN PROGRESS: Connecting / Queued / Generating / Rendering */
        <div className="flex flex-col items-center gap-4 p-6 text-center max-w-sm w-full animate-in fade-in duration-300">
          {/* Animated Glow Container */}
          <div className="relative">
            <div className="absolute inset-0 bg-indigo-500/20 blur-xl rounded-full animate-pulse" />
            <div className="relative w-14 h-14 rounded-2xl bg-gradient-to-tr from-indigo-600/20 to-purple-600/20 border border-indigo-500/30 flex items-center justify-center shadow-lg">
              <Loader2 className="w-7 h-7 text-indigo-400 animate-spin" />
            </div>
          </div>

          {/* Status Badge */}
          <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-[10px] font-mono font-semibold text-indigo-300 uppercase tracking-wider">
            <Sparkles className="w-3 h-3 text-indigo-400" />
            <span>
              {status === "connecting"
                ? "Đang kết nối..."
                : status === "queued"
                ? "Đang xếp hàng..."
                : status === "generating"
                ? "Đang tạo mã chuyển động..."
                : "Đang render video..."}
            </span>
          </div>

          {/* Descriptive text */}
          <div className="space-y-1.5 w-full">
            <h4 className="text-sm font-semibold text-[var(--text-primary)]">
              {videoState?.message || "Đang xử lý animation..."}
            </h4>
            <p className="text-xs text-[var(--text-muted)] leading-relaxed">
              {status === "connecting"
                ? "Đang kết nối tới Manim Animation Engine..."
                : status === "queued"
                ? "Yêu cầu đã được ghi nhận và đang chờ phân bổ GPU..."
                : status === "generating"
                ? "AI đang chuyển đổi bài toán thành kịch bản chuyển động Manim..."
                : "Đang dựng từng khung hình và mã hóa video MP4..."}
            </p>
          </div>

          {/* Real-time Progress Bar */}
          <div className="w-full bg-white/5 rounded-full h-1.5 overflow-hidden border border-white/10 mt-1">
            <div
              className="bg-gradient-to-r from-indigo-500 via-purple-500 to-indigo-400 h-full rounded-full transition-all duration-500 ease-out"
              style={{
                width: `${Math.max(videoState?.progress || 20, 15)}%`,
              }}
            />
          </div>
        </div>
      ) : (
        /* 4. IDLE: Placeholder when no video generation started yet */
        <div className="flex flex-col items-center gap-3 p-8 text-center max-w-sm">
          <div className="w-12 h-12 rounded-2xl bg-indigo-500/10 border border-indigo-500/25 flex items-center justify-center shadow-sm">
            <Film className="w-6 h-6 text-zinc-500" />
          </div>
          <div>
            <h4 className="text-sm font-semibold text-[var(--text-primary)] mb-1">
              Chưa có Animation Video
            </h4>
            <p className="text-xs text-[var(--text-muted)] leading-relaxed">
              Bấm nút &quot;Tạo Animation&quot; để dựng video chuyển động toán học trực quan từng bước.
            </p>
          </div>
          {onRequestRender && (
            <button
              type="button"
              onClick={onRequestRender}
              className="flex items-center gap-2 px-4 py-2 mt-1 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-xs font-semibold text-white active:scale-95 transition-all shadow-md shadow-indigo-600/25"
            >
              <Film className="w-3.5 h-3.5" />
              <span>Tạo Animation</span>
            </button>
          )}
        </div>
      )}
    </div>
  );
}
