# Hướng dẫn Triển khai (Deployment Guide)

Tài liệu này hướng dẫn cách đưa Visual Math Solver v3.0 lên môi trường Production.

## 1. Backend (Hugging Face Spaces)
1. Truy cập [Hugging Face Spaces](https://huggingface.co/spaces) và tạo Space mới.
2. Chọn SDK là **Docker**.
3. Trong phần cấu hình Space, hãy thiết lập các **Variables & Secrets** (trong tab Settings) giống như file `backend/.env`.
   - `MEGALLM_API_KEY`, `MEGALLM_BASE_URL`, `SUPABASE_URL`, v.v.
   - **Lưu ý quan trọng**: Thiết lập `REDIS_URL` trỏ tới một Redis instance thực tế (như [Upstash](https://upstash.com/)).
4. Đẩy (Push) code trong thư mục `/backend` lên repository của HF Space (Hoặc trỏ HF Space về thư mục con nếu bạn dùng cấu trúc monorepo phức tạp). **File `Dockerfile.backend` đã được tối ưu cho port 7860 của HF.**

## 2. Frontend (Vercel)
1. Import dự án lên [Vercel](https://vercel.com).
2. Thiết lập **Root Directory** là `frontend`.
3. Thêm các **Environment Variables**:
   - `NEXT_PUBLIC_API_URL`: URL của Hugging Face Space bạn vừa tạo (ví dụ: `https://user-appname.hf.space`).
   - `NEXT_PUBLIC_WS_URL`: URL WebSocket của Space (ví dụ: `wss://user-appname.hf.space`).
4. Nhấn **Deploy**.

## 3. Cấu hình Supabase
1. Đảm bảo đã tạo Bucket tên là `video` trong Supabase Storage.
2. Thiết lập chính sách (Policy) cho phép đọc công khai (Public Read) để có thể xem video animation trên web.

---
**Dự án hiện đã sẵn sàng 100% để hoạt động trên môi trường Cloud thực tế!**
