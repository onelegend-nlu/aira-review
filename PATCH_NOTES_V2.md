# PATCH NOTES V2 — Áp cấu hình thắng E7 vào app + sẵn sàng deploy

V2 = V1 (gói vá P0/P1) + thay kiến trúc truy hồi theo kết quả thí nghiệm
E0–E7 đã kiểm chứng trên test giữ kín (xem bản tổng kết thí nghiệm).
Mọi thay đổi đều truy về được một con số đo cụ thể.

## 1. Chunking: token 512 / overlap 51 (mặc định mới)
- Thêm `chunk_pages_token` trong `src/chunker.py` — port nguyên bản cửa sổ
  trượt token theo trang của harness thí nghiệm (tokenizer e5-small).
- `chunk_pages_production` là điểm vào duy nhất của ingest; chế độ chọn qua
  `AIRA_CHUNK_MODE` (`token` mặc định, `sentence` = hành vi v1).
- Bằng chứng: trên test giữ kín, chunk 512/10% cho excerpt-hit 0.941 so với
  0.706 của chunker gốc 100 từ (E7); overlap 0% kém rõ (0.853), 20% hòa 10%.

## 2. Retrieval: hybrid BM25 + dense, RRF, pool 40
- Thêm `src/bm25.py`: Okapi BM25 + RRF — port nguyên bản thuật toán của
  harness (tokenize âm tiết tiếng Việt, IDF Lucene, k1=1.5, b=0.75, RRF k=60).
- `Retriever.search`: dense top-40 (pgvector) + BM25 top-40 trên chunk của
  session (index cache theo session, invalidate khi số chunk đổi) → hợp
  nhất RRF thành pool 40 → rerank → top-5. `AIRA_RETRIEVAL_MODE=dense`
  quay về hành vi v1.
- Bằng chứng: E1/E2 cho thấy nút cổ chai của hệ cũ là pool 10; E7: bản
  hybrid_rr40 thắng production +23.5 điểm excerpt-hit trên test
  (CI [+0.118, +0.382], McNemar p=0.0078). E4: top-5 là điểm ngọt về
  chất lượng/token ngữ cảnh; top-8 không đáng.
- E6 (generation, 33 ca V4): acceptance 88.9% → 96.3%, grounded giữ 85.2%,
  OOD/hallucination không đổi; độ trễ tăng (rerank 40 cặp chunk dài trên
  CPU ~29s/ca ở máy đo) — nếu cần giảm độ trễ trước mắt: hạ
  `AIRA_CANDIDATE_K` xuống 20 (E2 cho thấy với hybrid, pool 20 không thua
  10/40 trên chunker câu; với chunk 512 đây là đánh đổi cần đo lại).

## 3. Cấu hình tập trung (src/config.py)
`AIRA_CHUNK_MODE`, `AIRA_CHUNK_SIZE_TOKENS=512`,
`AIRA_CHUNK_OVERLAP_TOKENS=51`, `AIRA_RETRIEVAL_MODE=hybrid`,
`AIRA_BM25_K1/B`, `AIRA_RRF_K=60`, `AIRA_CANDIDATE_K=40` (đổi từ 10),
`AIRA_TOP_K=5`.

## 4. Deploy
- `Dockerfile` backend (tải sẵn 2 mô hình vào image), `frontend/Dockerfile`,
  `docker-compose.yml` đủ 3 service: postgres + backend + frontend.
  Xem `DEPLOY_VI.md`.

## 5. Kiểm chứng bản v2 này
- Unit tests: 12/12 pass (gồm test mới cho BM25/RRF và token chunker;
  2 test ban đầu sai tiền đề do người viết test — đã sửa test, không sửa code).
- Smoke test API thật trên Postgres + pgvector: **10/10 PASS** — health,
  session, upload, ingest (trang dài 5 chunk token thay vì ~13 chunk từ),
  hỏi đáp có trích dẫn, câu hỏi chứa mã hiếm KX-7741 (chân BM25) trả lời
  đúng, câu ngoài miền trả fallback nguyên văn + 0 trích dẫn, flashcards.

## Chưa làm (ngoài phạm vi v2)
- Tách frontend `page.tsx` (2.405 dòng) thành components — món nợ kỹ thuật
  còn lại, không ảnh hưởng chạy/deploy.
- Alembic migrations (vẫn dùng init_db + migrations/*.sql thủ công).
