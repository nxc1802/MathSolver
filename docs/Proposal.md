# 📐📷🎥 PROPOSAL DỰ ÁN

## **VISUAL MATH SOLVER**

**Hệ thống giải toán bằng OCR + AI Reasoning + Trực quan hóa 2D/3D & Video**

---

## 1. TÓM TẮT DỰ ÁN (EXECUTIVE SUMMARY)

Visual Math Solver là một hệ thống AI giải toán thế hệ mới, tập trung vào **hiểu đề toán từ hình ảnh**, **lập luận toán học chính xác**, và **trực quan hóa quá trình giải bằng hình vẽ 2D/3D và video animation**.

Dự án giải quyết trực tiếp hạn chế lớn của các mô hình AI hiện tại (ChatGPT, Gemini):

> **không thể trực quan hóa hình học một cách chính xác, từng bước, có tính giáo dục.**

Hệ thống sử dụng:

* **Math OCR chuyên dụng** (Pix2Tex + TrOCR)
* **LLM suy luận qua MegaLLM API** (DeepSeek-R1, GPT-4, Claude)
* **Geometry Engine độc lập** (SymPy + Custom Engine)
* **Renderer & Animation Engine** (Manim + Three.js)

👉 Mục tiêu cuối:

> **Không chỉ cho đáp án – mà dạy cách làm, cách vẽ, cách suy luận.**

---

## 2. VẤN ĐỀ & ĐỘNG LỰC (PROBLEM STATEMENT)

### 2.1 Thực trạng

* Học sinh gặp khó khăn với:

  * Toán hình (thiếu trực quan)
  * Oxyz, hình không gian
* Ứng dụng AI hiện tại:

  * Chỉ trả lời bằng chữ
  * Vẽ hình "tưởng tượng"
  * Không có animation hoặc video

### 2.2 Khoảng trống công nghệ

| Tiêu chí            | Công cụ hiện tại |
| ------------------- | ---------------- |
| OCR toán            | ❌ Không ổn định  |
| Hiểu cấu trúc đề    | ❌                |
| Vẽ hình chính xác   | ❌                |
| Trực quan từng bước | ❌                |
| Video giải toán     | ❌                |

👉 **Chưa có hệ thống nào kết hợp đầy đủ: OCR + Reasoning + Geometry + Animation**

---

## 3. MỤC TIÊU DỰ ÁN

### 3.1 Mục tiêu chính

Xây dựng một hệ thống có khả năng:

1. Nhận đề toán từ ảnh
2. Hiểu cấu trúc toán học
3. Giải toán bằng lập luận AI
4. Vẽ hình 2D / 3D chính xác
5. Tạo animation & video hướng dẫn

### 3.2 Mục tiêu cụ thể

* Hỗ trợ:

  * Toán THCS – THPT
  * Đại số, hình phẳng, Oxyz
* Output:

  * Lời giải từng bước
  * Hình vẽ động
  * Video hướng dẫn

### 3.3 KPIs (Chỉ số đo lường)

| Metric | Mục tiêu |
|--------|----------|
| OCR Accuracy | ≥ 95% |
| Solution Accuracy | ≥ 90% |
| Geometry Rendering Accuracy | ≥ 98% |
| Video Generation Time | < 30s |
| User Satisfaction | ≥ 4.5/5 |

---

## 4. PHẠM VI & ĐỐI TƯỢNG

### 4.1 Đối tượng sử dụng

* Học sinh THCS, THPT
* Sinh viên kỹ thuật
* Giáo viên
* Nền tảng EdTech

### 4.2 Phạm vi bài toán

| Dạng             | Hỗ trợ |
| ---------------- | ------ |
| Đại số           | ✅      |
| Hình phẳng       | ✅      |
| Hình không gian  | ✅      |
| Oxyz             | ✅      |
| Bài toán có hình | ✅      |

---

## 5. KIẾN TRÚC HỆ THỐNG

### 5.1 Tổng quan kiến trúc

