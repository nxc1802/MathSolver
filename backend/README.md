# Visual Math Solver - Backend

Hệ thống xử lý AI và tính toán hình học.

## Phân hệ chính
- `app/`: FastAPI application.
- `agents/`: Multi-Agent System (Orchestrator, Parser, OCR...).
- `solver/`: Geometry DSL & Constraint Solver (SymPy).
- `renderer/`: Manim & Visualization engine.

## Cài đặt
1. Tạo môi trường ảo:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Hoặc venv\Scripts\activate trên Windows
   ```
2. Cài đặt thư viện:
   ```bash
   pip install -r requirements.txt
   ```

## Chạy ứng dụng
```bash
uvicorn app.main:app --reload
```
