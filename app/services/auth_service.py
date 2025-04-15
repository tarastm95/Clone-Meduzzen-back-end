from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.db.database import get_db
from app.db.models.user import User
from app.core.config import security_settings
from app.schemas.auth import TokenData

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


class AuthService:

    def __init__(self, db: AsyncSession):
        self.db = db

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)

    def create_access_token(
        self, data: dict, expires_delta: Optional[timedelta] = None
    ) -> str:
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(
                minutes=security_settings.ACCESS_TOKEN_EXPIRE_MINUTES
            )
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(
            to_encode,
            security_settings.JWT_SECRET_KEY,
            algorithm=security_settings.JWT_ALGORITHM,
        )
        return encoded_jwt

    async def authenticate_user(self, email: str, password: str) -> User:
        result = await self.db.execute(select(User).filter(User.email == email))
        user = result.scalars().first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="error.auth.incorrectCredentials",
            )
        if not self.verify_password(password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="error.auth.incorrectCredentials",
            )
        return user

    @staticmethod
    async def get_current_user(
        token: str = Depends(oauth2_scheme),
        db: AsyncSession = Depends(get_db),
    ) -> User:
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="error.auth.couldNotValidate",
            headers={"WWW-Authenticate": "Bearer"},
        )
        try:
            payload = jwt.decode(
                token,
                security_settings.JWT_SECRET_KEY,
                algorithms=[security_settings.JWT_ALGORITHM],
            )
            user_id: str = payload.get("sub")
            if user_id is None:
                raise credentials_exception
        except jwt.PyJWTError:
            raise credentials_exception

        try:
            user_id_int = int(user_id)
        except ValueError:
            raise credentials_exception

        result = await db.execute(
            select(User)
            .options(selectinload(User.friends))
            .filter(User.id == user_id_int)
        )
        user = result.scalars().first()
        if user is None:
            raise credentials_exception
        return user
