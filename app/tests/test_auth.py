import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy import select
from app.main import app
from app.db.database import Base, get_db
from app.db.models.user import User
from passlib.context import CryptContext

pytestmark = pytest.mark.asyncio

DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def override_get_db():
    async with TestingSessionLocal() as session:
        yield session


app.dependency_overrides[get_db] = override_get_db


@pytest_asyncio.fixture(scope="session")
async def initialized_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client(initialized_db):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


@pytest_asyncio.fixture(scope="session")
async def test_user(initialized_db):
    async with TestingSessionLocal() as session:
        stmt = select(User).where(User.email == "test@example.com")
        existing = await session.scalar(stmt)
        if existing:
            return existing
        user = User(
            name="Test User",
            email="test@example.com",
            hashed_password=pwd_context.hash("password"),
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, test_user: User):
    response = await client.post(
        "/auth/login",
        data={"username": test_user.email, "password": "password"},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_fail(client: AsyncClient, test_user: User):
    response = await client.post(
        "/auth/login",
        data={"username": test_user.email, "password": "wrong_password"},
    )
    assert response.status_code == 400, response.text


@pytest.mark.asyncio
async def test_get_me(client: AsyncClient, test_user: User):
    login_response = await client.post(
        "/auth/login",
        data={"username": test_user.email, "password": "password"},
    )
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    me_response = await client.get("/auth/me", headers=headers)
    assert me_response.status_code == 200, me_response.text
    me_data = me_response.json()
    assert me_data["email"] == test_user.email
    assert me_data["id"] == test_user.id
