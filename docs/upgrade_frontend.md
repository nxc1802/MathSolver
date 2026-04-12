
-----

## I. Phân tích UI & Thẩm mỹ (UI Styles Integration)

### 1\. Phân tích Style chủ đạo

  * **Dark Mode (OLED Optimized):** Sử dụng nền `#0a0a0f` (True Black) giúp tăng độ tương phản cho công thức Toán học và tiết kiệm pin trên màn hình di động.
  * **Glassmorphism:** Áp dụng cho Sidebar, Chat Bubbles và Modal. Sử dụng `backdrop-filter: blur(12px)` và border `rgba(255,255,255,0.05)` để tạo cảm giác lớp kính chồng lên không gian 3D.
  * **3D & Hyperrealism:** Áp dụng riêng cho `Interactive3DCanvas`. Tận dụng `Stars` background và hiệu ứng đổ bóng vật lý để biến hình học không gian thành một trải nghiệm thị giác thực tế.

-----

### 2\. Mô tả UI chi tiết từng Page & State

| Page/State | Mô tả chi tiết UI & Style |
| :--- | :--- |
| **Login Page** | **Style: Vibrant & Glassmorphism.** <br> Card đăng nhập nằm giữa các "Gradient Orbs" mờ ảo. Nút Google/Github sử dụng hiệu ứng Glassmorphism với viền sáng rực (Indigo). |
| **Chat Sidebar** | **Style: Minimalism & Swiss Style.** <br> Khi thu gọn (Compact mode), chỉ còn các icon Lucide mảnh, tinh tế. Khi mở rộng, sử dụng typography Inter rõ ràng, phân cấp mạch lạc (Hierarchy). |
| **Chat Panel (Idle)** | **Style: Dark Mode.** <br> Ô nhập liệu (`InputBox`) dạng viên thuốc (rounded-full) với nền `rgba(24,24,27,0.8)`, tạo cảm giác chìm xuống bề mặt kính. |
| **State: Solving** | **Style: Vibrant.** <br> `StatusStepper` sử dụng các tia sáng chuyển động (shimmer) màu tím-xanh. Các bước OCR → Render sáng dần theo tiến độ. |
| **State: 2D Result** | **Style: Swiss Style.** <br> Canvas SVG cực kỳ sạch sẽ, các đường kẻ mảnh 1px, font chữ số rõ ràng, tập trung hoàn toàn vào tính chính xác của hình vẽ. |
| **State: 3D Result** | **Style: Hyperrealism.** <br> Không gian 3D với trục tọa độ RGB rực rỡ trên nền đen sâu thẳm, có các hạt "Stars" chuyển động nhẹ khi xoay camera. |

-----

## II. Nâng cấp cấu trúc dự án (Architecture Upgrade)

Codebase hiện tại có một file `page.tsx` dài hơn 800 dòng. Đây là "mùi code" (code smell) cần xử lý bằng cách phân rã theo cấu trúc **Feature-based Atomic Design**.

### 1\. Cấu trúc thư mục mới đề xuất

Tôi đề xuất tái cấu trúc để tách biệt Logic và UI, giúp dễ dàng bảo trì khi lên bản v6.0:

```text
Tự suy luận, miễn là các file không quá dài và dễ bảo trì.
```

### 2\. Tinh chỉnh Logic xử lý (Refinement)

  * **Custom Hooks:** Tách logic WebSocket và Polling ra khỏi UI. Tạo `useSolverJob(jobId)` để quản lý trạng thái pending/success tự động.
  * **Zod Validation:** Sử dụng thư viện Zod để parse `metadata` từ API. Hiện tại metadata đang được normalize thủ công, dễ gây lỗi runtime nếu API thay đổi.
  * **Viewport Unit Fix:** Thay vì dùng `100vh`, hãy dùng `dvl` (Dynamic Viewport Height) để tránh lỗi che khuất thanh công cụ trên trình duyệt di động (Safari/Chrome Mobile).

