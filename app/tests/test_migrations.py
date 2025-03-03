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
        "name": "Test User",
        "email": "user@example.com",
        "age": 30,
        "password": "secret123",
        "bio": "Test bio",
        "profilePicture": "http://example.com/pic.jpg",
        "is_active": True,
    }
    req = SignUpRequest(**data)
    assert req.name == data["name"]
    assert req.email == data["email"]
    assert req.age == data["age"]
    assert req.password == data["password"]
    assert req.bio == data["bio"]
    assert req.is_active is True
    assert str(req.profile_picture) == data["profilePicture"]


def test_signup_invalid_email():
    with pytest.raises(ValidationError):
        SignUpRequest(
            name="Test User", email="invalid-email", age=25, password="secret123"
        )


def test_signin():
    req = SignInRequest(email="user@example.com", password="secret123")
    assert req.email == "user@example.com"
    assert req.password == "secret123"


def test_user_update_optional():
    req = UserUpdateRequest(bio="New bio")
    assert req.bio == "New bio"
    assert req.email is None
    assert req.password is None
    assert req.name is None
    assert req.age is None


def test_user_detail_response():
    data = {
        "id": 1,
        "name": "Test User",
        "email": "user@example.com",
        "age": 30,
        "bio": "Test bio",
        "profilePicture": "http://example.com/pic.jpg",
        "friends": [],
    }
    detail = UserDetailResponse(**data)
    assert detail.id == 1
    assert detail.name == data["name"]
    assert detail.email == data["email"]
    assert detail.age == data["age"]
    assert detail.bio == data["bio"]
    assert str(detail.profile_picture) == data["profilePicture"]


def test_users_list_response():
    detail = UserDetailResponse(
        id=1,
        name="Test User",
        email="user@example.com",
        age=30,
        bio="Test bio",
        profilePicture="http://example.com/pic.jpg",
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
        name="Test User",
        email="user1@example.com",
        age=30,
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
    assert db_user.name == "Test User"
    assert db_user.age == 30
    assert db_user.bio == "Bio for user1"
    assert db_user.profile_picture == "http://example.com/user1.jpg"


def test_unique_email(db_session):
    user = User(
        name="Unique User",
        email="duplicate@example.com",
        age=25,
        hashed_password="passdup",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    dup = User(
        name="Another User",
        email="duplicate@example.com",
        age=26,
        hashed_password="anotherpass",
        is_active=True,
    )
    db_session.add(dup)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()
