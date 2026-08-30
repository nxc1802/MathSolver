"use client";

import React from "react";
import { ChevronLeft, ChevronRight, History } from "lucide-react";

interface VersionSwitcherProps {
  currentVersion: number;
  totalVersions: number;
  onNext: () => void;
  onPrev: () => void;
}

export default function VersionSwitcher({
  currentVersion,
  totalVersions,
  onNext,
  onPrev,
}: VersionSwitcherProps) {
  if (totalVersions <= 1) return null;

  return (
    <div className="flex items-center gap-2 px-3 py-1 bg-[var(--panel-glass)] border border-[var(--border)] rounded-full backdrop-blur-md shadow-md select-none">
      <div className="flex items-center gap-1.5 pr-2 border-r border-[var(--border)]">
        <History className="w-3.5 h-3.5 text-indigo-400" />
        <span className="text-[10px] font-mono font-semibold text-[var(--text-secondary)] uppercase tracking-wider tabular-nums">
          Snapshot {currentVersion}/{totalVersions}
        </span>
      </div>

      <div className="flex items-center gap-0.5">
        <button
          type="button"
          onClick={onPrev}
          disabled={currentVersion <= 1}
          data-testid="version-prev"
          aria-label="Previous version"
          className="p-1 hover:bg-white/10 active:scale-95 rounded-md text-[var(--text-secondary)] hover:text-white transition-all disabled:opacity-20 disabled:cursor-not-allowed"
        >
          <ChevronLeft className="w-3.5 h-3.5" />
        </button>
        <button
          type="button"
          onClick={onNext}
          disabled={currentVersion >= totalVersions}
          data-testid="version-next"
          aria-label="Next version"
          className="p-1 hover:bg-white/10 active:scale-95 rounded-md text-[var(--text-secondary)] hover:text-white transition-all disabled:opacity-20 disabled:cursor-not-allowed"
        >
          <ChevronRight className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  );
}
