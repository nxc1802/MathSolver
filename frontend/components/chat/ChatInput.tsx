import React from "react";
import { Send, Loader2, Film } from "lucide-react";

interface ChatInputProps {
  inputText: string;
  setInputText: (val: string | ((prev: string) => string)) => void;
  requestVideo: boolean;
  setRequestVideo: (val: boolean) => void;
  isLimitReached: boolean;
  solveLoading: boolean;
  ocrLoading: boolean;
  onSolve: (text?: string) => void;
  onRunOcr: (file: File) => void;
}

export default function ChatInput({
  inputText,
  setInputText,
  requestVideo,
  setRequestVideo,
  isLimitReached,
  solveLoading,
  ocrLoading,
  onSolve,
  onRunOcr
}: ChatInputProps) {

  const onPasteImages = (e: React.ClipboardEvent) => {
    const items = e.clipboardData?.items;
    if (!items?.length) return;
    for (let i = 0; i < items.length; i++) {
      const item = items[i];
      if (item.kind === "file" && item.type.startsWith("image/")) {
        e.preventDefault();
        const file = item.getAsFile();
        if (file) onRunOcr(file);
        return;
      }
    }
  };

  const onDragOverInput = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const onDropInput = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    const file = e.dataTransfer?.files?.[0];
    if (file?.type.startsWith("image/")) onRunOcr(file);
  };

  return (
    <div className="p-4 border-t border-[var(--border)] bg-[var(--panel-bg)]">
      <div className="max-w-3xl mx-auto space-y-3">
        <div className="flex items-center gap-2 px-1">
          <button
            type="button"
            onClick={() => setRequestVideo(!requestVideo)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border transition-all text-xs font-bold ${
              requestVideo
                ? "bg-indigo-500/20 border-indigo-500/40 text-indigo-300"
                : "bg-white/5 border-[rgba(255,255,255,0.05)] text-zinc-500 hover:text-white"
            }`}
          >
            <Film className="w-3.5 h-3.5" />
            MANIM VIDEO
          </button>
          {ocrLoading && (
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-indigo-500/10 border border-indigo-500/20 text-[10px] font-bold text-indigo-400 animate-pulse">
              <Loader2 className="w-3 h-3 animate-spin" />
              ĐANG QUÉT ẢNH...
            </div>
          )}
        </div>

        <div className="flex gap-3 items-stretch">
          <div className="relative flex-1 min-w-0" onDragOver={onDragOverInput} onDrop={onDropInput}>
            <textarea
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              placeholder={isLimitReached ? "Bạn đã đạt giới hạn 5 câu hỏi cho phiên này." : "Nhập đề hoặc dán / kéo ảnh đề..."}
              disabled={isLimitReached}
              rows={1}
              onPaste={onPasteImages}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey && !isLimitReached) {
                  e.preventDefault();
                  onSolve();
                }
              }}
              className={`w-full h-14 min-h-[3.5rem] max-h-14 resize-none overflow-y-auto bg-[var(--input-bg)] border border-[var(--border)] rounded-2xl px-4 py-3 text-sm text-[var(--foreground)] leading-snug focus:outline-none focus:border-indigo-500/50 transition-all ${isLimitReached ? "opacity-50 cursor-not-allowed" : ""}`}
            />
          </div>
          <button
            type="button"
            onClick={() => onSolve()}
            disabled={isLimitReached || !inputText.trim()}
            className="h-14 w-14 shrink-0 rounded-2xl bg-indigo-600 text-white flex items-center justify-center hover:bg-indigo-500 transition-all disabled:opacity-30 shadow-lg shadow-indigo-500/20"
          >
            {solveLoading ? (
              <Loader2 className="w-6 h-6 animate-spin" />
            ) : (
              <Send className="w-6 h-6" />
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
