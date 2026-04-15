"use client";

import React, { useState } from "react";
import { Bot, Check, Pencil, RotateCcw, X } from "lucide-react";

type OcrConfirmCardProps = {
  previewUrls: string[];
  combinedText: string;
  onChangeCombined: (text: string) => void;
  ocrLoading?: boolean;
  error?: string | null;
  onConfirm: () => void;
  onCancel: () => void;
  onRetryOcr: () => void;
};

export default function OcrConfirmCard({
  previewUrls,
  combinedText,
  onChangeCombined,
  ocrLoading,
  error,
  onConfirm,
  onCancel,
  onRetryOcr,
}: OcrConfirmCardProps) {
  const [editing, setEditing] = useState(false);

  return (
    <div className="rounded-2xl border border-indigo-500/25 bg-indigo-500/5 p-4 space-y-3 max-w-3xl mx-auto">
      <div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-widest text-indigo-400">
        <Bot className="w-4 h-4" />
        Xác nhận nội dung (OCR + tin nhắn)
      </div>

      {previewUrls.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {previewUrls.map((url) => (
            <img
              key={url}
              src={url}
              alt="Đính kèm"
              className="h-24 w-auto max-w-full rounded-lg border border-white/10 object-contain bg-black/40"
            />
          ))}
        </div>
      )}

      {ocrLoading ? (
        <p className="text-xs text-zinc-400 animate-pulse">Đang trích xuất chữ từ ảnh...</p>
      ) : error ? (
        <p className="text-xs text-red-400">{error}</p>
      ) : null}

      <div className="space-y-2">
        {editing ? (
          <textarea
            value={combinedText}
            onChange={(e) => onChangeCombined(e.target.value)}
            rows={6}
            className="w-full rounded-xl border border-white/10 bg-[var(--input-bg)] px-3 py-2 text-sm text-[var(--foreground)] focus:outline-none focus:border-indigo-500/50"
          />
        ) : (
          <pre className="whitespace-pre-wrap rounded-xl border border-white/10 bg-black/30 px-3 py-2 text-sm text-zinc-200 max-h-48 overflow-y-auto">
            {combinedText || "(Trống)"}
          </pre>
        )}
      </div>

      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          onClick={() => setEditing((e) => !e)}
          disabled={ocrLoading}
          className="inline-flex items-center gap-1.5 rounded-xl border border-white/15 px-3 py-2 text-xs font-bold text-zinc-200 hover:bg-white/5 disabled:opacity-40"
        >
          <Pencil className="w-3.5 h-3.5" />
          {editing ? "Xem trước" : "Chỉnh sửa"}
        </button>
        <button
          type="button"
          onClick={onRetryOcr}
          disabled={ocrLoading}
          className="inline-flex items-center gap-1.5 rounded-xl border border-white/15 px-3 py-2 text-xs font-bold text-zinc-200 hover:bg-white/5 disabled:opacity-40"
        >
          <RotateCcw className="w-3.5 h-3.5" />
          Thử lại OCR
        </button>
        <button
          type="button"
          onClick={onConfirm}
          disabled={ocrLoading || !combinedText.trim()}
          className="inline-flex items-center gap-1.5 rounded-xl bg-indigo-600 px-4 py-2 text-xs font-bold text-white hover:bg-indigo-500 disabled:opacity-40"
        >
          <Check className="w-3.5 h-3.5" />
          Xác nhận và gửi giải
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="inline-flex items-center gap-1.5 rounded-xl border border-red-500/30 px-3 py-2 text-xs font-bold text-red-300 hover:bg-red-500/10"
        >
          <X className="w-3.5 h-3.5" />
          Hủy
        </button>
      </div>
    </div>
  );
}
