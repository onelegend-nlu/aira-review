import os

from dotenv import load_dotenv

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


# =========================================================
# LOAD ENV
# =========================================================

load_dotenv()


DATABASE_URL = os.getenv("DATABASE_URL")


if not DATABASE_URL:
    raise ValueError(
        "Không tìm thấy DATABASE_URL trong file .env"
    )


# =========================================================
# ENGINE
# =========================================================

engine: AsyncEngine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True
)


# =========================================================
# SESSION FACTORY
# =========================================================

async_session_factory = async_sessionmaker(
    engine,
    expire_on_commit=False
)


# =========================================================
# SESSION HELPER
# =========================================================

async def get_session() -> AsyncSession:
    return async_session_factory()