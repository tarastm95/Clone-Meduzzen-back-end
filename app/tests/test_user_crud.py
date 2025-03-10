import asyncio
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy import text

from app.main import app
from app.db.database import Base, get_db
from app.db.models.user import User
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False
)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture()
async def db_session():
    async with TestingSessionLocal() as session:
        yield session


@pytest_asyncio.fixture()
async def client(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture(autouse=True)
async def clear_users(db_session):
    yield
    await db_session.execute(text("DELETE FROM users"))
    await db_session.commit()


@pytest.mark.asyncio
async def test_read_users(client, db_session):
    test_user = User(
        name="Test User",
        email="test_read_users@example.com",
        age=30,
        hashed_password=pwd_context.hash("secret"),
        is_active=True,
        bio="Test User",
        profile_picture=None,
    )
    db_session.add(test_user)
    await db_session.commit()
    await db_session.refresh(test_user)

    response = await client.get("/users/")

    assert response.status_code == 200
    data = response.json()
    assert "users" in data
    assert "total" in data
    assert isinstance(data["users"], list)
    assert data["total"] >= 1
    user = data["users"][0]
    assert user["id"] == test_user.id
    assert user["name"] == "Test User"
    assert user["email"] == "test_read_users@example.com"
    assert user["age"] == 30
    assert user["bio"] == "Test User"
    assert user["profilePicture"] is None
    assert user["friends"] == []


@pytest.mark.asyncio
async def test_read_user(client, db_session):
    test_user = User(
        name="Test User",
        email="test_read_user@example.com",
        age=30,
        hashed_password=pwd_context.hash("secret"),
        is_active=True,
        bio="Test User",
        profile_picture=None,
    )
    db_session.add(test_user)
    await db_session.commit()
    await db_session.refresh(test_user)

    response = await client.get(f"/users/{test_user.id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == test_user.id
    assert data["name"] == "Test User"
    assert data["email"] == "test_read_user@example.com"
    assert data["age"] == 30
    assert data["bio"] == "Test User"
    assert data["profilePicture"] is None
    assert data["friends"] == []


@pytest.mark.asyncio
async def test_create_new_user(client):
    new_user_data = {
        "name": "New User",
        "email": "test_create_new_user@example.com",
        "age": 25,
        "password": "secret",
    }

    response = await client.post("/users/", json=new_user_data)

    assert response.status_code == 200
    data = response.json()
    assert data["id"] is not None
    assert data["name"] == "New User"
    assert data["email"] == "test_create_new_user@example.com"
    assert data["age"] == 25
    assert data["bio"] in ["New User", None]
    assert data["profilePicture"] is None
    assert data["friends"] == []


@pytest.mark.asyncio
async def test_update_existing_user(client, db_session):
    test_user = User(
        name="Old User",
        email="test_update_existing_user@example.com",
        age=30,
        hashed_password=pwd_context.hash("secret"),
        is_active=True,
        bio="Old Bio",
        profile_picture=None,
    )
    db_session.add(test_user)
    await db_session.commit()
    await db_session.refresh(test_user)

    update_data = {"name": "Updated User", "email": "updated@example.com", "age": 35}

    response = await client.put(f"/users/{test_user.id}", json=update_data)

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == test_user.id
    assert data["name"] == "Updated User"
    assert data["email"] == "updated@example.com"
    assert data["age"] == 35
    assert data["bio"] in ["Updated User", "Old Bio"]
    assert data["profilePicture"] is None
    assert data["friends"] == []


@pytest.mark.asyncio
async def test_remove_user(client, db_session):
    test_user = User(
        name="User to Delete",
        email="test_remove_user@example.com",
        age=40,
        hashed_password=pwd_context.hash("secret"),
        is_active=True,
        bio="To be deleted",
        profile_picture=None,
    )
    db_session.add(test_user)
    await db_session.commit()
    await db_session.refresh(test_user)

    response = await client.delete(f"/users/{test_user.id}")

    assert response.status_code == 200
    data = response.json()
    assert data["detail"] == "User deleted successfully"

    response_get = await client.get(f"/users/{test_user.id}")
    assert response_get.status_code == 404
