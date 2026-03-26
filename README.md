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

## Quy trình phát triển
Dự án được triển khai theo 5 giai đoạn (Phases) như trong `docs/Architecture.md`.

## Hướng dẫn chạy Locally

### 0. Dọn dẹp Port (Nếu cần)
```bash
lsof -ti :8000,3000 | xargs kill -9
```

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
