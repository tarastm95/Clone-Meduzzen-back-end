from pydantic import BaseModel
from enum import Enum
from datetime import datetime

class InvitationStatus(str, Enum):
    pending = "pending"
    accepted = "accepted"
    declined = "declined"
    cancelled = "cancelled"

class MembershipRequestStatus(str, Enum):
    pending = "pending"
    accepted = "accepted"
    declined = "declined"
    cancelled = "cancelled"

# Схеми для запрошень
class CompanyInvitationCreate(BaseModel):
    invited_user_id: int

class CompanyInvitationResponse(BaseModel):
    id: int
    company_id: int
    invited_user_id: int
    status: InvitationStatus
    created_at: datetime

    class Config:
        orm_mode = True

# Схеми для заявок на членство
class CompanyMembershipRequestCreate(BaseModel):
    # Додаткових даних не потрібно, оскільки user_id визначається з поточного користувача
    pass

class CompanyMembershipRequestResponse(BaseModel):
    id: int
    company_id: int
    user_id: int
    status: MembershipRequestStatus
    created_at: datetime

    class Config:
        orm_mode = True

# Схема для членства в компанії
class CompanyMemberResponse(BaseModel):
    id: int
    company_id: int
    user_id: int
    joined_at: datetime

    class Config:
        orm_mode = True
        from_attributes = True
