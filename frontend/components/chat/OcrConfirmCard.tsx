"use client";

import React, { useState } from "react";
import { ScanLine, Check, Pencil, RotateCcw, X, Eye } from "lucide-react";

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
    <div className="rounded-2xl border border-indigo-500/30 bg-[var(--card-bg)] p-4 space-y-3.5 max-w-3xl mx-auto shadow-lg shadow-black/20 text-left">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-[10px] font-mono font-semibold uppercase tracking-wider text-indigo-400">
          <ScanLine className="w-4 h-4" />
          <span>Xác nhận nội dung quét OCR</span>
        </div>
        {ocrLoading && (
          <span className="text-[10px] font-mono text-indigo-400 animate-pulse">
            Đang xử lý ảnh...
          </span>
        )}
      </div>

      {previewUrls.length > 0 && (
        <div className="flex flex-wrap gap-2.5">
          {previewUrls.map((url, idx) => (
            <div
              key={idx}
              className="h-20 max-w-xs rounded-xl border border-white/10 overflow-hidden bg-black/40 p-1 flex items-center justify-center"
            >
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={url}
                alt="Đính kèm"
                className="h-full w-auto object-contain rounded-lg"
              />
            </div>
          ))}
        </div>
      )}

      {error && (
        <p className="text-xs text-red-400 bg-red-500/10 border border-red-500/20 p-2.5 rounded-xl">
          {error}
        </p>
      )}

      <div className="space-y-1.5">
        {editing ? (
          <textarea
            value={combinedText}
            onChange={(e) => onChangeCombined(e.target.value)}
            rows={5}
            placeholder="Nội dung đề bài sau khi quét..."
            className="w-full rounded-xl border border-indigo-500/30 bg-[var(--input-bg)] px-3.5 py-2.5 text-xs font-mono text-[var(--text-primary)] focus:outline-none focus:border-indigo-400 leading-relaxed"
          />
        ) : (
          <pre className="whitespace-pre-wrap rounded-xl border border-white/10 bg-black/30 px-3.5 py-2.5 text-xs font-mono text-zinc-200 max-h-44 overflow-y-auto leading-relaxed">
            {combinedText || "(Chưa có nội dung)"}
          </pre>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-2 pt-1">
        <button
          type="button"
          onClick={() => setEditing((e) => !e)}
          disabled={ocrLoading}
          className="inline-flex items-center gap-1.5 rounded-xl border border-white/10 bg-white/[0.03] hover:bg-white/[0.08] px-3 py-2 text-xs font-medium text-zinc-300 active:scale-95 transition-all disabled:opacity-40"
        >
          {editing ? <Eye className="w-3.5 h-3.5" /> : <Pencil className="w-3.5 h-3.5" />}
          {editing ? "Xem trước" : "Chỉnh sửa"}
        </button>

        <button
          type="button"
          onClick={onRetryOcr}
          disabled={ocrLoading}
          className="inline-flex items-center gap-1.5 rounded-xl border border-white/10 bg-white/[0.03] hover:bg-white/[0.08] px-3 py-2 text-xs font-medium text-zinc-300 active:scale-95 transition-all disabled:opacity-40"
        >
          <RotateCcw className="w-3.5 h-3.5" />
          Quét lại
        </button>

        <button
          type="button"
          onClick={onConfirm}
          disabled={ocrLoading || !combinedText.trim()}
          className="inline-flex items-center gap-1.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 px-4 py-2 text-xs font-semibold text-white shadow-md shadow-indigo-600/20 active:scale-95 transition-all disabled:opacity-40"
        >
          <Check className="w-3.5 h-3.5" />
          Xác nhận & Giải
        </button>

        <button
          type="button"
          onClick={onCancel}
          className="inline-flex items-center gap-1.5 rounded-xl border border-red-500/20 hover:bg-red-500/10 px-3 py-2 text-xs font-medium text-red-300 active:scale-95 transition-all ml-auto"
        >
          <X className="w-3.5 h-3.5" />
          Hủy
        </button>
      </div>
    </div>
  );
}