```
┌─────────────────────────────────────────────────────────────┐
│                      CLIENT LAYER                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │   Web App   │  │ Mobile App  │  │   API SDK   │         │
│  │  (Next.js)  │  │  (Flutter)  │  │  (Python)   │         │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘         │
└─────────┼────────────────┼────────────────┼─────────────────┘
          │                │                │
          ▼                ▼                ▼
┌─────────────────────────────────────────────────────────────┐
│                      API GATEWAY                            │
│              (FastAPI + Rate Limiting + Auth)               │
└─────────────────────────┬───────────────────────────────────┘
                          │
          ┌───────────────┼───────────────┐
          ▼               ▼               ▼
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│  Math OCR   │  │  Problem    │  │  Reasoning  │
│   Engine    │  │   Parser    │  │   Engine    │
│ (Pix2Tex +  │  │  (Custom)   │  │ (MegaLLM)   │
│   TrOCR)    │  │             │  │             │
└──────┬──────┘  └──────┬──────┘  └──────┬──────┘
       │                │                │
       └────────────────┼────────────────┘
                        ▼
          ┌─────────────────────────┐
          │   Geometry & Algebra    │
          │        Engine           │
          │   (SymPy + Custom)      │
          └───────────┬─────────────┘
                      ▼
          ┌─────────────────────────┐
          │  Rendering & Animation  │
          │        Engine           │
          │  (Manim + Three.js)     │
          └───────────┬─────────────┘
                      ▼
          ┌─────────────────────────┐
          │      Video Storage      │
          │     (S3 / Cloudflare)   │
          └─────────────────────────┘
```

### 5.2 Data Flow

```
Image Input → OCR → Structured Text → Problem Parser → JSON Schema
                                                          │
                                                          ▼
                                    Reasoning LLM ← Problem Context
                                          │
                                          ▼
                            Solution Steps + Geometry DSL
                                          │
                                          ▼
                              Geometry Engine (Validate)
                                          │
                                          ▼
                              Renderer → Animation → Video
```

---

## 6. CÁC MODULE CHI TIẾT

### 6.1 Math OCR Engine

* **Chức năng:**
  * Nhận diện chữ, công thức, ký hiệu toán
  * Phát hiện hình vẽ
  * Xử lý tiếng Việt

* **Công nghệ:**
  * **Pix2Tex** - OCR công thức LaTeX
  * **TrOCR** - OCR text đa ngôn ngữ
  * **YOLOv8** - Phát hiện vùng hình vẽ

* **Output:**

```json
{
  "text": "Cho tam giác ABC có AB = 5, AC = 7, góc A = 60°",
  "latex": "AB = 5, AC = 7, \\angle A = 60^{\\circ}",
  "diagram_detected": true,
  "diagram_bbox": [100, 50, 300, 250],
  "confidence": 0.95
}
```

---

### 6.2 Problem Parser

* Chuyển đề toán → cấu trúc logic
* Tách:

  * Đối tượng hình học
  * Quan hệ
  * Yêu cầu

* **Output Schema:**

```json
{
  "problem_type": "geometry_2d",
  "objects": [
    {"type": "triangle", "name": "ABC"},
    {"type": "segment", "name": "AB", "length": 5},
    {"type": "segment", "name": "AC", "length": 7},
    {"type": "angle", "name": "A", "value": 60, "unit": "degree"}
  ],
  "relations": [
    {"type": "vertex_of", "subject": "A", "object": "ABC"}
  ],
  "requirements": [
    {"action": "calculate", "target": "BC"},
    {"action": "calculate", "target": "area_ABC"}
  ]
}
```

---

### 6.3 Reasoning Engine (LLM via MegaLLM API)

* **API Provider: MegaLLM**
  * Unified API Gateway cho 70+ LLMs
  * OpenAI-compatible API
  * Hỗ trợ: DeepSeek-R1, GPT-4, Claude, Gemini

* **Configuration:**

