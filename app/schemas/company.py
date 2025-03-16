from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from enum import Enum


class VisibilityEnum(str, Enum):
    hidden = "hidden"
    visible = "visible"


class CompanyBase(BaseModel):
    name: str
    description: Optional[str] = None
    location: Optional[str] = None
    employees: Optional[int] = None
    established: Optional[int] = None
    services: Optional[List[str]] = None
    visibility: Optional[VisibilityEnum] = VisibilityEnum.hidden


class CompanyCreate(CompanyBase):
    pass


class CompanyUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    employees: Optional[int] = None
    established: Optional[int] = None
    services: Optional[List[str]] = None
    visibility: Optional[VisibilityEnum] = None


class CompanyResponse(CompanyBase):
    id: int
    owner_id: int

    model_config = ConfigDict(from_attributes=True)


class CompaniesListResponse(BaseModel):
    companies: List[CompanyResponse]
    total: int
