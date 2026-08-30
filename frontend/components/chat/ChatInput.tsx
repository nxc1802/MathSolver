import React, { useRef } from "react";
import { Send, Loader2, X, ImagePlus } from "lucide-react";
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
  const fileInputRef = useRef<HTMLInputElement>(null);

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

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files ?? []).filter((f) =>
      f.type.startsWith("image/")
    );
    if (files.length) onAddImageFiles(files);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const disabled = queueFullBlock || ocrPreviewBlocking;

  return (
    <div className="p-3 md:p-4 border-t border-[var(--border)] bg-[var(--panel-bg)] backdrop-blur-md select-none">
      <div className="max-w-3xl mx-auto space-y-2.5">
        {/* Pending image thumbnails row */}
        {pendingImages.length > 0 && (
          <div className="flex items-center flex-wrap gap-2 px-1">
            {pendingImages.map((d) => (
              <div
                key={d.id}
                className="relative group h-14 w-14 rounded-xl border border-white/15 overflow-hidden bg-black/40 shrink-0 shadow-sm"
              >
                {/* eslint-disable-next-line @next/next/no-img-element */}
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
                  <X className="w-4 h-4 text-white" />
                </button>
              </div>
            ))}
            <span className="text-[10px] font-mono text-[var(--text-muted)]">
              {pendingImages.length} ảnh đính kèm
            </span>
          </div>
        )}

        {/* OCR Status banner */}
        {(ocrLoading || ocrPreviewBlocking) && (
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-[10px] font-mono font-semibold text-indigo-400">
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
            <span>{ocrPreviewBlocking ? "Đang chuẩn bị quét OCR..." : "Đang trích xuất chữ từ ảnh đề..."}</span>
          </div>
        )}

        {/* Input Controls Box */}
        <div
          onDragOver={onDragOverInput}
          onDrop={onDropInput}
          className={`flex items-end gap-2 p-2 rounded-2xl bg-[var(--input-bg)] border transition-all ${
            disabled
              ? "opacity-60 border-[var(--border)]"
              : "border-[var(--border)] hover:border-white/20 focus-within:border-indigo-500/50 focus-within:ring-2 focus-within:ring-indigo-500/10 shadow-sm"
          }`}
        >
          {/* Upload button */}
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileChange}
            accept="image/*"
            multiple
            className="hidden"
          />
          <button
            type="button"
            title="Đính kèm ảnh đề bài"
            disabled={disabled}
            onClick={() => fileInputRef.current?.click()}
            className="p-2.5 text-[var(--text-muted)] hover:text-indigo-400 hover:bg-white/5 rounded-xl active:scale-95 transition-all disabled:opacity-40 shrink-0 mb-0.5"
          >
            <ImagePlus className="w-4 h-4" />
          </button>

          {/* Main Textarea */}
          <textarea
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            placeholder={
              queueFullBlock
                ? "Hàng đợi đã đầy 5 câu — đợi xử lý xong để gửi tiếp..."
                : ocrPreviewBlocking
                ? "Đang xác nhận OCR phía trên..."
                : "Nhập đề toán, kéo thả ảnh hoặc dán (Ctrl+V)..."
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
            className="flex-1 min-h-[44px] max-h-32 resize-none bg-transparent py-2.5 px-1 text-xs md:text-sm text-[var(--text-primary)] placeholder-[var(--text-muted)] leading-relaxed focus:outline-none scrollbar-thin"
          />

          {/* Send Action */}
          <div className="flex items-center gap-1 shrink-0 mb-0.5">
            <button
              type="button"
              onClick={() => onSolve()}
              disabled={!canSend || solveLoading}
              title={canSend ? "Giải toán (Enter)" : "Nhập câu hỏi hoặc dán ảnh"}
              className="h-9 w-9 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white flex items-center justify-center shadow-md shadow-indigo-600/25 active:scale-95 transition-all disabled:opacity-30 disabled:hover:bg-indigo-600"
            >
              {solveLoading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Send className="w-4 h-4" />
              )}
            </button>
          </div>
        </div>

        {/* Keyboard hints footer */}
        <div className="flex items-center justify-between px-2 text-[10px] font-mono text-[var(--text-muted)] opacity-70">
          <div className="flex items-center gap-3">
            <span className="flex items-center gap-1">
              <kbd className="px-1 py-0.5 rounded bg-white/5 border border-white/10 text-[9px]">Enter</kbd> gửi
            </span>
            <span className="flex items-center gap-1">
              <kbd className="px-1 py-0.5 rounded bg-white/5 border border-white/10 text-[9px]">Shift+Enter</kbd> xuống dòng
            </span>
          </div>
          <span>Dán ảnh trực tiếp từ Clipboard</span>
        </div>
      </div>
    </div>
  );
}
