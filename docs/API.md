# Visual Math Solver API v5.1 — Hướng dẫn tích hợp Frontend

Tài liệu này là **một nguồn duy nhất** cho tích hợp API: endpoint HTTP/WebSocket, luồng OCR preview → solve, và **luồng xử lý dữ liệu nội bộ** (pipeline agent, trước đây tách file `API_DataFlow.md`). Phiên bản **v5.1** gồm Symbolic Solver, 3D, và Manim on-demand.

Base URL mặc định khi chạy local: `http://localhost:7860`

**OCR offload (tùy chọn):** `OCR_USE_CELERY=true` gửi **OCR thô** (model trên worker) tới Celery queue `ocr`; **LLM làm sạch/LaTeX** vẫn chạy trên Space API sau khi nhận chuỗi từ worker. **Video Manim** dùng queue `render` (Space render: `README_HF_WORKER.md`, `deploy-worker.yml`). `OCR_CELERY_TIMEOUT_SEC` (mặc định 180) giới hạn thời gian chờ Celery.

## Xác thực (Supabase JWT)
Các route bảo vệ yêu cầu header:
```http
Authorization: Bearer <supabase_access_token>
```

---

## Luồng xử lý nội bộ (Data pipeline)

Luồng tuần tự từ input đến output (kiến trúc agent); chi tiết gọi HTTP/WebSocket nằm ở các mục dưới.

```text
(1) User Input: Text toán học hoặc ảnh đề bài
    │
    ▼
(2) OCR Agent (khi có ảnh: `solve_multipart` / JSON `solve` + URL / `ocr_preview` / `POST /ocr`):
    ├─ IN: file ảnh hoặc URL công khai
    ├─ OPTIONAL: nếu API bật `OCR_USE_CELERY=true`, model OCR chạy trên Celery queue `ocr` (worker riêng); bước LLM tinh chỉnh vẫn trên API
    └─ OUT: chuỗi (text + LaTeX, đã làm mượt trong agent khi bật LLM)
    │
    ▼
(3) Parser Agent:
    ├─ IN: chuỗi (text + LaTeX)
    └─ OUT: JSON semantic (objects, relations, constraints)
    │
    ▼
(4) Geometry Agent & Knowledge:
    ├─ IN: JSON semantic
    └─ OUT: Geometry DSL (chuỗi script)
    │
    ▼
(5) Constraint Solver (GeometryEngine / SymPy):
    ├─ IN: Geometry DSL
    └─ OUT: JSON tọa độ điểm ([x, y] hoặc [x, y, z])
    │
    ▼
(6) Validation / retry: nếu fail có thể lặp với feedback Parser/Geometry
    │
    ▼
(7) Blueprint hình học: từ tọa độ + phases → dữ liệu cho canvas FE
    │
    ▼
(8) Animation (on-demand): Celery + Manim → file mp4, URL lưu metadata / storage
    │
    ▼
(9) Frontend: REST/WS nhận job status, coordinates, video_url
```

### Liên hệ với HTTP API

- **OCR trước khi solve (khuyến nghị khi có ảnh + chữ):** `POST /api/v1/sessions/{session_id}/ocr_preview` — không ghi DB; sau đó `POST .../solve` với `text` đã chỉnh, **không** gửi `image_url` nếu đã gộp OCR vào `text`.
- **OCR nhanh (legacy):** `POST /api/v1/ocr` — JWT, multipart một file, trả `{"text": "..."}`.
- **Solve (JSON):** `POST /api/v1/sessions/{session_id}/solve` — JWT, body JSON `text`, `image_url` tùy chọn — trả `job_id`, `status: processing`.
- **Solve (multipart, ảnh chat):** `POST /api/v1/sessions/{session_id}/solve_multipart` — JWT, `text` + `file` trong một form; BE upload Supabase bucket `image`, ghi `session_assets`, lưu `messages.metadata` (URL + `attachment`) rồi enqueue solve giống JSON.
- **Theo dõi job:** `WS /ws/{job_id}` hoặc `GET /api/v1/solve/{job_id}` (JWT, chỉ job của user). Trạng thái ví dụ: `processing`, `solving`, `rendering_queued`, `rendering`, `success`, `error`.
- **Video:** `POST /api/v1/sessions/{session_id}/render_video` rồi theo dõi job render qua WS/poll tương tự.

Bản ghi bảng `jobs` có cột `result` (JSONB) khi hoàn thành — cấu trúc `coordinates`, `solution`, … xem mục **Kết quả giải toán (Job Result)**.

---

## 🚀 Tính năng mới trong v5.1
- **Symbolic Solver**: Trả về đáp án cuối cùng và các bước giải chi tiết thông qua trường `solution`.
- **3D Geometry**: Tọa độ hiện hỗ trợ 3 trục `[x, y, z]`. Nếu $z=0$ cho tất cả các điểm, hệ thống coi là bài toán 2D.
- **On-demand Manim**: Video minh họa được tạo theo yêu cầu (On-demand) sau khi bài toán đã được giải và có kết quả hình ảnh. Hệ thống không tự động render để tối ưu hóa tài nguyên server.

