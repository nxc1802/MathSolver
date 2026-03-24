
---

# 📐📷🎥 PROPOSAL DỰ ÁN (FINAL VERSION)

# **VISUAL MATH SOLVER v3.0**

### *Agent-based Geometry Reasoning & Visualization System*

---

# 1. 🎯 EXECUTIVE SUMMARY

Visual Math Solver v3.0 là một hệ thống AI có khả năng:

* Hiểu đề toán từ ảnh hoặc văn bản
* Phân tích cấu trúc toán học
* Lập luận chính xác
* **Tự động dựng hình từ đề bài**
* Trực quan hóa bằng hình vẽ + animation + video

---

## 🔥 Điểm đột phá

> Không chỉ “giải toán”
> → mà là **hiểu – dựng – kiểm chứng – trực quan hóa**

---

# 2. ❗ PROBLEM STATEMENT

## Thực trạng:

* AI hiện tại:

  * ❌ Không dựng được hình đúng
  * ❌ Không hiểu constraint hình học
  * ❌ Không có visualization chuẩn

---

## Gap công nghệ:

| Capability      | Hiện tại        |
| --------------- | --------------- |
| OCR toán        | ⚠️ chưa ổn định |
| Parse hình học  | ❌               |
| Dựng hình từ đề | ❌               |
| Animation       | ❌               |

---

# 3. 🧠 SOLUTION OVERVIEW

## Core Architecture:

```text
LLM (hiểu đề)
+ Symbolic Engine (đúng toán)
+ Geometry DSL (chuẩn hóa)
+ Rendering Engine (trực quan)
```

---

# 4. 🏗️ SYSTEM ARCHITECTURE (AGENT-BASED)

## 🎯 Tổng quan

```text
User Input
   ↓
🎯 Orchestrator Agent
   ↓
────────────────────────────
OCR Agent
Parser Agent
Knowledge Agent
Geometry Agent (DSL)
Constraint Solver Agent
Validation Agent
Rendering Agent
Animation Agent
────────────────────────────
   ↓
Output (solution + visualization + video)
```

---

# 5. 🧩 AGENT DESIGN (CHI TIẾT)

---

## 5.1 🎯 Orchestrator Agent

### Vai trò:

* Điều phối toàn bộ pipeline
* Retry / fallback
* Quản lý workflow

---

## 5.2 👁️ OCR Agent

### Công nghệ:

* Pix2Tex
* TrOCR

### Output:

```json
{
  "text": "...",
  "latex": "...",
  "confidence": 0.95
}
```

---

## 5.3 🧠 Parser Agent

### Vai trò:

* NLP + structure extraction
* Inspired từ InterGPS

### Output:

```json
{
  "objects": [...],
  "relations": [...],
  "constraints": [...]
}
```

---

## 5.4 📚 Knowledge Agent

### Chức năng:

* Cung cấp:

  * định lý
  * pattern
  * heuristic

---

## 5.5 📐 Geometry Agent

### Vai trò:

* Convert semantic → Geometry DSL

---

# 6. 🔥 GEOMETRY DSL (CORE)

## Mục tiêu:

* Chuẩn hóa toàn bộ logic hình học

---

## Ví dụ:

```dsl
POINT(A)
POINT(B)
POINT(C)

TRIANGLE(ABC)

LENGTH(AB, 5)
LENGTH(AC, 7)
ANGLE(A, 60deg)
```

---

## Đặc điểm:

* Declarative
* Deterministic
* Compile được

---

# 7. ⚙️ CONSTRAINT SOLVER LAYER

## Vai trò:

```text
DSL → equations → solve → coordinates
```

---

## Công nghệ:

* SymPy
* NumPy

---

## Output:

```json
{
  "A": [0,0],
  "B": [5,0],
  "C": [3.5,6.06]
}
```

---

# 8. ✅ VALIDATION LAYER

## Kiểm tra:

* Constraint hợp lệ?
* Không mâu thuẫn?
* Hình đúng đề?

---

## Ví dụ:

```text
AB + AC > BC
sum angles = 180°
```

---

## 🔁 Feedback loop:

```text
Validation fail → Geometry Agent → Solver → Retry
```

---

# 9. 🎨 RENDERING ENGINE

## Option:

### 1. GeoGebra

* MVP / preview

### 2. Manim

* Production

---

# 10. 🎬 ANIMATION ENGINE

## Features:

* Step-by-step drawing
* Highlight
* Explanation

---

## Có thể dùng:

* ManimAgentPrompts

---

# 11. 🔁 DATA FLOW (FINAL)

```text
Input (image/text)
   ↓
OCR Agent
   ↓
Parser Agent
   ↓
Geometry Agent → DSL
   ↓
Constraint Solver
   ↓
Validation
   ↺ (loop nếu fail)
   ↓
Rendering
   ↓
Animation
   ↓
Video Output
```

---

# 12. 🏗️ TECH STACK

## Backend:

* FastAPI
* Python

## Math:

* SymPy
* NumPy

## AI:

* LLM (MegaLLM)
* OCR (Local model)

## Rendering:

* Manim

## Frontend:

* Next.js
* Three.js

---