```python
# MegaLLM API Integration
import openai

client = openai.OpenAI(
    api_key="YOUR_MEGALLM_API_KEY",
    base_url="https://api.megallm.io/v1"
)

# Sử dụng DeepSeek-R1 cho reasoning
response = client.chat.completions.create(
    model="deepseek-r1",  # hoặc "deepseek-chat", "gpt-4", "claude-3"
    messages=[
        {"role": "system", "content": MATH_SOLVER_PROMPT},
        {"role": "user", "content": problem_json}
    ],
    temperature=0.1,
    max_tokens=4096
)
```

* **Vai trò:**
  * Lập luận toán học
  * Chia bước giải
  * Sinh chỉ dẫn vẽ hình (Geometry DSL)

* **⚠️ Không dùng để vẽ hoặc tính số** → Geometry Engine xử lý

* **Model Selection Strategy:**

| Task | Primary Model | Fallback |
|------|--------------|----------|
| Math Reasoning | DeepSeek-R1 | GPT-4 |
| Text Understanding | Claude-3 | GPT-4 |
| Code Generation | DeepSeek-Coder | GPT-4 |

---

### 6.4 Geometry DSL (Domain Specific Language)

* **Mục đích:** LLM sinh ra lệnh vẽ chuẩn hóa, Geometry Engine thực thi

* **DSL Specification:**

```yaml
# Geometry DSL v1.0

# Định nghĩa điểm
POINT(name, x, y)           # 2D
POINT3D(name, x, y, z)      # 3D

# Định nghĩa đoạn thẳng
SEGMENT(name, point1, point2)
LINE(name, point1, point2)  # Đường thẳng vô hạn

# Định nghĩa hình
TRIANGLE(name, A, B, C)
CIRCLE(name, center, radius)
POLYGON(name, [points...])

# Định nghĩa góc
ANGLE(name, point1, vertex, point2)
MARK_ANGLE(angle_name, value)

# Hành động vẽ
DRAW(object_name, style?)
HIGHLIGHT(object_name, color)
LABEL(object_name, text, position?)

# Animation
ANIMATE_DRAW(object_name, duration)
ANIMATE_TRANSFORM(object, from, to, duration)
STEP(description)  # Đánh dấu bước giải
```

* **Ví dụ Output từ LLM:**

```dsl
# Bước 1: Vẽ tam giác ABC
POINT(A, 0, 0)
POINT(B, 5, 0)
POINT(C, 3.5, 6.06)  # Tính từ cosine rule
TRIANGLE(ABC, A, B, C)

STEP("Vẽ tam giác ABC với AB = 5, AC = 7, góc A = 60°")
ANIMATE_DRAW(ABC, 2s)

# Bước 2: Tính BC bằng định lý cosine
SEGMENT(BC, B, C)
LABEL(BC, "BC = 6.24", "middle")
HIGHLIGHT(BC, "red")
STEP("Áp dụng định lý cosine: BC² = AB² + AC² - 2·AB·AC·cos(A)")
```

---

### 6.5 Geometry & Algebra Engine

* **Xử lý chính xác:**

  * Hình học 2D (Euclidean)
  * Hình học 3D / Oxyz
  * Đại số / Phương trình

* **Công nghệ:**

  * **SymPy** - Symbolic math
  * **NumPy** - Numerical computation
  * **Custom Geometry Engine** - Constraint solving

* **Tính toán deterministic** - không phụ thuộc LLM

* **API Interface:**

```python
class GeometryEngine:
    def parse_dsl(self, dsl_code: str) -> GeometryScene
    def validate(self, scene: GeometryScene) -> ValidationResult
    def compute(self, scene: GeometryScene) -> ComputedScene
    def to_render_commands(self, scene: ComputedScene) -> RenderCommands
```

---

### 6.6 Rendering & Animation Engine

* **2D Rendering:**
  * SVG generation
  * Canvas rendering
  * Manim (Python animation)

* **3D Rendering:**
  * Three.js (WebGL)
  * Manim 3D

* **Animation:**
  * Step-by-step construction
  * Smooth transitions
  * Highlighting & annotations

* **Video Output:**
  * MP4 (H.264)
  * GIF (preview)
  * WebM (web optimized)

* **Performance Targets:**

| Output Type | Target Time |
|-------------|-------------|
| Static 2D | < 1s |
| Static 3D | < 2s |
| Animation (30s) | < 15s |
| Full Video | < 30s |

