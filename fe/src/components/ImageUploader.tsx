'use client';

import React, { useState, useCallback, useRef } from 'react';

interface ImageUploaderProps {
  onImageSelect: (file: File) => void;
  onTextSubmit: (text: string) => void;
  isLoading: boolean;
}

export default function ImageUploader({ onImageSelect, onTextSubmit, isLoading }: ImageUploaderProps) {
  const [dragOver, setDragOver] = useState(false);
  const [preview, setPreview] = useState<string | null>(null);
  const [textInput, setTextInput] = useState('');
  const [mode, setMode] = useState<'image' | 'text'>('image');
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    
    const file = e.dataTransfer.files[0];
    if (file && file.type.startsWith('image/')) {
      handleFile(file);
    }
  }, []);

  const handleFile = (file: File) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      setPreview(e.target?.result as string);
    };
    reader.readAsDataURL(file);
    onImageSelect(file);
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      handleFile(file);
    }
  };

  const handleTextSubmit = () => {
    if (textInput.trim()) {
      onTextSubmit(textInput.trim());
    }
  };

  const clearPreview = () => {
    setPreview(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <div className="w-full max-w-2xl mx-auto">
      {/* Mode Toggle */}
      <div className="flex gap-2 mb-6 justify-center">
        <button
          onClick={() => setMode('image')}
          className={`px-6 py-2 rounded-lg font-medium transition-all ${
            mode === 'image'
              ? 'bg-primary text-white'
              : 'bg-surface border border-border text-foreground hover:border-primary'
          }`}
        >
          📷 Upload Ảnh
        </button>
        <button
          onClick={() => setMode('text')}
          className={`px-6 py-2 rounded-lg font-medium transition-all ${
            mode === 'text'
              ? 'bg-primary text-white'
              : 'bg-surface border border-border text-foreground hover:border-primary'
          }`}
        >
          ✏️ Nhập Đề
        </button>
      </div>

      {mode === 'image' ? (
        <>
          {!preview ? (
            <div
              className={`upload-zone ${dragOver ? 'dragover' : ''}`}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                onChange={handleFileSelect}
                className="hidden"
              />
              <div className="flex flex-col items-center gap-4">
                <div className="w-20 h-20 rounded-full bg-surface-light flex items-center justify-center">
                  <svg className="w-10 h-10 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                  </svg>
                </div>
                <div>
                  <p className="text-lg font-medium">Kéo thả hình ảnh vào đây</p>
                  <p className="text-sm text-gray-400 mt-1">hoặc click để chọn file</p>
                </div>
                <p className="text-xs text-gray-500">Hỗ trợ: PNG, JPG, JPEG (Max 10MB)</p>
              </div>
            </div>
          ) : (
            <div className="glass-card p-6">
              <div className="relative">
                <img
                  src={preview}
                  alt="Preview"
                  className="w-full max-h-80 object-contain rounded-lg"
                />
                <button
                  onClick={clearPreview}
                  className="absolute top-2 right-2 w-8 h-8 bg-red-500/80 hover:bg-red-500 rounded-full flex items-center justify-center transition-colors"
                >
                  ✕
                </button>
              </div>
              <div className="mt-4 flex justify-center">
                <button
                  onClick={() => onImageSelect(fileInputRef.current?.files?.[0] as File)}
                  disabled={isLoading}
                  className="btn-primary flex items-center gap-2"
                >
                  {isLoading ? (
                    <>
                      <svg className="w-5 h-5 spinner" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      Đang xử lý...
                    </>
                  ) : (
                    <>
                      🚀 Giải bài toán
                    </>
                  )}
                </button>
              </div>
            </div>
          )}
        </>
      ) : (
        <div className="glass-card p-6">
          <textarea
            value={textInput}
            onChange={(e) => setTextInput(e.target.value)}
            placeholder="Nhập đề bài toán...&#10;&#10;Ví dụ: Cho tam giác ABC có AB = 5, AC = 7, góc A = 60°. Tính độ dài BC và diện tích tam giác ABC."
            className="w-full h-40 bg-surface border border-border rounded-lg p-4 text-foreground placeholder-gray-500 resize-none focus:outline-none focus:border-primary transition-colors"
          />
          <div className="mt-4 flex justify-center">
            <button
              onClick={handleTextSubmit}
              disabled={isLoading || !textInput.trim()}
              className="btn-primary flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? (
                <>
                  <svg className="w-5 h-5 spinner" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Đang xử lý...
                </>
              ) : (
                <>
                  🚀 Giải bài toán
                </>
              )}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
