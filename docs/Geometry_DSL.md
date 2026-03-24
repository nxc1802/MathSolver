# Geometry Domain Specific Language (DSL) Specification

**Geometry DSL** là chuẩn ngôn ngữ hình học cốt lõi (Core) của Visual Math Solver v3.0, giúp biến cấu trúc ngôn ngữ tự nhiên, không định dạng thành cấu trúc khai báo có quy tắc (Declarative & Deterministic) cho Engine giải mã và render.

## 1. Thiết kế & Tính chất
- **Declarative**: Khai báo rõ ràng cái gì cần vẽ, không cần quan tâm nó vẽ thế nào.
- **Deterministic**: Đầu ra cho một bộ DSL là chính xác và duy nhất trong một hệ toạ độ (trừ khi có bậc tự do tuỳ ý).
- **Compile-able**: Bộ DSL có thể được dịch sang phương trình toán học sử dụng thuật toán hệ Constraint (Constraint-based solving).

## 2. Các thực thể (Primitives)
Các từ khoá khai báo thực thể căn bản.
- `POINT(id)`: Khai báo một điểm bất kỳ.
- `LINE(id1, id2)`: Khai báo một đoạn thẳng nối 2 điểm.
- `CIRCLE(center, radius)`: Đường tròn.

### Nhóm hình phức hợp:
- `TRIANGLE(id1_id2_id3)`: Khai báo tam giác.

## 3. Ràng buộc & Tính chất (Constraints)
- Ràng buộc độ dài: `LENGTH(id1_id2, value)`
- Ràng buộc góc: `ANGLE(id1, value_deg)` hoặc `ANGLE(id1_id2_id3, value_deg)`
- Ràng buộc đường: `PARALLEL(line1, line2)`, `PERPENDICULAR(line1, line2)`

## 4. Cú pháp Mẫu (Sample DSL Script)

Ví dụ tạo một tam giác ABC với độ dài 2 cạnh và 1 góc xen giữa:
```dsl
// Khai báo tập Đỉnh và Hình
POINT(A)
POINT(B)
POINT(C)
TRIANGLE(ABC)

// Khai báo Ràng buộc Cấu trúc đại số
LENGTH(AB, 5)
LENGTH(AC, 7)
ANGLE(A, 60deg)
```

## 5. Quy trình tích hợp với hệ thống
1. **Dữ liệu vào**: Từ **Geometry Agent** dịch.
2. **Tiến trình giải (Solver)**: Engine sẽ phân tích (lexer/parser) chuỗi DSL này sang biến và biểu thức SymPy.
3. **Tính toán Tọa độ**: Ví dụ `A = (0,0)`. `B = (5,0)` (vì AB=5). Tìm C dạng `(x, y)` biết khoảng cách `C->A` là `7` và góc hợp bởi hàm vec_to_angle là `60 độ`.
4. **Kết quả cuối**: Danh sách JSON Tọa độ:
```json
{
  "A": [0,0],
  "B": [5,0],
  "C": [3.5, 6.06]
}
```
