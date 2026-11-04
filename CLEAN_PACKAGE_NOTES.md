# CLEAN PACKAGE NOTES

Bản này được tạo từ project working ngày 2026-10-04 và không thay đổi logic production.

## Đã loại bỏ
- `.env` thật
- Git metadata
- Python/Next caches
- runtime PDF uploads
- corpus ZIP 30 PDF (~48 MB)
- embedding cache V3
- các experiment cũ V1/V2

## Đã giữ
- backend/FastAPI và toàn bộ `src/`
- frontend hiện tại, gồm chat, full-chunk citation và flashcards
- Docker/Postgres init
- V3 retrieval evaluator cùng kết quả retrieval cuối
- V4 generation evaluator cùng kết quả cuối
- benchmark CSV V4

## Lưu ý
Nếu cần tái chạy benchmark corpus 30 PDF, copy `data_vie_final_30.zip` trở lại project root.
