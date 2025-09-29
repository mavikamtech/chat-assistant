FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy packages directory to PYTHONPATH
COPY packages/ /app/packages/

# Copy application code first (required for Poetry installation)  
COPY services/mcp_servers/findb/src/ ./src/
COPY services/mcp_servers/findb/tests/ ./tests/

# Install Python dependencies
COPY services/mcp_servers/findb/pyproject.toml services/mcp_servers/findb/poetry.lock* ./
RUN pip install poetry && \
    poetry config virtualenvs.create false && \
    sed -i '/mavik-common = {path/d; /mavik-aws-clients = {path/d; /mavik-config = {path/d' pyproject.toml && \
    poetry install --only=main --no-root

# Install local packages in editable mode
RUN pip install -e /app/packages/common \
    && pip install -e /app/packages/aws_clients \
    && pip install -e /app/packages/config

# Set environment variables
ENV PYTHONPATH=/app:/app/src:/app/packages
ENV PORT=8003

# Expose port
EXPOSE 8003

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8003/health || exit 1

# Run the application
CMD ["python", "-m", "uvicorn", "src.findb_server.main:app", "--host", "0.0.0.0", "--port", "8003"]