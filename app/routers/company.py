from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.services.company import CompanyService
from app.schemas.company import (
    CompanyCreate,
    CompanyUpdate,
    CompanyResponse,
    CompaniesListResponse,
)
from app.db.models.user import User
from app.services.auth_service import AuthService

router = APIRouter(prefix="/companies", tags=["Companies"])

@router.get("/", response_model=CompaniesListResponse)
async def get_companies(
    skip: int = 0, limit: int = 10, db: AsyncSession = Depends(get_db)
):
    service = CompanyService(db)
    return await service.get_companies(skip=skip, limit=limit)

@router.get("/{company_id}", response_model=CompanyResponse)
async def get_company(company_id: int, db: AsyncSession = Depends(get_db)):
    service = CompanyService(db)
    return await service.get_company(company_id)

@router.post("/", response_model=CompanyResponse)
async def create_company(
    company: CompanyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_user),
):
    service = CompanyService(db)
    return await service.create_company(company, owner_id=current_user.id)

@router.put("/{company_id}", response_model=CompanyResponse)
async def update_company(
    company_id: int,
    company: CompanyUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_user),
):
    service = CompanyService(db)
    return await service.update_company(company_id, company, current_user_id=current_user.id)

@router.delete("/{company_id}")
async def delete_company(
    company_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_user),
):
    service = CompanyService(db)
    return await service.delete_company(company_id, current_user_id=current_user.id)
