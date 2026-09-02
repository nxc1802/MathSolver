Mục tiêu là chỉ ra **vấn đề hiện tại → kiến trúc nên có → code cần thay đổi → kết quả đạt được**.

---

# Tổng quan P0 → P4

Tôi xem đây là 5 tầng refactor liên tiếp:

```text
P0  Source of Truth
        ↓
P1  Job State Machine
        ↓
P2  Reliable Worker
        ↓
P3  Optimistic UI
        ↓
P4  Geometry Core Modularization
```

Thứ tự này quan trọng.

**Không nên làm P3 trước P0/P1**, vì nếu client optimistic nhưng backend state chưa có invariant rõ ràng thì bug sẽ khó debug hơn.

---

# P0 — Source of Truth

## Mục tiêu

Giải quyết câu hỏi:

> **"State nào mới là state thật?"**

Hiện MathSolver có nhiều tầng state:

```text
                    ┌──────────────┐
                    │  Supabase DB │
                    └──────┬───────┘
                           │
                  ┌────────▼────────┐
                  │ Backend Cache   │
                  └────────┬────────┘
                           │
                  ┌────────▼────────┐
                  │   API response  │
                  └────────┬────────┘
                           │
                  ┌────────▼────────┐
                  │      SWR        │
                  └────────┬────────┘
                           │
             ┌─────────────┼─────────────┐
             ▼             ▼             ▼
        React state   localStorage   sessionStorage
```

Vấn đề không phải mỗi thành phần này đều sai.

Vấn đề là **nhiều nơi có thể cùng được coi là source-of-truth**.

---

## 1. Quy định lại 3 loại state

### A. Server-authoritative state

Đây là state mà **DB quyết định**:

```text
sessions
messages
jobs
session_assets
geometry result
solution
video asset
```

Ví dụ:

```text
Session A tồn tại?
→ DB quyết định.

Message đã gửi chưa?
→ DB quyết định.

Job completed chưa?
→ DB quyết định.

Video nào là version mới nhất?
→ DB quyết định.
```

Frontend không được tự kết luận những thứ này là permanent state.

---

### B. Client state

Chỉ UI mới cần biết:

```text
sidebarOpen
sidebarWidth
selectedMessage
cameraPosition
zoom
activeTab
theme
```

Có thể lưu localStorage nếu muốn.

Ví dụ:

```text
localStorage
    └── sidebarWidth
```

hoàn toàn ổn.

---

### C. Ephemeral state

State tạm thời:

```text
uploading
optimistic message
temporary session
pending mutation
WebSocket connected
```

Không nên coi nó là persistent state.

---

# 2. Bỏ hoặc giảm Backend Session Cache

Code hiện tại có:

```python
session_owned_by_user(...)
invalidate_session_owner(...)
```

trong session API.

Ý tưởng cache ownership ban đầu hợp lý để tránh query DB lặp lại.

Nhưng với deployment nhiều worker:

```text
Worker A
  cache(session_1)

Worker B
  không có cache(session_1)
```

=> behavior không deterministic.

Tôi sẽ chuyển thành:

```text
DB
 ↑
API
 ↑
SWR
```

Nếu cần cache sau này:

```text
DB
 ↕
Redis
 ↕
API
```

**Không dùng process-local cache làm authoritative state.**

---

# 3. `sessions.updated_at`

Đây là một ví dụ rất điển hình của P0.

API đang list:

```python
.order("updated_at", desc=True)
```

Nhưng khi message mới được insert, cần đảm bảo:

```text
message INSERT
       ↓
sessions.updated_at = now()
```

Tốt nhất dùng DB trigger.

Như vậy:

```text
Message created
      ↓
DB transaction
      ↓
session.updated_at
      ↓
SWR revalidation
```

Frontend không cần tự nhớ:

> "À, gửi message thì phải update session timestamp."

---

# 4. P0 hoàn thành khi nào?

Bạn phải có một rule cực rõ:

> **Nếu reload browser, frontend phải reconstruct được toàn bộ persistent application state từ server.**

Tức là:

```text
F5
 ↓
GET sessions
 ↓
GET messages
 ↓
GET jobs/assets
 ↓
reconstruct UI
```

Không được xảy ra:

```text
F5
 ↓
mất geometry
 ↓
vì geometry chỉ nằm sessionStorage
```

hoặc:

```text
F5
 ↓
UI hiển thị job processing
 ↓
nhưng DB không biết job đó
```

