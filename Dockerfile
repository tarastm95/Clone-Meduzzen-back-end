# Using the slim version of the Python 3.13 image
FROM python:3.13-slim

# Installing dependencies for git and the virtual environment
RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

# Setting up the working directory
WORKDIR /app

# Copying Poetry configuration files
COPY pyproject.toml poetry.lock ./

# Installing Poetry
RUN pip install --no-cache-dir poetry

# Installing dependencies
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --no-root

# Copying all project files
COPY . .

# Exposing the port
EXPOSE 8000

# Command to run the application
CMD ["sh", "-c", "python prestart.py && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"]
