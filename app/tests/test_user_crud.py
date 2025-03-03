import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db.database import get_db
from app.routers import user as user_router


class DummyDB:
    async def execute(self, *args, **kwargs):
        return None


async def override_get_db():
    yield DummyDB()


app.dependency_overrides[get_db] = override_get_db


async def fake_get_users(db, skip: int, limit: int):
    return {
        "users": [
            {
                "id": 1,
                "name": "Test User",
                "email": "test@example.com",
                "age": 30,
                "bio": "Test User",
                "profilePicture": None,
                "friends": [],
            }
        ],
        "total": 1,
    }


async def fake_get_user(db, user_id: int):
    return {
        "id": user_id,
        "name": "Test User",
        "email": "test@example.com",
        "age": 30,
        "bio": "Test User",
        "profilePicture": None,
        "friends": [],
    }


async def fake_create_user(db, user):
    user_data = user.model_dump()
    bio = user_data.get("bio") or user_data.get("name", "Test User")
    return {
        "id": 2,
        "name": user_data.get("name", "New User"),
        "email": user_data.get("email", "test@example.com"),
        "age": user_data.get("age", 30),
        "bio": bio,
        "profilePicture": user_data.get("profile_picture", None),
        "friends": [],
    }


async def fake_update_user(db, user_id: int, user_data):
    data = user_data.model_dump()
    bio = data.get("bio") or data.get("name", "Updated User")
    return {
        "id": user_id,
        "name": data.get("name", "Updated User"),
        "email": data.get("email", "updated@example.com"),
        "age": data.get("age", 30),
        "bio": bio,
        "profilePicture": data.get("profile_picture", None),
        "friends": [],
    }


async def fake_delete_user(db, user_id: int):
    return {"detail": "User deleted"}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(user_router, "get_users", fake_get_users)
    monkeypatch.setattr(user_router, "get_user", fake_get_user)
    monkeypatch.setattr(user_router, "create_user", fake_create_user)
    monkeypatch.setattr(user_router, "update_user", fake_update_user)
    monkeypatch.setattr(user_router, "delete_user", fake_delete_user)
    return TestClient(app)


def test_read_users(client):
    response = client.get("/users/")
    assert response.status_code == 200
    data = response.json()
    assert "users" in data
    assert "total" in data
    assert isinstance(data["users"], list)
    assert data["total"] == 1
    assert len(data["users"]) == 1
    user = data["users"][0]
    assert user["id"] == 1
    assert user["name"] == "Test User"
    assert user["email"] == "test@example.com"
    assert user["age"] == 30
    assert user["bio"] == "Test User"
    assert user["profilePicture"] is None
    assert user["friends"] == []


def test_read_user(client):
    response = client.get("/users/1")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 1
    assert data["name"] == "Test User"
    assert data["email"] == "test@example.com"
    assert data["age"] == 30
    assert data["bio"] == "Test User"
    assert data["profilePicture"] is None
    assert data["friends"] == []


def test_create_new_user(client):
    new_user = {
        "name": "New User",
        "email": "new@example.com",
        "age": 25,
        "password": "secret",
    }
    response = client.post("/users/", json=new_user)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 2
    assert data["name"] == "New User"
    assert data["email"] == "new@example.com"
    assert data["age"] == 25
    assert data["bio"] == "New User"
    assert data["profilePicture"] is None
    assert data["friends"] == []


def test_update_existing_user(client):
    update_data = {"name": "Updated User", "email": "updated@example.com", "age": 35}
    response = client.put("/users/1", json=update_data)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 1
    assert data["name"] == "Updated User"
    assert data["email"] == "updated@example.com"
    assert data["age"] == 35
    assert data["bio"] == "Updated User"
    assert data["profilePicture"] is None
    assert data["friends"] == []


def test_remove_user(client):
    response = client.delete("/users/1")
    assert response.status_code == 200
    data = response.json()
    assert data["detail"] == "User deleted"