---

# P1 — Job State Machine

Sau P0, giải quyết:

> **Một job trong MathSolver có vòng đời chính xác như thế nào?**

Hiện job có nhiều status:

```text
processing
rendering_queued
...
completed
error
```

Nhưng chưa được formalize thành một state machine thống nhất.

---

# 1. Định nghĩa state

Tôi đề xuất:

```text
CREATED
   │
   ▼
QUEUED
   │
   ▼
PROCESSING
   │
   ├── OCR
   ├── PARSING
   ├── GEOMETRY
   ├── SOLVING
   │
   ▼
COMPLETED
```

Failure:

```text
PROCESSING
    │
    ▼
FAILED
```

Partial:

```text
PROCESSING
    │
    ▼
DEGRADED
```

Cancellation:

```text
QUEUED / PROCESSING
        │
        ▼
    CANCELLED
```

---

# 2. Tách `status` và `stage`

Đây là điểm rất quan trọng.

Không nên nhét tất cả vào một field.

Ví dụ:

```json
{
  "status": "processing",
  "stage": "geometry",
  "progress": 62
}
```

thay vì:

```json
{
  "status": "geometry_processing"
}
```

Vì sau này:

```text
processing + OCR
processing + geometry
processing + solving
processing + rendering
```

sẽ khiến enum phình to.

---

# 3. Job nên có lifecycle

Ví dụ:

```json
{
  "id": "...",
  "session_id": "...",
  "user_id": "...",

  "status": "processing",
  "stage": "geometry",

  "created_at": "...",
  "started_at": "...",
  "completed_at": "...",

  "attempt": 1,
  "error_code": null
}
```

---

# 4. Transition phải hợp lệ

Ví dụ:

```text
QUEUED → PROCESSING       ✓
PROCESSING → COMPLETED    ✓
PROCESSING → FAILED       ✓

COMPLETED → PROCESSING    ✗
FAILED → COMPLETED        ✗
```

Nếu code gọi:

```python
set_status("completed")
```

thì backend phải kiểm tra current state.

---

# 5. WebSocket không phải source-of-truth

Đây là điểm rất quan trọng.

WebSocket chỉ là:

```text
notification channel
```

không phải:

```text
database
```

Ví dụ:

```text
DB:
job = completed

WebSocket:
message bị mất
```

Không sao.

Frontend reconnect:

```text
GET /jobs/{id}
       ↓
completed
```

=> UI tự recover.

Đây chính là lý do endpoint polling hiện tại rất quan trọng. Code hiện đã có fallback lấy job theo `job_id`.

---

# P2 — Reliable Worker

P1 xác định job state.

P2 giải quyết:

> **Ai thực sự chạy job?**

Hiện solve pipeline vẫn dùng:

```python
background_tasks.add_task(
    process_session_job,
    ...
)
```

Điều này tiện cho MVP.

Nhưng:

```text
FastAPI process
      ↓
BackgroundTasks
      ↓
process_session_job
```

có vấn đề:

```text
process crash
     ↓
job biến mất
     ↓
DB vẫn:
status = processing
```

---

# 1. Chuyển sang queue

Architecture:

```text
             FastAPI
                │
                │ enqueue
                ▼
             Redis
                │
        ┌───────┴───────┐
        ▼               ▼
   Worker #1        Worker #2
        │               │
        └───────┬───────┘
                ▼
             Supabase
```

Bạn đã có Redis/Celery trong architecture của project cho asynchronous work; P2 là đưa solve pipeline dài hơi vào cùng mô hình reliable worker đó thay vì dựa vào process-local BackgroundTasks.

---

# 2. API chỉ làm 3 việc

```text
POST /solve
      ↓
validate
      ↓
create job
      ↓
enqueue
      ↓
return job_id
```

Không:

```text
POST /solve
      ↓
LLM
      ↓
OCR
      ↓
geometry
      ↓
solver
      ↓
...
```

---

# 3. Worker làm toàn bộ computation

```text
worker(job_id)
     ↓
load job
     ↓
PROCESSING
     ↓
OCR
     ↓
PARSING
     ↓
GEOMETRY
     ↓
VALIDATION
     ↓
DEEP MATH
     ↓
persist result
     ↓
COMPLETED
```

Nếu worker chết:

```text
job remains QUEUED/PROCESSING
```

sau đó recovery mechanism có thể detect stale jobs.

---

# 4. Idempotency

