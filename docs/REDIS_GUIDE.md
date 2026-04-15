# Hướng dẫn Cấu hình Upstash Redis (Serverless)

Dự án sử dụng Redis để làm Broker cho Celery (render video và pipeline giải toán/OCR trên worker). **Upstash Redis** là lựa chọn tối ưu cho môi trường Serverless và Cloud vì tính ổn định và miễn phí (Free Tier).

### Hàng đợi Celery (`render` / `solve`)

- Task render video được route tới queue `render`; task giải toán (`process_solve_session_job`) tới queue `solve`.
- Worker phải lắng nghe đúng queue, ví dụ: `celery -A worker.celery_app worker -Q render,solve --loglevel=info`.
- Biến `CELERY_SOLVE_QUEUE` (mặc định `solve`) phải khớp với queue worker đang consume.

### WebSocket và Redis pub/sub

API chạy WebSocket trong process riêng với Celery worker. Khi `JOB_WS_REDIS_BRIDGE=true` (mặc định) và có `REDIS_URL` / `CELERY_BROKER_URL`, worker **publish** trạng thái job lên kênh Redis; process API **subscribe** và gọi `notify_status` để client WS nhận cập nhật. Tắt bridge: `JOB_WS_REDIS_BRIDGE=false` (khi đó có thể dùng polling `GET /api/v1/solve/{job_id}`).

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
