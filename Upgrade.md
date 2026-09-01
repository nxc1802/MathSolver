Tôi đã audit trực tiếp branch `main` của [nxc1802/MathSolver](https://github.com/nxc1802/MathSolver?utm_source=chatgpt.com), tập trung vào **DB → cache → storage → SWR → optimistic UI → navigation/reload → job lifecycle**. Tôi cũng đối chiếu với kiến trúc dự án trong Proposal. Proposal định hướng PostgreSQL + Redis cache + S3/R2 storage, còn implementation hiện tại thực tế đang dùng **Supabase PostgreSQL + Supabase Storage + một lớp cache in-memory ở BE + SWR/localStorage/sessionStorage ở FE**. 

Điểm quan trọng nhất:

> **Vấn đề hiện tại không phải DB “yếu”, mà là hệ thống đang có quá nhiều nguồn state nhưng chưa có một source-of-truth và một cơ chế optimistic synchronization nhất quán.**

---

# 1. Đánh giá tổng thể MathSolver hiện tại

Từ commit mới nhất, project đã đi khá xa khỏi MVP ban đầu:

* AI Core + DeepMath solver
* Geometry DSL / compiler / validator
* canonical geometry
* 2D + 3D visualization
* topology graph
* Manim Agent external service
* WebSocket + polling fallback
* multi-session
* Supabase Auth
* Supabase Storage
* SWR
* client-side geometry cache
* persistent job tracking

Commit mới nhất ngày 31/08 còn bổ sung topological visualization và 3D solid occluder rendering.

Về mặt architecture, tôi đánh giá:

| Layer                      | Hiện tại                  | Đánh giá |
| -------------------------- | ------------------------- | -------: |
| Solver/Geometry            | khá mạnh                  |       🟢 |
| Job architecture           | khá tốt                   |       🟢 |
| WebSocket + polling        | tốt                       |       🟢 |
| DB schema                  | đủ dùng MVP               |       🟡 |
| Storage                    | hoạt động nhưng có vấn đề |       🟡 |
| BE cache                   | chưa production-grade     |       🟠 |
| FE state synchronization   | điểm yếu lớn              |       🔴 |
| Optimistic UI              | mới làm một phần          |       🟠 |
| Failure/reconciliation     | chưa thống nhất           |       🔴 |
| Multi-instance consistency | yếu                       |       🔴 |

Và chính phần 🔴 này đang tạo ra cảm giác:

> "Bấm action → web đứng chờ → đôi khi reload → state quay ngược lại."

---

# 2. DB hiện tại thực sự đang được thiết kế như thế nào?

DB core hiện tại gồm:

```text
auth.users
    │
    └── profiles

sessions
    │
    ├── messages
    ├── jobs
    └── session_assets

Storage
    ├── image
    └── video
```

Schema `sessions → messages/jobs/session_assets` là hợp lý. `messages`, `jobs`, `session_assets` đều reference `sessions` bằng FK với cascade delete.

Đặc biệt:

```text
sessions
  id
  user_id
  title
  created_at
  updated_at

messages
  id
  session_id
  role
  type
  content
  metadata
  created_at

jobs
  id
  user_id
  session_id
  status
  result
  ...

session_assets
  id
  session_id
  job_id
  asset_type
  storage_path
  public_url
  version
  created_at
```

### Đây là một schema hợp lý cho MathSolver.

Tôi **không khuyến nghị thay DB schema toàn bộ**.

Vấn đề nằm ở **cách application sử dụng DB**, không phải bản thân relational model.

---

# 3. Nhưng có một vấn đề DB rất đáng chú ý: `updated_at`

Bạn đang query session bằng:

```text
order("updated_at", desc=True)
```

nhưng trong code hiện tại, khi message mới được insert:

```text
messages.insert(...)
```

không thấy cơ chế cập nhật:

```text
sessions.updated_at
```

Trong `_enqueue_solve_common`, bạn insert message → job → sau đó chỉ update `title` nếu là message đầu tiên.

Điều này dẫn tới:

### Session list có thể không thực sự phản ánh "recently active".

Ví dụ:

```text
Session A created 10:00
Session B created 10:01

User quay lại A lúc 12:00
gửi thêm 5 câu
```

Nếu `updated_at` không được cập nhật:

```text
B
A
```

thay vì:

```text
A
B
```

### Tôi khuyến nghị xử lý bằng DB trigger.

Ví dụ conceptually:

```text
INSERT messages
        ↓
UPDATE sessions.updated_at = now()
```

và tương tự với job/session asset nếu cần.

**Không nên bắt FE tự update `updated_at`.**

Đây là state thuộc DB.

---

# 4. BE cache hiện tại là một điểm yếu lớn

`session_cache.py` hiện tại dùng:

```python
TTLCache(maxsize=512, ttl=45)
TTLCache(maxsize=4096, ttl=45)
```

cho:

* session list
* session ownership

Vấn đề lớn nhất:

## Đây là process-local cache.

Ví dụ:

```text
             ┌── Worker A
Request ─────┤
             └── Worker B
```

Worker A có:

```text
_session_list[user] = old data
```

Worker B có:

```text
_session_list[user] = new data
```

Hai process **không biết cache của nhau**.

Nếu deploy nhiều worker/container:

> Cache consistency không còn deterministic.

---

# 5. Cache này còn có một vấn đề khác: TTL 45 giây

Bạn đã có invalidate:

```text
create
delete
rename
```

điều này tốt. Nhưng chỉ invalidate **process đang nhận request**.

Nếu:

```text
POST /sessions
      ↓
Worker A
      ↓
DB updated
      ↓
invalidate Worker A
```

sau đó:

```text
GET /sessions
      ↓
Worker B
      ↓
cache HIT
      ↓
old sessions
```

FE sẽ thấy dữ liệu cũ.

Đây rất có thể là một trong những nguồn của cảm giác:

> "Server đã update rồi nhưng UI vẫn chưa update."

---

# 6. Tôi không nghĩ nên dùng BE `TTLCache` hiện tại cho session list nữa

Đây là một optimization hơi nguy hiểm so với lợi ích.

Query:

```sql
SELECT sessions
WHERE user_id = ?
ORDER BY updated_at DESC
```

trên index:

```text
idx_sessions_user_id
idx_sessions_updated_at
```

thực tế không phải workload quá nặng.

Trong khi cache này tạo thêm:

```text
DB state
     +
BE cache
     +
SWR cache
     +
localStorage
     +
sessionStorage
```

Tức là hiện tại bạn đang có **5 lớp state**.

Đối với MathSolver ở quy mô hiện tại:

> **Tôi sẽ bỏ BE session cache hoặc chuyển nó sang Redis nếu thực sự cần scale.**

Proposal ban đầu cũng định hướng Redis cho cache. 

---

# 7. FE hiện tại còn có nhiều cache/state hơn

Bạn đang có:

### SWR

```text
sessions
messages
assets
```

### sessionStorage

```text
sidebar width
main split
sidebar collapsed
geometry state
```

`session-ui-storage.ts` chỉ lưu UI layout, phần này hoàn toàn ổn.

### sessionStorage geometry

Lưu:

```text
coordinates
polygonOrder
drawingPhases
faces
solids
visualizationGraph
videoUrl
activeJobId
...
```

### localStorage job tracker

Lưu:

```text
sessionId
  ↓
jobId
timestamp
pendingQueue
```

### Supabase DB

Lưu:

```text
sessions
messages
jobs
session_assets
```

---

# 8. Đây chính là architectural problem lớn nhất

Bạn đang có:

```text
                 DB
                  ↑
                  │
             BE cache
                  ↑
                  │
             API response
                  ↑
                  │
              SWR cache
               /      \
              /        \
     localStorage   sessionStorage
```

Nhưng chưa có một quy tắc cực rõ:

> **State nào là authoritative?**

Tôi đề xuất:

```text
                SUPABASE DB
                SOURCE OF TRUTH
                     │
          ┌──────────┴──────────┐
          ↓                     ↓
      Server API           Storage
          │
          ↓
      SWR cache
          │
          ↓
      React UI
```

Còn:

```text
localStorage
sessionStorage
```

chỉ được phép chứa:

* UI preference
* transient draft
* recovery metadata
* client-only temporary state

**Không được trở thành authoritative state.**

---

# 9. Geometry cache hiện tại có nguy cơ "state ghost"

Đây là một điểm tôi đặc biệt chú ý.

Khi session thay đổi:

```text
loadGeometryState(sessionId)
```

và apply trực tiếp geometry từ sessionStorage.

Sau đó message DB mới được load.

Tức là timeline có thể là:

```text
t = 0
UI mở session

↓
load sessionStorage

UI:
Geometry v5

↓
SWR fetch DB

DB:
Geometry v4

↓
UI có thể bị overwrite
```

Hoặc ngược lại.

Đây chính là **stale state race**.

---

# 10. `job-tracker` cũng đang trộn hai concept

Hiện tại:

```text
mathsolver_active_jobs
```

vừa lưu:

```text
active job
```

vừa lưu:

```text
pending queue
```

Điều này không sai, nhưng:

```text
job
queue
```

thực chất là hai lifecycle khác nhau.

Tôi sẽ tách:

```text
active-job:{sessionId}
pending-queue:{sessionId}
```

hoặc tốt hơn:

```text
session recovery state
```

nhưng vẫn chỉ là **recovery state**, không phải DB state.

---

# 11. Một bug logic rất đáng chú ý trong active job

`getActiveJob()` coi job stale nếu:

```text
> 30 minutes
```

và xóa local record.

Nhưng DB job có thể vẫn:

```text
processing
```

hoặc:

```text
rendering
```

30 phút sau.

Khi user reload:

```text
localStorage
    ↓
job stale
    ↓
clear
    ↓
FE không attach
```

Trong khi:

```text
DB:
job vẫn running
```

Đây là một ví dụ điển hình của việc:

> client recovery metadata không được dùng làm source of truth.

---

# 12. Job system hiện tại thực ra khá tốt

Phần này tôi không muốn bạn sửa quá mạnh.

Hiện tại:

```text
POST /solve
    ↓
create DB job
    ↓
return job_id
    ↓
WebSocket
    ↓
fallback polling
```

và frontend còn có:

```text
saveActiveJob()
```

để reattach sau navigation/reload.

Đây là architecture đúng hướng.

Đặc biệt WebSocket failure → polling fallback:

```text
WS
 ↓ failure
poll every 1.5s
```

là hợp lý.

---

# 13. Nhưng có một vấn đề UX rất lớn: FE đang "chờ server" ở nhiều nơi không cần thiết

Bạn nói điều này là **hoàn toàn đúng**.

Ví dụ hiện tại create session:

```text
click Create
    ↓
POST /sessions
    ↓
await response
    ↓
mutate
    ↓
router.replace()
```

Trong khi UI có thể:

```text
click
 ↓
create temporary session
 ↓
navigate immediately
 ↓
POST server in background
 ↓
server success → replace temp ID with real ID
 ↓
server failure → rollback
```

Đây là **optimistic navigation**.

---

# 14. Delete session thì bạn đã làm đúng một nửa

Bạn đã có:

```text
Optimistic update
```

trước khi DELETE server hoàn thành.

Flow hiện tại:

```text
User click delete
       ↓
remove khỏi SWR
       ↓
navigate
       ↓
DELETE server
       ↓
failure?
       ↓
mutate()
```

Đây là hướng đúng.

Nhưng vẫn có một vấn đề:

### Navigation xảy ra trước khi transaction hoàn tất.

Ví dụ:

```text
Delete A
   ↓
UI remove A
   ↓
router.replace(B)
   ↓
DELETE A
   ↓
500
```

Sau đó:

```text
mutate()
```

có thể đưa A trở lại.

Đây không phải bug logic nghiêm trọng, nhưng UX sẽ là:

> A biến mất → một lúc sau tự xuất hiện.

---

# 15. Cách đúng hơn: Optimistic Mutation + Reconciliation

Không phải:

```text
wait server
→ update UI
```

mà:

```text
USER ACTION
     ↓
LOCAL OPTIMISTIC STATE
     ↓
UI responds immediately
     ↓
SERVER MUTATION
     ↓
 ┌───┴────┐
 ↓        ↓
SUCCESS  FAILURE
 ↓        ↓
commit   rollback
```

Đây chính là pattern bạn đang bắt đầu áp dụng, nhưng chưa áp dụng đồng bộ toàn app.

---

# 16. Những action nên optimistic

### Create session

Hiện tại:

```text
WAIT → create → navigate
```

Nên:

```text
create temp session
↓
UI insert ngay
↓
navigate ngay
↓
POST
↓
replace temp ID → real ID
```

---

### Delete session

Hiện tại đã gần đúng.

Nên:

```text
remove immediately
↓
DELETE
↓
success → nothing
failure → rollback
```

Không cần reload.

---

### Rename session

Nếu bổ sung rename:

```text
update title locally
↓
PATCH
↓
success → done
failure → restore old title
```

Không cần:

```text
PATCH
↓
GET /sessions
```

---

### Toggle sidebar

Đã optimistic hoàn toàn.

Không cần server.

---

### Resize layout

Đã optimistic hoàn toàn.

Không cần server.

---

# 17. Gửi message cũng đã optimistic

Bạn đã làm:

```text
mutateMessages(prev => [...prev, tempMessage])
```

rồi mới:

```text
startSolve()
```

Đây là đúng.

Nhưng thiếu một thứ:

## temporary message ID thật sự unique.

Hiện tại dùng:

```text
id: "temp"
```

Nếu user submit nhanh hoặc queue/retry:

```text
temp
temp
temp
```

Có nguy cơ React key/state reconciliation không đẹp.

Nên:

```text
clientMessageId = crypto.randomUUID()
```

và gửi ID đó lên server.

---

# 18. Đây cũng dẫn tới một cải tiến DB rất đáng làm

Cho `messages` thêm:

```text
client_message_id UUID
```

với unique constraint theo session:

```text
UNIQUE(session_id, client_message_id)
```

Khi đó:

```text
FE
 ↓
clientMessageId = abc
 ↓
POST
```

Nếu network timeout:

```text
FE không biết server đã nhận hay chưa
```

retry:

```text
POST same clientMessageId
```

DB sẽ đảm bảo:

```text
không tạo duplicate message
```

Đây gọi là **idempotency**.

Rất đáng có cho MathSolver.

---

# 19. Storage hiện tại có một vấn đề lớn hơn cache

Storage migration đang đặt:

```text
image bucket = public
video bucket = public
```

và có:

```text
Public read images
Public read videos
```

Điều đó có nghĩa:

> Nếu biết URL/path, asset có thể được đọc public.

Đối với một prototype thì tiện.

Đối với production:

**không nên.**

Đặc biệt bài toán học sinh upload có thể chứa:

* đề kiểm tra
* ảnh vở
* tài liệu cá nhân

Tôi sẽ chuyển sang:

```text
private bucket
```

và FE lấy:

```text
signed URL
```

hoặc proxy qua authenticated endpoint.

---

# 20. Storage còn có race condition về version

`upload_session_chat_image()` làm:

```text
SELECT max(version)
        ↓
version + 1
        ↓
upload
        ↓
INSERT session_assets
```

Nếu hai request đồng thời:

```text
Request A → max=5
Request B → max=5

A → v6
B → v6
```

Có thể xảy ra collision.

Nên version phải được generate **atomic ở DB**.

Ví dụ:

```text
(session_id, asset_type, version)
UNIQUE
```

và transaction / sequence logic.

---

# 21. Delete storage cũng chưa atomic

Delete session hiện tại:

```text
cleanup storage
↓
delete session_assets
↓
delete jobs
↓
delete messages
↓
delete session
```

Nhưng đây **không phải transaction**.

Ví dụ:

```text
storage deleted
↓
DB delete session_assets fails
↓
session vẫn tồn tại
```

hoặc:

```text
messages delete OK
jobs delete FAIL
session delete FAIL
```

Bạn sẽ có partial state.

Tuy nhiên:

> Storage không thể nằm trong PostgreSQL transaction.

Do đó nên thiết kế deletion thành **two-phase cleanup**:

```text
DB transaction
    ↓
mark session deleted
    ↓
delete DB rows
    ↓
enqueue storage cleanup
    ↓
delete objects
```

hoặc:

```text
soft-delete / deletion_pending
```

rồi worker xử lý storage.

---

# 22. Một điểm tôi đánh giá là khá nguy hiểm

Trong `delete_session()`:

```text
cleanup_session_storage()
```

được thực hiện **trước** DB deletion.

Nếu storage cleanup thành công nhưng DB deletion thất bại:

```text
DB:
session exists

Storage:
assets gone
```

=> broken references.

Ngược lại thì ít nguy hiểm hơn.

Tôi sẽ đảo lifecycle thành:

```text
DB authoritative deletion
        ↓
storage cleanup async
```

---

# 23. Về "web bị reload"

Từ code tôi kiểm tra được, tôi **chưa thấy một `window.location.reload()` rõ ràng** trong repo hiện tại.

Các navigation chính đang là:

```text
router.replace()
router.push()
```

chứ không phải hard reload. Ví dụ session navigation dùng `router.replace()`.

Do đó nếu bạn thấy:

> "web reload"

thì cần phân biệt:

### A. Hard browser reload

```text
GET /
JS bundle tải lại
React mount lại
```

### B. Next.js route transition

```text
/chat/A
    ↓
router.replace(/chat/B)
```

UI component remount/re-render nhưng **không phải browser reload**.

### C. Auth context remount

`AuthProvider` có `useEffect` phụ thuộc:

```text
router
pathname
```

và có auth state listener.

Có thể tạo cảm giác toàn app bị reset trong một số auth transitions.

---

# 24. Tôi nghi vấn lớn hơn nằm ở navigation + state rehydration

Ví dụ:

```text
Delete current session
       ↓
router.replace(next)
       ↓
ChatSessionPage remount
       ↓
loadGeometryState(next)
       ↓
SWR fetch messages(next)
       ↓
apply snapshot
       ↓
job hook attach
```

Rất nhiều lifecycle chạy đồng thời.

Nếu một trong các nguồn:

```text
sessionStorage
SWR
DB
job tracker
WebSocket
```

có state cũ, UI có thể nhảy.

Đây rất có thể là thứ bạn đang cảm nhận là:

> "web reload rồi quay lại trạng thái cũ."

---

# 25. Tôi đề xuất thay toàn bộ philosophy FE thành:

## Server State

Dùng:

```text
SWR
```

cho:

```text
sessions
messages
assets
job state
```

## Client State

Dùng:

```text
React/Zustand
```

cho:

```text
input
modal
dragging
OCR flow
UI
```

## Persistence

Chỉ:

```text
localStorage
sessionStorage
```

cho:

```text
UI preferences
draft
job recovery
```

Không dùng persistence để làm source of truth.

---

# 26. Kiến trúc tôi muốn MathSolver chuyển sang

```text
                    ┌───────────────┐
                    │   Supabase    │
                    │  PostgreSQL   │
                    └───────┬───────┘
                            │
                     SOURCE OF TRUTH
                            │
               ┌────────────┴────────────┐
               │                         │
          REST API                  Storage
               │
               ↓
        ┌──────────────┐
        │     SWR      │
        │ Server State │
        └──────┬───────┘
               │
        Optimistic Layer
               │
               ↓
        ┌──────────────┐
        │ React State  │
        └──────────────┘
```

Job:

```text
DB job
  │
  ├── WebSocket
  │
  └── Poll fallback
       ↓
      SWR
       ↓
      UI
```

Cache:

```text
             Redis
               │
       optional BE cache
               │
        NEVER authoritative
```

---

# 27. Những thứ tôi sẽ sửa theo Priority

## P0 — sửa ngay

### 1. Xác định DB là Source of Truth

Không để:

```text
sessionStorage geometry
localStorage job
SWR
BE TTLCache
```

ghi đè lẫn nhau một cách implicit.

---

### 2. Chuẩn hóa optimistic mutation

Áp dụng cho:

```text
create session
delete session
rename session
send message
create render job
```

Pattern:

```text
optimistic
→ request
→ commit
→ rollback
```

---

### 3. Không reload để đồng bộ state

Không dùng:

```text
window.location.reload()
```

hoặc workaround tương đương.

Dùng:

```text
SWR mutate()
```

---

### 4. Loại bỏ BE `TTLCache` session list

Hoặc chuyển sang Redis nếu benchmark chứng minh cần.

Hiện tại:

```text
TTLCache 45s
```

tạo consistency problem nhiều hơn giá trị nó mang lại.

---

## P1 — sửa tiếp

### 5. `sessions.updated_at` phải tự động update

DB trigger:

```text
message/job activity
       ↓
sessions.updated_at = now()
```

---

### 6. Thêm `client_message_id`

Để đảm bảo:

```text
retry ≠ duplicate
```

---

### 7. Tách job recovery khỏi pending queue

```text
active_job
pending_queue
```

---

### 8. Job recovery phải hỏi DB

Không:

```text
localStorage says no job
→ assume no job
```

Mà:

```text
localStorage
   ↓
candidate job ID

DB
   ↓
verify actual status
```

---

## P2 — production hardening

### 9. Private Storage

```text
public bucket ❌
private bucket + signed URL ✅
```

---

### 10. Atomic asset version

```text
UNIQUE(session_id, asset_type, version)
```

---

### 11. Async storage deletion

Không để delete session phụ thuộc vào việc storage cleanup hoàn thành.

---

# 28. Một vấn đề nữa: `create session` hiện tại có thể tối ưu UX rất mạnh

Hiện tại:

```text
Click
 ↓
POST
 ↓
await
 ↓
mutate
 ↓
router.replace
```

Tôi sẽ đổi thành:

```text
Click
 ↓
generate temp-session-id
 ↓
insert optimistic session
 ↓
router.replace(/chat/temp-xxx)
 ↓
POST /sessions
 ↓
real session returned
 ↓
replace temp → real
```

Người dùng gần như cảm thấy:

> **0 latency.**

Trong khi server vẫn đảm bảo persistence.

Nếu POST fail:

```text
temp session → error
↓
rollback
```

Không cần reload.

---

# 29. Delete cũng có thể hoàn thiện thành UX "instant"

```text
click delete
 ↓
remove immediately
 ↓
navigate immediately
 ↓
DELETE server
```

Nếu thành công:

```text
done
```

Nếu thất bại:

```text
rollback session
toast:
"Không thể xoá bài toán. Dữ liệu đã được khôi phục."
```

Không reload.

---

# 30. Quan trọng nhất: đừng "fix cache" bằng cách thêm cache

Tôi đặc biệt khuyên **không** làm:

```text
SWR stale
→ thêm localStorage
→ stale
→ thêm Redis
→ thêm invalidate
→ thêm refresh
```

Bạn sẽ tạo một distributed-state mess.

Thay vào đó:

```text
DB = truth

SWR = server-state cache

React = UI state

local/sessionStorage = recovery/preferences

Redis = performance optimization only
```

Ranh giới phải cực kỳ rõ.

---

# 31. Đánh giá cuối cùng

Tôi đánh giá MathSolver hiện tại về mặt core architecture khoảng:

**8/10 cho một research/product prototype.**

Nhưng UX state architecture chỉ khoảng:

**5.5–6/10.**

Không phải vì code FE tệ — thực tế bạn đã có khá nhiều cơ chế đúng như SWR, optimistic delete, job recovery, WebSocket fallback.

Vấn đề là các cơ chế đó được thêm vào **theo từng bug/problem**, dẫn tới hiện tại:

```text
SWR
+
sessionStorage
+
localStorage
+
BE TTL cache
+
Supabase
+
WebSocket
+
polling
```

nhưng chưa có **state consistency model** thống nhất.

### Và tôi cho rằng đây chính là bottleneck tiếp theo của MathSolver.

Không nên tiếp tục tối ưu Geometry/Manim/LLM trước khi giải quyết lớp này. Core solver hiện đã tương đối mature; commit history cho thấy các phần geometry/validator/Manim đang được cải thiện liên tục.

**Thứ tự tôi sẽ làm:**

```text
P0
│
├── Source of Truth
├── Optimistic UI
├── Rollback
├── SWR reconciliation
└── eliminate accidental reload

P1
│
├── updated_at trigger
├── idempotency
├── job recovery
└── remove BE TTLCache

P2
│
├── private storage
├── atomic asset version
└── async deletion
```

Nếu làm đúng P0, cảm giác sử dụng MathSolver sẽ thay đổi rất rõ: **click action → UI phản ứng ngay**, server chạy phía sau; chỉ khi server thất bại mới rollback. Đây chính xác là mô hình bạn mô tả trong câu hỏi, và **đó cũng là hướng kiến trúc tôi khuyến nghị cho repo hiện tại**, thay vì tiếp tục dùng reload/refetch để ép FE quay về trạng thái DB.
