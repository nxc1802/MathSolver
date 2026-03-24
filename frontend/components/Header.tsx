"use client";

import { motion } from "framer-motion";
import { Calculator } from "lucide-react";

export default function Header() {
  return (
    <header className="fixed top-0 left-0 right-0 z-50 bg-black/10 backdrop-blur-md border-b border-white/10">
      <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
        <motion.div 
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          className="flex items-center gap-2"
        >
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shadow-lg shadow-indigo-500/20">
            <Calculator className="w-5 h-5 text-white" />
          </div>
          <span className="text-xl font-bold tracking-tight text-white">
            MATHSOLVER <span className="text-indigo-400 font-light">v3.1</span>
          </span>
        </motion.div>
        
        <nav className="hidden md:flex items-center gap-8">
          <a href="#" className="text-sm font-medium text-zinc-400 hover:text-white transition-colors">Documentation</a>
          <a href="#" className="text-sm font-medium text-zinc-400 hover:text-white transition-colors">Gallery</a>
          <div className="h-4 w-px bg-white/10" />
          <button className="text-sm font-medium px-4 py-2 rounded-full bg-white text-black hover:bg-zinc-200 transition-colors shadow-xl shadow-white/5">
            Get Pro
          </button>
        </nav>
      </div>
    </header>
  );
}
