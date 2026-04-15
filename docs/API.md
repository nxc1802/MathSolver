# Visual Math Solver API v5.1 — Hướng dẫn tích hợp Frontend

Tài liệu này mô tả các endpoint HTTP và WebSocket để FE (web/mobile) gọi backend. Phiên bản **v5.1** bổ sung tính năng giải toán bước giải chi tiết (Symbolic Solver) và hỗ trợ hình học không gian (3D).

Base URL mặc định khi chạy local: `http://localhost:7860`

## Xác thực (Supabase JWT)
Các route bảo vệ yêu cầu header:
```http
Authorization: Bearer <supabase_access_token>
```

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

**Luồng ảnh + chữ (paste / confirm):** Nếu người dùng gửi ảnh kèm ghi chú và cần xem lại OCR trước khi giải, FE gọi `POST .../ocr_preview` (multipart), hiển thị `combined_draft`, cho sửa rồi gọi `POST /api/v1/sessions/{session_id}/solve` với `text` = nội dung đã chỉnh và **không** gửi `image_url` để tránh OCR hai lần. Endpoint solve chỉ nhận JSON, không nhận multipart.

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