Đây cực kỳ quan trọng.

Ví dụ:

```text
job 123
worker bắt đầu
 ↓
geometry completed
 ↓
worker crash trước khi mark completed
```

Job được retry.

Worker không được tạo:

```text
2 assistant messages
2 videos
2 geometry assets
```

Do đó cần:

```text
job_id = idempotency key
```

và database constraints.

---

# 5. P2 hoàn thành khi

Bạn có thể:

```text
kill worker
restart worker
```

mà job **không bị mất hoặc silently stuck**.

Đây mới là "production-grade".

---

# P3 — Optimistic UI

Sau P0–P2 mới làm P3.

Mục tiêu:

> **Frontend không cần chờ server cho những hành động mà user có thể thấy ngay.**

---

# Ví dụ Create Session

Hiện logic thiên về:

```text
click New Chat
      ↓
POST /sessions
      ↓
wait
      ↓
navigate
```

Latency:

```text
200–1000 ms
```

User cảm thấy UI chậm.

---

## Optimistic

```text
click
 ↓
create temporary session locally
 ↓
navigate immediately
 ↓
POST /sessions
 ↓
server returns real ID
 ↓
replace temporary ID
```

Ví dụ:

```text
temp_session_123
      ↓
server
      ↓
uuid_real_abc
```

Frontend reconcile:

```text
temp → real
```

---

# Ví dụ gửi message

Thay vì:

```text
send
 ↓
wait API
 ↓
show message
```

làm:

```text
send
 ↓
show message immediately
 ↓
status = sending
 ↓
API
 ↓
status = processing
 ↓
job result
```

UI:

```text
User:
"Cho tam giác ABC..."

             ✓ sending

             ↓

             ◌ processing

             ↓

Assistant:
...
```

---

# Nhưng optimistic UI phải có rollback

Ví dụ:

```text
User click Delete
 ↓
session biến mất ngay
 ↓
API DELETE
 ↓
500
```

phải:

```text
restore session
```

Không được:

```text
UI nghĩ đã delete
DB vẫn còn
```

---

# P3 architecture

Tôi muốn mutation có dạng:

```text
UI
 │
 ▼
optimistic mutation
 │
 ├──── success ────► reconcile
 │
 └──── failure ────► rollback
```

SWR rất phù hợp với pattern này.

---

# P4 — Geometry Core Modularization

Đây là P4 vì **không phải vấn đề cần fix gấp để production**.

Nó là vấn đề maintainability và research scalability.

Hiện solver package đã có:

```text
calculator.py
compiler.py
constructors.py
dsl_parser.py
engine.py
models.py
validator.py
vis_graph.py
vis_planner.py
```

Đây đã là một decomposition nhất định, nhưng `engine.py` vẫn đang gánh quá nhiều trách nhiệm.

---

# 1. Hiện tại

Conceptually:

```text
                 GeometryEngine
                       │
       ┌───────────────┼────────────────┐
       │               │                │
   constraints      solving         topology
       │               │                │
       └───────────────┼────────────────┘
                       │
                    result
```

---

# 2. Mục tiêu

Tách thành:

```text
                    GeometryPipeline
                           │
       ┌───────────────────┼──────────────────┐
       ▼                   ▼                  ▼
ConstraintCompiler   CoordinateSolver   CanonicalConstructor
       │                   │                  │
       └───────────────────┼──────────────────┘
                           ▼
                    GeometryNormalizer
                           │
                           ▼
                      TopologyBuilder
                           │
                           ▼
                    ResultAssembler
```

---

# 3. ConstraintCompiler

Input:

```text
DSL
```

Output:

```text
equations
constraints
variables
```

Ví dụ:

```text
AB = AC
```

→

```text
distance(A,B) - distance(A,C) = 0
```

---

# 4. CoordinateSolver

Chỉ chịu trách nhiệm:

```text
equations
 ↓
coordinates
```

Không cần biết rendering.

---

# 5. CanonicalConstructor

Xử lý:

```text
equilateral triangle
square
rectangle
cube
tetrahedron
...
```

Nếu geometry có construction rõ ràng:

```text
canonical constructor
```

thay vì generic symbolic solver.

Đây phù hợp với logic hiện tại, nơi engine đã ưu tiên standard geometry construction trước generic solving.

---

# 6. TopologyBuilder

Đây là phần tôi muốn đầu tư mạnh.

Input:

```text
coordinates
geometry objects
```

Output:

