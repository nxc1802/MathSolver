import React from "react";
import { Send, Loader2, X, ImageIcon } from "lucide-react";
import type { DraftImage } from "@/lib/chat-attachments";

interface ChatInputProps {
  inputText: string;
  setInputText: (val: string | ((prev: string) => string)) => void;
  /** True when a job is running and the pending queue already has 5 items */
  queueFullBlock: boolean;
  solveLoading: boolean;
  ocrLoading: boolean;
  /** Composer blocked while OCR preview step runs */
  ocrPreviewBlocking?: boolean;
  pendingImages: DraftImage[];
  onRemoveImage: (id: string) => void;
  onAddImageFiles: (files: File[]) => void;
  onSolve: (text?: string) => void;
}

export default function ChatInput({
  inputText,
  setInputText,
  queueFullBlock,
  solveLoading,
  ocrLoading,
  ocrPreviewBlocking = false,
  pendingImages,
  onRemoveImage,
  onAddImageFiles,
  onSolve,
}: ChatInputProps) {
  const canSend =
    !queueFullBlock &&
    !ocrPreviewBlocking &&
    (inputText.trim().length > 0 || pendingImages.length > 0);

  const onPaste = (e: React.ClipboardEvent<HTMLTextAreaElement>) => {
    const items = e.clipboardData?.items;
    const imageFiles: File[] = [];
    if (items?.length) {
      for (let i = 0; i < items.length; i++) {
        const item = items[i];
        if (item.kind === "file" && item.type.startsWith("image/")) {
          const f = item.getAsFile();
          if (f) imageFiles.push(f);
        }
      }
    }
    const plain = e.clipboardData?.getData("text/plain") ?? "";

    if (imageFiles.length > 0) {
      e.preventDefault();
      if (plain.trim()) {
        setInputText((prev) => (prev ? `${prev}\n${plain}` : plain));
      }
      onAddImageFiles(imageFiles);
      return;
    }
    /* text-only: default paste into controlled textarea */
  };

  const onDragOverInput = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const onDropInput = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    const files = Array.from(e.dataTransfer?.files ?? []).filter((f) =>
      f.type.startsWith("image/")
    );
    if (files.length) onAddImageFiles(files);
  };

  const disabled = queueFullBlock || ocrPreviewBlocking;

  return (
    <div className="p-4 border-t border-[var(--border)] bg-[var(--panel-bg)]">
      <div className="max-w-3xl mx-auto space-y-3">
        {pendingImages.length > 0 && (
          <div className="flex flex-wrap gap-2 px-1">
            {pendingImages.map((d) => (
              <div
                key={d.id}
                className="relative group h-16 w-16 rounded-lg border border-white/10 overflow-hidden bg-black/40 shrink-0"
              >
                <img
                  src={d.previewUrl}
                  alt=""
                  className="h-full w-full object-cover"
                />
                <button
                  type="button"
                  title="Gỡ ảnh"
                  onClick={() => onRemoveImage(d.id)}
                  className="absolute inset-0 flex items-center justify-center bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity"
                >
                  <X className="w-5 h-5 text-white" />
                </button>
              </div>
            ))}
            <div className="flex items-center text-[10px] text-zinc-500 font-bold uppercase gap-1 px-1">
              <ImageIcon className="w-3 h-3" />
              {pendingImages.length} ảnh
            </div>
          </div>
        )}

        <div className="flex items-center gap-2 px-1">
          {(ocrLoading || ocrPreviewBlocking) && (
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-indigo-500/10 border border-indigo-500/20 text-[10px] font-bold text-indigo-400 animate-pulse">
              <Loader2 className="w-3 h-3 animate-spin" />
              {ocrPreviewBlocking ? "Đang chuẩn bị OCR..." : "ĐANG QUÉT ẢNH..."}
            </div>
          )}
        </div>

        <div className="flex gap-3 items-stretch">
          <div
            className="relative flex-1 min-w-0"
            onDragOver={onDragOverInput}
            onDrop={onDropInput}
          >
            <textarea
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              placeholder={
                queueFullBlock
                  ? "Hàng đợi đã đủ 5 câu — đợi xử lý xong rồi gửi thêm."
                  : ocrPreviewBlocking
                    ? "Đang xác nhận OCR phía trên..."
                    : "Nhập đề hoặc dán / kéo ảnh đề..."
              }
              disabled={disabled}
              rows={1}
              onPaste={onPaste}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey && !disabled && canSend) {
                  e.preventDefault();
                  onSolve();
                }
              }}
              className={`w-full h-14 min-h-[3.5rem] max-h-14 resize-none overflow-y-auto bg-[var(--input-bg)] border border-[var(--border)] rounded-2xl px-4 py-3 text-sm text-[var(--foreground)] leading-snug focus:outline-none focus:border-indigo-500/50 transition-all ${disabled ? "opacity-50 cursor-not-allowed" : ""}`}
            />
          </div>
          <button
            type="button"
            onClick={() => onSolve()}
            disabled={!canSend || solveLoading}
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
