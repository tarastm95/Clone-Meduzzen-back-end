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
    # Додаємо ondelete="CASCADE" для зовнішнього ключа company_id
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(Enum(MembershipRequestStatus), default=MembershipRequestStatus.pending, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # Використовуємо back_populates замість backref
    company = relationship("Company", back_populates="membership_requests")
    user = relationship("User", back_populates="membership_requests")