```text
vertices
edges
faces
adjacency
occlusion
visibility graph
```

Ví dụ cube:

```text
8 vertices
12 edges
6 faces
```

Sau đó renderer không cần tự suy luận.

---

# 7. GeometryNormalizer

Chuẩn hóa output:

```text
point naming
polygon ordering
coordinate frame
scale
orientation
degenerate objects
```

Điều này đặc biệt hữu ích cho 3D.

---

# 8. ResultAssembler

Cuối cùng tạo một canonical object:

```json
{
  "geometry": {...},
  "coordinates": {...},
  "topology": {...},
  "constraints": {...},
  "visualization_graph": {...},
  "validation": {...}
}
```

Sau đó:

```text
Three.js
Manim
GeoGebra
SVG
```

đều dùng **cùng một representation**.

---

# Tại sao P4 quan trọng cho MathSolver?

Bởi vì lúc đó architecture trở thành:

```text
                  LLM
                   │
                   ▼
              Geometry DSL
                   │
                   ▼
        ┌─────────────────────┐
        │ Geometry Compiler   │
        └──────────┬──────────┘
                   ▼
          Canonical Geometry IR
                   │
       ┌───────────┼────────────┐
       ▼           ▼            ▼
    Solver       2D/3D       Manim
```

Tôi gọi nó là **Geometry IR (Intermediate Representation)**.

Đây mới là architecture có giá trị dài hạn.

---

# Thứ tự triển khai tôi khuyên

Không nên:

```text
P0
P4
P3
P1
P2
```

Mà:

```text
             NOW
              │
              ▼
       ┌─────────────┐
       │     P0      │
       │ Source      │
       │ of Truth    │
       └──────┬──────┘
              ▼
       ┌─────────────┐
       │     P1      │
       │ Job State   │
       │ Machine     │
       └──────┬──────┘
              ▼
       ┌─────────────┐
       │     P2      │
       │ Reliable    │
       │ Worker      │
       └──────┬──────┘
              ▼
       ┌─────────────┐
       │     P3      │
       │ Optimistic  │
       │ UI          │
       └──────┬──────┘
              ▼
       ┌─────────────┐
       │     P4      │
       │ Geometry    │
       │ Modularize  │
       └─────────────┘
```

## Và mức độ ưu tiên thực tế:

| Phase  | Mục tiêu              |    Priority |     Rủi ro |
| ------ | --------------------- | ----------: | ---------: |
| **P0** | State consistency     | 🔴 Critical |        Cao |
| **P1** | Job lifecycle         | 🔴 Critical |        Cao |
| **P2** | Reliable worker       | 🔴 Critical |        Cao |
| **P3** | UX/optimistic         |     🟠 High | Trung bình |
| **P4** | Geometry architecture |   🟡 Medium |       Thấp |

### Quan trọng nhất:

**P0–P2 không phải "optimization".**

Chúng là việc biến MathSolver từ:

```text
"một hệ thống chạy tốt khi mọi thứ bình thường"
```

thành:

```text
"một distributed application có thể chịu được
reload, network failure, worker crash, duplicate request,
WebSocket disconnect và retry."
```

Còn **P3 là UX**, và **P4 là architectural investment cho tương lai của Geometry Engine**.

Nếu làm đúng P0→P4, kiến trúc cuối cùng sẽ rất sạch:

```text
                         ┌─────────────┐
                         │  Next.js    │
                         │     UI      │
                         └──────┬──────┘
                                │
                         SWR / WebSocket
                                │
                         ┌──────▼──────┐
                         │   FastAPI   │
                         │     API     │
                         └──────┬──────┘
                                │
                         enqueue job
                                │
                         ┌──────▼──────┐
                         │    Redis    │
                         └──────┬──────┘
                                │
                         ┌──────▼──────┐
                         │   Worker    │
                         └──────┬──────┘
                                │
                ┌───────────────┼───────────────┐
                ▼               ▼               ▼
              OCR        Geometry Engine    DeepMath
                                │
                                ▼
                       ┌────────────────┐
                       │ Geometry IR    │
                       └───────┬────────┘
                               │
                       ┌───────┼────────┐
                       ▼       ▼        ▼
                      2D      3D      Manim
                               │
                               ▼
                           Supabase
```

**Đây là target architecture mà tôi cho rằng hợp lý nhất cho codebase MathSolver hiện tại, và quan trọng là không cần rewrite project từ đầu.**
