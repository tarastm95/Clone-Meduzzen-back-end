from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from app.db.models.user import User, Auth0User
from app.schemas.user import (
    UserDetailResponse,
    UserUpdateRequest,
    SignUpRequest,
    Friend,
    UsersListResponse,
)
from passlib.context import CryptContext
from fastapi import HTTPException
from app.core.logger import logger
from typing import Dict
from sqlalchemy.exc import IntegrityError

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_users(self, skip: int = 0, limit: int = 10) -> UsersListResponse:
        result = await self.db.execute(
            select(User).options(selectinload(User.friends)).offset(skip).limit(limit)
        )
        users = result.scalars().all()

        total_result = await self.db.execute(select(User))
        total = len(total_result.scalars().all())

        return UsersListResponse(users=users, total=total)

    async def get_user(self, user_id: int) -> UserDetailResponse:
        result = await self.db.execute(
            select(User).options(selectinload(User.friends)).filter(User.id == user_id)
        )
        user = result.scalars().first()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        return UserDetailResponse(
            id=user.id,
            name=user.name,
            email=user.email,
            age=user.age,
            bio=user.bio,
            profile_picture=user.profile_picture,
            friends=[Friend(id=friend.id, name=friend.name) for friend in user.friends],
        )

    async def create_user(self, user_data: SignUpRequest) -> User:
        existing_user = await self.db.execute(
            select(User).filter(User.email == user_data.email)
        )
        if existing_user.scalars().first():
            raise HTTPException(
                status_code=400, detail="User with this email already exists"
            )

        hashed_password = pwd_context.hash(user_data.password)
        db_user = User(
            name=user_data.name,
            email=user_data.email,
            age=user_data.age,
            hashed_password=hashed_password,
            is_active=user_data.is_active,
            bio=user_data.bio,
            profile_picture=(
                str(user_data.profile_picture) if user_data.profile_picture else None
            ),
        )

        self.db.add(db_user)
        await self.db.commit()
        await self.db.refresh(db_user)

        return db_user

    async def update_user(self, user_id: int, user_data: UserUpdateRequest) -> User:
        result = await self.db.execute(select(User).filter(User.id == user_id))
        user = result.scalars().first()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        update_data = user_data.model_dump(exclude_unset=True)

        if (
            "profile_picture" in update_data
            and update_data["profile_picture"] is not None
        ):
            update_data["profile_picture"] = str(update_data["profile_picture"])

        for key, value in update_data.items():
            setattr(user, key, value)

        try:
            await self.db.commit()
        except IntegrityError as e:
            if "duplicate key value violates unique constraint" in str(e):
                raise HTTPException(status_code=400, detail="This email already exists")
            raise e

        await self.db.refresh(user)
        return user

    async def delete_user(self, user_id: int) -> Dict[str, str]:
        result = await self.db.execute(select(User).filter(User.id == user_id))
        user = result.scalars().first()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        result_auth0 = await self.db.execute(
            select(Auth0User).filter(Auth0User.user_id == user_id)
        )
        auth0_user = result_auth0.scalars().first()

        if auth0_user:
            await self.db.delete(auth0_user)

        await self.db.delete(user)
        await self.db.commit()

        return {"detail": "User deleted successfully"}
