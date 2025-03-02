from pydantic import BaseModel, EmailStr, HttpUrl
from typing import Optional, List

class UserBase(BaseModel):
    email: EmailStr
    is_active: bool = True
    bio: Optional[str] = None
    profile_picture: Optional[HttpUrl] = None

class SignUpRequest(UserBase):
    password: str

class SignInRequest(BaseModel):
    email: EmailStr
    password: str

class UserUpdateRequest(BaseModel):
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None
    bio: Optional[str] = None
    profile_picture: Optional[HttpUrl] = None

class FriendSchema(BaseModel):
    id: int
    friend_id: int

class UserDetailResponse(UserBase):
    id: int
    friends: List[FriendSchema] = []

    class Config:
        orm_mode = True

class UsersListResponse(BaseModel):
    users: List[UserDetailResponse]
    total: int
