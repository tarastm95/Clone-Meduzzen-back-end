from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException
from app.db.models.company import Company, VisibilityEnum
from app.schemas.company import (
    CompanyCreate,
    CompanyUpdate,
    CompanyResponse,
    CompaniesListResponse,
)
from app.core.logger import logger

class CompanyService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_companies(self, skip: int = 0, limit: int = 10) -> CompaniesListResponse:
        result = await self.db.execute(select(Company).offset(skip).limit(limit))
        companies = result.scalars().all()
        total_result = await self.db.execute(select(Company))
        total = len(total_result.scalars().all())
        company_responses = [CompanyResponse.model_validate(company) for company in companies]
        return CompaniesListResponse(companies=company_responses, total=total)

    async def get_company(self, company_id: int) -> CompanyResponse:
        result = await self.db.execute(select(Company).filter(Company.id == company_id))
        company = result.scalars().first()
        if not company:
            raise HTTPException(status_code=404, detail="error.company.notFound")
        return CompanyResponse.model_validate(company)

    async def create_company(self, company_data: CompanyCreate, owner_id: int) -> CompanyResponse:
        existing_company = await self.db.execute(
            select(Company).filter(Company.name == company_data.name)
        )
        if existing_company.scalars().first():
            raise HTTPException(status_code=400, detail="error.company.nameAlreadyExists")

        company = Company(
            name=company_data.name,
            description=company_data.description,
            location=company_data.location,
            employees=company_data.employees,
            established=company_data.established,
            services=company_data.services,
            visibility=(company_data.visibility if company_data.visibility else VisibilityEnum.hidden),
            owner_id=owner_id,
        )

        self.db.add(company)
        try:
            await self.db.commit()
            await self.db.refresh(company)
        except IntegrityError:
            await self.db.rollback()
            raise HTTPException(status_code=400, detail="error.company.nameMustBeUnique")

        return CompanyResponse.model_validate(company)

    async def update_company(self, company_id: int, company_data: CompanyUpdate, current_user_id: int) -> CompanyResponse:
        result = await self.db.execute(select(Company).filter(Company.id == company_id))
        company = result.scalars().first()
        if not company:
            raise HTTPException(status_code=404, detail="error.company.notFound")
        if company.owner_id != current_user_id:
            raise HTTPException(status_code=403, detail="error.company.notAuthorizedUpdate")

        update_data = company_data.model_dump(exclude_unset=True)

        if "name" in update_data and update_data["name"] != company.name:
            existing_company = await self.db.execute(
                select(Company).filter(Company.name == update_data["name"])
            )
            if existing_company.scalars().first():
                raise HTTPException(status_code=400, detail="error.company.nameAlreadyExists")

        for key, value in update_data.items():
            setattr(company, key, value)

        try:
            await self.db.commit()
            await self.db.refresh(company)
        except IntegrityError:
            await self.db.rollback()
            raise HTTPException(status_code=400, detail="error.company.nameMustBeUnique")

        return CompanyResponse.model_validate(company)

    async def delete_company(self, company_id: int, current_user_id: int) -> dict:
        result = await self.db.execute(select(Company).filter(Company.id == company_id))
        company = result.scalars().first()
        if not company:
            raise HTTPException(status_code=404, detail="error.company.notFound")
        if company.owner_id != current_user_id:
            raise HTTPException(status_code=403, detail="error.company.notAuthorizedDelete")

        await self.db.delete(company)
        await self.db.commit()
        return {"detail": "Company deleted successfully"}
