# Đặc tả Agent (Agent Specifications)

Hệ thống **Visual Math Solver v3.0** được chia thành các Agent với vai trò riêng biệt, tối ưu hóa quá trình từ đọc hiểu bài toán đến xuất đồ họa hình học.

## 1. Orchestrator Agent
- **Vai trò**: Điểm Pivot trung tâm, thiết lập Workflow và điều hướng luồng dữ liệu. Xử lý các logic Retry / Phục hồi / Fallback errors.
- **Trách nhiệm**: Tiếp nhận cấu trúc JSON từ Agent hiện tại và feed sang Agent tiếp theo đúng định dạng. Đảm bảo toàn bộ kiến trúc chạy xuyên suốt từ bài toán -> Video output.

## 2. OCR Agent
- **Công nghệ**: `Pix2Tex`, `TrOCR`.
- **Vai trò**: Nếu người dùng cấp hình ảnh, Agent dùng OCR đọc văn bản và công thức Toán (định dạng LaTeX).
- **Output Standard**:
```json
{
  "text": "Cho tam giác ABC...",
  "latex": "Cho $\\triangle ABC$...",
  "confidence": 0.95
}
```

## 3. Parser Agent
- **Công nghệ**: NLP / LLM extraction (Lấy cảm hứng từ InterGPS).
- **Vai trò**: Dịch đoạn văn bản tự nhiên thành cấu trúc dữ liệu JSON để máy tính dễ parse, bóc tách Entity (các đối tượng hình học) và Relational Constraints (Các ràng buộc).
- **Output Standard**:
```json
{
  "objects": ["Point A", "Point B", "Point C", "Triangle ABC"],
  "relations": ["A connects B", "B connects C", "C connects A"],
  "constraints": ["AB = 5", "AC = 7", "Angle A = 60deg"]
}
```

## 4. Knowledge Agent
- **Vai trò**: Kho dữ liệu và Logic Resolver trung gian.
- **Chức năng**: Cung cấp định lý, bổ đề, pattern giải nhanh để Parser/Geometry Agent nội suy các tính chất hình học còn thiếu (Ví dụ: Từ `Tam giác đều` => bổ sung tự động góc = 60 độ và 3 cạnh bằng nhau).

## 5. Geometry Agent
- **Vai trò**: Nhận bộ JSON bóc tách từ Parser Agent, chuẩn hóa nó thành cấu trúc script mã lệnh theo **Geometry DSL** tiêu chuẩn, làm input cho Solver.

## 6. Constraint Solver & Validation Agent
- **Constraint Solver**: Sử dụng SymPy, nhận DSL và giải cứu bằng lập phương trình, thiết lập hệ tọa độ Euclid (x, y) cho từng điểm ảnh.
- **Validation Agent**: Kiểm định hình học (Ví dụ tổng 3 góc tam giác, độ dài không hợp lý). Nếu Validation báo lỗi -> Vòng lập báo lại cho Solver hoặc Geometry Agent để Retry/Update lại thông số.
