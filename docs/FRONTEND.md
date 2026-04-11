# MathSolver Frontend — Tài liệu kỹ thuật toàn diện

> **Phiên bản**: v5.1 (phiên bản codebase) / Next.js 16.2.1  
> **Ngôn ngữ**: TypeScript 5 + React 19  
> **Styling**: TailwindCSS 4 + CSS Custom Properties  
> **Cập nhật lần cuối**: 2026-04-11

---

## Mục lục

1. [Tổng quan kiến trúc](#1-tổng-quan-kiến-trúc)
2. [Công nghệ & Dependencies](#2-công-nghệ--dependencies)
3. [Cấu trúc thư mục](#3-cấu-trúc-thư-mục)
4. [Cấu hình & Môi trường](#4-cấu-hình--môi-trường)
5. [Hệ thống Design](#5-hệ-thống-design)
6. [Pages (App Router)](#6-pages-app-router)
7. [Components](#7-components)
8. [Thư viện Utility (`/lib`)](#8-thư-viện-utility-lib)
9. [Hệ thống Type (`/types`)](#9-hệ-thống-type-types)
10. [Luồng dữ liệu & State Management](#10-luồng-dữ-liệu--state-management)
11. [Xác thực (Authentication)](#11-xác-thực-authentication)
12. [Giao tiếp với Backend API](#12-giao-tiếp-với-backend-api)
13. [Tính năng 3D (v5.0+)](#13-tính-năng-3d-v50)
14. [Tính năng Symbolic Solver UI (v5.1)](#14-tính-năng-symbolic-solver-ui-v51)
15. [Hệ thống Queuing & Job Tracking](#15-hệ-thống-queuing--job-tracking)
16. [Persistence & Local Storage](#16-persistence--local-storage)
17. [Chạy cục bộ (Local Development)](#17-chạy-cục-bộ-local-development)
18. [Build & Deploy](#18-build--deploy)

---

## 1. Tổng quan kiến trúc

MathSolver Frontend là một **Single-Page Application (SPA)** được xây dựng theo mô hình **App Router của Next.js 16**. Kiến trúc tổng thể là giao diện chat `3-pannel split`:

```
┌──────────────────────────────────────────────────────────┐
│  [Sidebar - Lịch sử] │ [Chat Panel] │ [Visualization]   │
│    SessionList,User   │  Messages,   │  StaticCanvas2D /  │
│    Settings, Logo     │  Input Box   │  Interactive3D /   │
│                       │              │  AnimationPreview  │
└──────────────────────────────────────────────────────────┘
```

**Luồng xử lý chính:**
1. Người dùng nhập đề toán (text hoặc ảnh OCR)
2. Frontend gửi request `POST /api/v1/sessions/{id}/solve`
3. Backend trả về `job_id`, Frontend theo dõi qua **WebSocket** (fallback: polling)
4. Khi job hoàn thành, kết quả được cập nhật: tọa độ, solution steps, video URL
5. UI tự động hiển thị Canvas **2D** (SVG) hoặc **3D** (Three.js) tùy thuộc vào metadata `is_3d`

---

## 2. Công nghệ & Dependencies

### Runtime Dependencies

| Package | Phiên bản | Mục đích |
|---|---|---|
| `next` | 16.2.1 | Framework chính (App Router, SSR) |
| `react` | 19.2.4 | UI library |
| `react-dom` | 19.2.4 | DOM renderer |
| `@supabase/supabase-js` | ^2.101.0 | Xác thực (Auth) và truy vấn DB |
| `swr` | ^2.4.1 | Data fetching & cache (stale-while-revalidate) |
| `framer-motion` | ^12.38.0 | Animation & transitions |
| `three` | ^0.183.2 | Rendering 3D geometry |
| `@react-three/fiber` | ^9.5.0 | React wrapper cho Three.js |
| `@react-three/drei` | ^10.7.7 | Helper components cho R3F |
| `react-markdown` | ^10.1.0 | Render Markdown trong chat |
| `remark-math` | ^6.0.0 | Parse LaTeX trong Markdown |
| `rehype-katex` | ^7.0.1 | Render công thức LaTeX bằng KaTeX |
| `remark-gfm` | ^4.0.1 | GitHub Flavored Markdown tables, etc. |
| `lucide-react` | ^1.7.0 | Icon library |
| `clsx` | ^2.1.1 | Conditional class helper |
| `tailwind-merge` | ^3.5.0 | Merge TailwindCSS class conflicts |

### Dev Dependencies

| Package | Phiên bản | Mục đích |
|---|---|---|
| `tailwindcss` | ^4 | CSS framework |
| `typescript` | ^5 | Type safety |
| `eslint` | ^9 | Linting |
| `@types/react` | ^19 | Type definitions cho React |

---

## 3. Cấu trúc thư mục

```
frontend/
├── app/                          # Next.js App Router
│   ├── layout.tsx                # Root layout: Font, AuthProvider, SWRProvider
│   ├── page.tsx                  # Index page: redirect to latest session
│   ├── globals.css               # CSS design system, KaTeX import
│   ├── login/
│   │   └── page.tsx              # Trang đăng nhập (Email/Google/Github)
│   └── chat/
│       └── [sessionId]/
│           └── page.tsx          # Màn hình chat chính (800+ dòng)
│
├── components/                   # React components tái sử dụng
│   ├── ChatMessage.tsx           # Bubble message: text, DSL, status, solution
│   ├── ChatSidebar.tsx           # Sidebar: logo, user, collapse toggle
│   ├── SessionList.tsx           # Danh sách sessions, tạo/xóa
│   ├── StaticGeometryCanvas.tsx  # Canvas 2D SVG với zoom/pan
│   ├── Interactive3DCanvas.tsx   # Canvas 3D Three.js với OrbitControls [NEW v5.0]
│   ├── AnimationPreview.tsx      # Player video Manim
│   ├── VersionSwitcher.tsx       # Điều hướng các phiên bản hình vẽ
│   ├── SettingsModal.tsx         # Modal cài đặt (theme dark/light)
│   ├── SolverForm.tsx            # Form nhập đề toán (legacy, không dùng trong chat)
│   ├── StatusStepper.tsx         # Thanh tiến trình pipeline (OCR→Parser→Solver→Render)
│   ├── ResultCard.tsx            # Card hiển thị kết quả với nút copy
│   └── Header.tsx                # Header cũ (legacy, không dùng trong chat)
│
├── lib/                          # Utility & business logic
│   ├── api-config.ts             # URL API base & WebSocket base config
│   ├── auth-context.tsx          # React Context cho Supabase Auth
│   ├── chat-messages.ts          # Normalizer: raw API data → ChatMessage type
│   ├── job-tracker.ts            # localStorage: theo dõi job đang chạy
│   ├── session-geometry-cache.ts # sessionStorage: cache tọa độ hình học
│   ├── session-ui-storage.ts     # sessionStorage: trạng thái UI (split %)
│   ├── supabase.ts               # Supabase client instance
│   └── swr-provider.tsx          # SWR global config provider
│
├── types/
│   └── chat.ts                   # TypeScript types cho ChatMessage, ChatSession
│
├── public/                       # Static assets
├── .env                          # Biến môi trường local
├── next.config.ts                # Next.js config (custom Cache-Control)
├── tsconfig.json                 # TypeScript config
└── package.json                  # Dependencies & scripts
```

---

## 4. Cấu hình & Môi trường

### File `.env` (local)

```bash
NEXT_PUBLIC_API_URL="http://localhost:7860"       # REST API endpoint
NEXT_PUBLIC_WS_URL="ws://localhost:7860"          # WebSocket endpoint (optional)
NEXT_PUBLIC_SUPABASE_URL="https://..."            # Supabase project URL
NEXT_PUBLIC_SUPABASE_ANON_KEY="eyJ..."           # Supabase anon key
```

> **Lưu ý**: Tất cả biến bắt đầu bằng `NEXT_PUBLIC_` sẽ được expose ra client-side bundle.

### `next.config.ts`

Cấu hình duy nhất hiện tại là thêm header `Cache-Control` dài hạn cho static assets của Next.js (`/_next/static/*`) để tối ưu hiệu suất.

```typescript
const nextConfig: NextConfig = {
  async headers() {
    return [
      {
        source: "/_next/static/:path*",
        headers: [{ key: "Cache-Control", value: "public, max-age=31536000, immutable" }],
      },
    ];
  },
};
```

---

## 5. Hệ thống Design

### Design Language

MathSolver sử dụng phong cách **Dark Glassmorphism** với:
- Màu nền cực tối (`#0a0a0f`)
- Borders mờ dần (`rgba(255,255,255,0.05)`)
- Glassmorphism panels (`backdrop-filter: blur`)
- Gradient accent `indigo-to-purple` (`#6366f1` → `#9333ea`)

### CSS Custom Properties (Design Tokens)

Định nghĩa trong `app/globals.css`:

```css
:root {
  --background: #0a0a0f;          /* Màu nền toàn trang */
  --bg-secondary: #08080d;        /* Màu nền phụ */
  --foreground: #ffffff;          /* Màu chữ chính */
  --card-bg: #0c0c14;             /* Nền card/sidebar */
  --panel-bg: rgba(12,12,20,0.4); /* Nền panel với glassmorphism */
  --border: rgba(255,255,255,0.05); /* Border mờ */
  --text-primary: #ffffff;
  --text-secondary: #a1a1aa;
  --text-muted: #71717a;
  --input-bg: rgba(24,24,27,0.8);
  --scrollbar-thumb: rgba(255,255,255,0.08);
  --msg-bot: rgba(24,24,27,0.6);  /* Nền bubble bot */
  --msg-user: rgba(59,130,246,0.15); /* Nền bubble user */
}
```

Hỗ trợ **Light Mode** thông qua `[data-theme='light']` selector. Người dùng chuyển qua `SettingsModal` và giá trị được lưu vào `localStorage.mathsolver-theme`.

### Typography

- Font chính: **Inter** (Google Fonts), fallback `system-ui`
- Font mono: **Geist Mono** (Next.js font)
- Sử dụng `font-family: 'Inter'` ở `body`

### Utility Classes

```css
.glass        /* Glassmorphism base */
.text-gradient /* indigo-to-purple text gradient */
.scrollbar-thin /* 4px custom scrollbar */
```

### KaTeX

CSS của KaTeX được import trực tiếp qua CDN trong `globals.css`:

```css
@import url('https://cdn.jsdelivr.net/npm/katex@0.16.8/dist/katex.min.css');
```

---

## 6. Pages (App Router)

### `app/layout.tsx` — Root Layout

Wrapper toàn ứng dụng. Chứa:
- Load font **Geist Sans** và **Geist Mono** từ Google Fonts
- SEO metadata (`title`, `description`)
- Wraps toàn bộ app trong `<AuthProvider>` và `<SWRProvider>`
- Set `lang="vi"` (tiếng Việt), `class="dark"` (dark mode mặc định)

```tsx
<AuthProvider>
  <SWRProvider>{children}</SWRProvider>
</AuthProvider>
```

---

### `app/page.tsx` — Index (Redirect) Page

**Vai trò**: Điểm vào sau đăng nhập. Không hiển thị UI, chỉ điều hướng.

**Logic**:
1. Chờ `useAuth()` load xong
2. Nếu chưa đăng nhập → redirect `/login`
3. Gọi `GET /api/v1/sessions` để lấy danh sách session
4. Nếu có session → redirect `/chat/{sessions[0].id}` (mới nhất)
5. Nếu không có → gọi `POST /api/v1/sessions` tạo mới rồi redirect

**Error handling**: Hiển thị trang lỗi với nút "Thử lại" và "Đăng xuất" nếu không kết nối được backend.

---

### `app/login/page.tsx` — Login Page

Trang đăng nhập. Hỗ trợ 3 phương thức:

1. **Email + Password**: Gọi `supabase.auth.signInWithPassword()` hoặc `supabase.auth.signUp()`
2. **Google OAuth**: `supabase.auth.signInWithOAuth({ provider: 'google' })`
3. **GitHub OAuth**: `supabase.auth.signInWithOAuth({ provider: 'github' })`

Design: Dark card với gradient background orbs, tab Đăng nhập/Đăng ký.

---

### `app/chat/[sessionId]/page.tsx` — Main Chat Page

**File quan trọng nhất**, ~863 dòng. Quản lý toàn bộ trải nghiệm giải toán.

#### Layout 3-panel (resizable)

- **Panel trái**: Sidebar (chiều rộng điều chỉnh, có thể collapse thành icon-only)
- **Panel giữa**: Chat messages + Input box
- **Panel phải**: Visualization (Canvas 2D/3D hoặc Video)

Kéo dividers (`cursor-col-resize`) để thay đổi tỷ lệ. Trạng thái split được lưu vào `sessionStorage`.

#### State quan trọng

| State | Kiểu | Mô tả |
|---|---|---|
| `inputText` | `string` | Nội dung ô nhập |
| `solveLoading` | `boolean` | Đang chờ kết quả |
| `currentStatus` | `string \| null` | Trạng thái job hiện tại |
| `coordinates` | `Record<string, [number,number] \| [number,number,number]> \| null` | Tọa độ điểm |
| `is3d` | `boolean` | Tự động detect 2D/3D |
| `polygonOrder` | `string[] \| null` | Thứ tự vẽ đa giác |
| `circles` | `Array \| null` | Danh sách đường tròn |
| `lines` | `Array \| null` | Đường thẳng (vô hạn) |
| `rays` | `Array \| null` | Tia |
| `drawingPhases` | `Array \| null` | Giai đoạn vẽ (base/auxiliary) |
| `videoUrl` | `string \| null` | URL video Manim |
| `pendingQueue` | `{ id, text }[]` | Hàng đợi câu hỏi |
| `videoVersion` | `number` | Index phiên bản hình vẽ hiện tại |
| `splitPercent` | `number` | % chiều rộng sidebar |
| `mainSplitPercent` | `number` | % chat vs visualization |

#### Quá trình gửi và nhận kết quả (`handleSolve`)

```
User clicks Send
    → POST /api/v1/sessions/{id}/solve
    → Nhận job_id
    → attachToJob(job_id):
        ├── Mở WebSocket ws://.../ws/{job_id}
        │   └── onmessage: cập nhật trạng thái + kết quả
        └── Fallback polling (1s interval): GET /api/v1/solve/{job_id}
    → Khi status === "success": finishSolveFlow()
        └── mutateMessages() + clearActiveJob() + xử lý pendingQueue
```

#### 3D/2D Auto-Switch Logic

```typescript
const hasZ = Object.values(newCoords).some(
  (c: any) => Array.isArray(c) && c.length === 3 && c[2] !== 0
);
setIs3d(r.is_3d || hasZ);
```

Sau đó trong JSX:
```tsx
{is3d ? (
  <Interactive3DCanvas coordinates={coordinates} drawingPhases={drawingPhases} />
) : (
  <StaticGeometryCanvas coordinates={...} polygonOrder={...} ... />
)}
```

#### Version Switching (Lịch sử hình vẽ)

`geometrySnapshots` là tập hợp tất cả messages `assistant` có `metadata.coordinates`. Người dùng điều hướng qua `VersionSwitcher` để xem lại hình vẽ của các câu hỏi trước.

---

## 7. Components

### `ChatMessage.tsx`

**Render bubble message trong chat**. Hỗ trợ 6 loại message:

| `message.type` | Hiển thị |
|---|---|
| `"status"` | Spinner + trạng thái pipeline |
| `"error"` | Icon lỗi + nội dung đỏ |
| `"analysis"` | Icon BrainCircuit + Markdown với KaTeX |
| `"dsl"` | Code block Geometry DSL (monospace) |
| `"coordinates"` | Thông báo "Đã tính tọa độ 2D/3D — xem bên phải" |
| `"text"` | Nội dung chính với 4 sub-sections |

**Sub-sections của type `"text"`**:
1. `semantic_analysis` — Phân tích ngữ nghĩa từ AI (collapse nhỏ)
2. Nội dung chính (full Markdown + KaTeX)
3. `solution` (v5.1) — Kết quả giải toán với accordion "Xem các bước giải chi tiết"
4. `image_url` / `video_url` — Media inline trong bubble

**Accordion steps** (Framer Motion):
```tsx
<AnimatePresence>
  {showSteps && (
    <motion.div initial={{ height: 0 }} animate={{ height: "auto" }} exit={{ height: 0 }}>
      {steps.map((step) => <ReactMarkdown ...>{step}</ReactMarkdown>)}
    </motion.div>
  )}
</AnimatePresence>
```

---

### `ChatSidebar.tsx`

Sidebar trái. 2 chế độ:
- **Full mode** (`compact=false`): Logo + version, SessionList, footer user info + Settings
- **Compact mode** (`compact=true`): Icon-only rail (52px), thu gọn khi người dùng kéo sidebar quá nhỏ

Render `SettingsModal` khi nhấn nút gear.

---

### `SessionList.tsx`

Danh sách các session chat với **Optimistic UI**:

- **Tạo session**: Tạo temp session local → navigate ngay → gọi API → replace với real session
- **Xóa session**: Xóa khỏi list ngay → gọi API → rollback nếu lỗi
- **Delete confirm**: Click lần 1 → hiện confirm, click lần 2 → xóa thật
- **Compact mode**: Chỉ hiện icon `MessageSquare`, tooltip là title

---

### `StaticGeometryCanvas.tsx`

**Canvas 2D** sử dụng SVG với tính năng zoom/pan:

**Input props**:
- `coordinates`: Mapping tên điểm → `[x, y]`
- `polygonOrder`: Thứ tự nối điểm thành đa giác
- `circles`: Danh sách đường tròn `{ center: string, radius: number }`
- `lines`: Đường thẳng (vô hạn hai chiều)
- `rays`: Tia (bắt đầu từ điểm, kéo dài về một phía)
- `drawingPhases`: Chia rendering thành phase 1 (đường cơ bản, solid) và phase 2+ (đường phụ, dashed)

**Tính năng**:
- Tự động tính `viewBox` từ tọa độ
- Y-axis inversion (hệ tọa độ toán học vs SVG)
- Zoom: `Ctrl+Scroll` hoặc nút +/-
- Pan: Kéo chuột trái
- Reset view button

**Rendering SVG**:
- Điểm: `<circle>` + `<text>` label
- Cạnh: `<path>` với `strokeDasharray` cho dashed
- Đường tròn: `<circle>` dashed
- Infinite lines/rays: Extend tọa độ × 2000

---

### `Interactive3DCanvas.tsx` *(NEW - v5.0)*

**Canvas 3D** sử dụng **React Three Fiber** và **Three.js**:

**Sub-components**:
- `Point`: Sphere mesh + Billboard HTML label (tự xoay theo camera)
- `Segments`: Render từng cặp điểm thành `Line` objects
- `Line`: `THREE.Line` với `LineBasicMaterial` (solid) hoặc `LineDashedMaterial` (dashed)

**Scene setup** (bên trong `<Canvas>`):
- `PerspectiveCamera` tại vị trí `[8, 8, 8]`, FOV 45°
- `OrbitControls` với damping (xoay mượt), min/max distance
- `Stars` background (2000 sao, radius 100)
- `Grid` vô hạn (chìm dưới geometry)
- `THREE.AxesHelper` màu RGB (X=đỏ, Y=xanh lá, Z=xanh dương)
- Lighting: ambient + point + spot

**Hệ tọa độ**: Mapping từ hệ toán học `(x, y, z)` sang Three.js `(x, z_math, -y)` vì Three.js dùng Y-up.

```typescript
position: [coords[0], coords[2] || 0, -coords[1]]
```

**HUD**:
- Badge "3D Interactive Mode" (top-left)
- Reset View button (top-right)
- Hint "Xoay để quan sát • Cuộn để thu phóng" (bottom-left, hiện khi hover)

---

### `AnimationPreview.tsx`

Player video Manim. 2 trạng thái:
- **Loading** (`loading=true`): Spinner + mô tả "Đang dựng animation..."
- **Video có URL**: `<video>` với autoplay + loop + controls
- **Empty** (không URL, không loading): Placeholder "Chưa có animation"

Nhúng `VersionSwitcher` ở góc dưới video để điều hướng phiên bản.

---

### `VersionSwitcher.tsx`

Điều hướng lịch sử hình vẽ. Chỉ hiện khi `totalVersions > 1`. Cấu trúc: `History icon | Version 2/3 | [◀] [▶]`.

Props: `currentVersion`, `totalVersions`, `onPrev`, `onNext`.

---

### `SettingsModal.tsx`

Modal cài đặt với backdrop blur. Hiện tại chỉ có tab **Giao diện**:
- Chọn Dark/Light theme với visual preview
- Toggle Animations (UI only, chưa có logic)
- Lưu theme vào `localStorage.mathsolver-theme` và apply qua `document.documentElement.setAttribute("data-theme", ...)`

---

### `SolverForm.tsx` *(Legacy)*

Form nhập đề cũ, không được dùng trong chat session page hiện tại. Vẫn tồn tại nhưng standalone. Chứa:
- Textarea nhập đề
- Upload OCR (gọi `POST /api/v1/ocr`)
- Toggle "Tạo Video Animation"
- Submit button với shimmer effect

---

### `StatusStepper.tsx` *(Legacy)*

Thanh tiến trình 4 bước: OCR → Parser → Solver → Render. Không dùng trong chat, chỉ là component độc lập.

---

### `ResultCard.tsx` *(Legacy)*

Card kết quả với code block và nút copy. Không dùng trong chat.

---

### `Header.tsx` *(Legacy)*

Header cũ với logo và nav links. Không dùng trong chat (sidebar thay thế).

---

## 8. Thư viện Utility (`/lib`)

### `api-config.ts`

Cung cấp base URL cho REST API và WebSocket:

```typescript
export function getApiBaseUrl(): string {
  return process.env.NEXT_PUBLIC_API_URL?.trim() || "http://localhost:7860";
}

export function getWsBaseUrl(): string {
  // Từ NEXT_PUBLIC_WS_URL hoặc tự suy ra từ API URL (ws:// vs wss://)
}
```

---

### `auth-context.tsx`

React Context bọc toàn bộ app. Cung cấp:
- `user: User | null` — Supabase user object
- `session: Session | null` — Supabase session (contains `access_token`)
- `loading: boolean` — Trạng thái init
- `signOut()` — Đăng xuất
- `signInWithGoogle()` — OAuth redirect
- `signInWithGithub()` — OAuth redirect

**Dev Bypass** (chỉ khi `NODE_ENV === 'development'`):
Nếu Supabase không có session, tự động tạo mock session với `access_token = "Test user-123"`. Backend có `ALLOW_TEST_BYPASS=true` sẽ chấp nhận token này.

**Safety Timeout**: Force `loading=false` sau 5 giây nếu Supabase không phản hồi.

---

### `chat-messages.ts`

Normalizer chuyển đổi raw API response sang `ChatMessage` type:

**`messageFromApi(m)`**: Map từ snake_case API fields sang camelCase ts types.

**`normalizeMessageMetadata(raw)`**: Validate và extract tất cả metadata fields:
- `coordinates`, `polygon_order`, `circles`, `drawing_phases`, `lines`, `rays`
- `is_3d` (boolean), `solution` (object - v5.1)
- `video_url` / `videoUrl` (backward compatible)
- `job_id` / `jobId` (backward compatible)

---

### `job-tracker.ts`

Sử dụng `localStorage` để persist trạng thái giải toán khi người dùng switch session hoặc reload trang.

**Storage key**: `"mathsolver_active_jobs"` → `Record<sessionId, ActiveJob>`

**Interface**:
```typescript
interface ActiveJob {
  jobId: string;
  timestamp: number;
  pendingQueue?: { id: string; text: string }[];
}
```

**Functions**:
- `saveActiveJob(sessionId, jobId)` — Lưu job đang chạy
- `getActiveJob(sessionId)` — Lấy (null nếu stale > 30 phút)
- `clearActiveJob(sessionId)` — Xóa khi job done
- `savePendingQueue(sessionId, queue)` — Lưu hàng đợi câu hỏi
- `getPendingQueue(sessionId)` — Lấy hàng đợi
- `clearPendingQueue(sessionId)` — Xóa hàng đợi

---

### `session-geometry-cache.ts`

Sử dụng `sessionStorage` để cache tọa độ hình học cho từng session.

**Interface `GeometryState`**:
```typescript
{
  coordinates: Record<string, [number,number] | [number,number,number]> | null;
  polygonOrder: string[] | null;
  circles: Array<{ center: string; radius: number }> | null;
  drawingPhases: Array<{ phase, label, points, segments }> | null;
  lines: Array<[string, string]> | null;
  rays: Array<[string, string]> | null;
  videoUrl: string | null;
  activeJobId: string | null;
  is3d?: boolean;
}
```

**Functions**: `saveGeometryState`, `loadGeometryState`, `clearGeometryState`

---

### `session-ui-storage.ts`

Lưu trạng thái UI (kích thước panels) vào `sessionStorage`:

| Key | Mô tả | Range |
|---|---|---|
| `mathsolver-split-percent` | % chiều rộng sidebar | 7% - 50% |
| `mathsolver-main-split-percent` | % chat vs visualization | 20% - 80% |
| `mathsolver-sidebar-collapsed` | Sidebar thu gọn | `"1"` / `"0"` |

---

### `supabase.ts`

Singleton Supabase client:

```typescript
export const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY
);
```

---

### `swr-provider.tsx`

SWR global config:
- `revalidateOnFocus: false` — Không refetch khi tab re-focus
- `revalidateOnReconnect: true` — Refetch khi kết nối mạng trở lại
- `dedupingInterval: 8000` — Dedup requests trong 8 giây
- `errorRetryCount: 2` — Thử lại tối đa 2 lần khi lỗi

---

## 9. Hệ thống Type (`/types`)

### `types/chat.ts`

```typescript
type MessageRole = 'user' | 'assistant' | 'system';

type MessageType =
  | 'text'       // Nội dung chính, phân tích, giải thích
  | 'status'     // Trạng thái pipeline  
  | 'dsl'        // Geometry DSL code
  | 'analysis'   // Phân tích ngữ nghĩa (deprecated, xài metadata.semantic_analysis)
  | 'error'      // Lỗi
  | 'coordinates'// Thông báo tọa độ đã tính xong
  | 'quiz'       // (reserved)
  | 'hint'       // (reserved)
  | 'step_solution'; // (reserved)

interface ChatMessage {
  id: string;
  role: MessageRole;
  type: MessageType;
  content: string;
  timestamp: number;
  metadata?: {
    coordinates?: Record<string, [number, number] | [number, number, number]>;
    semantic_analysis?: string;
    polygon_order?: string[];
    circles?: Array<{ center: string; radius: number }>;
    drawing_phases?: Array<{ phase, label, points, segments }>;
    lines?: Array<[string, string]>;
    rays?: Array<[string, string]>;
    solution?: {              // v5.1 Symbolic Solver
      answer: string;
      steps: string[];
      symbolic_math?: Record<string, string>;
    };
    is_3d?: boolean;          // v5.0 3D flag
    video_url?: string;
    videoUrl?: string;        // @deprecated
    job_id?: string;
    jobId?: string;           // @deprecated
    geometry_dsl?: string;
    image_url?: string;
  };
}

interface ChatSession {
  id: string;
  user_id: string;
  title: string;
  created_at: string;
  updated_at: string;
}
```

---

## 10. Luồng dữ liệu & State Management

### SWR Pattern

Dữ liệu từ server được quản lý qua **SWR** (stale-while-revalidate):

```typescript
// Messages
const { data: messages, mutate: mutateMessages } = useSWR(
  messagesKey,   // [url, token] — null khi chưa auth
  fetchChatMessages,
  { revalidateOnFocus: false }
);

// Session assets (videos)
const { data: sessionAssets } = useSWR(assetsKey, fetchSessionAssets);
```

**Optimistic Updates**: Khi user gửi message, thêm temp message vào cache ngay lập tức trước khi API respond:
```typescript
await mutateMessages((prev) => [...(prev || []), tempMsg], { revalidate: false });
```

### State Hierarchy

```
ChatSessionPage (root state manager)
├── useAuth() → userSession, user
├── useSWR → messages (từ API)
├── useSWR → sessionAssets (videos từ API)
├── Local state:
│   ├── Geometry: coordinates, is3d, polygonOrder, circles, lines, rays, drawingPhases
│   ├── Video: videoUrl, renderingVideo
│   ├── Job: activeJobId, currentStatus, solveLoading
│   ├── Queue: pendingQueue
│   ├── UI: splitPercent, mainSplitPercent, sidebarCollapsed, videoVersion
│   └── Input: inputText, ocrLoading, requestVideo
└── Refs:
    ├── pollIntervalRef (polling timer)
    ├── solveWsRef (WebSocket instance)
    ├── isProcessingRef (prevent double submit)
    └── draggingType (resize drag state)
```

---

## 11. Xác thực (Authentication)

### Supabase Auth

- Provider: Supabase (JWT-based)
- Strategies: Email/Password, Google OAuth, GitHub OAuth
- JWT token: Được đính kèm vào mọi API request qua header `Authorization: Bearer {token}`
- Redirect callback URL: `{origin}/login`

### Backend Auth Bypass (Dev only)

Khi `process.env.NODE_ENV === 'development'` và Supabase không có session:
- Frontend tự tạo mock session với `access_token = "Test user-123"`
- Backend check `ALLOW_TEST_BYPASS=true` và extract user ID từ token format `"Test {user_id}"`

---

## 12. Giao tiếp với Backend API

### Base URL

Đọc từ `NEXT_PUBLIC_API_URL` (mặc định `http://localhost:7860`).

### Endpoints được sử dụng

| Method | Endpoint | Mục đích |
|---|---|---|
| `GET` | `/api/v1/sessions` | Lấy danh sách sessions của user |
| `POST` | `/api/v1/sessions` | Tạo session mới |
| `DELETE` | `/api/v1/sessions/{id}` | Xóa session |
| `GET` | `/api/v1/sessions/{id}/messages` | Lịch sử chat |
| `GET` | `/api/v1/sessions/{id}/assets` | Video assets |
| `POST` | `/api/v1/sessions/{id}/solve` | Gửi bài toán → `{ job_id }` |
| `GET` | `/api/v1/solve/{job_id}` | Polling status job |
| `POST` | `/api/v1/ocr` | Upload ảnh → extract text |
| `WS` | `/ws/{job_id}` | Real-time job updates |

### WebSocket Protocol

Messages nhận được có format:

```json
{ "status": "processing | solving | rendering | success | error" }
{ "status": "success", "result": { "coordinates": {...}, "is_3d": false, "solution": {...}, ... } }
```

---

## 13. Tính năng 3D (v5.0+)

### Auto-Detection

Khi nhận coordinates từ backend:
```typescript
const hasZ = Object.values(newCoords).some(
  (c: any) => Array.isArray(c) && c.length === 3 && c[2] !== 0
);
setIs3d(r.is_3d || hasZ);
```

Nếu `is_3d=true` hoặc bất kỳ điểm nào có z ≠ 0 → hiển thị `Interactive3DCanvas`.

### Coordinate System Mapping

Toán học `(x, y, z)` → Three.js `(x, z, -y)`:
- Trục X giữ nguyên
- Trục Y toán (thẳng đứng) → Trục Z Three.js
- Trục Z toán (chiều sâu) → Trục Y Three.js (Y-up convention)

### Drawing Phases trong 3D

`drawingPhases` được xử lý trong component `Segments`:
- Phase 1 (base): Màu `#6366f1` (indigo), solid
- Phase 2+ (auxiliary): Màu `#a78bfa` (violet), dashed

---

## 14. Tính năng Symbolic Solver UI (v5.1)

Khi `message.metadata.solution` tồn tại trong ChatMessage:

```
┌─────────────────────────────┐
│ ✓ Kết quả giải toán         │
│ Diện tích = 6               │  ← answer (KaTeX rendered)
│                             │
│ [▼] Xem các bước giải chi  │
│     tiết                    │
│   ──────────────────────    │
│   Bước 1: S = 1/2 × b × h  │  ← steps (animated accordion)
│   Bước 2: = 1/2 × 3 × 4    │
│   Bước 3: = 6               │
└─────────────────────────────┘
```

Accordion dùng Framer Motion với `height: 0 → auto` animation.

Tất cả nội dung được render qua `ReactMarkdown` với plugins `remarkMath` + `rehypeKatex` để hỗ trợ LaTeX inline `$...$` và block `$$...$$`.

---

## 15. Hệ thống Queuing & Job Tracking

### Multi-Message Queue

```typescript
if (isProcessingRef.current && !isQueued) {
  // Thêm vào hàng đợi thay vì gửi ngay
  setPendingQueue((prev) => [...prev, { id: "q-" + Date.now(), text: textToUse }]);
  setInputText("");
  return;
}
```

**Sequential Processing** (useEffect):
```typescript
if (!solveLoading && pendingQueue.length > 0) {
  // Delay 800ms để đảm bảo DB sync
  const timer = setTimeout(() => {
    const next = pendingQueue[0];
    setPendingQueue((prev) => prev.slice(1));
    void handleSolve(next.text);
  }, 800);
}
```

Người dùng có thể:
- **Xem** các câu hỏi đang chờ trong chat UI
- **Sửa** → remove khỏi queue và put vào input
- **Hủy** → remove khỏi queue

### Re-attach on Session Switch

Khi chuyển session, `useEffect([sessionId])` kiểm tra `getActiveJob(sessionId)`:
- Nếu có job đang chạy (< 30 phút) → tự động `attachToJob(jobId)` để tiếp tục nhận kết quả

---

## 16. Persistence & Local Storage

| Storage | Key | Nội dung | Lifetime |
|---|---|---|---|
| `localStorage` | `mathsolver_active_jobs` | Job IDs đang chạy + pending queue | Vĩnh viễn (30 phút expire) |
| `localStorage` | `mathsolver-theme` | "dark" / "light" | Vĩnh viễn |
| `sessionStorage` | `mathsolver_geo_{sessionId}` | Geometry state (coords, phases, ...) | Tab session |
| `sessionStorage` | `mathsolver-split-percent` | Sidebar width % | Tab session |
| `sessionStorage` | `mathsolver-main-split-percent` | Chat/Viz split % | Tab session |
| `sessionStorage` | `mathsolver-sidebar-collapsed` | "1" / "0" | Tab session |

---

## 17. Chạy cục bộ (Local Development)

### Yêu cầu

- Node.js >= 18
- npm >= 9

### Khởi động

```bash
cd frontend
npm install        # Cài dependencies
npm run dev        # Khởi động dev server (port 3000, Turbopack)
```

Dev server: `http://localhost:3000`

> **Dev Bypass Auth**: Khi backend chạy ở `localhost:7860` với `ALLOW_TEST_BYPASS=true`, frontend tự tạo mock user, không cần đăng nhập thật.

### Cấu trúc scripts

```json
{
  "dev": "next dev",        // Turbopack dev server
  "build": "next build",    // Production bundle + type check
  "start": "next start",    // Serve production build
  "lint": "eslint"          // Lint check
}
```

---

## 18. Build & Deploy

### Build production

```bash
npm run build
```

Output:
- `✓ Compiled successfully`
- Type checking pass
- Static pages pre-rendered
- Route `ƒ /chat/[sessionId]` là Dynamic (SSR on demand)

### Docker

`Dockerfile.frontend` đã có sẵn để containerize:

```dockerfile
# (nội dung trong Dockerfile.frontend)
```

### Deploy lên Vercel

Vercel nhận diện Next.js tự động. Cần set environment variables:
- `NEXT_PUBLIC_API_URL` → URL backend production (https://)
- `NEXT_PUBLIC_WS_URL` → URL WebSocket production (wss://)
- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`

> **QUAN TRỌNG**: Khi deploy production, xóa bỏ hoặc bảo vệ **Dev Bypass** trong `auth-context.tsx` (chỉ nên chạy local).

### CORS cho production

`backend/app/main.py` cần add domain production vào `allow_origins`:

```python
allow_origins=[
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://your-production-domain.vercel.app",  # Thêm domain production
],
```

---

*Tài liệu này mô tả toàn bộ codebase MathSolver Frontend tính đến phiên bản v5.1 (April 2026).*
