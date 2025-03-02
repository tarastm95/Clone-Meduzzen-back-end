# test_app.py

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from schemas import (
    SignUpRequest,
    SignInRequest,
    UserUpdateRequest,
    UserDetailResponse,
    UsersListResponse,
)
from app.db.models.user import User
from app.db.database import Base


def test_signup_valid():
    data = {
        "email": "user@example.com",
        "password": "secret123",
        "is_active": True,
        "bio": "Test bio",
        "profile_picture": "http://example.com/pic.jpg",
    }
    req = SignUpRequest(**data)
    # Перевірка всіх полів за допомогою порівняння з вхідними даними
    assert req.email == data["email"]
    assert req.password == data["password"]
    assert req.is_active is True
    assert req.bio == data["bio"]
    assert str(req.profile_picture) == data["profile_picture"]


def test_signup_invalid_email():
    with pytest.raises(ValidationError):
        SignUpRequest(email="invalid-email", password="secret123")


def test_signin():
    req = SignInRequest(email="user@example.com", password="secret123")
    assert req.email == "user@example.com"
    assert req.password == "secret123"


def test_user_update_optional():
    req = UserUpdateRequest(bio="New bio")
    assert req.bio == "New bio"
    assert req.email is None
    assert req.password is None


def test_user_detail_response():
    data = {
        "id": 1,
        "email": "user@example.com",
        "is_active": True,
        "bio": "Test bio",
        "profile_picture": "http://example.com/pic.jpg",
        "friends": [],
    }
    detail = UserDetailResponse(**data)
    assert detail.id == 1
    assert str(detail.profile_picture) == data["profile_picture"]


def test_users_list_response():
    detail = UserDetailResponse(
        id=1,
        email="user@example.com",
        is_active=True,
        bio="Test bio",
        profile_picture="http://example.com/pic.jpg",
        friends=[],
    )
    response = UsersListResponse(users=[detail], total=1)
    assert response.total == 1
    assert len(response.users) == 1
    assert str(response.users[0].profile_picture) == "http://example.com/pic.jpg"


@pytest.fixture(scope="module")
def db_session():
    engine = create_engine("sqlite:///:memory:")
    SessionLocal = sessionmaker(bind=engine)
    Base.metadata.create_all(engine)

    try:
        del User.__mapper__.relationships["friends"]
    except Exception:
        pass
    session = SessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(engine)


def test_create_user(db_session):
    user = User(
        email="user1@example.com",
        hashed_password="hashedsecret",
        is_active=True,
        bio="Bio for user1",
        profile_picture="http://example.com/user1.jpg",
    )
    db_session.add(user)
    db_session.commit()
    db_user = db_session.query(User).filter_by(email="user1@example.com").first()
    assert db_user is not None
    assert db_user.email == "user1@example.com"
    assert db_user.bio == "Bio for user1"


def test_unique_email(db_session):
    user = User(
        email="duplicate@example.com", hashed_password="passdup", is_active=True
    )
    db_session.add(user)
    db_session.commit()
    dup = User(
        email="duplicate@example.com", hashed_password="anotherpass", is_active=True
    )
    db_session.add(dup)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()
