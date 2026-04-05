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

Xóa session và **toàn bộ dữ liệu liên quan** (messages, jobs). Bản ghi trong bảng `jobs` và `messages` sẽ được xóa trước để tránh lỗi ràng buộc khóa ngoại (FK).

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
3. **Tự động đổi tên Session**: Nếu tiêu đề hiện tại là `"Bài toán mới"`, backend sẽ tự động cập nhật tiêu đề dựa trên 50 ký tự đầu của `text`.
4. Xử lý nền: OCR (nếu có ảnh) → parse → knowledge augment → DSL → solver → (tuỳ chọn) Celery render video.
5. Cập nhật `jobs` và gửi sự kiện qua WebSocket.
6. Khi xử lý thành công, kết quả sẽ được chèn vào bảng `messages` dưới dạng tin nhắn của `assistant`.

**Trạng thái job đặc biệt:** `rendering_queued` khi đã giải xong nhưng video đang chờ worker.

**Lỗi:** `403` nếu không sở hữu session.

---

## Kết quả giải toán (Job Result)

Khi `status = "success"`, trường `result` của job (qua WebSocket hoặc `GET /api/v1/solve/{job_id}`) trả về cấu trúc sau:

```json
{
  "status": "success",
  "semantic_analysis": "Cho hình chữ nhật ABCD có AB=10, AD=20. M và N lần lượt là trung điểm AB, AD.\n\n**Các bước dựng hình:**\n- **Hình cơ bản**: Xác định các điểm A, B, C, D. Vẽ các đoạn thẳng AB, BC, CD, DA.\n- **Điểm và đoạn phụ**: Xác định các điểm M, N. Vẽ đoạn thẳng MN.",
  "geometry_dsl": "POLYGON_ORDER(A,B,C,D)\nPOINT(A)\nPOINT(B)\nPOINT(C)\nPOINT(D)\nLENGTH(AB, 10)\nLENGTH(AD, 20)\nMIDPOINT(M, AB)\nMIDPOINT(N, AD)\nSEGMENT(M, N)",
  "coordinates": {
    "A": [0.0, 0.0],
    "B": [-10.0, 0.0],
    "C": [-10.0, -20.0],
    "D": [0.0, -20.0],
    "M": [-5.0, 0.0],
    "N": [0.0, -10.0]
  },
  "polygon_order": ["A", "B", "C", "D"],
  "circles": [
    {"center": "O", "radius": 5.0}
  ],
  "drawing_phases": [
    {
      "phase": 1,
      "label": "Hình cơ bản",
      "points": ["A", "B", "C", "D"],
      "segments": [["A","B"],["B","C"],["C","D"],["D","A"]]
    },
    {
      "phase": 2,
      "label": "Điểm và đoạn phụ",
      "points": ["M", "N"],
      "segments": [["M","N"]]
    }
  ],
  "video_url": "https://storage.../manim_video.mp4"
}
```

### Mô tả các trường

| Trường | Kiểu | Mô tả |
|--------|------|--------|
| `semantic_analysis` | string | **Mô tả tiếng Việt** tóm tắt bài toán + **Các bước dựng hình** do trợ lý sinh ra. Dùng để hiển thị trong chat bubble của assistant. |
| `polygon_order` | `string[]` | Danh sách đỉnh tạo thành khung hình chính (Base shape). |
| `circles` | `array` | Danh sách đường tròn: `[{"center": "O", "radius": 5.0}, ...]`. |
| `drawing_phases` | `array` | Danh sách giai đoạn vẽ. **FE nên dùng cái này để vẽ hình** vì nó tách biệt hình chính và điểm phụ. |
| `video_url` | `string` | Link video Manim (có sau khi worker xử lý xong Celery). |

### drawing_phases — Hướng dẫn tích hợp FE

> [!IMPORTANT]
> FE **phải** ưu tiên vẽ theo `drawing_phases` thay vì tự ý nối các điểm. Cấu trúc này đảm bảo các điểm trung điểm (M, N) hay điểm phụ không bị nối nhầm vào chu vi của hình chính.

Mỗi phần tử trong `drawing_phases`:

```typescript
interface DrawingPhase {
  phase: number;        // Số thứ tự (1, 2, ...)
  label: string;        // Tên phase (tiếng Việt)
  points: string[];     // Danh sách điểm cần render trong phase này
  segments: string[][]; // Danh sách cặp điểm tạo thành đoạn thẳng, e.g. [["M","N"]]
}
```

**Gợi ý rendering (Canvas/WebGL):**

```
Phase 1 → Vẽ polygon chính (dùng polygon_order), hiện tên điểm gốc (A,B,C,D)
Phase 2 → Thêm điểm phụ (M, N), vẽ các đoạn thẳng phụ (MN)
```

Tọa độ cho mỗi điểm lấy từ `coordinates[pointId]` dưới dạng `[x, y]` (đơn vị logic, FE cần scale phù hợp với canvas).

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
