# Description

This repository contains a backend application based on FastAPI, which uses Docker to simplify deployment and development.

## Running the Project in Docker

### 1. Installing Docker

If you haven't installed Docker yet, download and install it:

- [Docker for Windows/Mac](https://www.docker.com/products/docker-desktop)
- [Docker for Linux](https://docs.docker.com/engine/install/)

### 2. Cloning the Repository

Open your terminal and run the following commands:

```bash
git clone https://github.com/your-repo/meduzzen-back-end.git
cd meduzzen-back-end
```

### 3. Starting the Container

Use docker-compose to create and start the container:

```bash
docker-compose up --build
```

This command:

- Builds the Docker image for the application.
- Runs the application in a container.
- Opens port 8000 for access to the API.

### 4. Checking Functionality

After starting the container, the API will be available at:

http://localhost:8000

This is the Swagger UI for testing the API.

### 5. Stopping the Container

To stop the container, press Ctrl+C or run:

```bash
docker-compose down
```

## Database Integration

### PostgreSQL

The application connects to a PostgreSQL database using SQLAlchemy with AsyncSession.

- Ensure that PostgreSQL is running in Docker Compose.
- The database URL is configured in the environment variables.
- The connection is defined in `app/db/database.py`.
- A test route `/postgres-test` is available to check the connection.

### Redis Integration

The application integrates Redis for caching and session management.

- Redis is connected asynchronously using `redis.asyncio`.
- The connection is defined in `app/db/redis.py`.
- A test route `/redis-test` is available to check the connection.

## Development Environment

### Managing Development Dependencies

Development dependencies (e.g., testing libraries) are grouped under `[tool.poetry.group.dev.dependencies]`.
To add new development dependencies, use:

```bash
poetry add --group dev <package_name>
```

### Running Tests

Use pytest to run all tests:

```bash
docker-compose exec app pytest  
```

This will execute all tests in your tests folder, displaying the results. If your tests pass successfully, you will see a success message.

---

### **SQLAlchemy Models**

The file `app/db/models/user.py` contains models for users and friends:
```python
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.db.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    bio = Column(String, nullable=True)
    profile_picture = Column(String, nullable=True)

    friends = relationship("Friend", back_populates="user")

class Friend(Base):
    __tablename__ = "friends"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    friend_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    user = relationship("User", back_populates="friends", foreign_keys=[user_id])
    friend = relationship("User", foreign_keys=[friend_id])
```

---

### **Pydantic Schemas**

The file `app/schemas/user.py` contains schemas for validation and serialization:
```python
from pydantic import BaseModel, EmailStr, HttpUrl
from typing import Optional, List

class UserBase(BaseModel):
    email: EmailStr
    is_active: bool = True
    bio: Optional[str] = None
    profile_picture: Optional[HttpUrl] = None

class SignUpRequest(UserBase):
    password: str

class SignInRequest(BaseModel):
    email: EmailStr
    password: str

class UserUpdateRequest(BaseModel):
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None
    bio: Optional[str] = None
    profile_picture: Optional[HttpUrl] = None

class FriendSchema(BaseModel):
    id: int
    friend_id: int

class UserDetailResponse(UserBase):
    id: int
    friends: List[FriendSchema] = []
    class Config:
        orm_mode = True

class UsersListResponse(BaseModel):
    users: List[UserDetailResponse]
    total: int
```

---

### **Alembic Configuration**

#### **Initializing Alembic**
```sh
docker-compose run --rm app alembic init alembic
```

#### **Creating the First Migration**
```sh
docker-compose run --rm app alembic revision --autogenerate -m "Create users and friends tables"
```

#### **Applying Migrations**
```sh
docker-compose run --rm app alembic upgrade head
```

#### **Checking Tables in the Database**
```sh
docker-compose exec db psql -U postgres -d meduzzen_db -c "\dt"
```

---

### **Summary**
- **Alembic is configured for database migrations.**
- **SQLAlchemy models `User` and `Friend` have been added.**
- **Pydantic schemas have been updated for working with users and friends.**
- **The first migration has been generated and applied.**
- **The correctness of created tables in the database has been verified.**

