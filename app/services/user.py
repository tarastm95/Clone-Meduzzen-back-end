from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from app.db.models.user import User
from app.schemas.user import UserDetailResponse, UserUpdateRequest, SignUpRequest
from passlib.context import CryptContext
from fastapi import HTTPException

from app.core.logger import logger

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def get_users(db: AsyncSession, skip: int = 0, limit: int = 10):
    logger.info("Fetching users with skip=%s and limit=%s", skip, limit)

    result = await db.execute(
        select(User).options(selectinload(User.friends)).offset(skip).limit(limit)
    )
    users = result.scalars().all()

    total_result = await db.execute(select(User))
    total = len(total_result.scalars().all())

    logger.info("Fetched %s users out of total %s", len(users), total)
    return {"users": users, "total": total}


async def get_user(db: AsyncSession, user_id: int):
    logger.info("Fetching user with id=%s", user_id)

    result = await db.execute(
        select(User).options(selectinload(User.friends)).filter(User.id == user_id)
    )
    user = result.scalars().first()

    if not user:
        logger.error("User with id=%s not found", user_id)
        raise HTTPException(status_code=404, detail="User not found")

    logger.info("User with id=%s successfully fetched", user_id)
    return UserDetailResponse(
        id=user.id,
        name=user.name,
        email=user.email,
        age=user.age,
        bio=user.bio,
        profile_picture=user.profile_picture,
        friends=[Friend(id=friend.id, name=friend.name) for friend in user.friends],
    )


async def create_user(db: AsyncSession, user_data: SignUpRequest):
    logger.info("Creating user with email=%s", user_data.email)

    existing_user = await db.execute(select(User).filter(User.email == user_data.email))
    if existing_user.scalars().first():
        logger.warning("User creation failed: email %s already exists", user_data.email)
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

    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)

    logger.info(
        "User with email=%s created successfully with id=%s",
        user_data.email,
        db_user.id,
    )
    return db_user


async def update_user(db: AsyncSession, user_id: int, user_data: UserUpdateRequest):
    logger.info("Updating user with id=%s", user_id)

    result = await db.execute(select(User).filter(User.id == user_id))
    user = result.scalars().first()

    if not user:
        logger.error("Update failed: User with id=%s not found", user_id)
        raise HTTPException(status_code=404, detail="User not found")

    update_data = user_data.dict(exclude_unset=True)

    if "profile_picture" in update_data and update_data["profile_picture"] is not None:
        update_data["profile_picture"] = str(update_data["profile_picture"])

    for key, value in update_data.items():
        setattr(user, key, value)

    await db.commit()
    await db.refresh(user)

    logger.info("User with id=%s updated successfully", user_id)
    return user


async def delete_user(db: AsyncSession, user_id: int):
    logger.info("Deleting user with id=%s", user_id)

    result = await db.execute(select(User).filter(User.id == user_id))
    user = result.scalars().first()

    if not user:
        logger.error("Delete failed: User with id=%s not found", user_id)
        raise HTTPException(status_code=404, detail="User not found")

    await db.delete(user)
    await db.commit()

    logger.info("User with id=%s deleted successfully", user_id)
    return {"detail": "User deleted successfully"}
