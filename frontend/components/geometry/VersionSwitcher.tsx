"use client";

import { ChevronLeft, ChevronRight, History } from "lucide-react";

interface VersionSwitcherProps {
  currentVersion: number;
  totalVersions: number;
  onNext: () => void;
  onPrev: () => void;
}

export default function VersionSwitcher({ currentVersion, totalVersions, onNext, onPrev }: VersionSwitcherProps) {
  if (totalVersions <= 1) return null;

  return (
    <div className="flex items-center gap-3 px-3 py-1.5 bg-zinc-900/80 border border-white/10 rounded-full backdrop-blur-md shadow-lg">
      <div className="flex items-center gap-2 pr-2 border-r border-white/10">
        <History className="w-3.5 h-3.5 text-indigo-400" />
        <span className="text-[10px] font-bold text-zinc-400 uppercase tracking-widest">
          Version {currentVersion} / {totalVersions}
        </span>
      </div>
      
      <div className="flex items-center gap-1">
        <button
          onClick={onPrev}
          disabled={currentVersion <= 1}
          data-testid="version-prev"
          aria-label="Previous version"
          className="p-2.5 hover:bg-white/10 active:scale-95 rounded-md transition-all disabled:opacity-20 disabled:cursor-not-allowed group"
        >
          <ChevronLeft className="w-4 h-4 text-zinc-400 group-hover:text-white" />
        </button>
        <button
          onClick={onNext}
          disabled={currentVersion >= totalVersions}
          data-testid="version-next"
          aria-label="Next version"
          className="p-2.5 hover:bg-white/10 active:scale-95 rounded-md transition-all disabled:opacity-20 disabled:cursor-not-allowed group"
        >
          <ChevronRight className="w-4 h-4 text-zinc-400 group-hover:text-white" />
        </button>
      </div>
    </div>
  );
}
