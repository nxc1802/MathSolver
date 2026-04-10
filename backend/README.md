---
title: Math Solver Backend
emoji: 📐
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
---

# Visual Math Solver - Backend (Hugging Face Space)

Hệ thống AI giải toán hình học sử dụng Multi-Agent và Manim. Hiện đã nâng cấp lên phiên bản **v5.1**.

## Tính năng mới (v5.1)
- **Symbolic Solver**: Tích hợp SymPy để tự động hóa việc tính toán các giá trị hình học (diện tích, chu vi, độ dài) với độ chính xác tuyệt đối và trình bày các bước giải chi tiết.
- **3D Video Support**: Nâng cấp công cụ Manim để hỗ trợ hiển thị và xoay camera cho các bài toán hình học không gian (Hình chóp, Hình lăng trụ, v.v.).

## Kiến trúc Pipeline (Agentic Flow)
1. **OCR Agent**: Nhận diện văn bản từ hình ảnh câu hỏi.
2. **Parser Agent**: Chuyển đổi ngôn ngữ tự nhiên thành Geometry DSL.
3. **Knowledge Agent**: Bổ sung kiến thức chuyên sâu về hình học.
4. **Geometry Engine**: Giải hệ phương trình tọa độ để dựng hình.
5. **Solver Agent (New)**: Thực hiện các phép tính toán học hình thức (Symbolic Math).
6. **Renderer Agent**: Sinh mã Manim và render video (hỗ trợ cả 2D và 3D).

## Triển khai
Space này chạy Docker container chứa FastAPI và môi trường Manim. Để chạy cục bộ, tham khảo `setup.sh` và `.env.example`.
