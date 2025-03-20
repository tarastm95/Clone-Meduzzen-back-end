from sqlalchemy import Column, Integer, ForeignKey, DateTime, Enum
from sqlalchemy.orm import relationship
from app.db.database import Base
from datetime import datetime, timezone
import enum

class MembershipRequestStatus(enum.Enum):
    pending = "pending"
    accepted = "accepted"
    declined = "declined"
    cancelled = "cancelled"

class CompanyMembershipRequest(Base):
    __tablename__ = "company_membership_requests"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(Enum(MembershipRequestStatus), default=MembershipRequestStatus.pending, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    company = relationship("Company", backref="membership_requests")
    user = relationship("User", backref="membership_requests")
