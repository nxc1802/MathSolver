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

Gửi bài toán trong một session. **Tính năng mới**: Backend tự động lấy toàn bộ lịch sử chat trong session để làm ngữ cảnh (Context-aware). Điều này cho phép người dùng ra lệnh bổ sung (ví dụ: "vẽ thêm đường cao AH") cho hình đang có.

**Request body (JSON):**

| Trường | Kiểu | Bắt buộc | Mô tả |
|--------|------|----------|--------|
| `text` | string | Có | Mô tả bài toán hoặc lệnh bổ sung |
| `image_url` | string \| null | Không | URL ảnh đề bài (chỉ dùng cho lượt đầu hoặc khi có hình mới) |
| `request_video` | boolean | Không | Có render video Manim hay không |

**Ghi chú về Rendering:**
- **Hình vẽ (Drawing)**: Backend cung cấp đầy đủ `coordinates`, `geometry_dsl` và `drawing_phases`. **Frontend (FE) chịu trách nhiệm render** dựa trên dữ liệu này cho mọi bài toán.
- **Video**: Nếu `request_video=true`, BE sẽ render video và lưu trữ có versioning.

---

## 📈 Quản lý Asset & Versioning

Mọi video được sinh ra trong một session sẽ được lưu trữ dưới dạng version để tránh bị ghi đè.

### Bảng `session_assets` (Tham chiếu DB)
- Mỗi bản ghi liên kết một `job_id` với một file trong Storage.
- Path mẫu: `sessions/{session_id}/video_v{version}_{job_id}.mp4`

---

## Kết quả giải toán (Job Result) — Multi-turn Example

Khi người dùng gửi lệnh bổ sung, `geometry_dsl` trả về sẽ bao gồm cả các thực thể cũ và mới.

**Response `result` example (sau lệnh "vẽ thêm đường chéo AC"):**

```json
{
  "status": "success",
  "semantic_analysis": "Cho hình chữ nhật ABCD có AB=10, AD=5. Vẽ thêm đường chéo AC.",
  "geometry_dsl": "POLYGON_ORDER(A,B,C,D)\nPOINT(A)\nPOINT(B)\nPOINT(C)\nPOINT(D)\nLENGTH(AB, 10)\nLENGTH(AD, 5)\nPERPENDICULAR(AB, AD)\nSEGMENT(A, C)",
  "coordinates": {
    "A": [0.0, 0.0],
    "B": [10.0, 0.0],
    "C": [10.0, 5.0],
    "D": [0.0, 5.0]
  },
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
      "points": [],
      "segments": [["A","C"]]
    }
  ],
  "lines": [],
  "rays": []
}
```

> [!IMPORTANT]
> FE luôn ưu tiên vẽ toàn bộ `coordinates` và các `segments` trong `drawing_phases` để đảm bảo tính nhất quán qua các lượt chat.

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
Phase 1 → Vẽ polygon chính dựa trên polygon_order (Boundary) hoặc drawing_phases[0].segments.
Phase 2+ → Vẽ các đoạn thẳng phụ (Auxiliary lines) dựa trên drawing_phases[1+].segments.
Lưu ý: 
- Luôn vẽ điểm (nodes) và nhãn (labels) cho tất cả các điểm có trong coordinates.
- **Mới**: Vẽ đường thẳng vô hạn cho các cặp điểm trong `lines` (scale lớn ra ngoài canvas).
- **Mới**: Vẽ tia bắt đầu từ điểm đầu và kéo dài qua điểm thứ hai cho các cặp trong `rays`.
```

Tọa độ cho mỗi điểm lấy từ `coordinates[pointId]` dưới dạng `[x, y]` (đơn vị logic, FE cần scale phù hợp với canvas).

---

## 🛠 Yêu cầu Persistence (Lưu trữ Metadata)

> [!CAUTION]
> **CỰC KỲ QUAN TRỌNG**: Để tính năng **Chuyển đổi Version (Version Switching)** và **Duy trì Session** hoạt động, Backend **BẮT BUỘC** phải lưu đầy đủ kết quả hình học vào cột `metadata` của bảng `messages` cho **TẤT CẢ** các tin nhắn của `assistant` trong lịch sử, không chỉ tin nhắn mới nhất.
>
> Nếu thiếu metadata ở các tin nhắn cũ, người dùng sẽ không thể nhấn nút quay lại các phiên bản vẽ trước đó.

### Các trường bắt buộc trong `messages.metadata`:
1. `job_id`: ID của task xử lý.
2. `coordinates`: Object chứa tọa độ các điểm.
3. `polygon_order`: Mảng các điểm tạo thành đa giác chính.
4. `drawing_phases`: Mảng các bước vẽ chi tiết (Phân biệt nét đứt/nét liền, nét chính/phụ).
5. `circles`: Danh sách các hình tròn (nếu có).
6. `lines`: Danh sách các đường thẳng vô hạn (nếu có).
7. `rays`: Danh sách các tia (nếu có).
8. `video_url`: URL video Manim (phải cập nhật vào metadata sau khi render xong).

**Lưu ý cho BE Engineer:** Hiện tại khi gọi `GET /messages`, các tin nhắn cũ đang bị thiếu metadata dẫn đến lỗi "không có version cũ nào được lưu lại". Vui lòng kiểm tra lại hàm lưu tin nhắn trong `solve.py` và worker `tasks.py`.

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
