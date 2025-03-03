from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.schemas.user import (
    UserDetailResponse,
    UserUpdateRequest,
    SignUpRequest,
    UsersListResponse,
)
from app.services.user import get_users, get_user, create_user, update_user, delete_user

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/", response_model=UsersListResponse)
async def read_users(
    skip: int = 0, limit: int = 10, db: AsyncSession = Depends(get_db)
):
    return await get_users(db, skip=skip, limit=limit)


@router.get("/{user_id}", response_model=UserDetailResponse)
async def read_user(user_id: int, db: AsyncSession = Depends(get_db)):
    return await get_user(db, user_id)


@router.post("/", response_model=UserDetailResponse)
async def create_new_user(user: SignUpRequest, db: AsyncSession = Depends(get_db)):
    return await create_user(db, user)


@router.put("/{user_id}", response_model=UserDetailResponse)
async def update_existing_user(
    user_id: int, user_data: UserUpdateRequest, db: AsyncSession = Depends(get_db)
):
    return await update_user(db, user_id, user_data)


@router.delete("/{user_id}")
async def remove_user(user_id: int, db: AsyncSession = Depends(get_db)):
    return await delete_user(db, user_id)
