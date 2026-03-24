# Hệ thống Trực quan họa (Rendering & Animation System)

Tài liệu thiết kế luồng Render ảnh và Video Animation cho kết quả bài toán hình học trong phần mềm Visual Math Solver v3.0.

## 1. Động cơ Đồ họa Cơ bản (Rendering Engine)
Sau khi Constraint Solver Layer chốt được bộ tọa độ Euclid cho các điểm và hình dạng, Rendering Layer dựa vào các tọa độ này tạo Graphic primitives.
### Tech Stack Tùy chọn:
- **GeoGebra MVP**: Export script theo syntax GeoGebra để lấy nhanh bản thể 2D Interactive trên Web. Phù hợp cho tính năng xem nhanh, test chức năng. 
- **Matplotlib / Pillow**: Dành cho việc render ảnh tĩnh đơn giản để debug nội bộ.

### Format Data Truyền tải:
```json
{
  "points": [{"id": "A", "x": 0, "y": 0, "color": "white", "label": "A"}],
  "lines": [{"p1": "A", "p2": "B", "style": "solid", "color": "blue"}],
  "angles": [{"center": "A", "p1": "B", "p2": "C", "measure": "60deg", "show_value": true}]
}
```

## 2. Animation Engine (Video Step-by-Step Generator)
Để đáp ứng điểm nhấn cốt lõi (Wow Factor) của nền tảng v3.0, Animation Engine bằng **Manim** sẽ đóng vai trò sản xuất Animation dựng hình.
### Các tính năng Animation chính:
- Hiệu ứng tạo từng điểm (`Write` / `Create`).
- Căng đường kéo từ điểm này đến điểm kia để dựng Đoạn thẳng (`Transform`, `MoveTo`).
- Bôi viền tô màu các mặt bị giới hạn (Highlight Polygon khu vực tam giác).
- Ghi chú góc (`RightAngle`, `Arc`).
- Tạo Text label giải thích bên cạnh hình vẽ (Voiceover sync if applicable).

### Cách Thức Tích hợp (Integration):
- Python Web App (FastAPI) nhận yêu cầu sinh video.
- Chuyển tiếp Request vào Background Worker/Queue (VD: Celery) để tránh Block Main Thread vì Manim Render cần nhiều tài nguyên CPU và thời gian (vài giây - phút phụ thuộc chất lượng 1080p60fps).
- **Manim Generator script** nội tại sẽ map Data Input (Toạ độ JSON) với các Method tạo hình Manim có sẵn (`Dot`, `Line`, `Polygon`, `Angle`).
- Sau khi build ra `.mp4`, kết quả được ném lên phân vùng lưu trữ (S3 / Local Storage), Frontend sẽ chọc API nhận URL về phát trong Video Player.
