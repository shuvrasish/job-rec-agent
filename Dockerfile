FROM python:3.14-slim

# Prevent Python from creating .pyc files
ENV PYTHONDONTWRITEBYTECODE=1

# Make Python output appear immediately in Docker logs
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install uv
RUN pip install --no-cache-dir uv

# Copy dependency files first for Docker layer caching
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen

# Copy application
COPY agent ./agent
COPY main.py .
COPY resumes ./resumes

# Create data directory
RUN mkdir -p /app/data

# Run the agent
CMD ["uv", "run", "python", "main.py"]