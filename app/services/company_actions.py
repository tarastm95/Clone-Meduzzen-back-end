from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi import HTTPException
from app.db.models.company_invitation import CompanyInvitation, InvitationStatus
from app.db.models.company_membership_request import CompanyMembershipRequest, MembershipRequestStatus
from app.db.models.company_member import CompanyMember
from app.db.models.company import Company
from app.db.models.user import User


class CompanyActionsService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # 1. Запрошення

    async def send_invitation(self, company_id: int, invited_user_id: int, current_user: User) -> CompanyInvitation:
        result = await self.db.execute(select(Company).filter(Company.id == company_id))
        company = result.scalars().first()
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")
        if company.owner_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to invite users to this company")

        # Перевірка, чи не існує вже активного запрошення
        existing = await self.db.execute(
            select(CompanyInvitation).filter(
                CompanyInvitation.company_id == company_id,
                CompanyInvitation.invited_user_id == invited_user_id,
                CompanyInvitation.status == InvitationStatus.pending
            )
        )
        if existing.scalars().first():
            raise HTTPException(status_code=400, detail="Invitation already sent")

        invitation = CompanyInvitation(
            company_id=company_id,
            invited_user_id=invited_user_id,
            status=InvitationStatus.pending
        )
        self.db.add(invitation)
        await self.db.commit()
        await self.db.refresh(invitation)
        return invitation

    async def cancel_invitation(self, invitation_id: int, current_user: User) -> CompanyInvitation:
        result = await self.db.execute(select(CompanyInvitation).filter(CompanyInvitation.id == invitation_id))
        invitation = result.scalars().first()
        if not invitation:
            raise HTTPException(status_code=404, detail="Invitation not found")
        # Переконуємось, що поточний користувач – власник компанії
        result_company = await self.db.execute(select(Company).filter(Company.id == invitation.company_id))
        company = result_company.scalars().first()
        if company.owner_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to cancel this invitation")
        invitation.status = InvitationStatus.cancelled
        await self.db.commit()
        await self.db.refresh(invitation)
        return invitation

    async def accept_invitation(self, invitation_id: int, current_user: User) -> CompanyInvitation:
        result = await self.db.execute(select(CompanyInvitation).filter(CompanyInvitation.id == invitation_id))
        invitation = result.scalars().first()
        if not invitation:
            raise HTTPException(status_code=404, detail="Invitation not found")
        if invitation.invited_user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to accept this invitation")
        if invitation.status != InvitationStatus.pending:
            raise HTTPException(status_code=400, detail="Invitation is not pending")

        # Додаємо користувача до членів компанії, якщо ще не є учасником
        result_member = await self.db.execute(
            select(CompanyMember).filter(
                CompanyMember.company_id == invitation.company_id,
                CompanyMember.user_id == current_user.id
            )
        )
        if not result_member.scalars().first():
            member = CompanyMember(company_id=invitation.company_id, user_id=current_user.id)
            self.db.add(member)

        invitation.status = InvitationStatus.accepted
        await self.db.commit()
        await self.db.refresh(invitation)
        return invitation

    async def decline_invitation(self, invitation_id: int, current_user: User) -> CompanyInvitation:
        result = await self.db.execute(select(CompanyInvitation).filter(CompanyInvitation.id == invitation_id))
        invitation = result.scalars().first()
        if not invitation:
            raise HTTPException(status_code=404, detail="Invitation not found")
        if invitation.invited_user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to decline this invitation")
        if invitation.status != InvitationStatus.pending:
            raise HTTPException(status_code=400, detail="Invitation is not pending")
        invitation.status = InvitationStatus.declined
        await self.db.commit()
        await self.db.refresh(invitation)
        return invitation

    # 2. Запит на членство

    async def request_membership(self, company_id: int, current_user: User) -> CompanyMembershipRequest:
        result = await self.db.execute(select(Company).filter(Company.id == company_id))
        company = result.scalars().first()
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")

        # Перевірка: якщо поточний користувач є власником компанії, то він вже є її членом
        if company.owner_id == current_user.id:
            raise HTTPException(status_code=400, detail="Company owner is already a member")

        # Перевірка, чи користувач уже є учасником
        result_member = await self.db.execute(
            select(CompanyMember).filter(
                CompanyMember.company_id == company_id,
                CompanyMember.user_id == current_user.id
            )
        )
        if result_member.scalars().first():
            raise HTTPException(status_code=400, detail="Already a member of the company")

        # Перевірка, чи вже існує запит
        existing = await self.db.execute(
            select(CompanyMembershipRequest).filter(
                CompanyMembershipRequest.company_id == company_id,
                CompanyMembershipRequest.user_id == current_user.id,
                CompanyMembershipRequest.status == MembershipRequestStatus.pending
            )
        )
        if existing.scalars().first():
            raise HTTPException(status_code=400, detail="Membership request already exists")

        membership_request = CompanyMembershipRequest(
            company_id=company_id,
            user_id=current_user.id,
            status=MembershipRequestStatus.pending
        )
        self.db.add(membership_request)
        await self.db.commit()
        await self.db.refresh(membership_request)
        return membership_request

    async def cancel_membership_request(self, request_id: int, current_user: User) -> CompanyMembershipRequest:
        result = await self.db.execute(
            select(CompanyMembershipRequest).filter(CompanyMembershipRequest.id == request_id))
        membership_request = result.scalars().first()
        if not membership_request:
            raise HTTPException(status_code=404, detail="Membership request not found")
        if membership_request.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to cancel this request")
        if membership_request.status != MembershipRequestStatus.pending:
            raise HTTPException(status_code=400, detail="Cannot cancel a non-pending request")
        membership_request.status = MembershipRequestStatus.cancelled
        await self.db.commit()
        await self.db.refresh(membership_request)
        return membership_request

    async def handle_membership_request(self, request_id: int, action: str,
                                        current_user: User) -> CompanyMembershipRequest:
        result = await self.db.execute(
            select(CompanyMembershipRequest).filter(CompanyMembershipRequest.id == request_id))
        membership_request = result.scalars().first()
        if not membership_request:
            raise HTTPException(status_code=404, detail="Membership request not found")

        result_company = await self.db.execute(select(Company).filter(Company.id == membership_request.company_id))
        company = result_company.scalars().first()
        if company.owner_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to handle membership requests for this company")

        if membership_request.status != MembershipRequestStatus.pending:
            raise HTTPException(status_code=400, detail="Membership request is not pending")

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
            membership_request.status = MembershipRequestStatus.accepted
        elif action == "decline":
            membership_request.status = MembershipRequestStatus.declined
        else:
            raise HTTPException(status_code=400, detail="Invalid action")

        await self.db.commit()
        await self.db.refresh(membership_request)
        return membership_request

    # 3. Управління учасниками

    async def remove_member(self, company_id: int, member_user_id: int, current_user: User) -> dict:
        result = await self.db.execute(select(Company).filter(Company.id == company_id))
        company = result.scalars().first()
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")
        if company.owner_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to remove members from this company")

        result_member = await self.db.execute(
            select(CompanyMember).filter(
                CompanyMember.company_id == company_id,
                CompanyMember.user_id == member_user_id
            )
        )
        member = result_member.scalars().first()
        if not member:
            raise HTTPException(status_code=404, detail="Member not found in the company")

        await self.db.delete(member)
        await self.db.commit()
        return {"detail": "Member removed successfully"}

    async def leave_company(self, company_id: int, current_user: User) -> dict:
        result_member = await self.db.execute(
            select(CompanyMember).filter(
                CompanyMember.company_id == company_id,
                CompanyMember.user_id == current_user.id
            )
        )
        member = result_member.scalars().first()
        if not member:
            raise HTTPException(status_code=404, detail="You are not a member of this company")
        await self.db.delete(member)
        await self.db.commit()
        return {"detail": "You have left the company"}

    # 4. Перегляд запитів та запрошень

    async def get_invitations_for_user(self, current_user: User) -> list[CompanyInvitation]:
        result = await self.db.execute(
            select(CompanyInvitation).filter(CompanyInvitation.invited_user_id == current_user.id)
        )
        return result.scalars().all()

    async def get_membership_requests_for_user(self, current_user: User) -> list[CompanyMembershipRequest]:
        result = await self.db.execute(
            select(CompanyMembershipRequest).filter(CompanyMembershipRequest.user_id == current_user.id)
        )
        return result.scalars().all()

    async def get_invitations_for_company(self, company_id: int, current_user: User) -> list[CompanyInvitation]:
        result = await self.db.execute(select(Company).filter(Company.id == company_id))
        company = result.scalars().first()
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")
        if company.owner_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to view invitations for this company")
        result_inv = await self.db.execute(
            select(CompanyInvitation).filter(CompanyInvitation.company_id == company_id)
        )
        return result_inv.scalars().all()

    async def get_membership_requests_for_company(self, company_id: int, current_user: User) -> list[
        CompanyMembershipRequest]:
        result = await self.db.execute(select(Company).filter(Company.id == company_id))
        company = result.scalars().first()
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")
        if company.owner_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to view membership requests for this company")
        result_req = await self.db.execute(
            select(CompanyMembershipRequest).filter(CompanyMembershipRequest.company_id == company_id)
        )
        return result_req.scalars().all()

    async def get_company_members(self, company_id: int, skip: int = 0, limit: int = 10) -> tuple[
        list[CompanyMember], int]:
        result = await self.db.execute(
            select(CompanyMember).filter(CompanyMember.company_id == company_id).offset(skip).limit(limit)
        )
        members = result.scalars().all()
        result_total = await self.db.execute(
            select(CompanyMember).filter(CompanyMember.company_id == company_id)
        )
        total = len(result_total.scalars().all())
        return members, total
