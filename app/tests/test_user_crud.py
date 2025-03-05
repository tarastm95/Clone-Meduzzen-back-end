import pytest_asyncio
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool
from app.main import app
from app.db.database import get_db, Base


SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_database():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session():
    async with TestingSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def client(db_session: AsyncSession):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_read_users(client: AsyncClient):

    response = await client.get("/users/")
    assert response.status_code == 200
    data = response.json()
    assert "users" in data
    assert isinstance(data["users"], list)


@pytest.mark.asyncio
async def test_create_new_user(client: AsyncClient):

    new_user = {
        "name": "New User",
        "email": "new@example.com",
        "age": 25,
        "password": "secret",
    }
    response = await client.post("/users/", json=new_user)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] is not None
    assert data["name"] == "New User"
    assert data["email"] == "new@example.com"
    assert data["age"] == 25


@pytest.mark.asyncio
async def test_read_user(client: AsyncClient):

    user_payload = {
        "name": "Some User",
        "email": "some@example.com",
        "age": 30,
        "password": "secret",
    }
    create_resp = await client.post("/users/", json=user_payload)
    assert create_resp.status_code == 200
    created_user = create_resp.json()
    user_id = created_user["id"]
    read_resp = await client.get(f"/users/{user_id}")
    assert read_resp.status_code == 200
    read_data = read_resp.json()
    assert read_data["id"] == user_id
    assert read_data["name"] == "Some User"
    assert read_data["email"] == "some@example.com"
    assert read_data["age"] == 30


@pytest.mark.asyncio
async def test_update_existing_user(client: AsyncClient):

    user_payload = {
        "name": "Old Name",
        "email": "old@example.com",
        "age": 20,
        "password": "secret",
    }
    create_resp = await client.post("/users/", json=user_payload)
    assert create_resp.status_code == 200
    created_user = create_resp.json()
    update_data = {"name": "Updated User", "email": "updated@example.com", "age": 35}
    user_id = created_user["id"]
    update_resp = await client.put(f"/users/{user_id}", json=update_data)
    assert update_resp.status_code == 200
    updated_user = update_resp.json()
    assert updated_user["id"] == user_id
    assert updated_user["name"] == "Updated User"
    assert updated_user["email"] == "updated@example.com"
    assert updated_user["age"] == 35


@pytest.mark.asyncio
async def test_remove_user(client: AsyncClient):

    user_payload = {
        "name": "User to Delete",
        "email": "delete@example.com",
        "age": 40,
        "password": "secret",
    }
    create_resp = await client.post("/users/", json=user_payload)
    assert create_resp.status_code == 200
    created_user = create_resp.json()
    user_id = created_user["id"]
    delete_resp = await client.delete(f"/users/{user_id}")
    assert delete_resp.status_code == 200
    data = delete_resp.json()
    assert (
        data.get("detail") == "User deleted"
        or "deleted" in data.get("detail", "").lower()
    )
