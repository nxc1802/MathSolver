# Tài liệu Nâng cấp: Tích hợp Bộ Giải Toán (v5.1)

> **Phiên bản mục tiêu**: MathSolver v5.1  
> **Trọng tâm**: Từ "Vẽ hình" sang "Giải toán", tích hợp SymPy cho tính toán chính xác và xuất quy trình giải.

---

## 1. Phân tích Hiện trạng (AS-IS)

Hệ thống hiện tại (v4.0/5.0) mới chỉ là một bộ **Hình học Trực quan** (Geometry Visualizer):
- **Đầu vào**: Đề bài văn bản/hình ảnh.
- **Đầu ra**: Hình vẽ 2D/3D và tọa độ điểm.
- **Thiếu sót**: Không trả lời được các câu hỏi cụ thể như "Tính diện tích tam giác", "Chứng minh hai đường thẳng vuông góc", "Tìm giá trị của x".

---

## 2. Kiến trúc Mục tiêu (TO-BE)

### 2.1 Thành phần mới: **Solver Agent**
Bên cạnh việc sinh DSL để vẽ hình, hệ thống sẽ có một Agent chuyên trách việc suy luận logic và tính toán giá trị.

- **Nhiệm vụ**: Phân tích câu hỏi toán học, lập phương trình và gọi các hàm tính toán của SymPy.
- **Công cụ**: Sử dụng trực tiếp `SymPy` ở Backend để đảm bảo độ chính xác tuyệt đối về mặt ký hiệu (Symbolic).

### 2.2 Cấu trúc API Nâng cấp
Kết quả trả về từ `/solve` sẽ bao gồm thêm phần `solution`:

```json
{
  "status": "success",
  "coordinates": { ... },
  "solution": {
    "answer": "12.5 cm²",
    "steps": [
      "Bước 1: Xác định tọa độ các đỉnh A(0,0), B(5,0), C(0,5).",
      "Bước 2: Sử dụng công thức tính diện tích S = 1/2 * đáy * cao.",
      "Bước 3: Thay số: S = 1/2 * 5 * 5 = 12.5."
    ],
    "symbolic_expression": "25/2"
  }
}
```

---

## 3. Thay đổi Chi tiết

### 3.1 Backend: Solver Engine (SymPy Integration)
Nâng cấp `backend/solver/` để không chỉ trả về tọa độ mà còn thực hiện các phép toán hình học:

- **Diện tích/Thể tích**: Sử dụng các module `sympy.geometry` (Polygon, Circle, Plane, Segment).
- **Chứng minh**: Kiểm tra các tính chất như `is_perpendicular`, `is_parallel`, `is_collinear`.
- **Giải phương trình**: Sử dụng `sp.solve()` để tìm các ẩn số dựa trên các ràng buộc đã khai báo trong DSL.

### 3.2 Cập nhật Orchestrator
Quy trình mới của Orchestrator:
1. `Parser Agent` tách riêng **Dữ liệu hình học** và **Câu hỏi chính**.
2. `Geometry Agent` giải hình để lấy tọa độ (cho hiển thị).
3. `Solver Agent` nhận tọa độ + câu hỏi để tính toán đáp án cuối cùng.
4. Tổng hợp kết quả trả về cho User.

---

## 4. Kế hoạch Triển khai (Phases)

### Phase 1: Mở rộng Solver Cơ bản
- [ ] Tích hợp `sympy.geometry` vào pipeline.
- [ ] Hỗ trợ các câu hỏi tính độ dài đoạn thẳng và diện tích tam giác/tứ giác cơ bản.

### Phase 2: Xuất quy trình giải (Steps)
- [ ] Phát triển công cụ chuyển đổi các bước tính toán của SymPy thành ngôn ngữ tự nhiên (Vietnamese).
- [ ] Hiển thị các bước giải trên UI dưới dạng `StatusStepper` hoặc `Accordion`.

### Phase 3: Công cụ độ chính xác cao
- [ ] Triển khai cơ chế **Verify-by-Coordinates**: Kiểm tra xem đáp án tính được có khớp với tọa độ thực tế trên hình vẽ hay không để đảm bảo tính nhất quán.

---

## 5. Ví dụ Minh họa

**Đề bài**: "Cho tam giác ABC vuông tại A, AB=3, AC=4. Tính diện tích tam giác."

**Quy trình v5.1**:
1. **Vẽ hình**: Tính ra tọa độ A(0,0), B(3,0), C(0,4).
2. **Tính toán**:
   - Gọi `sympy.geometry.Triangle((0,0), (3,0), (0,4)).area`.
   - Kết quả: `6`.
3. **Phản hồi**: Trả về hình vẽ tam giác và lời giải chi tiết qua 3 bước.
