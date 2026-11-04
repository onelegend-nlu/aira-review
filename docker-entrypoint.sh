#!/bin/sh
# Entrypoint của container backend:
# 1) Chạy init_db.py để tạo bảng trước khi API phục vụ
#    (init_db.py dùng create_all + CREATE EXTENSION/INDEX
#    IF NOT EXISTS nên chạy lại nhiều lần là vô hại).
# 2) exec uvicorn để nó trở thành tiến trình chính (PID 1).
# set -e: nếu khởi tạo DB lỗi thì container dừng ngay,
# không phục vụ API khi bảng chưa sẵn sàng.
set -e

python init_db.py

exec uvicorn api:app --host 0.0.0.0 --port 8000
