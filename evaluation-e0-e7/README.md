# Bản tổng kết kiểm định E0–E7 của AIRA

Nguồn gốc: các file này lấy từ máy msi (thư mục `experiments/`), đồng bộ lên repo ngày 2026-11-04 theo yêu cầu của chủ repo để tiện tra cứu. Antigravity chuẩn bị file, Muse quét secret rồi mới push. Không chứa key, token hay nội dung file `.env`.

## Các file trong thư mục này

- `overall_summary.md` (1.325 dòng): bảng tổng kết đầy đủ các cấu hình thí nghiệm — Hit@5, PageHit@5, ExcerptHit@5, MRR, nDCG@5, CandRecall@40 theo từng biến thể chunking/retrieval.
- `summary_ctrl-fixed.md`: cấu hình đối chứng (chunker gốc theo câu).
- `summary_tok128o10.md`: chunk token 128, overlap 13.
- `summary_tok256o10.md`: chunk token 256, overlap 26.
- `summary_tok512o0.md`: chunk token 512, overlap 0.
- `summary_tok512o10.md`: chunk token 512, overlap 51 — cấu hình thắng E7 (cùng với hybrid + RRF k=60 + pool 40 + top-5).
- `summary_tok512o20.md`: chunk token 512, overlap 102.
- `TASK-008-RESULT.md`: kết quả task 008 liên quan.

## Liên hệ với các tài liệu khác trong repo

- Bộ câu hỏi kiểm định: `aira_v4_vietnamese_final_120.csv` (120 câu tiếng Việt, mỗi câu có đáp án vàng và đoạn vàng).
- Tóm tắt quá trình và kết quả chốt: `PATCH_NOTES_V2.md`, `BUILD_NOTES.md`.
- Số test chính thức 94,1% (so với 70,6% cấu hình gốc) được hiển thị trong tab Giới thiệu của app (`frontend/components/SystemInfoPanel.tsx`).

## Lưu ý

- `benchmark-v1/` không tồn tại thật: cái tên đó chỉ là mục phòng ngừa trong `.dockerignore`. Bộ đánh giá giai đoạn 1 thật tên là `evaluation/`, không nằm trong đợt đồng bộ này.
- Đợt này chỉ đồng bộ các file `.md` tóm tắt. Dữ liệu thô (JSON/JSONL), checkpoint, cache chunks/embeddings và các file zip vẫn nằm trên máy msi, chưa đưa lên repo.
