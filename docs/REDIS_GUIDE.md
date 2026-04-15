# Hướng dẫn Cấu hình Upstash Redis (Serverless)

Dự án sử dụng Redis làm broker cho Celery: queue **`render`** (Manim, worker riêng) và **`ocr`** (OCR khi API bật `OCR_USE_CELERY=true`, worker riêng). Pipeline **solve** chạy trên process API, không qua queue Celery `solve`. **Upstash Redis** phù hợp môi trường serverless/cloud (free tier, TLS).

## 1. Tạo Database trên Upstash
1. Truy cập [Upstash Console](https://console.upstash.com/) và đăng nhập.
2. Nhấn **Create Database**.
3. Chọn Region gần với nơi bạn deploy Backend (ví dụ: `AWS us-east-1`).
4. Bật tùy chọn **TLS (SSL)** - Đây là yêu cầu bắt buộc khi kết nối từ Cloud.

## 2. Lấy Connection String
1. Sau khi tạo xong, cuộn xuống phần **Connect to your database**.
2. Chọn tab **Celery** hoặc **Redis-py**.
3. Sao chép URL có dạng: `rediss://default:your-password@your-endpoint.upstash.io:6379`.
   - **Lưu ý**: Sử dụng `rediss://` (có 2 chữ s) để kích hoạt kết nối bảo mật SSL.

## 3. Cấu hình vào Dự án

### A. Chạy Local (.env)
Cập nhật file `backend/.env`:
```env
REDIS_URL=rediss://default:your-password@your-endpoint.upstash.io:6379
```

### B. Triển khai Cloud (Hugging Face / Vercel)
Thêm biến môi trường `REDIS_URL` vào phần **Variables/Secrets** trên Dashboard của dịch vụ bạn đang dùng.

## 4. Kiểm tra
Khi bạn khởi chạy backend/worker, Celery sẽ tự động kết nối tới Upstash. Bạn có thể theo dõi số lượng request/keys tại Dashboard của Upstash trong tab **Data Browser**.
