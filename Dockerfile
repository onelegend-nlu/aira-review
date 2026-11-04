# AIRA backend — FastAPI + mô hình local (e5-small + bge-reranker-base).
# Mô hình được tải sẵn lúc build để lần chạy đầu không phải chờ.
FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    HF_HOME=/app/hf-cache \
    PIP_NO_CACHE_DIR=1

COPY requirements.txt .
RUN pip install -r requirements.txt

# Tải sẵn embedding model, reranker và tokenizer vào image.
RUN python -c "from sentence_transformers import SentenceTransformer, CrossEncoder; \
SentenceTransformer('intfloat/multilingual-e5-small'); \
CrossEncoder('BAAI/bge-reranker-base'); \
from transformers import AutoTokenizer; \
AutoTokenizer.from_pretrained('intfloat/multilingual-e5-small')"

COPY . .

# Entrypoint chạy init_db.py (tạo bảng) rồi mới exec uvicorn,
# để API chỉ bắt đầu phục vụ sau khi DB đã sẵn sàng.
RUN chmod +x docker-entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["./docker-entrypoint.sh"]
