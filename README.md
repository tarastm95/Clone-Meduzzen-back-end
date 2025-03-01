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

http\://localhost:8000

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
- The connection is defined in app/db/database.py.
- A test route /postgres-test is available to check the connection.

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

