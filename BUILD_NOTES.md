# BUILD_NOTES — AIRA bản build local (sau thay đổi phạm vi của Kevin)

Ngày build: 2026-11-02. Thư mục: `~/workspace/aira-app/` (bản sao từ source v2 đã khóa winner E7).

## 0. THAY ĐỔI PHẠM VI (ghi đè brief gốc)

Kevin quyết định đây là **bản DEMO trình diễn kết quả tiểu luận, không phải sản phẩm nhiều người dùng**:

- **HỦY toàn bộ auth**: không model User, không `src/auth.py`, không JWT/PyJWT, không endpoint register/login/me, không cột `user_id`, không migration users, không `tests/test_auth.py`, không AuthScreen, không lưu token.
- Backend giữ nguyên cơ chế v2: middleware X-API-Key tùy chọn theo `AIRA_API_KEY` (trống = không khóa) — **không sửa hành vi này**.
- Thay auth bằng **rate limit nhẹ chống spam đốt quota** (thuần thư viện chuẩn, không thêm dependency).
- Frontend giữ Việc 2 (tách 5 component), bỏ phần auth; `frontend/lib/api.ts` giữ nguyên đúng bản v2 (X-API-Key từ `NEXT_PUBLIC_AIRA_API_KEY`).

### Trạng thái khôi phục / đối chiếu với source v2 gốc

Tại thời điểm nhận thay đổi phạm vi, **chưa có file auth nào từng được tạo** trong thư mục này (phiên làm việc trước mới ở bước đọc code; lệnh `pip install` các gói auth đã bị abort giữa chừng, venv không thay đổi). Kiểm chứng bằng diff từng file với `~/workspace/rag-audit/v2/my-rag-assistant/`:

```
DIFF: api.py                  <- chỉ khác vì rate limit (mục 1)
SAME: src/models.py
DIFF: src/config.py           <- chỉ khác vì thêm khóa RATE_LIMIT_PER_MIN (mục 1)
SAME: requirements.txt        <- không thêm dependency nào (không có PyJWT)
SAME: src/schemas.py
SAME: src/session_service.py
SAME: src/database.py
SAME: src/bm25.py
SAME: src/chunker.py
SAME: src/retriever.py
SAME: src/reranker.py
SAME: src/embedder.py
SAME: src/parser.py
SAME: frontend/lib/api.ts
```

Không tồn tại: `src/auth.py`, `tests/test_auth.py`, `migrations/002_users.sql`, `frontend/components/AuthScreen.tsx`. Không có `User`/`user_id`/`JWT` trong bất kỳ file backend nào (đã grep kiểm chứng).

## 1. Backend — rate limit (thay cho auth)

### File thêm
- `src/rate_limit.py` — `RateLimiter`: bộ đếm cửa sổ trượt (sliding window) theo khóa (IP), thuần thư viện chuẩn (`threading`, `time`, `collections.deque`). Đồng hồ tiêm được (tham số `clock`) để test. Request bị từ chối không được ghi nhận vào bộ đếm. `limit <= 0` = tắt.
- `tests/test_rate_limit.py` — 7 test: dưới ngưỡng, vượt ngưỡng, cửa sổ trượt giải phóng slot, request bị từ chối không tính, các IP độc lập, limit=0 tắt, `remaining`/`reset`.

### File sửa
- `src/config.py` — thêm mục mới "RATE LIMIT (demo public)": `RATE_LIMIT_PER_MIN = int(os.getenv("AIRA_RATE_LIMIT_PER_MIN", "30"))`. Không đổi bất kỳ khóa cũ nào (regression pin 9/9 vẫn khớp).
- `api.py` — thêm middleware `rate_limit` (middleware X-API-Key cũ giữ nguyên từng dòng):
  - Chỉ áp cho `POST` tới `/api/v1/sessions/{id}/chat`, `/api/v1/sessions/{id}/chat/stream` và `/api/v1/sessions/{id}/documents` (upload) — khớp bằng hậu tố path.
  - Đếm theo `request.client.host`.
  - Vượt giới hạn → HTTP 429, body `{"detail": "Bạn đang gửi yêu cầu quá nhanh. Vui lòng đợi khoảng một phút rồi thử lại."}`.
  - `AIRA_RATE_LIMIT_PER_MIN=0` = tắt (qua chính `RateLimiter`, middleware không rẽ nhánh riêng).

### Quyết định kỹ thuật
- Bộ đếm nằm trong RAM tiến trình backend: đủ cho demo một tiến trình; restart là reset; không dùng chung giữa nhiều worker (đã ghi rõ giới hạn này trong docstring của module).
- Rate limit chỉ là chống spam đốt quota, không phải cơ chế bảo mật — ghi rõ trong code và ghi chú này.

## 2. Frontend — tách module (Việc 2, không auth)

`frontend/app/page.tsx`: 2.435 dòng → **542 dòng** (chỉ còn state cấp trang, effects, handlers, lắp ráp).

### File thêm (`frontend/components/`)
- `HistoryPanel.tsx` (99 dòng) — sidebar: brand AIRA, nút New Chat, danh sách sessions (chọn/xóa).
- `DocumentLibrary.tsx` (28 dòng) — chips tài liệu + trạng thái ở header.
- `UploadPanel.tsx` (35 dòng) — input file PDF (`id="pdf-input"` giữ nguyên vì page dùng để reset sau upload) + nút Upload.
- `ChatPanel.tsx` (155 dòng) — vùng tin nhắn (gồm `MessageBubble` + trích dẫn), trạng thái streaming, form nhập + ghi chú chân trang.
- `FlashcardPanel.tsx` (160 dòng) — chuyển nguyên component `FlashcardsPanel` cũ, giữ nguyên props/hành vi.
- `EmptyState.tsx` (17 dòng) — tách dùng chung cho ChatPanel/FlashcardPanel (trước nằm trong page.tsx).

