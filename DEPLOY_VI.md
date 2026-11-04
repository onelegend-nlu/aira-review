# DEPLOY AIRA LÊN MẠNG — Hướng dẫn theo hướng khuyến nghị: VPS + Docker Compose

## Vì sao hướng này
App cần Postgres+pgvector và ~2GB mô hình ML chạy local (e5-small +
bge-reranker-base). Các free tier của Render/Railway/Fly (512MB–1GB RAM,
cold start) không đủ cho hai mô hình; HF Spaces chạy được nhưng phải bẻ
Postgres đi chỗ khác. Một VPS nhỏ chạy trọn gói bằng docker-compose là
đường thẳng nhất, chi phí cố định, không cold start.

## Chuẩn bị
- VPS RAM tối thiểu 4GB (khuyến nghị 2 vCPU/4GB; Hetzner CX22 ~€4.5/tháng
  hoặc Vultr $6/tháng đều đủ). OS Ubuntu 22.04/24.04.
- (Khuyến nghị) một tên miền trỏ về IP VPS — có domain thì mới cấp được
  HTTPS miễn phí qua Caddy/Let's Encrypt. Chưa có domain vẫn chạy được
  qua IP + cổng 3000 để demo.

## Các bước
1. Cài Docker + compose plugin trên VPS (script get.docker.com chính thức).
2. Copy thư mục project lên VPS (scp/git), `cd` vào thư mục.
3. Tạo file `.env` cạnh `docker-compose.yml`:
   ```
   GEMINI_API_KEY=<key của bạn>
   AIRA_API_KEY=<đặt một khóa dài ngẫu nhiên — BẮT BUỘC khi public>
   NEXT_PUBLIC_API_URL=http://<IP-VPS>:8000
   ```
   (Có domain + reverse proxy HTTPS thì NEXT_PUBLIC_API_URL =
   https://api.<domain> và sửa lại trước khi build frontend — biến này
   được nhúng lúc build.)
4. `docker compose up -d --build` — lần đầu build backend sẽ tải ~2GB
   mô hình vào image, mất vài phút. Xong: frontend ở cổng 3000, API ở 8000.
5. Kiểm tra: mở `http://<IP-VPS>:3000`, tạo session, nạp một PDF, hỏi thử.
   Gọi API không kèm header `X-API-Key` phải bị 401.
6. Đặt reverse proxy (Caddy là gọn nhất: tự HTTPS) trước frontend/backend
   nếu có domain; đồng thời cân nhắc chỉ mở cổng 80/443 ra ngoài, đóng
   5432 (Postgres không nên lộ — compose hiện chỉ map 5432 cho local,
   khi public hãy bỏ dòng ports của postgres).

## Lưu ý vận hành
- Dữ liệu nằm ở 2 volume docker: `postgres_data` (DB) và `app_data`
  (file upload). Backup = backup 2 volume này.
- Đổi cấu hình truy hồi/chunking qua biến môi trường `AIRA_*` (xem
  PATCH_NOTES_V2.md) rồi `docker compose up -d` lại. Lưu ý: đổi chế độ
  chunking chỉ áp dụng cho tài liệu nạp MỚI; tài liệu cũ giữ chunk cũ.
- Độ trễ trả lời trên CPU VPS khoảng 5–30 giây/câu tùy độ dài tài liệu
  (rerank là khâu nặng nhất). Cần nhanh hơn: hạ `AIRA_CANDIDATE_K=20`
  hoặc dùng VPS có nhiều vCPU hơn.

## Phương án thay thế (không khuyến nghị chính)
- Frontend lên Vercel (free) + backend/DB ở VPS như trên: được nếu muốn
  tận dụng CDN cho giao diện; nhớ NEXT_PUBLIC_API_URL trỏ về backend.
- Railway/Render trả phí (~$20+/tháng cho đủ RAM): ít việc sysadmin hơn
  nhưng đắt hơn VPS cho cùng cấu hình.
