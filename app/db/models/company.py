from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Enum, JSON
from sqlalchemy.orm import relationship
from app.db.database import Base
import enum
from datetime import datetime, timezone


class VisibilityEnum(enum.Enum):
    hidden = "hidden"
    visible = "visible"


class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(Text, nullable=True)
    location = Column(String, nullable=True)
    employees = Column(Integer, nullable=True)
    established = Column(Integer, nullable=True)
    services = Column(JSON, nullable=True)
    visibility = Column(
        Enum(VisibilityEnum), default=VisibilityEnum.hidden, nullable=False
    )
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
    )

    owner = relationship("User", back_populates="companies")