---

## 7. TECH STACK

### 7.1 Backend

| Component | Technology |
|-----------|------------|
| API Framework | FastAPI (Python 3.11+) |
| LLM Integration | MegaLLM API (OpenAI-compatible) |
| Math Engine | SymPy + NumPy |
| OCR | Pix2Tex + TrOCR |
| Animation | Manim |
| Task Queue | Celery + Redis |
| Database | PostgreSQL + pgvector |
| Cache | Redis |
| Storage | S3 / Cloudflare R2 |

### 7.2 Frontend

| Component | Technology |
|-----------|------------|
| Web App | Next.js 14 (React) |
| 3D Rendering | Three.js |
| State Management | Zustand |
| Styling | TailwindCSS |
| Mobile | Flutter (future) |

### 7.3 Infrastructure

| Component | Technology |
|-----------|------------|
| Container | Docker |
| Orchestration | Kubernetes |
| CI/CD | GitHub Actions |
| Monitoring | Prometheus + Grafana |
| Logging | ELK Stack |

---

## 8. ĐIỂM KHÁC BIỆT (INNOVATION)

| Tiêu chí  | Chatbot AI | Visual Math Solver |
| --------- | ---------- | ------------------ |
| Giải toán | ✅ | ✅ |
| Hiểu hình | ❌ | ✅ |
| Vẽ đúng   | ❌ | ✅ |
| Animation | ❌ | ✅ |
| Video     | ❌ | ✅ |
| Giáo dục  | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| Deterministic | ❌ | ✅ |

👉 **Không phải chatbot – mà là Math Visualization System**

### Core Innovations:

1. **Hybrid Architecture**: LLM (reasoning) + Symbolic Engine (computation) = Best of both worlds
2. **Geometry DSL**: Standardized language for geometry instructions
3. **Step-by-step Visualization**: Educational animation, not just answers
4. **Multi-modal Input**: Text + Image + Handwriting

---

## 9. ROADMAP TRIỂN KHAI

### Phase 1 – MVP (2–3 tháng)

| Week | Milestone |
|------|-----------|
| 1-2 | Project setup, API skeleton |
| 3-4 | Math OCR integration |
| 5-6 | Problem Parser + Basic LLM |
| 7-8 | 2D Geometry rendering |
| 9-10 | Basic animation |
| 11-12 | MVP testing & demo |

**Deliverables:**
* OCR toán hoạt động
* Giải toán chữ cơ bản
* Hình vẽ tĩnh 2D

### Phase 2 – Visualization (3–4 tháng)

| Week | Milestone |
|------|-----------|
| 1-4 | Geometry DSL v1.0 |
| 5-8 | Step-by-step animation |
| 9-12 | Interactive UI |
| 13-16 | Video generation pipeline |

**Deliverables:**
* Geometry DSL hoàn chỉnh
* Animation từng bước
* Video MP4 output
* Web UI tương tác

### Phase 3 – Advanced (3–5 tháng)

| Week | Milestone |
|------|-----------|
| 1-6 | 3D Geometry Engine |
| 7-12 | Oxyz coordinate system |
| 13-16 | Mobile app |
| 17-20 | Performance optimization |

**Deliverables:**
* 3D Geometry hoàn chỉnh
* Oxyz visualization
* Mobile app (Flutter)
* Production-ready system

---

## 10. NHÂN SỰ & NGUỒN LỰC

### 10.1 Nhân sự (4–6 người)

| Vai trò | Số lượng | Trách nhiệm |
| ------- | -------- | ----------- |
| AI/ML Engineer | 1-2 | OCR, LLM integration, Geometry Engine |
| Backend Engineer | 1-2 | API, Infrastructure, Video pipeline |
| Frontend Engineer | 1 | Web app, 3D visualization |
| Math Expert | 1 | Problem design, validation, DSL spec |

### 10.2 Hạ tầng & Chi phí

