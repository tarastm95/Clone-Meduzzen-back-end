from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.services.company_actions import CompanyActionsService
from app.schemas.company_actions import (
    CompanyInvitationCreate,
    CompanyInvitationResponse,
    CompanyMembershipRequestResponse,
    CompanyMembershipRequestDetailResponse,
    CompanyMemberResponse
)
from app.schemas.company import CompanyResponse  # Для нового маршруту
from app.db.models.user import User
from app.services.auth_service import AuthService
from app.core.logger import logger

router = APIRouter(prefix="/companies", tags=["Company Actions"])

# --- Ендпоінти для запрошень ---
@router.post("/{company_id}/invite", response_model=CompanyInvitationResponse)
async def invite_user(
        company_id: int,
        invitation: CompanyInvitationCreate,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(AuthService.get_current_user)
):
    logger.info("Endpoint invite_user called with company_id=%s, invited_user_id=%s, current_user=%s", company_id, invitation.invited_user_id, current_user.id)
    service = CompanyActionsService(db)
    result = await service.send_invitation(company_id, invitation.invited_user_id, current_user)
    logger.info("Invitation created with id=%s", result.id)
    return result

@router.delete("/invitations/{invitation_id}", response_model=CompanyInvitationResponse)
async def cancel_invitation(
        invitation_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(AuthService.get_current_user)
):
    logger.info("Endpoint cancel_invitation called with invitation_id=%s, current_user=%s", invitation_id, current_user.id)
    service = CompanyActionsService(db)
    result = await service.cancel_invitation(invitation_id, current_user)
    logger.info("Invitation %s cancelled", invitation_id)
    return result

@router.put("/invitations/{invitation_id}/accept", response_model=CompanyInvitationResponse)
async def accept_invitation(
        invitation_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(AuthService.get_current_user)
):
    logger.info("Endpoint accept_invitation called with invitation_id=%s, current_user=%s", invitation_id, current_user.id)
    service = CompanyActionsService(db)
    result = await service.accept_invitation(invitation_id, current_user)
    logger.info("Invitation %s accepted", invitation_id)
    return result

@router.put("/invitations/{invitation_id}/decline", response_model=CompanyInvitationResponse)
async def decline_invitation(
        invitation_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(AuthService.get_current_user)
):
    logger.info("Endpoint decline_invitation called with invitation_id=%s, current_user=%s", invitation_id, current_user.id)
    service = CompanyActionsService(db)
    result = await service.decline_invitation(invitation_id, current_user)
    logger.info("Invitation %s declined", invitation_id)
    return result

# --- Ендпоінти для запитів на членство ---
@router.post("/{company_id}/membership-requests", response_model=CompanyMembershipRequestResponse)
async def request_membership(
        company_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(AuthService.get_current_user)
):
    logger.info("Endpoint request_membership called with company_id=%s, current_user=%s", company_id, current_user.id)
    service = CompanyActionsService(db)
    result = await service.request_membership(company_id, current_user)
    logger.info("Membership request created with id=%s for company_id=%s", result.id, company_id)
    return result

@router.get("/membership-requests/my", response_model=list[CompanyMembershipRequestDetailResponse])
async def get_user_membership_requests(
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(AuthService.get_current_user)
):
    logger.info("Endpoint get_user_membership_requests called for current_user=%s", current_user.id)
    service = CompanyActionsService(db)
    result = await service.get_membership_requests_for_user(current_user)
    logger.info("Found %s membership requests for user %s", len(result), current_user.id)
    return result

@router.delete("/membership-requests/{request_id}", response_model=CompanyMembershipRequestResponse)
async def cancel_membership_request(
        request_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(AuthService.get_current_user)
):
    logger.info("Endpoint cancel_membership_request called with request_id=%s, current_user=%s", request_id, current_user.id)
    service = CompanyActionsService(db)
    result = await service.cancel_membership_request(request_id, current_user)
    logger.info("Membership request %s cancelled", request_id)
    return result

