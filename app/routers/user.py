from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.schemas.user import (
    UserDetailResponse,
    UserUpdateRequest,
    SignUpRequest,
    UsersListResponse,
)
from app.services.user import UserService
from app.db.models.user import User
from app.services.auth_service import AuthService

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/", response_model=UsersListResponse)
async def read_users(
    skip: int = 0, limit: int = 10, db: AsyncSession = Depends(get_db)
):
    service = UserService(db)
    return await service.get_users(skip=skip, limit=limit)


@router.get("/{user_id}", response_model=UserDetailResponse)
async def read_user(user_id: int, db: AsyncSession = Depends(get_db)):
    service = UserService(db)
    return await service.get_user(user_id)


@router.post("/", response_model=UserDetailResponse)
async def create_new_user(user: SignUpRequest, db: AsyncSession = Depends(get_db)):
    service = UserService(db)
    return await service.create_user(user)


@router.put("/{user_id}", response_model=UserDetailResponse)
async def update_existing_user(
    user_id: int,
    user_data: UserUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_user),
):
    if current_user.id != user_id:
        raise HTTPException(
            status_code=403, detail="You cannot update another user's profile."
        )

    service = UserService(db)
    return await service.update_user(user_id, user_data)


@router.delete("/{user_id}")
async def remove_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_user),
):
    if current_user.id != user_id:
        raise HTTPException(
            status_code=403, detail="You cannot delete another user's profile."
        )

    service = UserService(db)
    return await service.delete_user(user_id)