-----

## III. Làm cho dự án "Hoàn thiện hơn" (Professional Polish)

Để MathSolver v5.1 thực sự hoàn thiện, hãy bổ sung các kỹ thuật sau:

### 1\. Hiệu ứng chuyển cảnh (Framer Motion)

Đừng chỉ hiển thị kết quả. Hãy thêm:

  * **Layout Transitions:** Khi Sidebar collapse, các panel còn lại co giãn mượt mà thay vì giật cục.
  * **Stagger Children:** Các bubble chat xuất hiện lần lượt từ dưới lên với hiệu ứng `opacity` và `y-offset`.

### 2\. Xử lý trạng thái rỗng (Empty States)

Thay vì để màn hình trống khi chưa có session, hãy thiết kế một **"Hero Welcome"** theo style **Vibrant & Block-based**:

  * Hiển thị các khối gợi ý: "Giải hệ phương trình 3 ẩn", "Vẽ hình chóp cụt".
  * Mỗi khối có một icon 3D nhỏ (Skeuomorphism) để thu hút người dùng.

### 3\. Tối ưu hóa hiệu suất

  * **Three.js Tree Shaking:** Chỉ import những module cần thiết của Three.js để giảm bundle size (hiện tại `three` khá nặng).
  * **Canvas Offscreen:** Sử dụng `OffscreenCanvas` cho việc tính toán tọa độ 2D nếu hình vẽ quá phức tạp (\>1000 điểm), giúp UI không bị lag.

-----

### 4\. Bổ sung tính năng "Symbolic Solver" (UI v5.1)

Tận dụng triệt để hệ thống **Brutalism-lite** cho các bước giải bài:

  * Các bước giải toán (Steps) được đặt trong các thẻ có viền dày, đổ bóng cứng (hard shadow) để tạo sự tách biệt rõ ràng với phần chat.
  * Sử dụng màu nền `bg-amber-500/10` cho các kết quả quan trọng để gây chú ý (Accessible & Ethical style).





### IV. Tối ưu hóa cơ chế bắt sự kiện (event handling)

Để tối ưu hóa cơ chế bắt sự kiện (event handling) cho quy trình giải toán đa giai đoạn (OCR → Parser → Solver → Render), chúng ta cần thay đổi cách tiếp cận từ việc xử lý rời rạc trong component sang một **State Machine** đồng bộ.

Thay vì để file `page.tsx` gánh vác hơn 800 dòng code logic, chúng ta sẽ xây dựng một **Custom Hook** chuyên biệt mang tên `useSolverJob`. Hook này sẽ đóng vai trò là "nhà điều phối" duy nhất, kết nối giữa REST API, WebSocket và cơ chế Polling fallback.

Dưới đây là kiến trúc logic hoàn hảo để quản lý các giai đoạn này:

### 1. Định nghĩa "Pipeline State"
Đầu tiên, chúng ta chuẩn hóa các trạng thái từ Backend để khớp với UI Stepper.

```typescript
type SolverPhase = 'idle' | 'uploading' | 'ocr' | 'parsing' | 'solving' | 'rendering' | 'success' | 'error';

interface JobState {
  phase: SolverPhase;
  progress: number; // 0-100
  message: string;
  result?: any;
  error?: string;
}
```

---

### 2. Xây dựng Hook `useSolverJob`
Hook này sẽ đóng gói toàn bộ sự phức tạp của WebSocket và Polling.

