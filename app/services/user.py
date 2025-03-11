from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from app.db.models.user import User, Auth0User
from app.schemas.user import (
    UserDetailResponse,
    UserUpdateRequest,
    SignUpRequest,
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
        logger.info("Fetching users with skip=%s and limit=%s", skip, limit)
        result = await self.db.execute(
            select(User).options(selectinload(User.friends)).offset(skip).limit(limit)
        )
        users = result.scalars().all()

        total_result = await self.db.execute(select(User))
        total = len(total_result.scalars().all())

        logger.info("Fetched %s users out of total %s", len(users), total)
        return UsersListResponse(users=users, total=total)

    async def get_user(self, user_id: int) -> UserDetailResponse:
        logger.info("Fetching user with id=%s", user_id)
        result = await self.db.execute(
            select(User).options(selectinload(User.friends)).filter(User.id == user_id)
        )
        user = result.scalars().first()

        if not user:
            logger.error("User with id=%s not found", user_id)
            raise HTTPException(status_code=404, detail="User not found")

        logger.info("User with id=%s successfully fetched", user_id)
        return UserDetailResponse.model_validate(user)

    async def create_user(self, user_data: SignUpRequest) -> User:
        logger.info("Creating user with email=%s", user_data.email)
        existing_user = await self.db.execute(
            select(User).filter(User.email == user_data.email)
        )
        if existing_user.scalars().first():
            logger.warning(
                "User creation failed: email %s already exists", user_data.email
            )
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

        logger.info(
            "User with email=%s created successfully with id=%s",
            user_data.email,
            db_user.id,
        )
        return db_user

    async def update_user(self, user_id: int, user_data: UserUpdateRequest) -> User:
        logger.info("Updating user with id=%s", user_id)
        result = await self.db.execute(select(User).filter(User.id == user_id))
        user = result.scalars().first()

        if not user:
            logger.error("Update failed: User with id=%s not found", user_id)
            raise HTTPException(status_code=404, detail="User not found")

        update_data = user_data.model_dump(exclude_unset=True)

        if "password" in update_data:
            user.hashed_password = pwd_context.hash(update_data.pop("password"))

        if update_data.get("profile_picture") is not None:
            update_data["profile_picture"] = str(update_data["profile_picture"])

        for key, value in update_data.items():
            setattr(user, key, value)

        try:
            await self.db.commit()
        except IntegrityError as e:
            if "duplicate key value violates unique constraint" in str(e):
                logger.error("Email %s already exists", update_data.get("email"))
                raise HTTPException(status_code=400, detail="This email already exists")
            raise e

        await self.db.refresh(user)
        logger.info("User with id=%s updated successfully", user_id)
        return user

    async def delete_user(self, user_id: int) -> Dict[str, str]:
        logger.info("Deleting user with id=%s", user_id)
        result = await self.db.execute(select(User).filter(User.id == user_id))
        user = result.scalars().first()

        if not user:
            logger.error("Delete failed: User with id=%s not found", user_id)
            raise HTTPException(status_code=404, detail="User not found")

        result_auth0 = await self.db.execute(
            select(Auth0User).filter(Auth0User.user_id == user_id)
        )
        auth0_user = result_auth0.scalars().first()

        if auth0_user:
            await self.db.delete(auth0_user)

        await self.db.delete(user)
        await self.db.commit()

        logger.info("User with id=%s deleted successfully", user_id)
        return {"detail": "User deleted successfully"}
