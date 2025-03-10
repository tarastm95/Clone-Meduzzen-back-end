from pydantic import BaseModel, EmailStr, HttpUrl, Field, ConfigDict
from typing import Optional, List


class Friend(BaseModel):
    id: int
    name: str


class UserBase(BaseModel):
    name: str
    email: EmailStr
    age: Optional[int]
    bio: Optional[str] = None
    profile_picture: Optional[HttpUrl] = Field(None, alias="profilePicture")


class SignUpRequest(UserBase):
    password: str
    is_active: bool = False


class SignInRequest(BaseModel):
    email: EmailStr
    password: str


class UserUpdateRequest(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    age: Optional[int] = None
    bio: Optional[str] = None
    profile_picture: Optional[HttpUrl] = Field(None, alias="profilePicture")


class UserDetailResponse(UserBase):
    id: int
    friends: List[Friend]

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class UsersListResponse(BaseModel):
    users: List[UserDetailResponse]
    total: int
