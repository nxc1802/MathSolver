"use client";

import { motion } from "framer-motion";
import { PlayCircle, Loader2 } from "lucide-react";
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
  onPrev = () => {} 
}: AnimationPreviewProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-zinc-950 border border-white/10 rounded-3xl overflow-hidden aspect-video relative group flex items-center justify-center p-2"
    >
      {videoUrl ? (
        <div className="relative w-full h-full">
          <video 
            key={`${videoUrl}-${currentVersion}`}
            src={videoUrl}
            controls
            className="w-full h-full object-contain rounded-2xl"
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
        <div className="flex flex-col items-center gap-4 p-12 text-center">
          <div className="w-16 h-16 rounded-3xl bg-white/5 border border-white/10 flex items-center justify-center shadow-2xl">
            {loading ? (
              <Loader2 className="w-8 h-8 text-indigo-500 animate-spin" />
            ) : (
              <PlayCircle className="w-8 h-8 text-zinc-600" />
            )}
          </div>
          <div>
            <h4 className="text-white font-semibold text-lg mb-1">
              {loading ? "Đang dựng animation..." : "Chưa có animation"}
            </h4>
            <p className="text-zinc-500 text-sm max-w-[280px]">
              {loading 
                ? "Manim Engine đang mô tả hóa bài toán của bạn thành video từng bước." 
                : "Animation sẽ xuất hiện tại đây sau khi GPU xử lý xong."}
            </p>
          </div>
        </div>
      )}

      {/* Glow Effect */}
      <div className="absolute -bottom-24 -left-24 w-64 h-64 bg-indigo-500/10 blur-[120px] rounded-full pointer-events-none" />
      <div className="absolute -top-24 -right-24 w-64 h-64 bg-purple-500/10 blur-[120px] rounded-full pointer-events-none" />
    </motion.div>
  );
}
