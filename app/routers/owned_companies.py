from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.services.company import CompanyService
from app.services.company_actions import CompanyActionsService
from app.schemas.company import CompanyCreate, CompanyUpdate, CompanyResponse
from app.db.models.user import User
from app.services.auth_service import AuthService
from app.core.logger import logger

router = APIRouter(prefix="/companies/owned", tags=["Owned Companies"])

@router.get("/", response_model=dict)
async def get_owned_companies(
    skip: int = 0,
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_user)
):
    logger.info("GET /companies/owned: Current user %s requested owned companies", current_user.id)
    service = CompanyActionsService(db)
    companies, total = await service.get_user_companies(current_user.id, skip, limit)
    companies_data = [CompanyResponse.from_orm(company) for company in companies]
    return {"companies": companies_data, "total": total}

@router.post("/", response_model=CompanyResponse)
async def create_owned_company(
    company: CompanyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_user)
):
    logger.info("POST /companies/owned: User %s is creating a company", current_user.id)
    service = CompanyService(db)
    return await service.create_company(company, owner_id=current_user.id)

@router.put("/{company_id}", response_model=CompanyResponse)
async def update_owned_company(
    company_id: int,
    company: CompanyUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_user)
):
    logger.info("PUT /companies/owned/%s: User %s is updating company", company_id, current_user.id)
    service = CompanyService(db)
    return await service.update_company(company_id, company, current_user_id=current_user.id)

@router.delete("/{company_id}", response_model=dict)
async def delete_owned_company(
    company_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_user)
):
    logger.info("DELETE /companies/owned/%s: User %s is deleting company", company_id, current_user.id)
    service = CompanyService(db)
    return await service.delete_company(company_id, current_user_id=current_user.id)
