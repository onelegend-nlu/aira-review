import asyncio

from sqlalchemy import text

from src.database import engine
from src.models import Base


async def main():

    print(
        "Connecting to PostgreSQL..."
    )


    async with engine.begin() as connection:

        # Đảm bảo pgvector extension tồn tại
        await connection.execute(
            text(
                "CREATE EXTENSION "
                "IF NOT EXISTS vector"
            )
        )


        print(
            "Creating database tables..."
        )


        await connection.run_sync(
            Base.metadata.create_all
        )


        # HNSW index cho vector search.
        # CREATE INDEX IF NOT EXISTS nên chạy lại
        # init_db.py trên database cũ là an toàn
        # và sẽ bổ sung index còn thiếu.
        await connection.execute(
            text(
                "CREATE INDEX IF NOT EXISTS "
                "ix_chunks_embedding_hnsw "
                "ON chunks USING hnsw "
                "(embedding vector_cosine_ops) "
                "WITH (m = 16, ef_construction = 64)"
            )
        )


    print(
        "Database initialized successfully!"
    )


    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(
        main()
    )