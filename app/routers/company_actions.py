from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.services.company_actions import CompanyActionsService
from app.schemas.company_actions import (
    CompanyInvitationCreate,
    CompanyInvitationResponse,
    CompanyMembershipRequestResponse,
    CompanyMemberResponse
)
from app.db.models.user import User
from app.services.auth_service import AuthService

router = APIRouter(prefix="/companies", tags=["Company Actions"])

# Ендпоінти для запрошень

@router.post("/{company_id}/invite", response_model=CompanyInvitationResponse)
async def invite_user(company_id: int, invitation: CompanyInvitationCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(AuthService.get_current_user)):
    service = CompanyActionsService(db)
    return await service.send_invitation(company_id, invitation.invited_user_id, current_user)

@router.delete("/invitations/{invitation_id}", response_model=CompanyInvitationResponse)
async def cancel_invitation(invitation_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(AuthService.get_current_user)):
    service = CompanyActionsService(db)
    return await service.cancel_invitation(invitation_id, current_user)

@router.put("/invitations/{invitation_id}/accept", response_model=CompanyInvitationResponse)
async def accept_invitation(invitation_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(AuthService.get_current_user)):
    service = CompanyActionsService(db)
    return await service.accept_invitation(invitation_id, current_user)

@router.put("/invitations/{invitation_id}/decline", response_model=CompanyInvitationResponse)
async def decline_invitation(invitation_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(AuthService.get_current_user)):
    service = CompanyActionsService(db)
    return await service.decline_invitation(invitation_id, current_user)

# Ендпоінти для запитів на членство

@router.post("/{company_id}/membership-requests", response_model=CompanyMembershipRequestResponse)
async def request_membership(company_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(AuthService.get_current_user)):
    service = CompanyActionsService(db)
    return await service.request_membership(company_id, current_user)

@router.delete("/membership-requests/{request_id}", response_model=CompanyMembershipRequestResponse)
async def cancel_membership_request(request_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(AuthService.get_current_user)):
    service = CompanyActionsService(db)
    return await service.cancel_membership_request(request_id, current_user)

@router.put("/membership-requests/{request_id}/{action}", response_model=CompanyMembershipRequestResponse)
async def handle_membership_request(request_id: int, action: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(AuthService.get_current_user)):
    if action not in ["accept", "decline"]:
        raise HTTPException(status_code=400, detail="Invalid action")
    service = CompanyActionsService(db)
    return await service.handle_membership_request(request_id, action, current_user)

# Ендпоінти для управління учасниками

@router.delete("/{company_id}/members/me", response_model=dict)
async def leave_company(company_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(AuthService.get_current_user)):
    service = CompanyActionsService(db)
    return await service.leave_company(company_id, current_user)

@router.delete("/{company_id}/members/{member_user_id}", response_model=dict)
async def remove_member(company_id: int, member_user_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(AuthService.get_current_user)):
    service = CompanyActionsService(db)
    return await service.remove_member(company_id, member_user_id, current_user)



# Ендпоінти для перегляду запрошень та заявок

@router.get("/invitations/my", response_model=list[CompanyInvitationResponse])
async def get_user_invitations(db: AsyncSession = Depends(get_db), current_user: User = Depends(AuthService.get_current_user)):
    service = CompanyActionsService(db)
    return await service.get_invitations_for_user(current_user)

@router.get("/membership-requests/my", response_model=list[CompanyMembershipRequestResponse])
async def get_user_membership_requests(db: AsyncSession = Depends(get_db), current_user: User = Depends(AuthService.get_current_user)):
    service = CompanyActionsService(db)
    return await service.get_membership_requests_for_user(current_user)

@router.get("/{company_id}/invitations", response_model=list[CompanyInvitationResponse])
async def get_company_invitations(company_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(AuthService.get_current_user)):
    service = CompanyActionsService(db)
    return await service.get_invitations_for_company(company_id, current_user)

@router.get("/{company_id}/membership-requests", response_model=list[CompanyMembershipRequestResponse])
async def get_company_membership_requests(company_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(AuthService.get_current_user)):
    service = CompanyActionsService(db)
    return await service.get_membership_requests_for_company(company_id, current_user)

@router.get("/{company_id}/members", response_model=dict)
async def get_company_members(company_id: int, skip: int = 0, limit: int = 10, db: AsyncSession = Depends(get_db)):
    service = CompanyActionsService(db)
    members, total = await service.get_company_members(company_id, skip, limit)
    members_data = [CompanyMemberResponse.from_orm(member) for member in members]
    return {"members": members_data, "total": total}
