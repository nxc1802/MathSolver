"use client";

import { motion } from "framer-motion";
import { PlayCircle, Loader2 } from "lucide-react";

interface AnimationPreviewProps {
  videoUrl?: string;
  imageUrl?: string;
  loading?: boolean;
}

export default function AnimationPreview({ videoUrl, imageUrl, loading }: AnimationPreviewProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-zinc-950 border border-white/10 rounded-3xl overflow-hidden aspect-video relative group flex items-center justify-center"
    >
      {videoUrl ? (
        <video 
          key={videoUrl}
          src={videoUrl}
          controls
          className="w-full h-full object-contain"
          autoPlay
          muted
          loop
        />
      ) : imageUrl ? (
        <div className="relative w-full h-full flex flex-col">
          <img 
            src={imageUrl} 
            alt="Geometry Result" 
            className="w-full h-full object-contain p-4"
          />
          <div className="absolute top-4 right-4 bg-black/60 backdrop-blur-md px-3 py-1 rounded-full border border-white/10 flex items-center gap-2">
            <Loader2 className="w-3 h-3 text-indigo-400 animate-spin" />
            <span className="text-[10px] text-zinc-300 font-bold uppercase tracking-wider">Rendering MP4...</span>
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
                ? "Hệ thống đang giải và vẽ mô phỏng bài toán." 
                : "Kết quả hình ảnh và video sẽ xuất hiện tại đây."}
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
