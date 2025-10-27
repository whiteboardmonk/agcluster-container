FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and package metadata
COPY requirements.txt pyproject.toml ./

# Install Python dependencies with cache mount for faster rebuilds
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

# Copy application code
COPY src/ ./src/

# Copy config files
COPY configs/ ./configs/

# Install package in development mode
RUN pip install -e .

# Expose API port
EXPOSE 8000

# Run the API server
CMD ["python", "-m", "uvicorn", "agcluster.container.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
