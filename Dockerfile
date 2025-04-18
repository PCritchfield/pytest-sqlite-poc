FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install poetry==2.0.0

# Copy poetry configuration
COPY pyproject.toml poetry.lock* ./

# Configure poetry to not use virtualenvs inside container
RUN poetry config virtualenvs.create false

# Install dependencies
RUN poetry install --no-interaction --no-ansi

# Copy project files
COPY . .

# Set environment variables
ENV PYTHONPATH=/app

# Default command
CMD ["pytest"]
