import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from fastapi import HTTPException
from app.db.models.company_invitation import CompanyInvitation, InvitationStatus
from app.db.models.company_membership_request import CompanyMembershipRequest, MembershipRequestStatus
from app.db.models.company_member import CompanyMember
from app.db.models.company import Company
from app.db.models.user import User
from app.core.logger import logger

class CompanyActionsService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # Отримання компаній користувача (де користувач є власником)
    async def get_user_companies(self, owner_id: int, skip: int = 0, limit: int = 10) -> tuple[list[Company], int]:
        logger.info("get_user_companies: Fetching companies for owner %s with skip=%s and limit=%s", owner_id, skip, limit)
        query = select(Company).filter(Company.owner_id == owner_id).offset(skip).limit(limit)
        result = await self.db.execute(query)
        companies = result.scalars().all()
        total_query = select(Company).filter(Company.owner_id == owner_id)
        total_result = await self.db.execute(total_query)
        total = len(total_result.scalars().all())
        logger.info("get_user_companies: Found %s companies (total %s) for owner %s", len(companies), total, owner_id)
        return companies, total

    # 1. Запрошення
    async def send_invitation(self, company_id: int, invited_user_id: int, current_user: User) -> CompanyInvitation:
        logger.info("send_invitation: User %s requests to invite user %s to company %s", current_user.id, invited_user_id, company_id)
        result = await self.db.execute(select(Company).filter(Company.id == company_id))
        company = result.scalars().first()
        if not company:
            logger.error("send_invitation: Company %s not found", company_id)
            raise HTTPException(status_code=404, detail="error.company.notFound")
        if company.owner_id != current_user.id:
            logger.error("send_invitation: User %s is not owner of company %s", current_user.id, company_id)
            # Використовуємо загальний ключ "forbidden" для неавторизованої дії
            raise HTTPException(status_code=403, detail="error.forbidden")
        existing = await self.db.execute(
            select(CompanyInvitation).filter(
                CompanyInvitation.company_id == company_id,
                CompanyInvitation.invited_user_id == invited_user_id,
                CompanyInvitation.status == InvitationStatus.pending
            )
        )
        if existing.scalars().first():
            logger.error("send_invitation: Invitation already exists for user %s in company %s", invited_user_id, company_id)
            raise HTTPException(status_code=400, detail="error.invitation.alreadySent")
        invitation = CompanyInvitation(
            company_id=company_id,
            invited_user_id=invited_user_id,
            status=InvitationStatus.pending
        )
        self.db.add(invitation)
        await self.db.commit()
        await self.db.refresh(invitation)
        logger.info("send_invitation: Invitation created with id %s", invitation.id)
        return invitation

    async def cancel_invitation(self, invitation_id: int, current_user: User) -> CompanyInvitation:
        logger.info("cancel_invitation: User %s requests to cancel invitation %s", current_user.id, invitation_id)
        result = await self.db.execute(select(CompanyInvitation).filter(CompanyInvitation.id == invitation_id))
        invitation = result.scalars().first()
        if not invitation:
            logger.error("cancel_invitation: Invitation %s not found", invitation_id)
            raise HTTPException(status_code=404, detail="error.invitation.notFound")
        result_company = await self.db.execute(select(Company).filter(Company.id == invitation.company_id))
        company = result_company.scalars().first()
        if company.owner_id != current_user.id:
            logger.error("cancel_invitation: User %s is not authorized to cancel invitation for company %s", current_user.id, invitation.company_id)
            raise HTTPException(status_code=403, detail="error.invitation.notAuthorizedCancel")
        invitation.status = InvitationStatus.cancelled
        await self.db.commit()
        await self.db.refresh(invitation)
        logger.info("cancel_invitation: Invitation %s cancelled", invitation_id)
        return invitation

    async def accept_invitation(self, invitation_id: int, current_user: User) -> CompanyInvitation:
        logger.info("accept_invitation: User %s requests to accept invitation %s", current_user.id, invitation_id)
        result = await self.db.execute(select(CompanyInvitation).filter(CompanyInvitation.id == invitation_id))
        invitation = result.scalars().first()
        if not invitation:
            logger.error("accept_invitation: Invitation %s not found", invitation_id)
            raise HTTPException(status_code=404, detail="error.invitation.notFound")
        if invitation.invited_user_id != current_user.id:
            logger.error("accept_invitation: User %s is not authorized to accept invitation %s", current_user.id, invitation_id)
            raise HTTPException(status_code=403, detail="error.invitation.notAuthorizedAccept")
        if invitation.status != InvitationStatus.pending:
            logger.error("accept_invitation: Invitation %s is not pending", invitation_id)
            raise HTTPException(status_code=400, detail="error.invitation.notPending")
        result_member = await self.db.execute(
            select(CompanyMember).filter(
                CompanyMember.company_id == invitation.company_id,
                CompanyMember.user_id == current_user.id
            )
        )
        if not result_member.scalars().first():
            member = CompanyMember(company_id=invitation.company_id, user_id=current_user.id)
            self.db.add(member)
            logger.info("accept_invitation: Added user %s as member to company %s", current_user.id, invitation.company_id)
        invitation.status = InvitationStatus.accepted
        await self.db.commit()
        await self.db.refresh(invitation)
        logger.info("accept_invitation: Invitation %s accepted", invitation_id)
        return invitation

    async def decline_invitation(self, invitation_id: int, current_user: User) -> CompanyInvitation:
        logger.info("decline_invitation: User %s requests to decline invitation %s", current_user.id, invitation_id)
        result = await self.db.execute(select(CompanyInvitation).filter(CompanyInvitation.id == invitation_id))
        invitation = result.scalars().first()
        if not invitation:
            logger.error("decline_invitation: Invitation %s not found", invitation_id)
            raise HTTPException(status_code=404, detail="error.invitation.notFound")
        if invitation.invited_user_id != current_user.id:
            logger.error("decline_invitation: User %s is not authorized to decline invitation %s", current_user.id, invitation_id)
            raise HTTPException(status_code=403, detail="error.invitation.notAuthorizedDecline")
        if invitation.status != InvitationStatus.pending:
            logger.error("decline_invitation: Invitation %s is not pending", invitation_id)
            raise HTTPException(status_code=400, detail="error.invitation.notPending")
        invitation.status = InvitationStatus.declined
        await self.db.commit()
        await self.db.refresh(invitation)
        logger.info("decline_invitation: Invitation %s declined", invitation_id)
        return invitation

    # 2. Запит на членство
    async def request_membership(self, company_id: int, current_user: User) -> CompanyMembershipRequest:
        logger.info("request_membership: User %s requests membership for company %s", current_user.id, company_id)
        result = await self.db.execute(select(Company).filter(Company.id == company_id))
        company = result.scalars().first()
        if not company:
            logger.error("request_membership: Company %s not found", company_id)
            raise HTTPException(status_code=404, detail="error.company.notFound")
        if company.owner_id == current_user.id:
            logger.error("request_membership: User %s is owner of company %s and cannot request membership", current_user.id, company_id)
            raise HTTPException(status_code=400, detail="error.membership.companyOwnerIsMember")
        result_member = await self.db.execute(
            select(CompanyMember).filter(
                CompanyMember.company_id == company_id,
                CompanyMember.user_id == current_user.id
            )
        )
        if result_member.scalars().first():
            logger.error("request_membership: User %s is already a member of company %s", current_user.id, company_id)
            raise HTTPException(status_code=400, detail="error.membership.alreadyMember")
        existing = await self.db.execute(
            select(CompanyMembershipRequest).filter(
                CompanyMembershipRequest.company_id == company_id,
                CompanyMembershipRequest.user_id == current_user.id,
                CompanyMembershipRequest.status == MembershipRequestStatus.pending
            )
        )
        if existing.scalars().first():
            logger.error("request_membership: Membership request already exists for user %s in company %s", current_user.id, company_id)
            raise HTTPException(status_code=400, detail="error.membership.alreadyRequested")
        membership_request = CompanyMembershipRequest(
            company_id=company_id,
            user_id=current_user.id,
            status=MembershipRequestStatus.pending
        )
        self.db.add(membership_request)
        await self.db.commit()
        await self.db.refresh(membership_request)
        logger.info("request_membership: Membership request created with id %s", membership_request.id)
        return membership_request

    async def cancel_membership_request(self, request_id: int, current_user: User) -> CompanyMembershipRequest:
        logger.info("cancel_membership_request: User %s requests cancellation of membership request %s", current_user.id, request_id)
        result = await self.db.execute(
            select(CompanyMembershipRequest).filter(CompanyMembershipRequest.id == request_id)
        )
        membership_request = result.scalars().first()
        if not membership_request:
            logger.error("cancel_membership_request: Membership request %s not found", request_id)
            raise HTTPException(status_code=404, detail="error.membership.notFound")
        if membership_request.user_id != current_user.id:
            logger.error("cancel_membership_request: User %s is not authorized to cancel membership request %s", current_user.id, request_id)
            raise HTTPException(status_code=403, detail="error.membership.notAuthorizedCancel")
        if membership_request.status != MembershipRequestStatus.pending:
            logger.error("cancel_membership_request: Cannot cancel non-pending membership request %s", request_id)
            raise HTTPException(status_code=400, detail="error.membership.cannotCancelNonPending")
        membership_request.status = MembershipRequestStatus.cancelled
        await self.db.commit()
        await self.db.refresh(membership_request)
        logger.info("cancel_membership_request: Membership request %s cancelled", request_id)
        return membership_request

    async def handle_membership_request(self, request_id: int, action: str, current_user: User) -> CompanyMembershipRequest:
        logger.info("handle_membership_request: User %s handles membership request %s with action '%s'", current_user.id, request_id, action)
        result = await self.db.execute(
            select(CompanyMembershipRequest).filter(CompanyMembershipRequest.id == request_id)
        )
        membership_request = result.scalars().first()
        if not membership_request:
            logger.error("handle_membership_request: Membership request %s not found", request_id)
            raise HTTPException(status_code=404, detail="error.membership.notFound")
        if membership_request.company_id is None:
            logger.error("handle_membership_request: Membership request %s has null company_id", request_id)
            raise HTTPException(status_code=500, detail="error.membership.internalErrorNullCompanyId")
        result_company = await self.db.execute(select(Company).filter(Company.id == membership_request.company_id))
        company = result_company.scalars().first()
        if not company:
            logger.error("handle_membership_request: Company with id %s not found", membership_request.company_id)
            raise HTTPException(status_code=404, detail="error.company.notFound")
        if company.owner_id != current_user.id:
            logger.error("handle_membership_request: User %s is not authorized to handle requests for company %s", current_user.id, membership_request.company_id)
            raise HTTPException(status_code=403, detail="error.membership.notAuthorizedHandle")
        if membership_request.status != MembershipRequestStatus.pending:
            logger.error("handle_membership_request: Membership request %s is not pending", request_id)
            raise HTTPException(status_code=400, detail="error.membership.notPending")
        if action == "accept":
            result_member = await self.db.execute(
                select(CompanyMember).filter(
                    CompanyMember.company_id == membership_request.company_id,
                    CompanyMember.user_id == membership_request.user_id
                )
            )
            if not result_member.scalars().first():
                member = CompanyMember(company_id=membership_request.company_id, user_id=membership_request.user_id)
                self.db.add(member)
                logger.info("handle_membership_request: Added user %s as member to company %s", membership_request.user_id, membership_request.company_id)
            membership_request.status = MembershipRequestStatus.accepted
        elif action == "decline":
            membership_request.status = MembershipRequestStatus.declined
        else:
            logger.error("handle_membership_request: Invalid action '%s'", action)
            raise HTTPException(status_code=400, detail="error.membership.invalidAction")
        await self.db.commit()
        await self.db.refresh(membership_request)
        logger.info("handle_membership_request: Membership request %s handled with status %s", request_id, membership_request.status)
        return membership_request

    # 3. Управління учасниками
    async def remove_member(self, company_id: int, member_user_id: int, current_user: User) -> dict:
        logger.info("remove_member: User %s requests to remove member %s from company %s", current_user.id, member_user_id, company_id)
        result = await self.db.execute(select(Company).filter(Company.id == company_id))
        company = result.scalars().first()
        if not company:
            logger.error("remove_member: Company %s not found", company_id)
            raise HTTPException(status_code=404, detail="error.company.notFound")
        if company.owner_id != current_user.id:
            logger.error("remove_member: User %s is not authorized to remove members from company %s", current_user.id, company_id)
            raise HTTPException(status_code=403, detail="error.member.notAuthorizedRemove")
        result_member = await self.db.execute(
            select(CompanyMember).filter(
                CompanyMember.company_id == company_id,
                CompanyMember.user_id == member_user_id
            )
        )
        member = result_member.scalars().first()
        if not member:
            logger.error("remove_member: Member %s not found in company %s", member_user_id, company_id)
            raise HTTPException(status_code=404, detail="error.member.notFound")
        await self.db.delete(member)
        await self.db.commit()
        logger.info("remove_member: Member %s removed from company %s", member_user_id, company_id)
        return {"detail": "Member removed successfully"}

    async def leave_company(self, company_id: int, current_user: User) -> dict:
        logger.info("leave_company: User %s requests to leave company %s", current_user.id, company_id)
        result_member = await self.db.execute(
            select(CompanyMember).filter(
                CompanyMember.company_id == company_id,
                CompanyMember.user_id == current_user.id
            )
        )
        member = result_member.scalars().first()
        if not member:
            logger.error("leave_company: User %s is not a member of company %s", current_user.id, company_id)
            raise HTTPException(status_code=404, detail="error.member.notAMember")
        await self.db.delete(member)
        await self.db.commit()
        logger.info("leave_company: User %s has left company %s", current_user.id, company_id)
        return {"detail": "You have left the company"}

    async def get_invitations_for_user(self, current_user: User) -> list[CompanyInvitation]:
        logger.info("get_invitations_for_user: Fetching invitations for user %s", current_user.id)
        result = await self.db.execute(
            select(CompanyInvitation).filter(CompanyInvitation.invited_user_id == current_user.id)
        )
        invitations = result.scalars().all()
        logger.info("get_invitations_for_user: Found %s invitations", len(invitations))
        return invitations

    async def get_membership_requests_for_user(self, current_user: User) -> list[CompanyMembershipRequest]:
        logger.info("get_membership_requests_for_user: Fetching membership requests for user %s", current_user.id)
        result = await self.db.execute(
            select(CompanyMembershipRequest)
            .filter(CompanyMembershipRequest.user_id == current_user.id)
            .options(selectinload(CompanyMembershipRequest.company))
        )
        requests = result.scalars().all()
        logger.info("get_membership_requests_for_user: Found %s membership requests", len(requests))
        return requests

    async def get_invitations_for_company(self, company_id: int, current_user: User) -> list[CompanyInvitation]:
        logger.info("get_invitations_for_company: User %s requests invitations for company %s", current_user.id, company_id)
        result = await self.db.execute(select(Company).filter(Company.id == company_id))
        company = result.scalars().first()
        if not company:
            logger.error("get_invitations_for_company: Company %s not found", company_id)
            raise HTTPException(status_code=404, detail="error.company.notFound")
        if company.owner_id != current_user.id:
            logger.error("get_invitations_for_company: User %s is not authorized to view invitations for company %s", current_user.id, company_id)
            raise HTTPException(status_code=403, detail="error.forbidden")
        result_inv = await self.db.execute(
            select(CompanyInvitation).filter(CompanyInvitation.company_id == company_id)
        )
        invitations = result_inv.scalars().all()
        logger.info("get_invitations_for_company: Found %s invitations for company %s", len(invitations), company_id)
        return invitations

    async def get_membership_requests_for_company(self, company_id: int, current_user: User) -> list[CompanyMembershipRequest]:
        logger.info("get_membership_requests_for_company: User %s requests membership requests for company %s", current_user.id, company_id)
        result = await self.db.execute(select(Company).filter(Company.id == company_id))
        company = result.scalars().first()
        if not company:
            logger.error("get_membership_requests_for_company: Company %s not found", company_id)
            raise HTTPException(status_code=404, detail="error.company.notFound")
        if company.owner_id != current_user.id:
            logger.error("get_membership_requests_for_company: User %s is not authorized to view membership requests for company %s", current_user.id, company_id)
            raise HTTPException(status_code=403, detail="error.forbidden")
        result_req = await self.db.execute(
            select(CompanyMembershipRequest).filter(CompanyMembershipRequest.company_id == company_id)
        )
        requests = result_req.scalars().all()
        logger.info("get_membership_requests_for_company: Found %s membership requests for company %s", len(requests), company_id)
        return requests

    async def get_company_members(self, company_id: int, skip: int = 0, limit: int = 10) -> tuple[list[CompanyMember], int]:
        logger.info("get_company_members: Fetching members for company %s with skip=%s and limit=%s", company_id, skip, limit)
        result = await self.db.execute(
            select(CompanyMember).filter(CompanyMember.company_id == company_id).offset(skip).limit(limit)
        )
        members = result.scalars().all()
        result_total = await self.db.execute(
            select(CompanyMember).filter(CompanyMember.company_id == company_id)
        )
        total = len(result_total.scalars().all())
        logger.info("get_company_members: Found %s members (total %s) for company %s", len(members), total, company_id)
        return members, total

    async def get_companies_where_user_is_member(self, current_user: User) -> list:
        logger.info("get_companies_where_user_is_member: Fetching companies for user %s", current_user.id)
        result = await self.db.execute(
            select(Company)
            .join(CompanyMember)
            .filter(CompanyMember.user_id == current_user.id, Company.owner_id != current_user.id)
        )
        companies = result.scalars().all()
        logger.info("get_companies_where_user_is_member: Found %s companies for user %s", len(companies), current_user.id)
        return companies