---

## Giải bài (Solve)

### `POST /api/v1/sessions/{session_id}/solve`
Gửi bài toán trong một session (Context-aware). Chỉ tạo hình ảnh tĩnh và lời giải văn bản.

**Request body (JSON):**
| Trường | Kiểu | Mô tả |
|--------|------|--------|
| `text` | string | Đề bài hoặc lệnh bổ sung |
| `image_url` | string | URL ảnh đề bài (tùy chọn) |

**Luồng ảnh + chữ (paste / confirm):** Nếu người dùng cần xem lại OCR trước khi giải, FE gọi `POST .../ocr_preview`, chỉnh `combined_draft`, rồi `POST .../solve` (JSON) với `text` đã chỉnh và **không** gửi `image_url`.

**Khi nào dùng JSON vs multipart:** Dùng **`solve_multipart`** nếu FE cần một request duy nhất (text + file), ảnh lưu bucket `image` + metadata trong history (khuyến nghị cho chatbox). Dùng **`solve` (JSON)** nếu đã có URL ảnh công khai (hoặc chỉ text).

---

### `POST /api/v1/sessions/{session_id}/solve_multipart`
Gửi **cùng lúc** `text` và file ảnh đề: BE kiểm tra magic bytes / loại file, upload lên Storage bucket **`image`** (biến môi trường `SUPABASE_IMAGE_BUCKET`), insert **`session_assets`** (`asset_type: image`), insert **`messages`** user với `metadata` gồm `image_url` (public URL) và object **`attachment`** (`public_url`, `storage_path`, `size_bytes`, `content_type`, `original_filename`, `session_asset_id`), tạo job `processing` và chạy pipeline giống `solve` (orchestrator nhận `image_url` để OCR).

**Headers:** `Authorization: Bearer <token>`.

**Body:** `multipart/form-data`
| Trường | Kiểu | Mô tả |
|--------|------|--------|
| `text` | string (form, bắt buộc) | Đề bài / ghi chú (trim; không được rỗng) |
| `file` | file (bắt buộc) | PNG, JPEG, WebP, GIF, BMP; kiểm tra nội dung; giới hạn kích thước giống OCR preview (mặc định 10 MB, có thể chỉnh `CHAT_IMAGE_MAX_BYTES`) |

**Response:** Giống `solve`: `{ "job_id", "status": "processing" }`.

**Supabase:** Chạy migration [`backend/migrations/add_image_bucket_storage.sql`](backend/migrations/add_image_bucket_storage.sql) để tạo bucket `image` và policy storage.

---

## OCR Preview (trước khi Solve)

### `POST /api/v1/sessions/{session_id}/ocr_preview`
Chạy OCR trên file ảnh upload, ghép với `user_message` (nếu có), trả bản nháp để người dùng chỉnh / xác nhận trên UI. **Không** ghi `messages`, **không** tạo job solve.

**Headers:** `Authorization: Bearer <token>` (giống các route session khác).

**Body:** `multipart/form-data`
| Trường | Kiểu | Mô tả |
|--------|------|--------|
| `file` | file | Ảnh đề bài (PNG/JPEG/WebP/GIF/BMP; tối đa 10 MB) |
| `user_message` | string (form field, tùy chọn) | Ghi chú người dùng nhập kèm ảnh |

**Response (JSON):**
| Trường | Mô tả |
|--------|--------|
| `ocr_text` | Kết quả sau pipeline OCR (Paddle + làm mượt LLM trong agent) |
| `user_message` | Chuỗi ghi chú đã trim (echo) |
| `combined_draft` | Ghép theo quy ước: `user_message` + hai dòng trống + `ocr_text` nếu cả hai có; nếu thiếu một phần thì chỉ phần còn lại |

**Lỗi thường gặp:** `400` file rỗng, `413` vượt quá 10 MB, `403` không sở hữu session, `401` thiếu token.

---

## OCR nhanh (legacy, stateless)

### `POST /api/v1/ocr`
Upload một file ảnh, trả text OCR (không gắn session, không tạo job). Dùng cùng pipeline OCR với solve/preview.

**Headers:** `Authorization: Bearer <token>`.

**Body:** `multipart/form-data`, field `file` (ảnh).

**Response (JSON):** `{ "text": "<chuỗi OCR>" }`

---

## Trạng thái job (polling)

### `GET /api/v1/solve/{job_id}`
Lấy một dòng job từ Supabase (dùng khi WebSocket lỗi). **JWT bắt buộc**; chỉ trả job nếu `user_id` khớp token.

