import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy import text
from passlib.context import CryptContext

from app.main import app
from app.db.database import Base, get_db
from app.db.models.company import Company
from app.db.models.user import User
from app.services.auth_service import AuthService

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False
)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture()
async def db_session():
    async with TestingSessionLocal() as session:
        yield session


@pytest_asyncio.fixture()
async def client(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture(autouse=True)
async def clear_tables(db_session):
    yield
    await db_session.execute(text("DELETE FROM companies"))
    await db_session.execute(text("DELETE FROM users"))
    await db_session.commit()


@pytest_asyncio.fixture()
async def test_owner(db_session):
    user = User(
        name="Owner User",
        email="owner@example.com",
        hashed_password=pwd_context.hash("secret"),
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture()
async def another_user(db_session):
    user = User(
        name="Another User",
        email="another@example.com",
        hashed_password=pwd_context.hash("secret"),
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


async def override_get_current_user(user):
    async def _override():
        return user

    return _override


@pytest.mark.asyncio
async def test_create_company(client, db_session, test_owner):
    company_payload = {
        "name": "Test Company",
        "description": "A company for testing",
        "location": "Kyiv, Ukraine",
        "employees": 100,
        "established": 2015,
        "services": ["Consulting", "Development", "Support"],
        "visibility": "visible",
    }
    app.dependency_overrides[AuthService.get_current_user] = lambda: test_owner

    response = await client.post("/companies/", json=company_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Company"
    assert data["description"] == "A company for testing"
    assert data["location"] == "Kyiv, Ukraine"
    assert data["employees"] == 100
    assert data["established"] == 2015
    assert data["services"] == ["Consulting", "Development", "Support"]
    assert data["visibility"] == "visible"
    assert data["owner_id"] == test_owner.id


@pytest.mark.asyncio
async def test_update_company_for_owner(client, db_session, test_owner):
    from app.db.models.company import VisibilityEnum

    company = Company(
        name="Old Company",
        description="Old Description",
        location="Lviv",
        employees=50,
        established=2010,
        services=["Old Service"],
        visibility=VisibilityEnum.hidden,
        owner_id=test_owner.id,
    )
    db_session.add(company)
    await db_session.commit()
    await db_session.refresh(company)

    app.dependency_overrides[AuthService.get_current_user] = lambda: test_owner

    update_payload = {
        "name": "Updated Company",
        "description": "Updated Description",
        "location": "Odessa",
        "employees": 75,
        "established": 2012,
        "services": ["Consulting", "Support"],
        "visibility": "visible",
    }
    response = await client.put(f"/companies/{company.id}", json=update_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Company"
    assert data["description"] == "Updated Description"
    assert data["location"] == "Odessa"
    assert data["employees"] == 75
    assert data["established"] == 2012
    assert data["services"] == ["Consulting", "Support"]
    assert data["visibility"] == "visible"


@pytest.mark.asyncio
async def test_update_company_for_non_owner(
    client, db_session, test_owner, another_user
):
    from app.db.models.company import VisibilityEnum

    company = Company(
        name="Owner's Company",
        description="Original Description",
        location="Dnipro",
        employees=80,
        established=2008,
        services=["Service1"],
        visibility=VisibilityEnum.hidden,
        owner_id=test_owner.id,
    )
    db_session.add(company)
    await db_session.commit()
    await db_session.refresh(company)

    app.dependency_overrides[AuthService.get_current_user] = lambda: another_user

    update_payload = {"name": "Hacked Company"}
    response = await client.put(f"/companies/{company.id}", json=update_payload)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_delete_company_for_owner(client, db_session, test_owner):
    company = Company(
        name="Company to Delete",
        description="To be deleted",
        location="Kharkiv",
        employees=60,
        established=2018,
        services=["ServiceX"],
        visibility="visible",
        owner_id=test_owner.id,
    )
    db_session.add(company)
    await db_session.commit()
    await db_session.refresh(company)

    app.dependency_overrides[AuthService.get_current_user] = lambda: test_owner

    response = await client.delete(f"/companies/{company.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["detail"] == "Company deleted successfully"

    response_get = await client.get(f"/companies/{company.id}")
    assert response_get.status_code == 404


@pytest.mark.asyncio
async def test_delete_company_for_non_owner(
    client, db_session, test_owner, another_user
):
    company = Company(
        name="Company to Delete",
        description="To be deleted",
        location="Zaporizhzhia",
        employees=40,
        established=2016,
        services=["ServiceY"],
        visibility="visible",
        owner_id=test_owner.id,
    )
    db_session.add(company)
    await db_session.commit()
    await db_session.refresh(company)

    app.dependency_overrides[AuthService.get_current_user] = lambda: another_user

    response = await client.delete(f"/companies/{company.id}")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_get_company_by_id(client, db_session, test_owner):
    company = Company(
        name="Lookup Company",
        description="Find me by ID",
        location="Odesa",
        employees=120,
        established=2005,
        services=["ServiceZ"],
        visibility="visible",
        owner_id=test_owner.id,
    )
    db_session.add(company)
    await db_session.commit()
    await db_session.refresh(company)

    response = await client.get(f"/companies/{company.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == company.id
    assert data["name"] == "Lookup Company"
    assert data["owner_id"] == test_owner.id


@pytest.mark.asyncio
async def test_get_companies(client, db_session, test_owner):
    companies_payload = [
        {
            "name": f"Company {i}",
            "description": f"Description of Company {i}",
            "location": "City",
            "employees": 10 * i,
            "established": 2000 + i,
            "services": [f"Service {i}"],
            "visibility": "visible",
        }
        for i in range(1, 6)
    ]
    app.dependency_overrides[AuthService.get_current_user] = lambda: test_owner

    for payload in companies_payload:
        await client.post("/companies/", json=payload)

    response = await client.get("/companies/", params={"skip": 0, "limit": 2})
    assert response.status_code == 200
    data = response.json()
    assert "companies" in data
    assert "total" in data
    assert len(data["companies"]) == 2
    assert data["total"] >= 5
