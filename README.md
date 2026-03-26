---
title: MathSolver v3.1
emoji: 📐
colorFrom: indigo
colorTo: purple
sdk: docker
pinned: false
---

# Visual Math Solver v3.1

Hệ thống giải toán hình học và trực quan hóa bằng AI (Multi-Agent).

## Cấu trúc thư mục
- `/backend`: FastAPI, AI Agents, Geometry Solver, Manim Renderer.
- `/frontend`: Next.js web application.
- `/docs`: Tài liệu chi tiết dự án.

## Hướng dẫn cài đặt & Chạy Locally

### 1. Cài đặt môi trường (macOS)
Dự án yêu cầu các thư viện hệ thống (Pango, Cairo) để render video. Chạy script sau để tự động cài đặt:
```bash
cd backend
chmod +x setup.sh
./setup.sh
```

### 2. Dọn dẹp Port (LSOF)
Nếu bạn gặp lỗi `Address already in use`, hãy chạy lệnh sau:
```bash
# LƯU Ý: lsof (viết tắt của list open files), không phải sof
lsof -ti :8000,3000 | xargs kill -9
```

## Troubleshooting (Sửa lỗi thường gặp)

| Lỗi | Nguyên nhân | Giải pháp |
|---|---|---|
| `Failed to fetch` | Backend đang khởi động hoặc reload | Chờ vài giây và thử lại. Đảm bảo Backend đang chạy ở port 8000. |
| `zsh: command not found: sof` | Gõ thiếu chữ 'l' | Gõ chính xác `lsof` (L-S-O-F). |
| `Internal Server Error` | Redis chưa kết nối | Kiểm tra file `.env` đã có `REDIS_URL` chính xác chưa. |
| `ParseError` (Manim) | Thiếu Pango/Cairo | Chạy lại `./setup.sh` trong folder backend. |

### 1. Backend (FastAPI - Debug Mode)
```bash
cd backend
source venv/bin/activate
# Chạy với reload và log info/debug
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Worker (Celery - Debug Mode)
```bash
cd backend
source venv/bin/activate
# Loglevel debug để xem chi tiết quá trình render
celery -A worker.celery_app worker --loglevel=debug
```

### 3. Frontend (Next.js - Dev/Log Mode)
```bash
cd frontend
npm run dev
```
Truy cập: [http://localhost:3000](http://localhost:3000)
