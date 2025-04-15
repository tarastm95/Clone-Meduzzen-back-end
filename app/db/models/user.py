from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Table
from sqlalchemy.orm import relationship
from app.db.database import Base
from app.db.timestamp_mixin import TimestampMixin
from app.db.models.company import Company
from app.db.models.company_membership_request import CompanyMembershipRequest

friends_association = Table(
    "friends",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("friend_id", Integer, ForeignKey("users.id"), primary_key=True),
)


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    auth0_sub = Column(String, unique=True, nullable=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    age = Column(Integer, nullable=True)
    hashed_password = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    bio = Column(String, nullable=True)
    profile_picture = Column(String, nullable=True)

    friends = relationship(
        "User",
        secondary=friends_association,
        primaryjoin=id == friends_association.c.user_id,
        secondaryjoin=id == friends_association.c.friend_id,
        backref="user_friends",
        lazy="selectin",
    )

    # Додаємо зв’язок для запитів на членство
    membership_requests = relationship(
        "CompanyMembershipRequest",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class Auth0User(Base):
    __tablename__ = "auth0_users"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    auth0_sub = Column(String, unique=True, nullable=False)
    email_verified = Column(Boolean, default=False)
    updated_at = Column(String, nullable=True)
    sid = Column(String, nullable=True)

    user = relationship("User", backref="auth0_data", lazy="joined")


User.companies = relationship(
    Company, back_populates="owner", cascade="all, delete-orphan"
)
