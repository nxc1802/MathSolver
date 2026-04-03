# Visual Math Solver API v4.0 — Hướng dẫn tích hợp Frontend

Tài liệu này mô tả các endpoint HTTP và WebSocket để FE (web/mobile) gọi backend. Base URL mặc định khi chạy local: `http://localhost:7860` (Docker/Hugging Face Spaces) hoặc cổng bạn cấu hình cho Uvicorn.

## Xác thực (Supabase JWT)

Các route bảo vệ yêu cầu header:

```http
Authorization: Bearer <supabase_access_token>
```

Token lấy từ Supabase Auth phía client (sau đăng nhập). Không có token hoặc token sai → `401`.

**Lưu ý backend:** phần lớn thao tác DB dùng **service role** phía server nhưng mọi truy vấn đều lọc theo `user_id` từ JWT sau khi `get_user` xác thực. Dependency `get_authenticated_supabase` tạo client dùng **anon key + JWT** khi cần áp dụng RLS đúng chuẩn (mở rộng sau).

### Biến môi trường (tham khảo)

| Biến | Mô tả |
|------|--------|
| `SUPABASE_URL` | URL dự án Supabase |
| `SUPABASE_SERVICE_ROLE_KEY` | Key server (bắt buộc cho API hiện tại) |
| `SUPABASE_ANON_KEY` | Publishable key — dùng khi gọi `get_authenticated_supabase` / RLS |
| `MEGALLM_API_KEY` / `MEGALLM_BASE_URL` / `MEGALLM_MODEL` | LLM parse/sinh DSL |
| `CELERY_BROKER_URL` / `REDIS_URL` | Hàng đợi render video (Celery) |
| `LOG_LEVEL` | **Một biến duy nhất** (mặc định `info`): `info` = chỉ log **HTTP** (method + path + status + thời gian); `debug` = thêm chi tiết từng bước (orchestrator, DB, cache); `warning` = giảm ồn, chỉ cảnh báo/lỗi + request 4xx/5xx; `error` = gần như chỉ lỗi |

---

## Nhóm Auth

### `GET /api/v1/auth/me`

Trả về profile hiện tại (bảng `profiles`).

**Response:** object profile (theo schema Supabase).

**Lỗi:** `404` nếu chưa có profile.

### `PATCH /api/v1/auth/me`

Cập nhật profile (body JSON tùy schema cột `profiles`).

**Response:** bản ghi đã cập nhật.

---

## Nhóm Sessions

### `GET /api/v1/sessions`

Danh sách session của user, sắp xếp `updated_at` giảm dần.

**Response:** `array` các session.

### `POST /api/v1/sessions`

Tạo session mới (tiêu đề mặc định `"Bài toán mới"`).

**Response:** object session vừa tạo.

### `GET /api/v1/sessions/{session_id}/messages`

Toàn bộ tin nhắn của session (theo `created_at` tăng dần).

**Lỗi:** `403` nếu session không thuộc user.

### `DELETE /api/v1/sessions/{session_id}`

Xóa session (và dữ liệu liên quan tùy FK phía DB).

**Response:** `{ "status": "ok", "deleted_id": "<uuid>" }`

### `PATCH /api/v1/sessions/{session_id}/title`

Đổi tiêu đề. Tham số `title` là **query string** (ví dụ `?title=Hình%20học`).

**Response:** session đã cập nhật.

---

## Giải bài (Solve)

### `POST /api/v1/sessions/{session_id}/solve`

Gửi bài toán trong một session.

**Request body (JSON):**

| Trường | Kiểu | Bắt buộc | Mô tả |
|--------|------|----------|--------|
| `text` | string | Có | Mô tả bài toán (tiếng Việt hoặc LaTeX) |
| `image_url` | string \| null | Không | URL ảnh đề bài; backend sẽ OCR |
| `request_video` | boolean | Không (mặc định `false`) | Có xếp hàng render video Manim qua Celery |

**Response:**

```json
{
  "job_id": "<uuid>",
  "status": "processing"
}
```

**Luồng:**

1. Lưu tin nhắn user vào `messages`.
2. Tạo bản ghi `jobs` (`status`: `processing`).
3. Xử lý nền: parse → DSL → solver → (tuỳ chọn) Celery render video.
4. Cập nhật `jobs` và gửi sự kiện qua WebSocket (xem dưới).

**Trạng thái job đặc biệt:** `rendering_queued` khi đã giải xong nhưng video đang chờ worker — tin nhắn assistant có thể được ghi sau khi video xong (xem worker).

**Lỗi:** `403` nếu không sở hữu session.

---

## Trạng thái job (polling)

### `GET /api/v1/solve/{job_id}`

Đọc một dòng trong bảng `jobs` (dùng khi WebSocket lỗi).

**Response:** object job (gồm `status`, `result`, …).

**Lỗi:** `404` nếu không tồn tại.

---

## WebSocket — cập nhật realtime theo job

### `WS /ws/{job_id}`

- Kết nối sau khi đã có `job_id` từ `POST .../solve`.
- Server gửi JSON, ví dụ: `{ "status": "processing" }`, `{ "status": "success", "result": { ... } }`, `{ "status": "error", "message": "..." }`.
- Client có thể gửi bất kỳ text nào để giữ kênh (server đọc trong vòng lặp).

**Gợi ý FE:** ưu tiên WS; fallback polling `GET /api/v1/solve/{job_id}` mỗi 1–2 giây.

---

## OCR (legacy, không gắn session)

### `POST /api/v1/ocr`

- **Content-Type:** `multipart/form-data`
- **Field:** `file` — ảnh (PNG/JPG, …)

**Response:**

```json
{ "text": "<chuỗi sau OCR + tinh chỉnh LLM>" }
```

Lần đầu gọi có thể chậm do tải model (YOLO/Paddle/Pix2Tex).

---

## Health / root

### `GET /`

```json
{ "message": "Visual Math Solver API v4.0 is running" }
```

Dùng kiểm tra service sống.

---

## Mã lỗi thường gặp

| HTTP | Ý nghĩa |
|------|---------|
| 401 | Thiếu/sai `Authorization` |
| 403 | Không có quyền với session |
| 404 | Profile/job không tồn tại |
| 503 | Thiếu cấu hình (ví dụ anon key khi dùng client RLS) |

---

## CORS

Backend bật CORS `allow_origins=["*"]` — FE dev có thể gọi trực tiếp; production nên thu hẹp theo domain.

---

## Phiên bản

API title: **Visual Math Solver API v4.0** (OpenAPI tại `/docs` khi bật Uvicorn).
