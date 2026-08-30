# Geometry Domain Specific Language (DSL) Specification — v5.2

**Geometry DSL** là chuẩn ngôn ngữ hình học cốt lõi của **Visual Math Solver v5.2**, giúp chuyển hóa ngôn ngữ tự nhiên thành cấu trúc khai báo có quy tắc (Declarative & Deterministic) cho Solver Engine giải hệ phương trình ràng buộc (Constraint-based solving) và Render trực quan hóa 2D/3D.

---

## 1. Các Thực Thể Cơ Bản (Primitives)

- `POINT(id)`: Khai báo điểm (hỗ trợ $A, B, C, A_1, B_1, A', B', M_1, S_1$).
- `POINT(id, x, y)` / `POINT(id, x, y, z)`: Khai báo điểm với tọa độ tường minh trong không gian 2D/3D.
- `SEGMENT(id1, id2)`: Đoạn thẳng nối 2 điểm.
- `LINE(id1, id2)`: Đường thẳng vô hạn đi qua 2 điểm.
- `RAY(id1, id2)`: Tia xuất phát từ `id1` đi qua `id2`.
- `CIRCLE(center, radius)`: Đường tròn (2D).
- `POLYGON_ORDER(id1, id2, ...)`: Thứ tự các đỉnh tạo thành đường bao đa giác.
- `TRIANGLE(id1_id2_id3)`: Tam giác 2D.

---

## 2. Các Khối Không Gian 3D (3D Polyhedrons & Solids)

| Cú pháp DSL | Khối hình học | Ý nghĩa & Cạnh sinh tự động |
|---|---|---|
| `PYRAMID(S_ABCD)` | Hình chóp đỉnh S, đáy ABCD | Sinh các cạnh bên $SA, SB, SC, SD$ và cạnh đáy $AB, BC, CD, DA$. |
| `PRISM(ABC_DEF)` | Hình lăng trụ tam giác | Sinh cạnh đáy 1 ($AB, BC, CA$), đáy 2 ($DE, EF, FD$) và cạnh bên ($AD, BE, CF$). |
| `PRISM(ABCD_A1B1C1D1)` | Hình lăng trụ tứ giác | Sinh 8 cạnh của 2 đáy và 4 cạnh bên. |
| `TETRAHEDRON(ABCD)` | Hình tứ diện | Sinh đủ 6 cạnh $AB, AC, AD, BC, CD, DB$. |
| `CUBE(ABCD_A1B1C1D1)` | Hình lập phương | Sinh 12 cạnh, tự động gán các mặt đáy và các mặt vuông góc. |
| `CUBOID(ABCD_A1B1C1D1)` | Hình hộp chữ nhật / Hình hộp | Sinh đủ 12 cạnh kết nối 2 đáy. |
| `FRUSTUM(ABCD_A1B1C1D1)` | Hình chóp cụt | Sinh 4 cạnh đáy dưới, 4 cạnh đáy trên và 4 cạnh bên. |
| `CONE(S, O, r)` hoặc `CONE(S, O, r, h)` | Hình nón | Đỉnh S, tâm đáy O, bán kính r, chiều cao h, trục $SO$. |
| `CYLINDER(O1, O2, r)` | Hình trụ | Hai tâm đáy O1, O2, bán kính r, trục $O_1O_2$. |
| `SPHERE(O, r)` | Mặt cầu / Khối cầu | Tâm O, bán kính r. |

---

## 3. Ràng Buộc Hình Học (Constraints)

### 3.1. Ràng Buộc Cơ Bản (2D & 3D)
- `LENGTH(AB, value)`: Khoảng cách giữa 2 điểm bằng `value`.
- `ANGLE(A, deg)` / `ANGLE(A, B, C, deg)`: Góc giữa các đỉnh/vectơ.
- `PARALLEL(AB, CD)`: Đoạn thẳng $AB \parallel CD$ (3D: Tích có hướng $\vec{AB} \times \vec{CD} = \vec{0}$).
- `PERPENDICULAR(AB, CD)`: Đoạn thẳng $AB \perp CD$ (3D: Tích vô hướng $\vec{AB} \cdot \vec{CD} = 0$).
- `MIDPOINT(M, AB)`: M là trung điểm của $AB$ ($\vec{M} = \frac{\vec{A} + \vec{B}}{2}$).
- `SECTION(E, A, C, k)`: Điểm E chia đoạn AC theo tỉ lệ $\vec{AE} = k \cdot \vec{AC}$.

### 3.2. Ràng Buộc Không Gian Cấp Cao (Advanced 3D)
- `PERPENDICULAR_PLANE(Line, Plane)` (hoặc `LINE_PERP_PLANE`): Đường thẳng vuông góc mặt phẳng.
  *Ví dụ:* `PERPENDICULAR_PLANE(SO, ABCD)` $\implies SO \perp AB$ và $SO \perp AC$.
- `COPLANAR(A, B, C, D)`: 4 điểm đồng phẳng $\implies (\vec{AB} \times \vec{AC}) \cdot \vec{AD} = 0$.
- `POINT_ON_PLANE(P, ABC)`: Điểm P thuộc mặt phẳng $(ABC)$.

---

## 4. Các Mẫu Cú Pháp DSL (Standard Examples)

### Ví dụ 1: Hình chóp $S.ABCD$ đáy hình vuông cạnh 10, $SO \perp (ABCD)$, $SO=15$
```dsl
PYRAMID(S_ABCD)
POINT(A, 0, 0, 0)
POINT(B, 10, 0, 0)
POINT(C, 10, 10, 0)
POINT(D, 0, 10, 0)
POINT(S)
POINT(O)
SECTION(O, A, C, 0.5)
PERPENDICULAR_PLANE(SO, ABCD)
LENGTH(SO, 15)
POLYGON_ORDER(A, B, C, D)
```

### Ví dụ 2: Hình lập phương $ABCD.A_1B_1C_1D_1$ cạnh $a=5$
```dsl
CUBE(ABCD_A1B1C1D1)
POINT(A, 0, 0, 0)
POINT(B, 5, 0, 0)
POINT(C, 5, 5, 0)
POINT(D, 0, 5, 0)
POINT(A1)
POINT(B1)
POINT(C1)
POINT(D1)
LENGTH(AA1, 5)
PERPENDICULAR_PLANE(AA1, ABCD)
```

### Ví dụ 3: Hình nón đỉnh S, đáy tâm O bán kính $r=4$, chiều cao $h=8$
```dsl
POINT(O, 0, 0, 0)
POINT(S, 0, 0, 8)
CONE(S, O, 4, 8)
```
