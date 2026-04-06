# Tài liệu Nâng cấp: Hình học Không gian 3D & Tương tác (v5.0)

> **Phiên bản mục tiêu**: MathSolver v5.0  
> **Trọng tâm**: Chuyển đổi từ 2D SVG sang 3D Three.js, hỗ trợ hệ trục tọa độ Oxyz và tương tác người dùng.

---

## 1. Phân tích Hiện trạng (AS-IS)

| Thành phần | Hiện trạng (v4.0) | Hạn chế |
|---|---|---|
| **Rendering** | SVG (Scalable Vector Graphics) | Chỉ hỗ trợ 2D (x, y). Không thể xoay hoặc xem chiều sâu. |
| **Geometry Engine** | SymPy giải hệ 2 biến (x, y) | Không tính toán được tọa độ z cho các bài toán không gian. |
| **DSL** | Khai báo thực thể phẳng (Polygon) | Thiếu các từ khóa khối (Sphere, Cone, Cylinder, Pyramid). |
| **Tương tác** | Tĩnh (Static) | Người dùng không thể thay đổi góc nhìn để quan sát các mặt khuất. |

---

## 2. Kiến trúc Mục tiêu (TO-BE)

### 2.1 Cư chế Hiển thị mới (3D Engine)
- **Thư viện**: `Three.js` kết hợp với `@react-three/fiber` và `@react-three/drei`.
- **Thành phần**:
    - **Scene**: Chứa toàn bộ vật thể 3D.
    - **Camera**: PerspectiveCamera hỗ trợ chiều sâu.
    - **Controls**: `OrbitControls` cho phép Xoay (Rotate), Thu phóng (Zoom) và Di chuyển (Pan).
    - **Helpers**: `AxesHelper` hiển thị trục Oxyz (X: Đỏ, Y: Xanh lá, Z: Xanh dương).

### 2.2 Luồng Dữ liệu 3D
```mermaid
graph LR
    DSL_3D[Geometry DSL 3D] --> Engine[Geometry Engine 3D]
    Engine --> Coords_XYZ[Coordinates JSON {x,y,z}]
    Coords_XYZ --> FE_Canvas[Three.js Canvas]
```

---

## 3. Thay đổi Chi tiết

### 3.1 Cập nhật Geometry DSL 3D
Hỗ trợ khai báo tọa độ 3 chiều và các khối không gian:

- **Điểm**: `POINT(A, 0, 0, 5)` (tọa độ x, y, z).
- **Khối**:
    - `PYRAMID(S_ABCD)`: Hình chóp đáy ABCD.
    - `PRISM(ABC_DEF)`: Hình lăng trụ.
    - `SPHERE(O, R)`: Mặt cầu tâm O bán kính R.
- **Ràng buộc**:
    - `PERPENDICULAR_PLANE(Line, Plane)`: Đường thẳng vuông góc với mặt phẳng.
    - `ANGLE_BETWEEN_PLANES(Plane1, Plane2, val)`: Góc giữa hai mặt phẳng.

### 3.2 Backend: Geometry Engine (SymPy)
- **Biến số**: Mỗi điểm `P` sẽ có 3 biểu thức ký hiệu `P_x, P_y, P_z`.
- **Hệ phương trình**: Nâng cấp các hàm tính khoảng cách và góc sang công thức 3D chuẩn:
    - Khoảng cách: `sqrt((x2-x1)**2 + (y2-y1)**2 + (z2-z1)**2)`.
    - Tích vô hướng (Dot product) để tính góc trong không gian.

### 3.3 Frontend: `Interactive3DCanvas.tsx` [MỚI]
Thay thế `StaticGeometryCanvas.tsx` bằng một component Three.js:

```tsx
import { Canvas } from '@react-three/fiber';
import { OrbitControls, Stars, AxesHelper } from '@react-three/drei';

export default function Interactive3DCanvas({ data }) {
  return (
    <Canvas camera={{ position: [10, 10, 10], fov: 50 }}>
      <ambientLight intensity={0.5} />
      <pointLight position={[10, 10, 10]} />
      <OrbitControls makeDefault />
      
      {/* Vẽ các điểm và cạnh 3D dựa trên data.coordinates */}
      <AxesHelper args={[5]} /> 
      <Stars radius={100} depth={50} count={5000} factor={4} saturation={0} fade speed={1} />
    </Canvas>
  );
}
```

---

## 4. Kế hoạch Triển khai (Phases)

### Phase 1: Thử nghiệm 3D Boilerplate
- [ ] Cài đặt `three`, `@types/three`, `@react-three/fiber`, `@react-three/drei`.
- [ ] Tạo giao diện Canvas 3D cơ bản có trục tọa độ và lưới (GridHelper).

### Phase 2: Nâng cấp Solver sang 3.0 (3D)
- [ ] Cập nhật `backend/solver/engine.py` để xử lý thêm biến `z`.
- [ ] Viết unit test cho việc tính toán tọa độ hình chóp tứ giác đều.

### Phase 3: Hoàn thiện Tương tác
- [ ] Tích hợp `OrbitControls` để User có thể xoay trục.
- [ ] Hiển thị Label (nhãn tên điểm) luôn hướng về phía camera (Billboarding).

---

## 5. Lưu ý Kỹ thuật
- **Đơn vị (Units)**: Cần quy định 1 đơn vị toán học tương đương bao nhiêu đơn vị trong Three.js (Gợi ý: 1:1).
- **Hiệu năng**: Với các bài toán cực kỳ phức tạp (nhiều mặt), cần tối ưu hóa bằng cách dùng `BufferGeometry`.
- **Mobile**: Đảm bảo Touch events hoạt động tốt cho thao tác xoay trên điện thoại.
