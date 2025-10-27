FROM python:3.11-slim

# Install system dependencies including Node.js
RUN apt-get update && apt-get install -y \
    curl \
    git \
    ca-certificates \
    build-essential \
    procps \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install Claude Code CLI globally
RUN npm install -g @anthropic-ai/claude-code

# Create non-root user for security
RUN useradd -m -u 1000 agentuser && \
    mkdir -p /workspace /app && \
    chown -R agentuser:agentuser /workspace /app

# Copy requirements and install Python dependencies with cache mount
COPY container/requirements.txt /tmp/requirements.txt
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r /tmp/requirements.txt && \
    rm /tmp/requirements.txt

# Copy agent server
COPY container/agent_server.py /app/agent_server.py

# Switch to non-root user
USER agentuser

# Set working directory
WORKDIR /workspace

# Expose HTTP/SSE port
EXPOSE 3000

# Health check - check if HTTP endpoint is responding
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:3000/health || exit 1

# Add /app to Python path so uvicorn can find agent_server.py
ENV PYTHONPATH=/app

# Start agent server with uvicorn
CMD ["uvicorn", "agent_server:app", "--host", "0.0.0.0", "--port", "3000"]
