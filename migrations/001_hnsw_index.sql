-- HNSW index cho tìm kiếm cosine trên chunks.embedding.
-- Chạy trên database đã tồn tại (hoặc đơn giản là chạy lại
-- `python init_db.py`, script đó đã tự tạo index này).
CREATE INDEX IF NOT EXISTS ix_chunks_embedding_hnsw
    ON chunks USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);