@router.put("/membership-requests/{request_id}/{action}", response_model=CompanyMembershipRequestResponse)
async def handle_membership_request(
        request_id: int,
        action: str,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(AuthService.get_current_user)
):
    logger.info("Endpoint handle_membership_request called with request_id=%s, action=%s, current_user=%s", request_id, action, current_user.id)
    if action not in ["accept", "decline"]:
        logger.error("handle_membership_request: Invalid action %s", action)
        raise HTTPException(status_code=400, detail="Invalid action")
    service = CompanyActionsService(db)
    result = await service.handle_membership_request(request_id, action, current_user)
    logger.info("Membership request %s handled with action %s", request_id, action)
    return result

# --- Ендпоінти для управління учасниками ---
@router.delete("/{company_id}/members/me", response_model=dict)
async def leave_company(
        company_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(AuthService.get_current_user)
):
    logger.info("Endpoint leave_company called with company_id=%s, current_user=%s", company_id, current_user.id)
    service = CompanyActionsService(db)
    result = await service.leave_company(company_id, current_user)
    logger.info("User %s left company %s", current_user.id, company_id)
    return result

@router.delete("/{company_id}/members/{member_user_id}", response_model=dict)
async def remove_member(
        company_id: int,
        member_user_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(AuthService.get_current_user)
):
    logger.info("Endpoint remove_member called with company_id=%s, member_user_id=%s, current_user=%s", company_id, member_user_id, current_user.id)
    service = CompanyActionsService(db)
    result = await service.remove_member(company_id, member_user_id, current_user)
    logger.info("Member %s removed from company %s by user %s", member_user_id, company_id, current_user.id)
    return result

# --- Ендпоінти для перегляду запрошень та заявок ---
@router.get("/invitations/my", response_model=list[CompanyInvitationResponse])
async def get_user_invitations(
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(AuthService.get_current_user)
):
    logger.info("Endpoint get_user_invitations called for current_user=%s", current_user.id)
    service = CompanyActionsService(db)
    result = await service.get_invitations_for_user(current_user)
    logger.info("Found %s invitations for user %s", len(result), current_user.id)
    return result

@router.get("/{company_id}/invitations", response_model=list[CompanyInvitationResponse])
async def get_company_invitations(
        company_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(AuthService.get_current_user)
):
    logger.info("Endpoint get_company_invitations called with company_id=%s, current_user=%s", company_id, current_user.id)
    service = CompanyActionsService(db)
    result = await service.get_invitations_for_company(company_id, current_user)
    logger.info("Found %s invitations for company %s", len(result), company_id)
    return result

@router.get("/{company_id}/membership-requests", response_model=list[CompanyMembershipRequestResponse])
async def get_company_membership_requests(
        company_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(AuthService.get_current_user)
):
    logger.info("Endpoint get_company_membership_requests called with company_id=%s, current_user=%s", company_id, current_user.id)
    service = CompanyActionsService(db)
    result = await service.get_membership_requests_for_company(company_id, current_user)
    logger.info("Found %s membership requests for company %s", len(result), company_id)
    return result

@router.get("/{company_id}/members", response_model=dict)
async def get_company_members(
        company_id: int,
        skip: int = 0,
        limit: int = 10,
        db: AsyncSession = Depends(get_db)
):
    logger.info("Endpoint get_company_members called with company_id=%s, skip=%s, limit=%s", company_id, skip, limit)
    service = CompanyActionsService(db)
    members, total = await service.get_company_members(company_id, skip, limit)
    logger.info("Returning %s members out of total %s for company %s", len(members), total, company_id)
    members_data = [CompanyMemberResponse.from_orm(member) for member in members]
    return {"members": members_data, "total": total}

# --- Додатковий маршрут для отримання компаній, де користувач є учасником (але не власником) ---
@router.get("/members/me", response_model=list[CompanyResponse])
async def get_companies_for_member(
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(AuthService.get_current_user)
):
    logger.info("Endpoint get_companies_for_member called for current_user=%s", current_user.id)
    service = CompanyActionsService(db)
    result = await service.get_companies_where_user_is_member(current_user)
    logger.info("Found %s companies where user %s is a member", len(result), current_user.id)
    return result
