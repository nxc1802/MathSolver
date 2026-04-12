"use client";

import { motion } from "framer-motion";
import { Search, FileText, Activity, Play } from "lucide-react";
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

interface StatusStepperProps {
  status: string;
}

const steps = [
  { id: "ocr", label: "OCR", icon: Search },
  { id: "parser", label: "Parser", icon: FileText },
  { id: "solver", label: "Solver", icon: Activity },
  { id: "render", label: "Render", icon: Play },
];

export default function StatusStepper({ status }: StatusStepperProps) {
  const getStatusIndex = (s: string) => {
    if (s.includes("ocr")) return 0;
    if (s.includes("parsing")) return 1;
    if (s.includes("solving")) return 2;
    if (s.includes("rendering") || s === "ready") return 3;
    return -1;
  };

  const currentIndex = getStatusIndex(status);

  return (
    <div className="w-full max-w-xl mx-auto mt-8 flex items-center justify-between relative px-2">
      {/* Background Line */}
      <div className="absolute top-1/2 left-0 right-0 h-0.5 bg-white/5 -translate-y-1/2 mx-10" />
      
      {/* Progress Line */}
      <motion.div 
        initial={{ width: "0%" }}
        animate={{ width: `${(currentIndex / (steps.length - 1)) * 100}%` }}
        className="absolute top-1/2 left-0 h-0.5 bg-indigo-500 -translate-y-1/2 ml-10 transition-all duration-500"
      />

      {steps.map((step, idx) => {
        const isActive = idx <= currentIndex;
        const isCurrent = idx === currentIndex;
        const Icon = step.icon;

        return (
          <div key={step.id} className="relative z-10 flex flex-col items-center gap-2">
            <motion.div
              animate={{
                scale: isCurrent ? [1, 1.1, 1] : 1,
                backgroundColor: isActive ? "rgb(99 102 241)" : "rgb(24 24 27)",
                borderColor: isActive ? "rgb(99 102 241)" : "rgba(255, 255, 255, 0.1)",
              }}
              transition={{ repeat: isCurrent ? Infinity : 0, duration: 2 }}
              className={cn(
                "w-10 h-10 rounded-full border-2 flex items-center justify-center transition-colors",
                isActive ? "text-white" : "text-zinc-600"
              )}
            >
              <Icon className="w-5 h-5" />
            </motion.div>
            <span className={cn(
              "text-[10px] font-bold uppercase tracking-wider",
              isActive ? "text-indigo-400" : "text-zinc-600"
            )}>
              {step.label}
            </span>
          </div>
        );
      })}
    </div>
  );
}
