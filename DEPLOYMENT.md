# Hướng dẫn Triển khai (Deployment Guide)

Tài liệu này hướng dẫn cách đưa Visual Math Solver v5.1 lên môi trường Production.

## 1. Backend (Hugging Face Spaces)
1. Truy cập [Hugging Face Spaces](https://huggingface.co/spaces) và tạo Space mới.
2. Chọn SDK là **Docker**.
3. Trong phần cấu hình Space, hãy thiết lập các **Variables & Secrets** (trong tab Settings) giống như file `backend/.env`. Các biến quan trọng mới:
   - `OPENROUTER_MODEL_1`, `OPENROUTER_MODEL_2`, `OPENROUTER_MODEL_3`: Danh sách model fallback (v5.1).
   - `OPENROUTER_API_KEY_1`: API key chính cho OpenRouter.
   - `SUPABASE_URL`, `SUPABASE_KEY`, `REDIS_URL`, v.v.
   - **Lưu ý**: Hệ thống v5.1 sử dụng cơ chế **Model Fallback** (thử lần lượt từ Model 1 đến 3) để đảm bảo độ tin cậy.
4. Đẩy (Push) code trong thư mục `/backend` lên repository của HF Space. **File `Dockerfile` đã được tối ưu cho port 7860 của HF.**

## 2. Quy trình Vẽ hình & Video (v5.1 Workflow)
Hệ thống v5.1 đã tách biệt quá trình giải toán và tạo video:
1. **Giải toán**: Chỉ tạo hình ảnh tĩnh và bước giải văn bản (`POST /solve`).
2. **Tạo Video**: Thực hiện theo yêu cầu (`POST /render_video`) sau khi người dùng đã xem và hài lòng với hình vẽ tĩnh. FE cần hiển thị nút "Tạo Video" riêng biệt.

## 3. Frontend (Vercel)
1. Import dự án lên [Vercel](https://vercel.com).
2. Thiết lập **Root Directory** là `frontend` (hoặc root nếu monorepo).
3. Thêm các **Environment Variables**:
   - `NEXT_PUBLIC_API_URL`: URL của Hugging Face Space.
   - `NEXT_PUBLIC_WS_URL`: URL WebSocket của Space (wss://...).
4. Nhấn **Deploy**.

## 4. Cấu hình Supabase
1. Đảm bảo đã tạo Bucket tên là `video` trong Supabase Storage.
2. Thiết lập chính sách (Policy) cho phép đọc công khai (Public Read) để có thể xem video animation trên web.

---
**Dự án hiện đã sẵn sàng 100% để hoạt động trên môi trường Cloud thực tế!**