| Resource | Specification | Est. Cost/month |
|----------|--------------|-----------------|
| GPU Server | A100 40GB hoặc RTX 4090 | $200-500 |
| MegaLLM API | ~1M tokens/day | $100-300 |
| Cloud Storage | 1TB S3/R2 | $20-50 |
| Database | PostgreSQL managed | $50-100 |
| CDN | Video delivery | $50-100 |
| **Total** | | **$420-1050/month** |

### 10.3 Development Tools

* Version Control: GitHub
* Project Management: Linear / Notion
* Communication: Discord / Slack
* Documentation: Notion / GitBook

---

## 11. RỦI RO & GIẢI PHÁP

| Rủi ro | Xác suất | Tác động | Giải pháp |
| ------ | -------- | -------- | --------- |
| OCR sai | Cao | Trung bình | Human-in-the-loop, confidence threshold |
| LLM hallucination | Cao | Cao | Geometry engine validation, multi-model verification |
| Hình vẽ sai | Trung bình | Cao | Constraint solver, visual validation |
| API downtime | Thấp | Cao | Multi-provider fallback (MegaLLM hỗ trợ 70+ models) |
| Video render chậm | Trung bình | Trung bình | Queue system, caching, pre-rendering |
| Scale issues | Trung bình | Cao | Kubernetes auto-scaling, CDN |

---

## 12. DATASET & BENCHMARK

### 12.1 Training Data

| Dataset | Size | Purpose |
|---------|------|---------|
| Math problems (THCS) | 10,000+ | Problem parsing |
| Math problems (THPT) | 15,000+ | Reasoning validation |
| Geometry diagrams | 5,000+ | OCR + Diagram detection |
| Step-by-step solutions | 3,000+ | Animation template |

### 12.2 Benchmark Suite

```
benchmark/
├── ocr/
│   ├── printed_formulas/     # 500 test cases
│   ├── handwritten/          # 300 test cases
│   └── mixed_text_formula/   # 200 test cases
├── reasoning/
│   ├── algebra/              # 400 test cases
│   ├── geometry_2d/          # 500 test cases
│   └── geometry_3d/          # 300 test cases
└── visualization/
    ├── static_render/        # 200 test cases
    └── animation/            # 100 test cases
```

### 12.3 Evaluation Metrics

| Module | Metric | Formula |
|--------|--------|---------|
| OCR | Character Error Rate | CER = (S + D + I) / N |
| Parser | Structure Match | F1-score |
| Reasoning | Solution Correctness | Exact match % |
| Geometry | Render Accuracy | IoU with ground truth |
| Animation | Step Coverage | % steps correctly animated |

---

## 13. API SPECIFICATION

### 13.1 Endpoints

```yaml
# Core APIs
POST /api/v1/solve
  - Input: image (file) or text (string)
  - Output: solution JSON + video URL

GET /api/v1/solution/{id}
  - Get solution status and results

POST /api/v1/render
  - Input: Geometry DSL
  - Output: SVG/Image/Video

# Health & Status
GET /api/v1/health
GET /api/v1/models
```

### 13.2 Response Format

```json
{
  "id": "sol_abc123",
  "status": "completed",
  "problem": {
    "text": "...",
    "type": "geometry_2d"
  },
  "solution": {
    "steps": [...],
    "answer": "BC = 6.24"
  },
  "visualization": {
    "static_image": "https://...",
    "animation_gif": "https://...",
    "video_mp4": "https://..."
  },
  "metadata": {
    "model": "deepseek-r1",
    "processing_time_ms": 2500
  }
}
```

---

## 14. KẾT LUẬN

Visual Math Solver hướng tới:

* Chuẩn hóa cách AI giải toán
* Biến AI thành **giáo viên trực quan**
* Đặt nền móng cho EdTech thế hệ mới

> **AI không chỉ trả lời – AI phải biết vẽ, biết dạy, biết giải thích.**

### Next Steps:

1. ✅ Finalize proposal & get approval
2. 🔲 Setup development environment
3. 🔲 Begin Phase 1 development
4. 🔲 Weekly progress reviews

---

*Document Version: 2.0*
*Last Updated: 2026-01-10*
*Author: Visual Math Solver Team*