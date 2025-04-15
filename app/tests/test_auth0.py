import pytest
import pytest_asyncio
from datetime import datetime, timedelta, timezone
import jwt
from sqlalchemy import select
from app.core.config import security_settings, auth0_settings
from app.services.auth0_service import decode_and_update_db
from app.db.models.user import User
from app.db.database import AsyncSessionLocal


@pytest_asyncio.fixture
async def fake_id_token():
    fake_payload = {
        "sub": "auth0|abc123",
        "email": "newauth0@example.com",
        "name": "Auth0 User",
        "given_name": "Auth0",
        "family_name": "User",
        "picture": "http://example.com/avatar.png",
        "email_verified": True,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=30),
    }
    token = jwt.encode(
        fake_payload,
        security_settings.JWT_SECRET_KEY,
        algorithm="HS256",
        headers={"kid": "fake_kid"},
    )
    return token


@pytest_asyncio.fixture
async def token_data(fake_id_token):
    return {"id_token": fake_id_token}


@pytest.mark.asyncio
async def test_auth0_dynamic_user_creation(monkeypatch, token_data):
    def fake_find_public_key(kid: str):
        return security_settings.JWT_SECRET_KEY

    monkeypatch.setattr(
        "app.services.auth0_service.find_public_key", fake_find_public_key
    )

    from app.services import auth0_service

    original_decode = auth0_service.jwt.decode

    def fake_decode(token, key, audience, algorithms, **kwargs):
        return original_decode(
            token, key, audience=audience, algorithms=["HS256"], **kwargs
        )

    monkeypatch.setattr(auth0_service.jwt, "decode", fake_decode)

    await decode_and_update_db(token_data)

    async with AsyncSessionLocal() as session:
        stmt = select(User).where(User.email == "newauth0@example.com")
        result = await session.scalar(stmt)
        assert result is not None
        assert result.name == "Auth0 User"