**Response:** object job (các trường ví dụ `id`, `status`, `session_id`, `result`, `input_text`, …). Trường `result` khi `status` là `success`/`error` chứa payload pipeline; cấu trúc success xem mục **Kết quả giải toán (Job Result)**.

---

## Tạo Video (Render Video) — v5.1 New Endpoint

### `POST /api/v1/sessions/{session_id}/render_video`
Yêu cầu hệ thống tạo video Manim mô phỏng quy trình vẽ hình. Theo mặc định, hệ thống sẽ lấy trạng thái hình học mới nhất của session. Bạn có thể chỉ định một `job_id` cụ thể để render lại một kết quả cũ.

**Request body (JSON):**
| Trường | Kiểu | Mô tả |
|--------|------|--------|
| `job_id` | string | ID của job giải toán cụ thể (tùy chọn, mặc định là mới nhất) |

**Response (JSON):**
```json
{
  "job_id": "render_job_uuid_456",
  "status": "rendering_queued"
}
```
FE nên lắng nghe WebSocket của `job_id` (render job) này để nhận kết quả khi video hoàn thành. Khi hoàn thành, hệ thống sẽ tự động gửi một tin nhắn `assistant` mới chứa `video_url` vào session.

---

## Kết quả giải toán (Job Result) — v5.1 JSON Structure

Khi job hoàn thành, kết quả `result` trả về sẽ có cấu trúc như sau:

```json
{
  "status": "success",
  "job_id": "job_uuid_123",
  "semantic_analysis": "Cho hình chóp S.ABCD có đáy là hình vuông cạnh 10...",
  "geometry_dsl": "POINT(S)\nPOINT(A)\n...",
  "coordinates": {
    "A": [0.0, 0.0, 0.0],
    "B": [10.0, 0.0, 0.0],
    "C": [10.0, 10.0, 0.0],
    "D": [0.0, 10.0, 0.0],
    "S": [5.0, 5.0, 15.0]
  },
  "drawing_phases": [
    {
      "phase": 1,
      "label": "Mặt đáy",
      "points": ["A", "B", "C", "D"],
      "segments": [["A","B"],["B","C"],["C","D"],["D","A"]]
    },
    {
      "phase": 2,
      "label": "Cạnh bên",
      "points": ["S"],
      "segments": [["S","A"],["S","B"],["S","C"],["S","D"]]
    }
  ],
  "solution": {
    "answer": "Thể tích hình chóp là 500 đơn vị khối.",
    "steps": [
      "Bước 1: Tính diện tích đáy hình vuông cạnh 10: S = 10 * 10 = 100.",
      "Bước 2: Xác định chiều cao hình chóp h = 15.",
      "Bước 3: Áp dụng công thức V = 1/3 * S * h = 1/3 * 100 * 15 = 500."
    ],
    "symbolic_math": {
      "V": "1/3 * a^2 * h",
      "result": "500"
    }
  },
  "is_3d": true,
  "video_url": "https://.../video_v1.mp4"
}
```

### 💡 Lưu ý cho Frontend (FE):
1. **Coordinates**: Luôn kiểm tra mảng tọa độ. Nếu có 3 phần tử `[x, y, z]`, FE nên sử dụng thư viện render 3D (như Three.js) hoặc chiếu xuống 2D (Perspective projection).
2. **Solution Display**: FE nên hiển thị `solution.answer` nổi bật và cung cấp nút "Xem chi tiết" để hiện thị `solution.steps`.
3. **Drawing Phases**: 
   - `phase: 1`: Vẽ các đối tượng chính (Boundary).
   - `phase: 2+`: Vẽ các đối tượng phụ (Auxiliary).

---

## 🛠 Yêu cầu Persistence (Lưu trữ Metadata)

Backend **BẮT BUỘC** lưu trữ các trường sau vào `messages.metadata` để hỗ trợ tính năng Versioning:

1. `job_id`
2. `coordinates`: Hỗ trợ `[x, y, z]`.
3. `polygon_order`
4. `drawing_phases`
5. `is_3d`: Boolean xác định chế độ hiển thị.
6. `solution`: Kết quả giải toán chi tiết.
7. `circles`, `lines`, `rays`: (Nếu có).
8. `video_url`: Cập nhật sau khi render xong.

---

## WebSocket — cập nhật realtime theo job
`WS /ws/{job_id}`
Server gửi updates trạng thái: `processing` -> `solving` -> `rendering_queued` (nếu có video) -> `success`.

---

## Mã lỗi thường gặp
| HTTP | Ý nghĩa |
|------|---------|
| 401 | Unauthenticated |
| 403 | Forbidden (Session owner mismatch) |
| 404 | Session/Job Not Found |
| 413 | Payload quá lớn (ví dụ ảnh OCR preview > 10 MB) |

---

## Phiên bản
API title: **Visual Math Solver API v5.1**
OpenAPI Spec tại: `/docs`
