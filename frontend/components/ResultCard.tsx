"use client";

import { motion } from "framer-motion";
import { Copy, Check } from "lucide-react";
import { useState } from "react";

interface ResultCardProps {
  title: string;
  content: string;
  delay?: number;
}

export default function ResultCard({ title, content, delay = 0 }: ResultCardProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ delay }}
      className="bg-zinc-900/30 border border-white/5 rounded-2xl p-6 relative group overflow-hidden"
    >
      <div className="absolute inset-0 bg-gradient-to-br from-indigo-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
      
      <div className="flex items-center justify-between mb-4 relative z-10">
        <h3 className="text-sm font-bold text-zinc-400 uppercase tracking-widest">{title}</h3>
        <button 
          onClick={handleCopy}
          className="p-2 rounded-lg bg-white/5 text-zinc-500 hover:text-white hover:bg-white/10 transition-all"
        >
          {copied ? <Check className="w-4 h-4 text-green-400" /> : <Copy className="w-4 h-4" />}
        </button>
      </div>

      <div className="bg-black/40 rounded-xl p-4 border border-white/5 relative z-10 overflow-x-auto">
        <code className="text-sm text-zinc-300 font-mono whitespace-pre-wrap leading-relaxed">
          {content}
        </code>
      </div>
    </motion.div>
  );
}