```typescript
export function useSolverJob(sessionId: string) {
  const [job, setJob] = useState<JobState>({ phase: 'idle', progress: 0, message: '' });
  const socketRef = useRef<WebSocket | null>(null);
  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // 1. Khởi động Job
  const startSolve = async (text: string) => {
    setJob({ phase: 'uploading', progress: 10, message: 'Đang gửi yêu cầu...' });
    
    try {
      const { job_id } = await api.post(`/sessions/${sessionId}/solve`, { text });
      saveActiveJob(sessionId, job_id); // Lưu vào localStorage để khôi phục nếu reload
      connectSocket(job_id);
    } catch (err) {
      setJob({ phase: 'error', progress: 0, message: 'Lỗi khởi tạo', error: String(err) });
    }
  };

  // 2. Quản lý WebSocket (Real-time events)
  const connectSocket = (jobId: string) => {
    const ws = new WebSocket(`${getWsBaseUrl()}/ws/${jobId}`);
    socketRef.current = ws;

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      updateJobState(data);
      if (data.status === 'success' || data.status === 'error') {
        stopPolling();
        ws.close();
      }
    };

    ws.onerror = () => startPolling(jobId); // Nếu WS lỗi, tự động chuyển sang Polling
  };

  // 3. Fallback Polling (An toàn tuyệt đối)
  const startPolling = (jobId: string) => {
    if (pollIntervalRef.current) return;
    pollIntervalRef.current = setInterval(async () => {
      const data = await api.get(`/solve/${jobId}`);
      updateJobState(data);
      if (data.status === 'success' || data.status === 'error') stopPolling();
    }, 1500);
  };

  const updateJobState = (data: any) => {
    // Map backend status sang UI phase
    const phaseMap: Record<string, SolverPhase> = {
      'processing': 'ocr',
      'parsing': 'parsing',
      'solving': 'solving',
      'rendering': 'rendering',
      'success': 'success',
      'error': 'error'
    };
    setJob(prev => ({ ...prev, phase: phaseMap[data.status] || prev.phase, result: data.result }));
  };

  // Dọn dẹp khi unmount
  useEffect(() => {
    return () => {
      socketRef.current?.close();
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
    };
  }, []);

  return { job, startSolve };
}
```

---

### 3. Tối ưu hóa UI Stepper & Persistence
Để trải nghiệm người dùng không bị ngắt quãng, chúng ta cần kết hợp với hệ thống lưu trữ đã có:

* **Re-attachment Logic:** Khi người dùng chuyển session hoặc F5, `useEffect` trong Chat Page sẽ kiểm tra `getActiveJob(sessionId)`. Nếu tồn tại một job chưa hoàn thành trong 30 phút qua, nó sẽ tự động gọi `connectSocket(jobId)` để "bắt" tiếp luồng sự kiện đang chạy.
* **Optimistic Phase Transition:** Thay vì đợi Backend gửi event tiếp theo, Frontend có thể dự đoán tiến trình (ví dụ: chạy progress bar từ 0-90% trong khi chờ `rendering`).
* **Hệ thống Queuing:** Nếu người dùng gửi tin nhắn liên tục khi job cũ đang chạy, logic sẽ đẩy tin nhắn vào `pendingQueue` trong `localStorage`. Khi job hiện tại chuyển sang `success`, hook sẽ tự động kích hoạt `startSolve` cho tin nhắn tiếp theo.

### 4. Xử lý "Side Effects" sau khi giải xong
Khi `job.phase === 'success'`, logic hoàn thiện sẽ tự động kích hoạt các hàm xử lý dữ liệu hình học:

1.  **Auto-detect Dimension:** Kiểm tra tọa độ có trục Z hay không để bật `Interactive3DCanvas`.
2.  **Cache Geometry:** Lưu tọa độ vào `sessionStorage` (`mathsolver_geo_{sessionId}`) để chuyển đổi giữa các phiên bản hình vẽ mà không cần gọi lại API.
3.  **Scroll to Bottom:** Tự động cuộn khung chat xuống kết quả mới nhất với hiệu ứng mượt mà của `framer-motion`.

Cách build này đảm bảo: **Không bao giờ mất sự kiện**, **Giao diện luôn phản hồi** và **Codebase sạch sẽ** nhờ tách biệt logic giải toán ra khỏi component UI.