### File sửa
- `frontend/lib/types.ts` — thêm interface `UiMessage` (trước khai báo nội bộ trong page.tsx) để các component dùng chung.
- `frontend/app/page.tsx` — viết lại theo cấu trúc component ở trên. Toàn bộ handler (`loadSessions`, `loadConversation`, `handleNewChat`, `handleDeleteSession`, `handleUpload`, `handleGenerateFlashcards`, `handleDeleteFlashcard`, `handleSubmit` + streaming callbacks), effects (poll trạng thái document 2s, initial load, session change, auto-scroll) giữ nguyên logic; mọi chuỗi UI, class Tailwind và hợp đồng gọi `lib/api.ts` giữ nguyên.

### Không đổi
- `frontend/lib/api.ts` — nguyên bản v2 (diff SAME), vẫn gửi `X-API-Key` từ `NEXT_PUBLIC_AIRA_API_KEY` như thiết kế local/LAN của v2. Không JWT, không localStorage token, không AuthScreen.

## 3. Output kiểm chứng (nguyên văn)

### 3.1 Regression (sau mọi thay đổi)

Lệnh: `HF_HOME=~/workspace/rag-audit/run/hf-cache HF_HUB_O
...[truncated 3601 chars]

## 4. Đợt gói trình diễn (2026-11-02) — FRONTEND-ONLY

Kevin duyệt gói trình diễn + sửa upload. Phạm vi đợt này: **chỉ frontend**. Không sửa backend, không đổi hợp đồng API, không đổi giá trị config.

### File thêm
- `frontend/components/SystemInfoPanel.tsx` (107 dòng) — tab "Giới thiệu": mô tả AIRA, sơ đồ pipeline 8 khối (Chia đoạn 512 token chồng lấp 10% → Embedding multilingual-e5-small → Truy xuất lai Dense + BM25 → RRF k=60 → Pool 40 → Reranker bge-reranker-base → Top-5 → Gemini có trích dẫn), bảng cấu hình chính thức 8 dòng, khối kết quả kiểm định (ExcerptHit@5 E7: 94,1% cấu hình chính thức so với 70,6% cấu hình gốc; nguồn: bộ 120 câu hỏi tiếng Việt, tập test 34 câu E7). Số liệu dùng nguyên văn hồ sơ nghiên cứu đã khóa, không thêm bớt.

### File sửa
- `frontend/app/page.tsx` (542 → 581 dòng):
  - Tab thứ ba "Giới thiệu" theo đúng cơ chế tab hiện tại (cùng thanh tab, cùng style nút; thanh tab hiện khi đã chọn session như hai tab cũ); `activeTab` mở rộng `"chat" | "flashcards" | "info"`.
  - Tách thân `handleSubmit` thành `sendQuestion(text)` — đường gửi câu hỏi duy nhất dùng chung cho form nhập và chip câu hỏi mẫu (không viết đường gửi mới).
  - Đo thời gian trả lời phía client trong `sendQuestion`: `performance.now()` ngay trước `streamChat(...)`; khi promise resolve (= stream kết thúc, đã nhận xong toàn bộ câu trả lời) tính giây trôi qua và ghi vào tin nhắn assistant (`responseTimeSec`). Nếu streamChat ném lỗi (HTTP lỗi trước khi stream) thì không ghi metadata.
  - UploadPanel đổi props: `selectedFileName` + `onFileSelect(file)` thay cho `hasSelectedFile` + `onFileChange(event)` (handler mới `handleFileSelect` chỉ set state).
- `frontend/components/ChatPanel.tsx` (155 → 218 dòng):
  - 4 chip câu hỏi mẫu phía trên ô nhập, hiện khi: đã chọn session + có ≥1 tài liệu `ready` + chưa có tin nhắn nào + không đang tải lịch sử; bấm chip gọi `onSuggestionClick` → `sendQuestion` ở page. Có tin nhắn là chip biến mất.
  - Chỉ báo giai đoạn khi chờ trả lời (thay dòng "AIRA đang trả lời..." cũ): component `StreamingProgress` chuyển "Đang tìm trong tài liệu…" → "Đang xếp hạng các đoạn liên quan…" → "Đang soạn câu trả lời…" theo mốc thời gian phía client 0s / 1,2s / 2,5s. **Đây là hiển thị theo mốc thời gian phía client, KHÔNG phải tín hiệu thật từ backend** (backend không phát sự kiện giai đoạn).
  - Dòng metadata nhỏ mờ dưới mỗi câu trả lời mới của AIRA: "Trả lời trong X giây · N nguồn trích dẫn" — X là thời gian đo thật phía client (1 chữ số thập phân, dấu phẩy theo kiểu Việt), N là số trích dẫn của chính câu trả lời đó. Tin nạp từ lịch sử không có `responseTimeSec` nên không hiện dòng này.
- `frontend/components/UploadPanel.tsx` (35 → 100 dòng):
  - Bỏ hẳn cụm `file:` mặc định của trình duyệt (cụm bị cắt chữ "Không c...ợc chọn"). Thay bằng input `type=file` ẩn (giữ `id="pdf-input"` để page reset sau upload như cũ) + nút "Chọn PDF" tự thiết kế + tên file đã chọn (truncate ellipsis, `title` chứa tên đầy đủ) + nút "Tải lên" giữ nguyên hành vi/endpoint.
  - Kéo–thả: kéo file vào vùng panel thì sáng viền xanh (border-blue-500 + nền blue-500/10), thả vào là nhận file làm file đã chọn.
  - Kiểm tra đuôi `.pdf` ở cả hai đường (chọn tệp và kéo–thả) qua cùng một hàm `acceptFile`; sai định dạng thì hiện lỗi nhẹ ngay trong panel ("Chỉ nhận file PDF (.pdf).") và không chọn file.
- `frontend/lib/types.ts` — `UiMessage` thêm trường tùy chọn `responseTimeSec?: number`.

### Không đổi
- `frontend/lib/api.ts` — không sửa (diff với v2: SAME). Endpoint/payload upload và chat giữ nguyên.
- Backend: diff 0 file trong đợt này — đối chiếu lại với source v2 cho ra đúng trạng thái cuối đợt trước (chỉ `api.py` + `src/config.py` khác v2 vì rate limit đợt trước; toàn bộ `src/*.py` còn lại và `requirements.txt` SAME). Kiểm chứng bằng diff từng file, không phải suy đoán.

### Output kiểm chứng (nguyên văn)

Regression (kỳ vọng nguyên trạng vì backend không đổi):

```text
Kết quả pin: 9/9 khớp

== UNIT TESTS ==
...................
----------------------------------------------------------------------
Ran 19 tests in 0.038s

OK
Tests: 19 chạy, 0 fail, 0 error, 0 skipped

== TỔNG KẾT ==
REGRESSION: PASS (đầy đủ)
```

Frontend build (`npm run build`):

```text
   Creating an optimized production build ...
 ✓ Finished writing to disk in 26ms
 ✓ Compiled successfully in 9.7s
   Linting and checking validity of types ...
   Collecting page data ...
   Generating static pages (0/5) ...
   Generating static pages (1/5)
   Generating static pages (2/5)
   Generating static pages (3/5)
 ✓ Generating static pages (5/5)
   Finalizing page optimization ...
   Collecting build traces ...

Route (app)                         Size  First Load JS
┌ ○ /                            7.49 kB         121 kB
└ ○ /_not-found                      0 B         114 kB
+ First Load JS shared by all     119 kB
```

- Build PASS, type-check qua. Route `/` tăng 5,88 kB → 7,49 kB (thêm SystemInfoPanel + chip + chỉ báo giai đoạn), First Load 120 → 121 kB.
- Chưa kiểm chứng runtime trực quan đợt này trên VM (không có backend/Postgres sống như các đợt trước) — các thay đổi đều ở tầng hiển thị/handler phía client, hợp đồng API không đổi; kiểm chứng trực quan để dành cho lần chạy demo tiếp theo (máy Kevin hoặc staging AWS).

## 5. Đợt render markdown (2026-11-02) — FRONTEND-ONLY

Kevin yêu cầu trực tiếp: câu trả lời của AIRA đang hiện ký tự markdown thô (`**`, `*` hiện nguyên văn thay vì in đậm/gạch đầu dòng — lộ rõ ở ảnh chụp TASK-009 với câu trả lời dạng tóm tắt). Đợt này cho bong bóng trả lời của AIRA render markdown đúng định dạng.

### File sửa
- `frontend/package.json` (+ `package-lock.json`) — thêm dependency `react-markdown` `^10.1.0` qua `npm install react-markdown`. Không thêm plugin nào khác (không dùng typography plugin).
- `frontend/components/ChatPanel.tsx` — trong `MessageBubble`:
  - Tin nhắn **người dùng**: giữ nguyên render text thuần (`whitespace-pre-wrap`) như cũ.
  - Tin nhắn **AIRA (assistant)**: render bằng `<ReactMarkdown>` bên trong `<div className="aira-markdown text-sm leading-7">`.
  - Pills trích dẫn và dòng metadata ("Trả lời trong X giây · N nguồn trích dẫn") không đổi, giữ nguyên vị trí/logic.
- `frontend/app/globals.css` — thêm khối style `.aira-markdown` tự viết theo hệ nền tối (không plugin): đoạn văn có margin dễ đọc và bỏ margin ở đoạn cuối; `strong` màu slate-100 + đậm rõ; `ul` kiểu disc / `ol` kiểu decimal, thụt lề 1,4em; tiêu đề bị giới hạn cỡ vừa (h1 1,05rem, h2 1rem, h3 0,95rem, h4 0,9rem — không to hơn nội dung quá nhiều); `code` nền slate-800 bo góc, `pre` nền slate-900 có viền + cuộn ngang; `blockquote` viền trái slate; link màu blue-400 gạch chân.

### Về streaming (đã kiểm tra code, không suy đoán)
- Logic hiện tại trong `page.tsx`: `streamChat` callback `onToken` cộng token thô trực tiếp vào `message.content` của tin assistant đang stream (`content: message.content + token`). **Không có bước tiền xử lý/regex tự chế nào trên nội dung tin nhắn** — cả ở đường stream lẫn đường nạp lịch sử (`loadConversation` map `content` nguyên văn). Vì vậy chuyển sang react-markdown không bị phá vỡ bởi xử lý text trung gian.
- Markdown chưa hoàn chỉnh trong lúc stream (ví dụ `**` chưa đóng) được react-markdown/remark render an toàn ở dạng text thường cho tới khi đóng cú pháp — không lỗi, không crash. Tin nhắn đang stream dùng chung `MessageBubble` nên tự chuyển sang hiển thị có định dạng khi cú pháp hoàn chỉnh.

### Không đổi
- Backend: **diff 0 file trong đợt này** — đối chiếu từng file với source v2 vẫn cho đúng trạng thái cuối đợt trước: chỉ `api.py`, `src/config.py` khác v2 và `src/rate_limit.py` là file mới, cả ba đều thuộc đợt rate limit; toàn bộ `src/*.py` còn lại và `requirements.txt` SAME.
- `frontend/lib/api.ts` — không sửa. Hợp đồng API không đổi.

### Output kiểm chứng (nguyên văn)

NPM install + build (`npm install react-markdown`, sau đó `npm run build`):

```text
   Creating an optimized production build ...
 ✓ Finished writing to disk in 14ms
 ✓ Compiled successfully in 10.2s
   Linting and checking validity of types ...
   Collecting page data ...
   Generating static pages (0/5) ...
   Generating static pages (1/5)
   Generating static pages (2/5)
   Generating static pages (3/5)
 ✓ Generating static pages (5/5)
   Finalizing page optimization ...
   Collecting build traces ...

Route (app)                         Size  First Load JS
┌ ○ /                            42.3 kB         156 kB
└ ○ /_not-found                      0 B         114 kB
+ First Load JS shared by all     120 kB
```

- Build PASS, type-check qua. Route `/` tăng 7,49 kB → 42,3 kB và First Load 121 kB → 156 kB do thêm cây thư viện react-markdown/micromark (~35 kB) — đánh đổi hợp lý cho một trang demo tĩnh, ghi rõ để không bất ngờ.

Regression (kỳ vọng nguyên trạng vì backend không đổi):

```text
Kết quả pin: 9/9 khớp

== UNIT TESTS ==
...................
----------------------------------------------------------------------
Ran 19 tests in 0.027s

OK
Tests: 19 chạy, 0 fail, 0 error, 0 skipped

== TỔNG KẾT ==
REGRESSION: PASS (đầy đủ)
```

### Chưa kiểm chứng được
- **Không chụp được ảnh kiểm chứng trực quan trong đợt này**: VM không có backend/Postgres sống nên không chạy được luồng chat thật để chụp màn hình câu trả lời có định dạng. Mới kiểm chứng ở mức build + type-check + đọc code. Phần chụp ảnh đối chiếu (câu trả lời dạng tóm tắt phải hiện chữ đậm/gạch đầu dòng thay vì ký tự `**`/`*` thô) để dành cho task chạy demo phía Antigravity (máy Kevin) hoặc staging AWS.

## 6. Đợt polish giao diện (2026-11-02) — FRONTEND-ONLY, thuần trình bày

Kevin yêu cầu: "update thêm giao diện web đi, xem coi làm cho nó đẹp hơn được k". Phạm vi đợt này: **chỉ CSS + class trình bày trong component + vài icon SVG inline nhỏ**. Không đổi bố cục tổng thể, giữ theme nền tối xanh navy + màu nhấn xanh dương, không đổi hành vi/chức năng/hợp đồng API, không sửa backend, **0 dependency mới** (không thêm thư viện icon; mọi icon là SVG inline tự viết).

### Việc đã làm theo danh mục
1. **Nền & bề mặt** (`app/globals.css`, `app/page.tsx`): body có nền gradient nhiều lớp rất nhẹ (radial xanh dương ở góc trên phải + radial chàm ở góc dưới trái + linear navy → gần đen, `background-attachment: fixed`); `main` bỏ nền đặc để gradient hiện lên; sidebar/header/thanh tab/ô nhập dùng nền bán trong suốt + `backdrop-blur`; card/bong bóng/input thống nhất bo góc lớn (rounded-2xl), thêm bóng đổ mềm.
2. **Sidebar** (`HistoryPanel.tsx`): tile logo "AI" thành gradient xanh dương → chàm + bóng + ring sáng mờ, bo rounded-2xl; nút "+ New Chat" gradient; nhãn "Sessions" chuyển cỡ 11px + `tracking-[0.18em]` + tăng khoảng cách; mục session active có nền gradient nhẹ từ xanh + ring xanh mờ + **thanh nhấn gradient bên trái**, hover sáng nền rõ hơn.
3. **Header phiên** (`page.tsx` + `DocumentLibrary.tsx`): header `sticky top-0 z-20`, nền bán trong suốt + `backdrop-blur-md` + bóng nhẹ; tiêu đề tracking-tight. Pill tài liệu trạng thái `ready` thêm **chấm xanh lục nhấp nháy (animate-ping + chấm đặc)** và phát sáng mờ (`shadow` emerald); các trạng thái khác giữ nguyên.
4. **Bong bóng chat** (`ChatPanel.tsx`): tin AIRA thành card nền `slate-900/60` + viền mờ + bóng + avatar tile "AI" gradient nhỏ bên trái (nhãn "AIRA", metadata và pills trích dẫn giữ nguyên nội dung/vị trí); tin người dùng nền gradient xanh dương → chàm + bóng + ring, bo góc dưới-phải nhỏ (kiểu bong bóng); mọi tin nhắn mới có hiệu ứng xuất hiện fade/slide nhẹ (class `.aira-msg-in` trong globals.css); pill trích dẫn hover sáng viền xanh + phát sáng mờ. Chỉ báo chờ trả lời thêm chấm pulse cạnh dòng giai đoạn (nội dung 3 giai đoạn không đổi).
5. **Ô nhập & nút gửi** (`ChatPanel.tsx`): textarea bo rounded-2xl, nền bán trong suốt, focus có `ring-4 ring-blue-500/25` + viền xanh sáng; nút gửi thành nút gradient kèm **icon giấy máy bay SVG inline** + chữ "Send" (đang stream vẫn hiện "..." như cũ), disabled mờ rõ + mất bóng.
6. **Chip câu hỏi mẫu** (`ChatPanel.tsx`): pill nền gradient xanh/chàm rất nhẹ + viền xanh mờ, thêm **icon tia lửa SVG** nhỏ màu xanh ở đầu, hover nhấc nhẹ (`-translate-y-0.5`) + sáng viền + bóng. Nội dung 4 câu hỏi không đổi.
7. **Tab Giới thiệu** (`SystemInfoPanel.tsx`): tiêu đề các mục thêm thanh nhấn gradient nhỏ bên trái + tracking-tight; pipeline thành stepper: mỗi khối có **số thứ tự trong vòng tròn gradient**, viền xanh mờ + nền gradient nhẹ, nối nhau bằng **mũi tên SVG** màu xanh rõ ràng (thay ký tự "→" xám); bảng cấu hình bo rounded-2xl, giữ zebra rất nhẹ + thêm hover hàng; khối kết quả thành **thẻ số liệu nổi bật**: nền gradient xanh/chàm + viền xanh, số **94,1%** cỡ 5xl in đậm với chữ gradient — toàn bộ nội dung/số liệu giữ nguyên (vẫn đủ "ExcerptHit@5 trên tập test E7", "70,6% (cấu hình gốc)" và dòng nguồn bộ 120 câu/tập test 34 câu E7).
8. **Flashcards** (`FlashcardPanel.tsx`): thẻ có viền xanh mờ + nền gradient nhẹ (slate → chàm) + ring sáng mờ + bóng sâu, hover nhấc nhẹ + sáng viền; nhãn "Thẻ x / y" thành pill có viền/nền/bóng; nút Trước/Sau thêm viền mờ, nút tạo thẻ thành gradient như các nút chính khác. Nội dung/hành vi lật thẻ không đổi.
9. **Chi tiết toàn cục** (`globals.css` + `EmptyState.tsx`): thanh cuộn mảnh 6px theo theme (thumb slate đậm, hover xanh) + `scrollbar-width: thin` cho Firefox; màu chọn văn bản (`::selection`) xanh mờ; tiêu đề dùng tracking-tight, line-height giữ nguyên hệ cũ; EmptyState thêm **tile icon tia lửa gradient** phía trên tiêu đề — toàn bộ văn bản EmptyState giữ nguyên.
10. **Vùng upload** (`UploadPanel.tsx`): thêm **icon PDF SVG** cạnh dòng gợi ý; viền đứt nét nay luôn hiện mờ (slate) quanh khu vực kéo–thả và **sáng xanh + phát sáng khi kéo file vào** (hành vi nhận file/kiểm tra .pdf không đổi); dòng gợi ý rút ngắn từ "Kéo thả PDF vào đây hoặc chọn tệp" còn **"Kéo thả PDF vào đây"** để không bị cắt ở header hẹp; nút "Upload PDF" thành gradient khi sẵn sàng (disabled xám mờ), nút "Chọn PDF" thêm viền mờ.

### Không đổi
- Backend: **diff 0 file trong đợt này** — đối chiếu từng file với source v2 vẫn cho đúng trạng thái cuối đợt trước (chỉ `api.py`, `src/config.py` khác v2 và `src/rate_limit.py` là file mới, cả ba thuộc đợt rate limit).
- `frontend/lib/api.ts` — không sửa. `frontend/lib/types.ts` — không sửa trong đợt này. `frontend/package.json` — không sửa: **0 dependency mới** (dependencies vẫn chỉ next/react/react-dom/react-markdown của các đợt trước).
- Khối `.aira-markdown` trong globals.css giữ nguyên từng dòng; mọi chuỗi nội dung quan trọng (tiêu đề mục, số liệu, 4 câu hỏi mẫu, dòng fallback/ghi chú) giữ nguyên — ngoại lệ duy nhất là dòng gợi ý upload được rút ngắn theo đúng yêu cầu đợt này.

### File sửa (9 file, tất cả ở frontend)
- `frontend/app/globals.css` — nền gradient body, ::selection, scrollbar mảnh, keyframe `.aira-msg-in`.
- `frontend/app/page.tsx` — bỏ nền đặc của main, header kính mờ sticky, thanh tab gradient/translucent, hộp lỗi bo tròn + blur.
- `frontend/components/HistoryPanel.tsx` — logo/nút gradient, nhãn Sessions, session active/hover.
- `frontend/components/DocumentLibrary.tsx` — pill ready có chấm pulse + phát sáng.
- `frontend/components/UploadPanel.tsx` — icon PDF, viền đứt nét, gợi ý rút ngắn, nút gradient.
- `frontend/components/ChatPanel.tsx` — card AIRA + avatar, bong bóng người dùng gradient, chip tia lửa, ô nhập ring focus, nút gửi gradient + icon, pill trích dẫn hover.
- `frontend/components/SystemInfoPanel.tsx` — stepper pipeline, bảng cấu hình, thẻ 94,1%.
- `frontend/components/FlashcardPanel.tsx` — thẻ/pill/nút.
- `frontend/components/EmptyState.tsx` — tile icon gradient.

### Output kiểm chứng (nguyên văn)

Frontend build (`npm run build`):

```text
   Creating an optimized production build ...
 ✓ Finished writing to disk in 15ms
 ✓ Compiled successfully in 11.5s
   Linting and checking validity of types ...
   Collecting page data ...
   Generating static pages (0/5) ...
   Generating static pages (1/5)
   Generating static pages (2/5)
   Generating static pages (3/5)
   Generating static pages (4/5)
   Generating static pages (5/5)
   Finalizing page optimization ...
   Collecting build traces ...

Route (app)                         Size  First Load JS
┌ ○ /                            43.7 kB         157 kB
└ ○ /_not-found                      0 B         114 kB
+ First Load JS shared by all     122 kB
```

- Build PASS, type-check qua. Route `/` tăng 42,3 kB → 43,7 kB và First Load 156 → 157 kB — chỉ do thêm markup icon SVG inline + class, không có JS thư viện mới.

Regression (kỳ vọng nguyên trạng vì backend không đổi):

```text
Kết quả pin: 9/9 khớp

== UNIT TESTS ==
...................
----------------------------------------------------------------------
Ran 19 tests in 0.030s

OK
Tests: 19 chạy, 0 fail, 0 error, 0 skipped

== TỔNG KẾT ==
REGRESSION: PASS (đầy đủ)
```

### Chưa kiểm chứng được
- **Không chụp được ảnh kiểm chứng trực quan trong đợt này**: VM không có backend/Postgres sống nên không chạy được giao diện thật để chụp màn hình đối chiếu trước/sau. Đợt này thuần CSS/class nên rủi ro hành vi gần như bằng không, nhưng đối chiếu bằng ảnh (gradient, kính mờ, thẻ số liệu) để dành cho task chạy demo phía Antigravity (máy Kevin) hoặc staging AWS.

## 7. Đợt 3 chế độ tốc độ (2026-11-02) — backend + frontend

Kevin duyệt thêm 3 CHẾ ĐỘ TỐC ĐỘ truy xuất cho hỏi–đáp, dựa trên số liệu kiểm định Pareto đã chốt (rerank chiếm 97–99% thời gian truy xuất, tăng gần tuyến tính theo pool): `lau` = pool 40 (winner E7 nguyên bản, MẶC ĐỊNH; ExcerptHit dev 0,907, test chính thức 94,1% chỉ thuộc chế độ này), `trung_binh` = pool 20 (rerank ~53%, dev 0,884), `nhanh` = pool 10 (rerank ~28–32%, dev 0,872). Chế độ là override theo từng request; chỉ đổi pool rerank — chunking, embedding, BM25, RRF k=60, top-5, prompt, fallback giữ nguyên ở mọi chế độ. Flashcards KHÔNG áp dụng chế độ.

### Quyết định kỹ thuật (điểm truyền pool)
- Retriever **đã có sẵn** tham số `candidate_k` trong `search()` (chỉ là trước đây `api.py` luôn truyền hằng `CANDIDATE_K`). Vì vậy **không cần sửa `src/retriever.py`**: điểm truyền sạch nhất là tại hai endpoint chat trong `api.py`, nơi pool được tính một lần từ `payload.mode` rồi truyền xuống như cũ. Hành vi cũ (không gửi mode) cho kết quả y hệt: pool 40.
- Ánh xạ chế độ → pool nằm ở **một chỗ duy nhất**: `src/config.py` (`RETRIEVAL_MODES` + `DEFAULT_MODE` + hàm `candidate_k_for_mode`). Mode lạ/rỗng/None rơi về mặc định, không bao giờ ném lỗi.

### File sửa/thêm — backend
- `src/config.py` — **chỉ thêm mới** (diff với source v2: toàn bộ là dòng thêm, 0 dòng sửa/xóa — khối này và khối RATE_LIMIT của đợt 1): mục "CHẾ ĐỘ TỐC ĐỘ TRUY XUẤT" gồm `RETRIEVAL_MODES = {"lau": 40, "trung_binh": 20, "nhanh": 10}`, `DEFAULT_MODE = "lau"`, `candidate_k_for_mode(mode)`. Mọi giá trị cũ giữ nguyên từng ký tự (pin 9/9 bên dưới xác nhận; `CANDIDATE_K` vẫn 40).
- `src/schemas.py` — `ChatRequest` thêm trường tùy chọn `mode: str | None = None` (diff với v2: chỉ thêm 7 dòng này). Cả hai endpoint chat (JSON + stream) dùng chung `ChatRequest` nên đều nhận mode.
- `api.py` — import `candidate_k_for_mode` thay cho `CANDIDATE_K` (hằng này không còn được api.py dùng trực tiếp); ở cả `chat` và `chat_stream`: tính `candidate_k = candidate_k_for_mode(payload.mode)` một lần rồi truyền vào `retriever.search(candidate_k=...)`. Rate limit giữ nguyên không đổi (middleware khớp theo hậu tố path `/chat`, `/chat/stream`, áp dụng bất kể chế độ).
- `tests/test_retrieval_modes.py` — **file mới, 5 test**: 3 mode hợp lệ cho đúng pool (40/20/10); dict có đúng 3 chế độ; mặc định là `lau` và pool mặc định == `CANDIDATE_K` == 40; mode None/rỗng → 40; mode lạ ("turbo", "LAU") → 40.

### File sửa — frontend
- `frontend/lib/types.ts` — thêm `export type RetrievalMode = "nhanh" | "trung_binh" | "lau"`.
- `frontend/lib/api.ts` — `streamChat` thêm tham số tùy chọn cuối `mode?: RetrievalMode` (tương thích ngược: không truyền thì payload y hệt trước — `{message}`; có truyền thì thêm `mode`). Đây là hàm chat duy nhất của api.ts (frontend chỉ dùng đường stream; endpoint JSON phía backend cũng đã nhận mode qua `ChatRequest`).
- `frontend/app/page.tsx` — state `retrievalMode` (mặc định `"lau"`) giữ ở cấp trang nên còn hiệu lực suốt phiên làm việc của trang; `sendQuestion` truyền `retrievalMode` vào `streamChat` (áp dụng cho cả form nhập và chip câu hỏi mẫu vì dùng chung một đường gửi); truyền `retrievalMode`/`onRetrievalModeChange` xuống ChatPanel.
- `frontend/components/ChatPanel.tsx` — segmented control 3 nút (Nhanh · Trung bình · Lâu) dạng pill ngay trên hàng ô nhập, nút đang chọn gradient xanh→chàm như các nút chính, có `aria-pressed`; dưới thanh chọn là dòng chú thích đổi theo chế độ, dùng đúng số liệu đã chốt: Lâu → "Pool 40 · Chuẩn winner E7 — ExcerptHit test 94,1%"; Trung bình → "Pool 20 · Rerank nhanh hơn ~47% · ExcerptHit dev 0,884"; Nhanh → "Pool 10 · Rerank nhanh hơn ~70% · ExcerptHit dev 0,872".
- `frontend/components/SystemInfoPanel.tsx` — thêm mục "Ba chế độ truy xuất" (giữ nguyên mọi nội dung cũ): bảng 4 cột Chế độ | Pool | Thời gian rerank (tương đối) | ExcerptHit với 3 dòng — Lâu (mặc định) | 40 | 100% (chuẩn) | 0,907 (dev) · 94,1% (test); Trung bình | 20 | ~53% | 0,884 (dev); Nhanh | 10 | ~28–32% | 0,872 (dev) — và dòng ghi chú nguồn: số của Trung bình/Nhanh đo trên tập dev trong kiểm định E7, chỉ Lâu có số test chính thức 94,1%, ba chế độ chỉ khác nhau ở số ứng viên đưa vào reranker.

### Không đổi (đã đối chiếu)
- Giá trị config gốc: diff `src/config.py` với source v2 cho thấy **chỉ có dòng thêm** (khối chế độ tốc độ + khối rate limit đợt 1), không dòng nào bị sửa/xóa; regression pin 9/9 khớp (xem output dưới).
- `src/retriever.py`, `src/reranker.py`, `src/bm25.py`, `src/chunker.py`, `src/generator.py`, `src/rate_limit.py`, `requirements.txt`: không sửa trong đợt này.
- Flashcards: không truyền mode ở cả frontend lẫn backend — đã kiểm bằng grep: luồng flashcard không gọi `retriever.search` (chỉ hai endpoint chat gọi), nên luôn chạy như hiện tại.

### Output kiểm chứng (nguyên văn)

Regression (`HF_HOME=~/workspace/rag-audit/run/hf-cache HF_HUB_OFFLINE=1 .venv-build/bin/python regression/run_regression.py`):

```text
== PIN CẤU HÌNH WINNER E7 ==
[OK ] CHUNK_MODE = 'token' (chốt: 'token')
[OK ] CHUNK_SIZE_TOKENS = 512 (chốt: 512)
[OK ] CHUNK_OVERLAP_TOKENS = 51 (chốt: 51)
[OK ] RETRIEVAL_MODE = 'hybrid' (chốt: 'hybrid')
[OK ] BM25_K1 = 1.5 (chốt: 1.5)
[OK ] BM25_B = 0.75 (chốt: 0.75)
[OK ] RRF_K = 60 (chốt: 60)
[OK ] CANDIDATE_K = 40 (chốt: 40)
[OK ] TOP_K = 5 (chốt: 5)
Kết quả pin: 9/9 khớp

== UNIT TESTS ==
........................
----------------------------------------------------------------------
Ran 24 tests in 0.040s

OK
Tests: 24 chạy, 0 fail, 0 error, 0 skipped

== TỔNG KẾT ==
REGRESSION: PASS (đầy đủ)
```

- Tổng unit test: **24** (19 cũ + **5 mới** của `test_retrieval_modes.py`), 0 skipped — PASS đầy đủ.
- `py_compile` cho `api.py`, `src/config.py`, `src/schemas.py`, `src/retriever.py`, `tests/test_retrieval_modes.py`: OK.

Frontend build (`npm run build`):

```text
 ✓ Compiled successfully in 13.6s
   Linting and checking validity of types ...
   Collecting page data ...
   Generating static pages (0/5)
   Generating static pages (1/5)
   Generating static pages (2/5)
   Generating static pages (3/5)
   Generating static pages (4/5)
   Generating static pages (5/5)
   Finalizing page optimization ...
   Collecting build traces ...

Route (app)                         Size  First Load JS
┌ ○ /                            44.4 kB         158 kB
└ ○ /_not-found                      0 B         114 kB
+ First Load JS shared by all     123 kB
```

- Build PASS, type-check qua. Route `/` tăng 43,7 kB → 44,4 kB, First Load 157 → 158 kB (segmented control + bảng chế độ ở tab Giới thiệu), không thêm dependency nào.

### Chưa kiểm chứng được
- **Chưa kiểm chứng HTTP thật việc truyền mode**: VM không có backend/Postgres sống nên chưa chạy được request chat thật để xác nhận pool thay đổi theo mode ở mức HTTP. Đã kiểm chứng ở mức: ánh xạ config bằng unit test, cú pháp bằng py_compile, type-check + build frontend, và đọc lại toàn bộ đường truyền (UI → api.ts → ChatRequest.mode → candidate_k_for_mode → retriever.search). Lưu ý thêm: venv build không có pydantic/fastapi nên không import được `src/schemas.py`/`api.py` trong môi trường này (giới hạn đã biết từ các đợt trước; trường `mode: str | None = None` theo đúng mẫu `title: str | None = None` sẵn có trong cùng file). Phần chạy thật + chụp ảnh đối chiếu (segmented control, dòng chú thích, bảng ba chế độ) để dành cho task phía Antigravity (máy Kevin) hoặc staging AWS.

## 8. Đợt sửa đóng gói triển khai (2026-11-02) — sửa 4 lỗi chặn deploy + siết rò lỗi

Một đợt rà soát độc lập kết luận logic lõi đạt (regression 24/24, winner nguyên vẹn) nhưng có 4 lỗi ĐÓNG GÓI chặn triển khai. Đợt này chỉ sửa đóng gói/cấu hình chạy — **không đổi logic RAG, giá trị config gốc, prompt, và hợp đồng API** (ngoại lệ duy nhất đã được phép: nội dung thông điệp của sự kiện SSE `error`).

### 1. CORS theo env (`api.py`)
- Thêm `import os`; ngay trên khối CORS tính hằng `CORS_ORIGINS` từ `os.getenv("AIRA_CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")` (tách bằng dấu phẩy, strip khoảng trắng, bỏ phần tử rỗng) và `allow_origins=CORS_ORIGINS`. Env không đặt → hành vi local y như trước.
- Đã chạy thử đúng biểu thức trong code: env trống → `['http://localhost:3000', 'http://127.0.0.1:3000']`; env đặt `https://aira.example.com, https://app.example.com` → đúng 2 origin đó.

### 2. Frontend Docker dùng npm thống nhất (`frontend/Dockerfile`, thêm `frontend/.dockerignore`)
- Bỏ hẳn pnpm (corepack, `pnpm install --frozen-lockfile`, `pnpm build`, `pnpm start`): `pnpm-lock.yaml` đã lệch, thiếu `react-markdown`. Nay: `COPY package.json package-lock.json ./` → `npm ci` → `npm run build` → `CMD ["npm", "start"]`. Giữ nguyên build-arg `NEXT_PUBLIC_API_URL` (vẫn là ARG + ENV trước bước build).
- Đã đối chiếu trước khi sửa: `package-lock.json` (lockfileVersion 3) ghi đúng 4 dependency của `package.json` (next 15.5.27, react 19.1.0, react-dom 19.1.0, react-markdown ^10.1.0) — root deps trong lock **khớp tuyệt đối** package.json nên `npm ci` hợp lệ. File `pnpm-lock.yaml`/`pnpm-workspace.yaml` vẫn để nguyên trong cây làm việc, chỉ không còn được Dockerfile dùng.
- Thêm `frontend/.dockerignore` gồm `node_modules` và `.next`.

### 3. Tự khởi tạo bảng DB (thêm `docker-entrypoint.sh`, sửa `Dockerfile` backend)
- Cơ chế: container backend nay chạy qua entrypoint thay vì CMD uvicorn trực tiếp. `docker-entrypoint.sh` (`#!/bin/sh`, `set -e`): chạy `python init_db.py` trước, rồi `exec uvicorn api:app --host 0.0.0.0 --port 8000` (exec để uvicorn thành tiến trình chính). Nếu init DB lỗi, container dừng ngay (`set -e`) — API không phục vụ khi bảng chưa sẵn sàng.
- `init_db.py` vốn đã an toàn khi chạy lại: `Base.metadata.create_all` + `CREATE EXTENSION IF NOT EXISTS vector` + `CREATE INDEX IF NOT EXISTS` HNSW — chạy mỗi lần container khởi động là vô hại.
- `Dockerfile`: sau `COPY . .` thêm `RUN chmod +x docker-entrypoint.sh` và thay CMD bằng `ENTRYPOINT ["./docker-entrypoint.sh"]`. File script cũng đã chmod +x ngay trong cây làm việc. Trong docker-compose, backend vốn `depends_on: postgres (service_healthy)` nên khi entrypoint chạy, Postgres đã sẵn sàng nhận kết nối.

### 4. Đóng cổng Postgres + mật khẩu qua env (`docker-compose.yml`)
- Xóa toàn bộ khối `ports: - "5432:5432"` của service postgres — Postgres chỉ reachable trong mạng nội bộ compose (backend gọi qua tên service `postgres:5432` như cũ).
- `POSTGRES_PASSWORD: [REDACTED-LOCAL-DEV]` (cứng) → `POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}`; `DATABASE_URL` của backend từ chuỗi cứng `postgresql+asyncpg://[REDACTED-LOCAL-DEV]@postgres:5432/rag` → `postgresql+asyncpg://[REDACTED-LOCAL-DEV]@postgres:5432/rag` — mật khẩu chỉ khai báo một nơi (biến `POSTGRES_PASSWORD` trong `.env` cạnh compose/shell; compose tự đọc `.env` của project để nội suy). User/db giữ nguyên `rag`/`rag`.

### 5. `.dockerignore` backend (chỉ loại khỏi build context — KHÔNG xóa file nào)
Bổ sung: `.venv-build`, `ui-screenshots*/`, `benchmark-v1/`, `evaluation_v3/`, `evaluation_v4/`, `TASK-008-RESULT.md`, `CLEAN_PACKAGE_NOTES.md`, `PATCH_NOTES.md`, `PATCH_NOTES_V2.md`, `README_FLASHCARD_PHASE1.txt`, `REFACTOR_BRIEF.md`, `frontend_modular_ui.png`. Đã xác nhận các thư mục/file này vẫn nguyên vẹn trong cây làm việc sau khi sửa (chỉ bị loại khỏi Docker build context).

### 6. Siết lỗi stream (`api.py`, khối `except` của endpoint chat stream)
- Trước: sự kiện SSE `error` gửi `"message": str(error)` cho client — lộ chi tiết nội bộ. Nay: client chỉ nhận thông điệp chung **"Đã xảy ra lỗi khi xử lý yêu cầu. Vui lòng thử lại."**; dòng `print("Streaming error:", error)` phía server giữ nguyên để log vẫn có chi tiết. Grep sau sửa: `str(error)` không còn trong code gửi client (chỉ còn xuất hiện trong comment giải thích).

### 7. `.env.example`
Bổ sung 3 biến kèm chú thích ngắn (không sửa dòng nào sẵn có): `AIRA_RATE_LIMIT_PER_MIN=30`, `AIRA_CORS_ORIGINS=` (ghi rõ để trống = mặc định 2 origin localhost), `POSTGRES_PASSWORD=` (ghi rõ bắt buộc đặt giá trị riêng khi chạy compose).

### File sửa/thêm đợt này
- Sửa: `api.py` (import os + CORS theo env + thông điệp SSE error), `Dockerfile` (entrypoint backend), `frontend/Dockerfile` (npm), `docker-compose.yml`, `.dockerignore`, `.env.example`.
- Thêm: `docker-entrypoint.sh`, `frontend/.dockerignore`.
- Không sửa: mọi file `src/*.py` (kể cả `src/config.py` — giá trị gốc nguyên vẹn, pin 9/9 bên dưới xác nhận), `requirements.txt`, toàn bộ code frontend (`app/`, `components/`, `lib/`).

### Output kiểm chứng (nguyên văn)

Regression (`HF_HOME=~/workspace/rag-audit/run/hf-cache HF_HUB_OFFLINE=1 NO_PROXY=localhost,127.0.0.1 .venv-build/bin/python regression/run_regression.py`), kèm `py_compile api.py` = OK:

```text
== PIN CẤU HÌNH WINNER E7 ==
[OK ] CHUNK_MODE = 'token' (chốt: 'token')
[OK ] CHUNK_SIZE_TOKENS = 512 (chốt: 512)
[OK ] CHUNK_OVERLAP_TOKENS = 51 (chốt: 51)
[OK ] RETRIEVAL_MODE = 'hybrid' (chốt: 'hybrid')
[OK ] BM25_K1 = 1.5 (chốt: 1.5)
[OK ] BM25_B = 0.75 (chốt: 0.75)
[OK ] RRF_K = 60 (chốt: 60)
[OK ] CANDIDATE_K = 40 (chốt: 40)
[OK ] TOP_K = 5 (chốt: 5)
Kết quả pin: 9/9 khớp

== UNIT TESTS ==
........................
----------------------------------------------------------------------
Ran 24 tests in 0.637s

OK
Tests: 24 chạy, 0 fail, 0 error, 0 skipped

== TỔNG KẾT ==
REGRESSION: PASS (đầy đủ)
```

Frontend build (`npm run build`): PASS, route `/` 44,4 kB / First Load 158 kB — không đổi so với đợt 7 (đợt này không đụng code frontend).

Kiểm tra cú pháp `docker-compose.yml` bằng **python YAML parse** (máy này KHÔNG có Docker — `docker: command not found` — nên không chạy được `docker compose config` cũng như không build image thật):

```text
service postgres: ports published = []
service backend: ports published = ['8000:8000']
service frontend: ports published = ['3000:3000']
POSTGRES_PASSWORD = ${POSTGRES_PASSWORD}
DATABASE_URL      = postgresql+asyncpg://[REDACTED-LOCAL-DEV]@postgres:5432/rag
```

→ Postgres không còn publish cổng nào; backend vẫn publish 8000; mật khẩu ở cả hai chỗ đều là biến nội suy `${POSTGRES_PASSWORD}`.

Grep chứng minh trên `docker-compose.yml`: không còn chuỗi `rag:rag`; không còn `"5432:5432"` (số 5432 chỉ còn trong comment giải thích và trong `postgres:5432` nội bộ của DATABASE_URL — địa chỉ mạng nội bộ compose, không phải publish). Cú pháp shell của entrypoint: `sh -n docker-entrypoint.sh` = OK.

### Chưa kiểm chứng được
- **Chưa build Docker image thật và chưa chạy `docker compose up`**: VM này không có Docker. Các thay đổi Docker/compose mới kiểm chứng ở mức đọc code + YAML parse + đối chiếu lockfile như trên. Lần chạy compose thật đầu tiên (máy Kevin hoặc VPS khi deploy) cần xác nhận: `npm ci` trong image frontend chạy trọn, entrypoint backend tạo bảng xong mới mở cổng 8000, và biến `POSTGRES_PASSWORD` đã được đặt trong `.env` (nếu quên đặt, compose sẽ cảnh báo biến trống và Postgres từ chối khởi động với mật khẩu rỗng — đây là cố ý để không ai deploy với mật khẩu mặc định).
