# Brief đợt gọn cấu trúc AIRA (chỉ thi công SAU khi TASK-006 nghiệm thu ĐẠT)

Người đặt: Muse. Kevin đã duyệt 2026-11-02 11:42 +07.
Phạm vi: thay đổi CƠ HỌC về tổ chức code. Cấm thay đổi: thuật toán retrieval, nội dung prompt, giá trị config winner, hợp đồng API (URL/payload/response giữ nguyên từng trường).

## Việc 1 — Tách api.py thành routers
- Tạo package `routers/` với: `system.py` (root/health), `sessions.py`, `documents.py` (upload/list/delete + ingest nền), `chat.py` (chat + chat/stream), `flashcards.py`.
- `api.py` chỉ còn: tạo app, lifespan, 2 middleware (API key, rate limit), include_router. Mục tiêu < 200 dòng.
- Chuyển helper về đúng chủ: `build_citations`, `citation_coverage`, `is_insufficient_answer` → `src/chat_service.py`; `safe_pdf_name` → `src/document_service.py`; `sse` → `src/chat_service.py` hoặc module `src/sse.py` riêng.
- Route chỉ validate + gọi service; không chứa logic nghiệp vụ mới.

## Việc 2 — Tách hai module ôm hai việc
- `src/generator.py`: chuyển toàn bộ chuỗi mẫu prompt (gồm cả prompt flashcard) sang `src/prompts.py` dạng hằng số/fàm build; `build_flashcards_prompt` + `parse_flashcards_json` chuyển về `src/flashcard_service.py` (Generator không còn biết flashcard). Nội dung prompt giữ NGUYÊN VĂN từng ký tự.
- `src/retriever.py`: tách `normalize_for_follow_up_detection`, `needs_conversation_context`, `build_contextual_query` và các helper liên quan sang `src/query_rewriter.py`; Retriever gọi lại module này, hành vi không đổi.

## Việc 3 — Dọn cây production
- Chuyển `batch_test.py`, `create_session.py`, `ingest_pdf.py` → `archive/dev-scripts/`; chuyển `evaluation_v3/` → `archive/evaluation_v3/` (evaluation_v4 giữ nguyên — Quality Lab dùng bản mới nhất; nếu nghi ngờ v3 còn được tham chiếu ở đâu thì grep trước và ghi lại, không tự ý chuyển khi còn tham chiếu sống).

## Việc 4 — Ba cải tiến nhỏ
- Validate lúc khởi động trong lifespan: thiếu `GEMINI_API_KEY` → log cảnh báo đỏ rõ ràng ngay khi start (không crash, vì /health vẫn phải sống).
- `scripts/smoke.py` chuẩn hoá bài smoke TASK-004/005/006: health → tạo session → nạp PDF thử (tham số đường dẫn + mã kỳ vọng) → câu trong tài liệu (kỳ vọng chứa mã + ≥1 citation) → câu ngoài tài liệu (kỳ vọng đúng nguyên văn chuỗi từ chối) → in PASS/FAIL từng mục + exit code. Từ nay nghiệm thu ở mọi môi trường dùng script này.
- Log thời gian từng tầng trong chat: embed_ms, bm25_ms, rerank_ms, generate_ms vào log có cấu trúc (1 dòng JSON/request) — chỉ đo, không đổi hành vi.

## Lưới an toàn (bắt buộc, ghi nguyên văn vào BUILD_NOTES đợt này)
1. `regression/run_regression.py` PASS đầy đủ (pin 9/9, 19/19 tests) sau refactor.
2. Thêm test đơn vị cho `query_rewriter` (ít nhất 3 ca: câu độc lập, câu nối tiếp có đại từ, câu nối tiếp theo chủ đề) và cho `prompts` (build_prompt cho ra chuỗi chứa đúng các mảnh bắt buộc).
3. `scripts/smoke.py` không chạy được trên VM (thiếu môi trường) → ghi rõ; bài smoke HTTP đầy đủ sẽ do TASK-007 phía Antigravity chạy trên máy Kevin với cùng script này, đối chiếu kết quả khớp TASK-006.
4. compileall sạch; diff tổng: không file nào trong nhóm đông cứng (chunker/bm25/reranker/embedder/parser) bị sửa.
