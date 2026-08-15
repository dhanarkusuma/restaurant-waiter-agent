import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from apps.backend.app.config import settings
from apps.backend.app.database import Base, get_db
from apps.backend.app.main import app

# In-memory SQLite for fast, isolated unit & integration testing
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
async def setup_test_db():
    # Keep tests isolated from local .env webhook secret
    orig_secret = settings.TELEGRAM_WEBHOOK_SECRET
    settings.TELEGRAM_WEBHOOK_SECRET = ""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    settings.TELEGRAM_WEBHOOK_SECRET = orig_secret
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def db_session():
    async with TestSessionLocal() as session:
        yield session


@pytest.fixture
async def client(db_session: AsyncSession):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
