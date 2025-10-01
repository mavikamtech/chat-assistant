# Dockerfile for RAG MCP Server
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PATH="/root/.local/bin:$PATH"
ENV PYTHONPATH="/app:/app/packages:$PYTHONPATH"

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install poetry

# Copy packages directory to PYTHONPATH
COPY packages/ /app/packages/

# Copy poetry files (remove local dependencies first)
COPY services/mcp_servers/rag/pyproject.toml services/mcp_servers/rag/poetry.lock* ./

# Configure poetry
RUN poetry config virtualenvs.create false

# Copy application code first (required for Poetry installation)
COPY services/mcp_servers/rag/src/ ./src/
COPY services/mcp_servers/rag/tests/ ./tests/

# Remove local dependencies from pyproject.toml temporarily
RUN sed -i '/mavik-common = {path/d; /mavik-aws-clients = {path/d; /mavik-config = {path/d' pyproject.toml

# Install dependencies (excluding local packages)
RUN poetry install --only=main --no-interaction --no-ansi

# Install local packages in editable mode
RUN pip install -e /app/packages/common \
    && pip install -e /app/packages/aws_clients \
    && pip install -e /app/packages/config

# Create non-root user
RUN useradd --create-home --shell /bin/bash app
RUN chown -R app:app /app
USER app

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

# Expose port
EXPOSE 8001

# Run the application
CMD ["python", "-m", "uvicorn", "src.rag_server.main:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "1"]
