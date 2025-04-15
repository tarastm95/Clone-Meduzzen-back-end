from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.db.models.user import User
from app.schemas.auth import Token
from app.schemas.user import (
    UserDetailResponse,
    SignUpRequest,
    UserUpdateRequest,
)
from app.services.auth_service import AuthService
from app.services.user import UserService
from app.core.config import security_settings

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    auth_service = AuthService(db)
    user = await auth_service.authenticate_user(form_data.username, form_data.password)
    access_token = auth_service.create_access_token(
        data={"sub": str(user.id), "email": user.email}
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/register", response_model=UserDetailResponse)
async def register(
    user_data: SignUpRequest,
    db: AsyncSession = Depends(get_db),
):
    user_service = UserService(db)
    user = await user_service.create_user(user_data)
    return UserDetailResponse.model_validate(user)


@router.get("/me", response_model=UserDetailResponse)
async def get_me(current_user: User = Depends(AuthService.get_current_user)):
    return UserDetailResponse(
        id=current_user.id,
        name=current_user.name,
        email=current_user.email,
        age=current_user.age,
        bio=current_user.bio,
        profile_picture=current_user.profile_picture,
        friends=[
            {"id": friend.id, "name": friend.name} for friend in current_user.friends
        ],
    )


@router.post("/me", response_model=UserDetailResponse)
async def update_me(
    user_update: UserUpdateRequest,
    current_user: User = Depends(AuthService.get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user_service = UserService(db)
    updated_user = await user_service.update_user(current_user.id, user_update)
    return UserDetailResponse.model_validate(updated_user)


@router.delete("/me", response_model=dict)
async def delete_me(
    current_user: User = Depends(AuthService.get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user_service = UserService(db)
    result = await user_service.delete_user(current_user.id)
    return result
