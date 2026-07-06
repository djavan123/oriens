import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.models.user import User
from app.utils.auth import COOKIE_NAME, create_access_token, hash_password

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

# Senha e e-mail do usuário de teste (reusados pelos testes de auth).
TEST_EMAIL = "test@oriens.dev"
TEST_PASSWORD = "senha123"


@pytest_asyncio.fixture(scope="function")
async def db_engine():
    # StaticPool: uma única conexão compartilhada — o :memory: sobrevive entre
    # sessões dentro do mesmo engine (senão cada conexão teria um banco vazio).
    engine = create_async_engine(
        TEST_DB_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        import app.models  # noqa: F401 — registra todos os models
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db(db_engine) -> AsyncSession:
    factory = async_sessionmaker(db_engine, expire_on_commit=False)
    async with factory() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def test_user(db: AsyncSession) -> User:
    user = User(
        email=TEST_EMAIL,
        password=hash_password(TEST_PASSWORD),
        name="Test User",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest_asyncio.fixture(scope="function")
async def client(db: AsyncSession, test_user: User) -> AsyncClient:
    """Cliente HTTP autenticado como test_user."""
    from app.main import app

    async def _override_get_db():
        yield db

    app.dependency_overrides[get_db] = _override_get_db
    token = create_access_token(test_user.id)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        c.cookies.set(COOKIE_NAME, token)
        yield c
    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def anon_client(db: AsyncSession) -> AsyncClient:
    """Cliente HTTP não autenticado (usa o mesmo banco de teste)."""
    from app.main import app

    async def _override_get_db():
        yield db

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()
