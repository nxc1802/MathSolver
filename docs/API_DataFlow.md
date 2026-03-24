# Data Flow & Pipeline Specification

Tài liệu này xác định luồng di chuyển và trao đổi dữ liệu (Data Pipeline) qua từng công đoạn của Visual Math Solver v3.0, từ khi nhận Input của người dùng đến lúc xuất Video trực quan trên Frontend.

## 1. Sơ đồ Luồng Dữ Liệu (Data Flow)

Cấu trúc luồng tuần tự và các Data Type chuyển giao tại mỗi Node:

```text
(1) User Input: Mẫu dữ liệu (Text Toán học, Hoặc Image Đề bài)
    │
    ▼
(2) OCR Agent (Nếu input là Image):
    ├─ IN: Image file (jpg, png)
    └─ OUT: String (Text kết hợp Toán LaTeX)
    │
    ▼
(3) Parser Agent:
    ├─ IN: String (Text + LaTeX)
    └─ OUT: JSON Array (Objects, Relations, Semantic Constraints)
    │
    ▼
(4) Geometry Agent & Knowledge:
    ├─ IN: JSON Array theo chuẩn NLP/Semantic Domain
    └─ OUT: Script String (chuỗi Geometry DSL tiêu chuẩn)
    │
    ▼
(5) Constraint Solver:
    ├─ IN: Script String (Geometry DSL)
    ├─ SYNC: Giải phương trình lập trình bởi hệ SymPy/Numpy.
    └─ OUT: JSON Coordinates (Toạ độ điểm ảnh [x, y])
    │ 
    ▼
(6) Validation Layer:
    ├─ IN: JSON Coordinates
    ├─ FLOW: IF Fail -> Vòng lặp báo Constraint Solver/Geometry Agent xử lý lại. IF Pass -> Bước tiếp theo.
    └─ OUT: Vetted JSON Coordinates
    │
    ▼
(7) Rendering Engine (Geometric Blueprint):
    ├─ IN: Vetted JSON Coordinates
    └─ OUT: Vector Plot / Script đồ hoạ khởi nguồn (GeoGebra code / Manim Object Instance).
    │
    ▼
(8) Animation Engine (Video Processing):
    ├─ IN: Manim Object Instance kèm kịch bản step-by-step
    └─ OUT: Video File (mp4) giải thích từng bước. Xây điểm A, B, vẽ đường AB, v.v.
    │
    ▼
(9) Frontend Viewer:
    ├─ Xương sống API Gateway truyền tải Link Video, JSON Tọa độ về Frontend
    └─ Kết xuất lên Giao diện web Next.js
```

## 2. Giao thức Tương tác API (Dự kiến)

Hệ thống cung cấp REST/Graph API từ Backend FastAPI cho Web Client tiêu thụ:

### 2.1 API Endpoint Sinh Hình Học (`POST /api/v1/solve/geometry`)
- Nhận hình ảnh/text.
- Trả Job ID chạy ngầm (Asynchronous Data Generation do luồng Agent phân tích lâu).

### 2.2 API Lấy Trạng thái (`GET /api/v1/solve/{job_id}`)
- Trả về status: `pending`, `parsing`, `solving`, `rendering`, `success`.

### 2.3 Cấu trúc Response
```json
{
  "status": "success",
  "data": {
    "original_text": "Cho tam giác ABC có AB=5, AC=7...",
    "parsed_dsl": "POINT(A)\nPOINT(B)\n...",
    "coordinates": {"A": [0,0], "B": [5,0], "C": [3.5, 6.06]},
    "visualizer": {
      "type": "video",
      "url": "https://storage../output/ABC_triangle.mp4"
    }
  }
}
```
