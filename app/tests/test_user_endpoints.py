import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.db.database import Base, get_db
from app.db.models.user import User
from app.services.auth_service import AuthService
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy import text
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
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac


@pytest_asyncio.fixture(autouse=True)
async def clear_tables(db_session):
    yield
    await db_session.execute(text("DELETE FROM companies"))
    await db_session.execute(text("DELETE FROM users"))
    await db_session.commit()


@pytest_asyncio.fixture()
async def test_owner(db_session):
    user = User(
        name="Owner User",
        email="owner@example.com",
        hashed_password=pwd_context.hash("secret"),
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture()
async def another_user(db_session):
    user = User(
        name="Another User",
        email="another@example.com",
        hashed_password=pwd_context.hash("secret"),
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.mark.asyncio
async def test_update_own_profile_success(client):
    reg_payload = {
        "name": "TestUser",
        "email": "testuser@example.com",
        "password": "secret123",
        "age": 25,
        "bio": "Initial bio",
        "profilePicture": "http://example.com/pic.png",
        "is_active": True,
    }
    reg_response = await client.post("/users/", json=reg_payload)
    assert reg_response.status_code == 200
    created_user = reg_response.json()
    user_id = created_user["id"]

    login_payload = {
        "username": reg_payload["email"],
        "password": reg_payload["password"],
    }
    login_response = await client.post("/auth/login", data=login_payload)
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    update_payload = {
        "name": "UpdatedUser",
        "email": "updateduser@example.com",
        "password": "newsecret123",
        "age": 26,
        "bio": "Updated bio",
        "profilePicture": "http://example.com/newpic.png",
    }
    update_response = await client.put(
        f"/users/{user_id}", json=update_payload, headers=headers
    )
    assert update_response.status_code == 200
    updated_user = update_response.json()
    assert updated_user["name"] == "UpdatedUser"
    assert updated_user["email"] == "updateduser@example.com"
    assert updated_user["age"] == 26
    assert updated_user["bio"] == "Updated bio"
    assert updated_user["profilePicture"] == "http://example.com/newpic.png"

    new_login_payload = {
        "username": updated_user["email"],
        "password": update_payload["password"],
    }
    new_login_response = await client.post("/auth/login", data=new_login_payload)
    assert new_login_response.status_code == 200


@pytest.mark.asyncio
async def test_update_another_profile_forbidden(client):
    reg_payload1 = {
        "name": "UserOne",
        "email": "userone@example.com",
        "password": "password1",
        "age": 30,
        "bio": "Bio one",
        "profilePicture": "http://example.com/one.png",
        "is_active": True,
    }
    reg_response1 = await client.post("/users/", json=reg_payload1)
    assert reg_response1.status_code == 200
    user1 = reg_response1.json()
    user1_id = user1["id"]

    reg_payload2 = {
        "name": "UserTwo",
        "email": "usertwo@example.com",
        "password": "password2",
        "age": 35,
        "bio": "Bio two",
        "profilePicture": "http://example.com/two.png",
        "is_active": True,
    }
    reg_response2 = await client.post("/users/", json=reg_payload2)
    assert reg_response2.status_code == 200
    user2 = reg_response2.json()
    user2_id = user2["id"]

    login_payload1 = {
        "username": reg_payload1["email"],
        "password": reg_payload1["password"],
    }
    login_response1 = await client.post("/auth/login", data=login_payload1)
    assert login_response1.status_code == 200
    token1 = login_response1.json()["access_token"]
    headers1 = {"Authorization": f"Bearer {token1}"}

    update_payload = {"name": "HackedName"}
    update_response = await client.put(
        f"/users/{user2_id}", json=update_payload, headers=headers1
    )
    assert update_response.status_code == 403


@pytest.mark.asyncio
async def test_delete_own_profile_success(client, db_session):
    reg_payload = {
        "name": "DeleteUser",
        "email": "deleteuser@example.com",
        "password": "delete123",
        "age": 28,
        "bio": "Will be deleted",
        "profilePicture": "http://example.com/delete.png",
        "is_active": True,
    }
    reg_response = await client.post("/users/", json=reg_payload)
    assert reg_response.status_code == 200
    user = reg_response.json()
    user_id = user["id"]

    login_payload = {
        "username": reg_payload["email"],
        "password": reg_payload["password"],
    }
    login_response = await client.post("/auth/login", data=login_payload)
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    user_instance = await db_session.get(User, user_id)
    app.dependency_overrides[AuthService.get_current_user] = lambda: user_instance

    delete_response = await client.delete(f"/users/{user_id}", headers=headers)
    assert delete_response.status_code == 200
    assert delete_response.json()["detail"] == "User deleted successfully"


@pytest.mark.asyncio
async def test_delete_another_profile_forbidden(client):
    reg_payload1 = {
        "name": "DelUserOne",
        "email": "deluserone@example.com",
        "password": "passone",
        "age": 32,
        "bio": "User one bio",
        "profilePicture": "http://example.com/one.png",
        "is_active": True,
    }
    reg_response1 = await client.post("/users/", json=reg_payload1)
    assert reg_response1.status_code == 200
    user1 = reg_response1.json()
    user1_id = user1["id"]

    reg_payload2 = {
        "name": "DelUserTwo",
        "email": "delusertwo@example.com",
        "password": "passtwo",
        "age": 33,
        "bio": "User two bio",
        "profilePicture": "http://example.com/two.png",
        "is_active": True,
    }
    reg_response2 = await client.post("/users/", json=reg_payload2)
    assert reg_response2.status_code == 200
    user2 = reg_response2.json()
    user2_id = user2["id"]

    login_payload1 = {
        "username": reg_payload1["email"],
        "password": reg_payload1["password"],
    }
    login_response1 = await client.post("/auth/login", data=login_payload1)
    assert login_response1.status_code == 200
    token1 = login_response1.json()["access_token"]
    headers1 = {"Authorization": f"Bearer {token1}"}

    delete_response = await client.delete(f"/users/{user2_id}", headers=headers1)
    assert delete_response.status_code == 403
