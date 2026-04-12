import React from "react";
import { Sparkles, Hexagon, Box, Circle } from "lucide-react";
import { motion } from "framer-motion";

export default function HeroWelcome({ onSuggestionClick }: { onSuggestionClick?: (text: string) => void }) {
  return (
    <div className="h-full flex flex-col items-center justify-center text-center px-4">
      <motion.div 
        initial={{ scale: 0.8, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        className="w-16 h-16 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 flex flex-col items-center justify-center mb-6"
      >
        <Sparkles className="w-8 h-8 text-indigo-400" />
      </motion.div>
      
      <motion.h1 
        initial={{ y: 10, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ delay: 0.1 }}
        className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-indigo-400 to-purple-400 mb-2"
      >
        Bắt đầu phiên giải toán mới
      </motion.h1>
      
      <motion.p 
        initial={{ y: 10, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ delay: 0.2 }}
        className="text-zinc-400 max-w-sm mb-10 text-sm"
      >
        Hãy nhập đề bài, kéo thả ảnh đề, hoặc chọn một chủ đề gợi ý bên dưới để thử nghiệm hệ thống.
      </motion.p>
      
      <motion.div 
        initial={{ y: 20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ delay: 0.3 }}
        className="grid grid-cols-1 sm:grid-cols-3 gap-4 max-w-2xl w-full"
      >
        <div 
          onClick={() => onSuggestionClick?.("Cho hình chữ nhật ABCD có AB=5, AD=10. Tính diện tích.")}
          className="group p-5 rounded-2xl bg-zinc-900/50 border border-white/5 hover:border-indigo-500/30 hover:bg-zinc-800/50 transition-all cursor-pointer text-left"
        >
          <Circle className="w-6 h-6 text-indigo-400 mb-3 group-hover:scale-110 transition-transform" />
          <h3 className="font-semibold text-white mb-1">Hình học 2D</h3>
          <p className="text-xs text-zinc-500 leading-relaxed">Đường tròn nội/ngoại tiếp, hệ phương trình, tính chất tam giác.</p>
        </div>
        
        <div 
          onClick={() => onSuggestionClick?.("Cho hình chóp S.ABCD có đáy là hình vuông cạnh 6, chiều cao bằng 8.")}
          className="group p-5 rounded-2xl bg-zinc-900/50 border border-white/5 hover:border-purple-500/30 hover:bg-zinc-800/50 transition-all cursor-pointer text-left"
        >
          <Box className="w-6 h-6 text-purple-400 mb-3 group-hover:scale-110 transition-transform" />
          <h3 className="font-semibold text-white mb-1">Hình học 3D</h3>
          <p className="text-xs text-zinc-500 leading-relaxed">Hình chóp, tứ diện, quan hệ vuông góc và khoảng cách.</p>
        </div>

        <div 
          className="group p-5 rounded-2xl bg-zinc-900/50 border border-white/5 hover:border-amber-500/30 hover:bg-zinc-800/50 transition-all cursor-pointer text-left"
        >
          <Hexagon className="w-6 h-6 text-amber-400 mb-3 group-hover:scale-110 transition-transform" />
          <h3 className="font-semibold text-white mb-1">Xử lý ảnh OCR</h3>
          <p className="text-xs text-zinc-500 leading-relaxed">Dán hoặc tải ảnh chụp đề bài lên để tự động giải quyết.</p>
        </div>
      </motion.div>
    </div>
  );
}
