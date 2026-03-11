"""
pytest fixtures for AgentFlow backend tests.

Uses SQLite in-memory via aiosqlite so tests never touch PostgreSQL.
"""
import os
import sys
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# ---------------------------------------------------------------------------
# Ensure the backend package root is on sys.path so imports resolve correctly
# even when pytest is invoked from a different directory.
# ---------------------------------------------------------------------------
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

# ---------------------------------------------------------------------------
# Override DATABASE_URL + other required settings BEFORE importing config,
# so that pydantic-settings picks up the test values.
# ---------------------------------------------------------------------------
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-not-for-production")
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "15")
os.environ.setdefault("E2B_API_KEY", "e2b_testkey12345678901234")
os.environ.setdefault("OPENAI_API_KEY", "sk-test00000000000000000000")
os.environ.setdefault("FIRECRAWL_API_KEY", "fc-testkey1234567890123456")
os.environ.setdefault("RESULTS_DIR", "/tmp/agentflow_test_results")

# Now it is safe to import application code.
from database import get_db  # noqa: E402
from models import Base  # noqa: E402

# ---------------------------------------------------------------------------
# In-memory SQLite engine shared for the whole test session
# ---------------------------------------------------------------------------
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

_test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)

_TestSessionLocal = async_sessionmaker(
    bind=_test_engine,
    expire_on_commit=False,
    class_=AsyncSession,
)


# ---------------------------------------------------------------------------
# Session-scoped table creation / teardown
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_tables():
    """Create all ORM tables once before the test session, drop them after."""
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


# ---------------------------------------------------------------------------
# Per-test DB session — rolls back after each test to keep isolation
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture()
async def db() -> AsyncGenerator[AsyncSession, None]:
    """Yield a transactional DB session that is rolled back after each test."""
    async with _TestSessionLocal() as session:
        yield session
        await session.rollback()


# ---------------------------------------------------------------------------
# FastAPI app fixture — overrides the get_db dependency
# ---------------------------------------------------------------------------


@pytest.fixture()
def app(db: AsyncSession):
    """Return the FastAPI app with its DB dependency overridden to use SQLite."""
    from main import app as fastapi_app

    async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db

    fastapi_app.dependency_overrides[get_db] = _override_get_db
    yield fastapi_app
    fastapi_app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Async HTTP test client
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture()
async def client(app) -> AsyncGenerator[AsyncClient, None]:
    """Yield an AsyncClient wired to the test FastAPI app."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac
