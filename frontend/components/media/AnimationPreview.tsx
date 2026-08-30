"use client";

import React from "react";
import { Film, Loader2 } from "lucide-react";
import VersionSwitcher from "../geometry/VersionSwitcher";

interface AnimationPreviewProps {
  videoUrl?: string;
  loading?: boolean;
  currentVersion?: number;
  totalVersions?: number;
  onNext?: () => void;
  onPrev?: () => void;
}

export default function AnimationPreview({
  videoUrl,
  loading,
  currentVersion = 1,
  totalVersions = 1,
  onNext = () => {},
  onPrev = () => {},
}: AnimationPreviewProps) {
  return (
    <div className="bg-[var(--card-bg)] border border-[var(--border)] rounded-2xl overflow-hidden flex-1 min-h-0 relative flex items-center justify-center p-2 select-none shadow-inner">
      {videoUrl ? (
        <div className="relative w-full h-full flex items-center justify-center bg-black/50 rounded-xl overflow-hidden">
          <video
            key={`${videoUrl}-${currentVersion}`}
            src={videoUrl}
            controls
            playsInline
            className="w-full h-full object-contain rounded-xl"
            autoPlay
            muted
            loop
          />

          <div className="absolute bottom-4 left-1/2 -translate-x-1/2 z-30 pointer-events-auto">
            <VersionSwitcher
              currentVersion={currentVersion}
              totalVersions={totalVersions}
              onNext={onNext}
              onPrev={onPrev}
            />
          </div>
        </div>
      ) : (
        <div className="flex flex-col items-center gap-3 p-8 text-center max-w-sm">
          <div className="w-12 h-12 rounded-2xl bg-indigo-500/10 border border-indigo-500/25 flex items-center justify-center shadow-sm">
            {loading ? (
              <Loader2 className="w-6 h-6 text-indigo-400 animate-spin" />
            ) : (
              <Film className="w-6 h-6 text-zinc-500" />
            )}
          </div>
          <div>
            <h4 className="text-sm font-semibold text-[var(--text-primary)] mb-1">
              {loading ? "Đang render video Manim..." : "Chưa có Animation Video"}
            </h4>
            <p className="text-xs text-[var(--text-muted)] leading-relaxed">
              {loading
                ? "Hệ thống Manim Engine đang biên dịch mã hình học và dựng video chuyển động từng bước..."
                : "Bấm nút \"Tạo Animation\" để dựng video chuyển động toán học trực quan."}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
